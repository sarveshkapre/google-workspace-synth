from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime
from typing import List
from uuid import uuid4

from faker import Faker

from .config import seed_value
from .db import get_connection, init_db


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _random_cells(rng: random.Random) -> dict[str, str]:
    cells = {}
    for row in range(1, 6):
        for col in range(1, 4):
            cell = f"{chr(64 + col)}{row}"
            cells[cell] = str(rng.randint(1, 500))
    return cells


def seed_database(
    users: int,
    groups: int,
    folders: int,
    docs: int,
    sheets: int,
    seed: int | None,
) -> None:
    init_db()
    rng = random.Random(seed)
    faker = Faker()
    if seed is not None:
        Faker.seed(seed)

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        if existing:
            return

        user_rows: List[dict[str, str]] = []
        for _ in range(users):
            user_id = str(uuid4())
            row = {
                "id": user_id,
                "email": faker.unique.email(),
                "display_name": faker.name(),
                "created_at": _now(),
            }
            conn.execute(
                "INSERT INTO users (id, email, display_name, created_at) VALUES (?, ?, ?, ?)",
                (row["id"], row["email"], row["display_name"], row["created_at"]),
            )
            user_rows.append(row)

        group_rows: List[dict[str, str]] = []
        for _ in range(groups):
            group_id = str(uuid4())
            row = {
                "id": group_id,
                "name": faker.unique.company()[:60],
                "description": faker.catch_phrase()[:120],
                "created_at": _now(),
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
                    (str(uuid4()), group["id"], user["id"], _now()),
                )

        root_id = str(uuid4())
        now = _now()
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
            (root_id, "Shared Drive", "folder", None, None, None, None, now, now),
        )

        folders_rows: List[dict[str, str]] = []
        for _ in range(folders):
            owner = rng.choice(user_rows)
            folder_id = str(uuid4())
            now = _now()
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
                    root_id,
                    owner["id"],
                    None,
                    None,
                    now,
                    now,
                ),
            )
            folders_rows.append({"id": folder_id, "owner_user_id": owner["id"]})

        all_parents = [root_id] + [f["id"] for f in folders_rows]
        items: List[dict[str, str]] = []

        for _ in range(docs):
            owner = rng.choice(user_rows)
            parent_id = rng.choice(all_parents)
            item_id = str(uuid4())
            now = _now()
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
                    now,
                    now,
                ),
            )
            items.append({"id": item_id, "owner_user_id": owner["id"]})

        for _ in range(sheets):
            owner = rng.choice(user_rows)
            parent_id = rng.choice(all_parents)
            item_id = str(uuid4())
            now = _now()
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
                    now,
                    now,
                ),
            )
            items.append({"id": item_id, "owner_user_id": owner["id"]})

        all_items = items + folders_rows
        for item in all_items:
            if item.get("owner_user_id"):
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
                    (str(uuid4()), item["id"], "user", item["owner_user_id"], "owner", _now()),
                )
            if rng.random() < 0.3 and group_rows:
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
                        item["id"],
                        "group",
                        group["id"],
                        rng.choice(["viewer", "editor"]),
                        _now(),
                    ),
                )
            if rng.random() < 0.2:
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
                    (str(uuid4()), item["id"], "anyone", None, "viewer", _now()),
                )
            if rng.random() < 0.2:
                conn.execute(
                    """
                    INSERT INTO share_links (id, item_id, token, role, expires_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid4()),
                        item["id"],
                        f"seed-{rng.randint(100000, 999999)}",
                        "viewer",
                        None,
                        _now(),
                    ),
                )
            if rng.random() < 0.1 and user_rows:
                commenter = rng.choice(user_rows)
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
                        _now(),
                    ),
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Google Workspace Synth data")
    parser.add_argument("--users", type=int, default=25)
    parser.add_argument("--groups", type=int, default=6)
    parser.add_argument("--folders", type=int, default=12)
    parser.add_argument("--docs", type=int, default=30)
    parser.add_argument("--sheets", type=int, default=20)
    args = parser.parse_args()
    seed_database(
        users=args.users,
        groups=args.groups,
        folders=args.folders,
        docs=args.docs,
        sheets=args.sheets,
        seed=seed_value(),
    )


if __name__ == "__main__":
    main()
