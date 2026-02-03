from __future__ import annotations

from dataclasses import dataclass
from typing import Any

GROUP_TAG_PREFIX = "gwsynth_run:"


@dataclass
class UserSyncResult:
    email: str
    created: bool = False
    updated: bool = False
    skipped: bool = False
    conflict: bool = False


@dataclass
class GroupSyncResult:
    email: str
    created: bool = False
    updated: bool = False
    skipped: bool = False
    conflict: bool = False


def ensure_org_unit(service: Any, customer_id: str, ou_path: str, *, dry_run: bool) -> bool:
    if org_unit_exists(service, customer_id, ou_path):
        return False
    if dry_run:
        return True
    create_org_unit(service, customer_id, ou_path)
    return True


def org_unit_exists(service: Any, customer_id: str, ou_path: str) -> bool:
    try:
        service.orgunits().get(customerId=customer_id, orgUnitPath=ou_path).execute()
        return True
    except Exception as exc:
        if _is_http_error(exc, 404):
            return False
        raise


def create_org_unit(service: Any, customer_id: str, ou_path: str) -> None:
    parent_path, name = _split_ou_path(ou_path)
    body = {"name": name, "parentOrgUnitPath": parent_path}
    service.orgunits().insert(customerId=customer_id, body=body).execute()


def _split_ou_path(path: str) -> tuple[str, str]:
    stripped = path.strip()
    if not stripped.startswith("/"):
        raise ValueError("OU path must start with '/'")
    parts = [p for p in stripped.split("/") if p]
    if not parts:
        raise ValueError("OU path cannot be root")
    name = parts[-1]
    parent = "/" + "/".join(parts[:-1]) if len(parts) > 1 else "/"
    return parent, name


def get_user(service: Any, email: str) -> dict[str, Any] | None:
    try:
        result = service.users().get(userKey=email).execute()
        if isinstance(result, dict):
            return result
        return None
    except Exception as exc:
        if _is_http_error(exc, 404):
            return None
        raise


def ensure_user(
    service: Any,
    *,
    email: str,
    display_name: str,
    department: str,
    job_title: str,
    ou_path: str,
    dry_run: bool,
) -> UserSyncResult:
    existing = get_user(service, email)
    if existing:
        if existing.get("orgUnitPath") != ou_path:
            return UserSyncResult(email=email, conflict=True)
        if dry_run:
            return UserSyncResult(email=email, updated=True)
        payload = _user_payload(email, display_name, department, job_title, ou_path)
        service.users().patch(userKey=email, body=payload).execute()
        return UserSyncResult(email=email, updated=True)
    if dry_run:
        return UserSyncResult(email=email, created=True)
    payload = _user_payload(email, display_name, department, job_title, ou_path)
    payload["password"] = _random_password()
    payload["changePasswordAtNextLogin"] = False
    service.users().insert(body=payload).execute()
    return UserSyncResult(email=email, created=True)


def _user_payload(
    email: str, display_name: str, department: str, job_title: str, ou_path: str
) -> dict[str, Any]:
    given, family = _split_name(display_name)
    body: dict[str, Any] = {
        "primaryEmail": email,
        "name": {"givenName": given, "familyName": family},
        "orgUnitPath": ou_path,
    }
    if department or job_title:
        body["organizations"] = [
            {
                "department": department,
                "title": job_title,
                "primary": True,
                "type": "work",
            }
        ]
    return body


def _split_name(display_name: str) -> tuple[str, str]:
    parts = [p for p in display_name.split(" ") if p]
    if not parts:
        return ("Synthetic", "User")
    if len(parts) == 1:
        return (parts[0], "User")
    return (parts[0], " ".join(parts[1:]))


def _random_password() -> str:
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(20))


def get_group(service: Any, group_email: str) -> dict[str, Any] | None:
    try:
        result = service.groups().get(groupKey=group_email).execute()
        if isinstance(result, dict):
            return result
        return None
    except Exception as exc:
        if _is_http_error(exc, 404):
            return None
        raise


def ensure_group(
    service: Any,
    *,
    group_email: str,
    display_name: str,
    description: str,
    run_name: str,
    dry_run: bool,
) -> GroupSyncResult:
    existing = get_group(service, group_email)
    if existing:
        if not _has_group_tag(str(existing.get("description") or ""), run_name):
            return GroupSyncResult(email=group_email, conflict=True)
        if dry_run:
            return GroupSyncResult(email=group_email, updated=True)
        payload = {
            "name": display_name,
            "description": _tag_description(description, run_name),
        }
        service.groups().patch(groupKey=group_email, body=payload).execute()
        return GroupSyncResult(email=group_email, updated=True)
    if dry_run:
        return GroupSyncResult(email=group_email, created=True)
    payload = {
        "email": group_email,
        "name": display_name,
        "description": _tag_description(description, run_name),
    }
    service.groups().insert(body=payload).execute()
    return GroupSyncResult(email=group_email, created=True)


def sync_group_members(
    service: Any,
    *,
    group_email: str,
    members: list[str],
    run_name: str,
    dry_run: bool,
) -> int:
    group = get_group(service, group_email)
    if not group:
        return 0
    if not _has_group_tag(str(group.get("description") or ""), run_name):
        return 0
    existing_members = _list_group_members(service, group_email)
    to_add = [email for email in members if email not in existing_members]
    if dry_run:
        return len(to_add)
    for email in to_add:
        body = {"email": email, "role": "MEMBER"}
        try:
            service.members().insert(groupKey=group_email, body=body).execute()
        except Exception as exc:
            if _is_http_error(exc, 409):
                continue
            raise
    return len(to_add)


def _list_group_members(service: Any, group_email: str) -> list[str]:
    members: list[str] = []
    token: str | None = None
    while True:
        resp = service.members().list(groupKey=group_email, pageToken=token).execute()
        for member in resp.get("members", []) or []:
            email = str(member.get("email") or "").strip()
            if email:
                members.append(email)
        token = resp.get("nextPageToken")
        if not token:
            break
    return members


def _tag_description(description: str, run_name: str) -> str:
    tag = f"{GROUP_TAG_PREFIX}{run_name}"
    if tag in description:
        return description
    suffix = f" [{tag}]"
    return (description + suffix).strip()


def _has_group_tag(description: str, run_name: str) -> bool:
    return f"{GROUP_TAG_PREFIX}{run_name}" in description


def _is_http_error(exc: Exception, status: int) -> bool:
    resp = getattr(exc, "resp", None)
    code = getattr(resp, "status", None)
    return code == status
