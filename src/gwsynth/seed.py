from __future__ import annotations

import argparse
import json
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import List
from uuid import uuid4

from faker import Faker

from .config import seed_value
from .db import get_connection, init_db


@dataclass(frozen=True)
class SeedProfile:
    name: str
    drive_names: tuple[str, ...]
    group_names: tuple[str, ...]


ENGINEERING_PROFILE = SeedProfile(
    name="engineering",
    drive_names=(
        "Engineering",
        "Product",
        "Security",
        "Design",
        "Operations",
    ),
    group_names=(
        "Platform Engineering",
        "Application Engineering",
        "Security",
        "SRE",
        "Product",
        "Design",
    ),
)


DEFAULT_PROFILE = SeedProfile(
    name="default",
    drive_names=(
        "Shared Drive",
        "Team Projects",
        "Operations",
    ),
    group_names=(
        "All Hands",
        "Leadership",
        "Sales",
        "Support",
    ),
)


def _now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime) -> str:
    return value.isoformat()


def _random_cells(rng: random.Random) -> dict[str, str]:
    cells = {}
    for row in range(1, 6):
        for col in range(1, 4):
            cell = f"{chr(64 + col)}{row}"
            cells[cell] = str(rng.randint(1, 500))
    return cells


def _company_domain(company_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "", company_name.lower())
    return f"{slug}.example.com" if slug else "example.com"


def _unique_emails(
    faker: Faker, domain: str, count: int, rng: random.Random
) -> list[str]:
    emails: list[str] = []
    seen: set[str] = set()
    while len(emails) < count:
        handle = faker.user_name()
        handle = re.sub(r"[^a-z0-9_.-]+", "", handle.lower()) or "user"
        if rng.random() < 0.2:
            handle = f"{handle}{rng.randint(1, 999)}"
        email = f"{handle}@{domain}"
        if email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def _pick_profile(name: str) -> SeedProfile:
    lowered = name.strip().lower()
    if lowered == ENGINEERING_PROFILE.name:
        return ENGINEERING_PROFILE
    return DEFAULT_PROFILE


def _drive_names(
    rng: random.Random,
    faker: Faker,
    profile: SeedProfile,
    shared_drives: int,
    company_name: str,
) -> list[str]:
    names: list[str] = []
    for base in profile.drive_names:
        names.append(f"{company_name} {base}")
        if len(names) >= shared_drives:
            return names[:shared_drives]
    while len(names) < shared_drives:
        names.append(f"{company_name} {faker.bs().title()}")
    return names


def _random_past_timestamp(rng: random.Random, days: int) -> datetime:
    return _now() - timedelta(
        days=rng.randint(1, max(days, 1)),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )


def _later_timestamp(rng: random.Random, base: datetime, max_days: int) -> datetime:
    candidate = base + timedelta(
        days=rng.randint(0, max_days),
        hours=rng.randint(0, 23),
        minutes=rng.randint(0, 59),
    )
    return min(candidate, _now())


def _json_dumps(data: dict[str, str | list[str] | None]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def _record_activity(
    conn,
    *,
    item_id: str,
    event_type: str,
    actor_user_id: str | None,
    data: dict[str, str | list[str] | None],
    created_at: datetime,
) -> None:
    conn.execute(
        """
        INSERT INTO activities (id, item_id, event_type, actor_user_id, data_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            item_id,
            event_type,
            actor_user_id,
            _json_dumps(data),
            _isoformat(created_at),
        ),
    )


def seed_database(
    users: int,
    groups: int,
    folders: int,
    docs: int,
    sheets: int,
    seed: int | None,
    *,
    shared_drives: int = 2,
    personal_drives: bool = True,
    personal_docs: int = 2,
    personal_sheets: int = 1,
    company_name: str | None = None,
    domain: str | None = None,
    profile: str = "engineering",
    history_days: int = 90,
) -> None:
    init_db()
    rng = random.Random(seed)
    faker = Faker()
    if seed is not None:
        Faker.seed(seed)
    selected_profile = _pick_profile(profile)

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        if existing:
            return
        company_name = company_name or faker.company()
        domain = domain or _company_domain(company_name)
        email_pool = _unique_emails(faker, domain, users, rng)

        user_rows: List[dict[str, str]] = []
        for i in range(users):
            user_id = str(uuid4())
            display_name = faker.name()
            row = {
                "id": user_id,
                "email": email_pool[i],
                "display_name": display_name,
                "created_at": _isoformat(_random_past_timestamp(rng, history_days)),
            }
            conn.execute(
                "INSERT INTO users (id, email, display_name, created_at) VALUES (?, ?, ?, ?)",
                (row["id"], row["email"], row["display_name"], row["created_at"]),
            )
            user_rows.append(row)

        group_rows: List[dict[str, str]] = []
        group_names = list(selected_profile.group_names)
        while len(group_names) < groups:
            group_names.append(faker.bs().title())
        for name in group_names[:groups]:
            group_id = str(uuid4())
            row = {
                "id": group_id,
                "name": name[:60],
                "description": faker.catch_phrase()[:120],
                "created_at": _isoformat(_random_past_timestamp(rng, history_days)),
            }
            conn.execute(
                "INSERT INTO groups (id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (row["id"], row["name"], row["description"], row["created_at"]),
            )
            group_rows.append(row)

        for group in group_rows:
            for user in rng.sample(user_rows, k=min(len(user_rows), rng.randint(1, 5))):
                conn.execute(
                    "INSERT INTO group_members (id, group_id, user_id, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        group["id"],
                        user["id"],
                        _isoformat(_random_past_timestamp(rng, history_days)),
                    ),
                )

        shared_drive_names = _drive_names(
            rng,
            faker,
            selected_profile,
            max(shared_drives, 1),
            company_name,
        )
        shared_drive_rows: List[dict[str, str]] = []
        for drive_name in shared_drive_names:
            drive_id = str(uuid4())
            created_at = _random_past_timestamp(rng, history_days)
            updated_at = _later_timestamp(rng, created_at, 30)
            conn.execute(
                """
                INSERT INTO items (
                    id,
                    name,
                    item_type,
                    parent_id,
                    owner_user_id,
                    content_text,
                    content_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    drive_id,
                    drive_name[:80],
                    "folder",
                    None,
                    None,
                    None,
                    None,
                    _isoformat(created_at),
                    _isoformat(updated_at),
                ),
            )
            shared_drive_rows.append(
                {"id": drive_id, "created_at": _isoformat(created_at)}
            )
            _record_activity(
                conn,
                item_id=drive_id,
                event_type="item.created",
                actor_user_id=None,
                data={"name": drive_name},
                created_at=created_at,
            )
            if group_rows:
                group = rng.choice(group_rows)
                conn.execute(
                    """
                    INSERT INTO permissions (
                        id,
                        item_id,
                        principal_type,
                        principal_id,
                        role,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        drive_id,
                        "group",
                        group["id"],
                        "editor",
                        _isoformat(created_at),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=drive_id,
                    event_type="permission.created",
                    actor_user_id=None,
                    data={
                        "principal_type": "group",
                        "principal_id": group["id"],
                        "role": "editor",
                    },
                    created_at=created_at,
                )

        personal_drive_rows: List[dict[str, str]] = []
        if personal_drives:
            for user in user_rows:
                drive_id = str(uuid4())
                created_at = _random_past_timestamp(rng, history_days)
                updated_at = _later_timestamp(rng, created_at, 7)
                drive_name = f"My Drive - {user['display_name']}"
                conn.execute(
                    """
                    INSERT INTO items (
                        id,
                        name,
                        item_type,
                        parent_id,
                        owner_user_id,
                        content_text,
                        content_json,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        drive_id,
                        drive_name[:80],
                        "folder",
                        None,
                        user["id"],
                        None,
                        None,
                        _isoformat(created_at),
                        _isoformat(updated_at),
                    ),
                )
                personal_drive_rows.append(
                    {
                        "id": drive_id,
                        "owner_user_id": user["id"],
                        "created_at": _isoformat(created_at),
                        "skip_owner_permission": True,
                    }
                )
                _record_activity(
                    conn,
                    item_id=drive_id,
                    event_type="item.created",
                    actor_user_id=user["id"],
                    data={"name": drive_name},
                    created_at=created_at,
                )
                conn.execute(
                    """
                    INSERT INTO permissions (
                        id,
                        item_id,
                        principal_type,
                        principal_id,
                        role,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        drive_id,
                        "user",
                        user["id"],
                        "owner",
                        _isoformat(created_at),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=drive_id,
                    event_type="permission.created",
                    actor_user_id=user["id"],
                    data={
                        "principal_type": "user",
                        "principal_id": user["id"],
                        "role": "owner",
                    },
                    created_at=created_at,
                )

        folders_rows: List[dict[str, str]] = []
        for _ in range(folders):
            owner = rng.choice(user_rows)
            folder_id = str(uuid4())
            created_at = _random_past_timestamp(rng, history_days)
            updated_at = _later_timestamp(rng, created_at, 30)
            parent_id = rng.choice(shared_drive_rows)["id"]
            conn.execute(
                """
                INSERT INTO items (
                    id,
                    name,
                    item_type,
                    parent_id,
                    owner_user_id,
                    content_text,
                    content_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    folder_id,
                    faker.bs().title()[:80],
                    "folder",
                    parent_id,
                    owner["id"],
                    None,
                    None,
                    _isoformat(created_at),
                    _isoformat(updated_at),
                ),
            )
            folders_rows.append(
                {
                    "id": folder_id,
                    "owner_user_id": owner["id"],
                    "created_at": _isoformat(created_at),
                }
            )
            _record_activity(
                conn,
                item_id=folder_id,
                event_type="item.created",
                actor_user_id=owner["id"],
                data={"parent_id": parent_id},
                created_at=created_at,
            )

        shared_parents = [d["id"] for d in shared_drive_rows] + [
            f["id"] for f in folders_rows
        ]
        items: List[dict[str, str]] = []

        for _ in range(docs):
            owner = rng.choice(user_rows)
            parent_id = rng.choice(shared_parents)
            item_id = str(uuid4())
            created_at = _random_past_timestamp(rng, history_days)
            updated_at = _later_timestamp(rng, created_at, 20)
            conn.execute(
                """
                INSERT INTO items (
                    id,
                    name,
                    item_type,
                    parent_id,
                    owner_user_id,
                    content_text,
                    content_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    faker.sentence(nb_words=4)[:80],
                    "doc",
                    parent_id,
                    owner["id"],
                    faker.paragraph(nb_sentences=3),
                    None,
                    _isoformat(created_at),
                    _isoformat(updated_at),
                ),
            )
            items.append(
                {
                    "id": item_id,
                    "owner_user_id": owner["id"],
                    "created_at": _isoformat(created_at),
                }
            )
            _record_activity(
                conn,
                item_id=item_id,
                event_type="item.created",
                actor_user_id=owner["id"],
                data={"parent_id": parent_id},
                created_at=created_at,
            )
            if updated_at > created_at:
                _record_activity(
                    conn,
                    item_id=item_id,
                    event_type="item.content_updated",
                    actor_user_id=owner["id"],
                    data={"fields": ["content_text"]},
                    created_at=updated_at,
                )

        for _ in range(sheets):
            owner = rng.choice(user_rows)
            parent_id = rng.choice(shared_parents)
            item_id = str(uuid4())
            created_at = _random_past_timestamp(rng, history_days)
            updated_at = _later_timestamp(rng, created_at, 20)
            conn.execute(
                """
                INSERT INTO items (
                    id,
                    name,
                    item_type,
                    parent_id,
                    owner_user_id,
                    content_text,
                    content_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    faker.sentence(nb_words=3)[:80],
                    "sheet",
                    parent_id,
                    owner["id"],
                    None,
                    json.dumps(_random_cells(rng)),
                    _isoformat(created_at),
                    _isoformat(updated_at),
                ),
            )
            items.append(
                {
                    "id": item_id,
                    "owner_user_id": owner["id"],
                    "created_at": _isoformat(created_at),
                }
            )
            _record_activity(
                conn,
                item_id=item_id,
                event_type="item.created",
                actor_user_id=owner["id"],
                data={"parent_id": parent_id},
                created_at=created_at,
            )
            if updated_at > created_at:
                _record_activity(
                    conn,
                    item_id=item_id,
                    event_type="item.content_updated",
                    actor_user_id=owner["id"],
                    data={"fields": ["sheet_data"]},
                    created_at=updated_at,
                )

        personal_items: List[dict[str, str]] = []
        if personal_drives and personal_drive_rows:
            for drive in personal_drive_rows:
                owner = next(u for u in user_rows if u["id"] == drive["owner_user_id"])
                for _ in range(personal_docs):
                    item_id = str(uuid4())
                    created_at = _random_past_timestamp(rng, history_days)
                    updated_at = _later_timestamp(rng, created_at, 10)
                    conn.execute(
                        """
                        INSERT INTO items (
                            id,
                            name,
                            item_type,
                            parent_id,
                            owner_user_id,
                            content_text,
                            content_json,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item_id,
                            faker.sentence(nb_words=4)[:80],
                            "doc",
                            drive["id"],
                            owner["id"],
                            faker.paragraph(nb_sentences=2),
                            None,
                            _isoformat(created_at),
                            _isoformat(updated_at),
                        ),
                    )
                    personal_items.append(
                        {
                            "id": item_id,
                            "owner_user_id": owner["id"],
                            "created_at": _isoformat(created_at),
                        }
                    )
                    _record_activity(
                        conn,
                        item_id=item_id,
                        event_type="item.created",
                        actor_user_id=owner["id"],
                        data={"parent_id": drive["id"]},
                        created_at=created_at,
                    )
                    if updated_at > created_at:
                        _record_activity(
                            conn,
                            item_id=item_id,
                            event_type="item.content_updated",
                            actor_user_id=owner["id"],
                            data={"fields": ["content_text"]},
                            created_at=updated_at,
                        )
                for _ in range(personal_sheets):
                    item_id = str(uuid4())
                    created_at = _random_past_timestamp(rng, history_days)
                    updated_at = _later_timestamp(rng, created_at, 10)
                    conn.execute(
                        """
                        INSERT INTO items (
                            id,
                            name,
                            item_type,
                            parent_id,
                            owner_user_id,
                            content_text,
                            content_json,
                            created_at,
                            updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item_id,
                            faker.sentence(nb_words=3)[:80],
                            "sheet",
                            drive["id"],
                            owner["id"],
                            None,
                            json.dumps(_random_cells(rng)),
                            _isoformat(created_at),
                            _isoformat(updated_at),
                        ),
                    )
                    personal_items.append(
                        {
                            "id": item_id,
                            "owner_user_id": owner["id"],
                            "created_at": _isoformat(created_at),
                        }
                    )
                    _record_activity(
                        conn,
                        item_id=item_id,
                        event_type="item.created",
                        actor_user_id=owner["id"],
                        data={"parent_id": drive["id"]},
                        created_at=created_at,
                    )
                    if updated_at > created_at:
                        _record_activity(
                            conn,
                            item_id=item_id,
                            event_type="item.content_updated",
                            actor_user_id=owner["id"],
                            data={"fields": ["sheet_data"]},
                            created_at=updated_at,
                        )

        all_items = (
            items + folders_rows + personal_items + personal_drive_rows + shared_drive_rows
        )
        for item in all_items:
            if item.get("owner_user_id") and not item.get("skip_owner_permission"):
                permission_created = _later_timestamp(
                    rng,
                    datetime.fromisoformat(item["created_at"]),
                    30,
                )
                conn.execute(
                    """
                    INSERT INTO permissions (
                        id,
                        item_id,
                        principal_type,
                        principal_id,
                        role,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        item["id"],
                        "user",
                        item["owner_user_id"],
                        "owner",
                        _isoformat(permission_created),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=item["id"],
                    event_type="permission.created",
                    actor_user_id=item["owner_user_id"],
                    data={
                        "principal_type": "user",
                        "principal_id": item["owner_user_id"],
                        "role": "owner",
                    },
                    created_at=permission_created,
                )
            if rng.random() < 0.3 and group_rows:
                group = rng.choice(group_rows)
                permission_created = _later_timestamp(
                    rng,
                    datetime.fromisoformat(item["created_at"]),
                    30,
                )
                role = rng.choice(["viewer", "editor"])
                conn.execute(
                    """
                    INSERT INTO permissions (
                        id,
                        item_id,
                        principal_type,
                        principal_id,
                        role,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        item["id"],
                        "group",
                        group["id"],
                        role,
                        _isoformat(permission_created),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=item["id"],
                    event_type="permission.created",
                    actor_user_id=None,
                    data={
                        "principal_type": "group",
                        "principal_id": group["id"],
                        "role": role,
                    },
                    created_at=permission_created,
                )
            if rng.random() < 0.2:
                permission_created = _later_timestamp(
                    rng,
                    datetime.fromisoformat(item["created_at"]),
                    30,
                )
                conn.execute(
                    """
                    INSERT INTO permissions (
                        id,
                        item_id,
                        principal_type,
                        principal_id,
                        role,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        item["id"],
                        "anyone",
                        None,
                        "viewer",
                        _isoformat(permission_created),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=item["id"],
                    event_type="permission.created",
                    actor_user_id=None,
                    data={
                        "principal_type": "anyone",
                        "principal_id": None,
                        "role": "viewer",
                    },
                    created_at=permission_created,
                )
            if rng.random() < 0.2:
                link_created = _later_timestamp(
                    rng,
                    datetime.fromisoformat(item["created_at"]),
                    30,
                )
                token = f"seed-{rng.randint(100000, 999999)}"
                conn.execute(
                    """
                    INSERT INTO share_links (id, item_id, token, role, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        item["id"],
                        token,
                        "viewer",
                        None,
                        _isoformat(link_created),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=item["id"],
                    event_type="share_link.created",
                    actor_user_id=None,
                    data={"token": token, "role": "viewer"},
                    created_at=link_created,
                )
            if rng.random() < 0.1 and user_rows:
                commenter = rng.choice(user_rows)
                comment_created = _later_timestamp(
                    rng,
                    datetime.fromisoformat(item["created_at"]),
                    30,
                )
                conn.execute(
                    """
                    INSERT INTO comments (id, item_id, author_user_id, body, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        item["id"],
                        commenter["id"],
                        faker.sentence(nb_words=12),
                        _isoformat(comment_created),
                    ),
                )
                _record_activity(
                    conn,
                    item_id=item["id"],
                    event_type="comment.created",
                    actor_user_id=commenter["id"],
                    data={"author_user_id": commenter["id"]},
                    created_at=comment_created,
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Google Workspace Synth data")
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--groups", type=int, default=6)
    parser.add_argument("--folders", type=int, default=12)
    parser.add_argument("--docs", type=int, default=30)
    parser.add_argument("--sheets", type=int, default=20)
    parser.add_argument("--shared-drives", type=int, default=2)
    parser.add_argument("--personal-drives", action="store_true", default=True)
    parser.add_argument("--no-personal-drives", action="store_false", dest="personal_drives")
    parser.add_argument("--personal-docs", type=int, default=2)
    parser.add_argument("--personal-sheets", type=int, default=1)
    parser.add_argument("--company-name", type=str, default=None)
    parser.add_argument("--domain", type=str, default=None)
    parser.add_argument("--profile", type=str, default="engineering")
    parser.add_argument("--history-days", type=int, default=90)
    args = parser.parse_args()
    seed_database(
        users=args.users,
        groups=args.groups,
        folders=args.folders,
        docs=args.docs,
        sheets=args.sheets,
        seed=seed_value(),
        shared_drives=args.shared_drives,
        personal_drives=args.personal_drives,
        personal_docs=args.personal_docs,
        personal_sheets=args.personal_sheets,
        company_name=args.company_name,
        domain=args.domain,
        profile=args.profile,
        history_days=args.history_days,
    )


if __name__ == "__main__":
    main()
