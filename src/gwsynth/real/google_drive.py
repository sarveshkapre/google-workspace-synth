from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

DOC_MIME_TYPE = "application/vnd.google-apps.document"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


@dataclass
class DriveSyncResult:
    name: str
    drive_id: str | None
    created: bool = False
    conflict: bool = False


def build_app_properties(
    *,
    run_name: str,
    stable_id: str,
    kind: str,
    path: str,
    prompt_version: str | None = None,
    content_hash: str | None = None,
) -> dict[str, str]:
    props = {
        "gwsynth_run": run_name,
        "gwsynth_id": stable_id,
        "gwsynth_kind": kind,
        "gwsynth_path": path,
    }
    if prompt_version:
        props["gwsynth_prompt_version"] = prompt_version
    if content_hash:
        props["gwsynth_content_hash"] = content_hash
    return props


def ensure_shared_drive(
    service: Any,
    *,
    drive_name: str,
    request_id: str,
    dry_run: bool,
) -> DriveSyncResult:
    existing = _find_drive_by_name(service, drive_name)
    if existing:
        drive_id = existing["id"]
        return DriveSyncResult(name=drive_name, drive_id=drive_id, conflict=True)
    if dry_run:
        return DriveSyncResult(name=drive_name, drive_id=None, created=True)
    created = service.drives().create(requestId=request_id, body={"name": drive_name}).execute()
    return DriveSyncResult(name=drive_name, drive_id=created.get("id"), created=True)


def ensure_drive_marker(
    service: Any,
    *,
    drive_id: str,
    run_name: str,
    stable_id: str,
    prefix: str,
    dry_run: bool,
) -> str:
    marker = find_file_by_app_properties(
        service,
        app_properties={"gwsynth_id": stable_id, "gwsynth_kind": "drive_marker"},
        drive_id=drive_id,
    )
    if marker:
        return str(marker.get("id") or "")
    if dry_run:
        return ""
    body = {
        "name": f"{prefix} __gwsynth__",
        "mimeType": FOLDER_MIME_TYPE,
        "appProperties": build_app_properties(
            run_name=run_name,
            stable_id=stable_id,
            kind="drive_marker",
            path="/__gwsynth__",
        ),
    }
    created = service.files().create(
        body=body,
        supportsAllDrives=True,
        fields="id",
    ).execute()
    return str(created.get("id") or "")


def ensure_folder(
    service: Any,
    *,
    name: str,
    parent_id: str | None,
    drive_id: str | None,
    app_properties: dict[str, str],
    dry_run: bool,
) -> str | None:
    existing = find_file_by_app_properties(
        service, app_properties=app_properties, drive_id=drive_id
    )
    if existing:
        return str(existing.get("id"))
    if dry_run:
        return None
    body = {
        "name": name,
        "mimeType": FOLDER_MIME_TYPE,
        "appProperties": app_properties,
    }
    if parent_id:
        body["parents"] = [parent_id]
    created = service.files().create(
        body=body,
        supportsAllDrives=drive_id is not None,
        fields="id",
    ).execute()
    return str(created.get("id") or "")


def ensure_doc_file(
    service: Any,
    *,
    name: str,
    parent_id: str | None,
    drive_id: str | None,
    app_properties: dict[str, str],
    dry_run: bool,
) -> tuple[str | None, bool]:
    existing = find_file_by_app_properties(
        service, app_properties=app_properties, drive_id=drive_id
    )
    if existing:
        return str(existing.get("id")), False
    if dry_run:
        return None, True
    body = {
        "name": name,
        "mimeType": DOC_MIME_TYPE,
        "appProperties": app_properties,
    }
    if parent_id:
        body["parents"] = [parent_id]
    created = service.files().create(
        body=body,
        supportsAllDrives=drive_id is not None,
        fields="id",
    ).execute()
    return str(created.get("id") or ""), True


def update_app_properties(
    service: Any,
    *,
    file_id: str,
    app_properties: dict[str, str],
    drive_id: str | None,
) -> None:
    service.files().update(
        fileId=file_id,
        body={"appProperties": app_properties},
        supportsAllDrives=drive_id is not None,
    ).execute()


def find_file_by_app_properties(
    service: Any,
    *,
    app_properties: dict[str, str],
    drive_id: str | None,
) -> dict[str, Any] | None:
    query = _app_properties_query(app_properties)
    params: dict[str, Any] = {
        "q": f"{query} and trashed = false",
        "fields": "files(id,name,appProperties,mimeType,parents)",
        "pageSize": 1,
    }
    if drive_id:
        params["driveId"] = drive_id
        params["corpora"] = "drive"
        params["includeItemsFromAllDrives"] = True
        params["supportsAllDrives"] = True
    response = service.files().list(**params).execute()
    files = response.get("files", [])
    if isinstance(files, list) and files:
        first = files[0]
        if isinstance(first, dict):
            return first
    return None


def list_files_by_app_properties(
    service: Any,
    *,
    app_properties: dict[str, str],
    drive_id: str | None,
) -> Iterable[dict[str, Any]]:
    query = _app_properties_query(app_properties)
    params: dict[str, Any] = {
        "q": f"{query} and trashed = false",
        "fields": "nextPageToken,files(id,name,appProperties,mimeType,parents)",
        "pageSize": 1000,
    }
    if drive_id:
        params["driveId"] = drive_id
        params["corpora"] = "drive"
        params["includeItemsFromAllDrives"] = True
        params["supportsAllDrives"] = True
    token: str | None = None
    while True:
        if token:
            params["pageToken"] = token
        response = service.files().list(**params).execute()
        files = response.get("files", [])
        if isinstance(files, list):
            for item in files:
                if isinstance(item, dict):
                    yield item
        token = response.get("nextPageToken")
        if not token:
            break


def delete_file(service: Any, *, file_id: str, drive_id: str | None, dry_run: bool) -> bool:
    if dry_run:
        return True
    service.files().delete(fileId=file_id, supportsAllDrives=drive_id is not None).execute()
    return True


def delete_drive(service: Any, *, drive_id: str, dry_run: bool) -> bool:
    if dry_run:
        return True
    service.drives().delete(driveId=drive_id).execute()
    return True


def ensure_permission(
    service: Any,
    *,
    file_id: str,
    role: str,
    permission_type: str,
    email: str | None,
    drive_id: str | None,
    dry_run: bool,
) -> bool:
    existing = _permission_exists(
        service,
        file_id=file_id,
        role=role,
        permission_type=permission_type,
        email=email,
        drive_id=drive_id,
    )
    if existing:
        return False
    if dry_run:
        return True
    body: dict[str, Any] = {"type": permission_type, "role": role}
    if email:
        body["emailAddress"] = email
    service.permissions().create(
        fileId=file_id,
        body=body,
        sendNotificationEmail=False,
        supportsAllDrives=drive_id is not None,
    ).execute()
    return True


def _permission_exists(
    service: Any,
    *,
    file_id: str,
    role: str,
    permission_type: str,
    email: str | None,
    drive_id: str | None,
) -> bool:
    params: dict[str, Any] = {
        "fileId": file_id,
        "fields": "permissions(id,role,type,emailAddress)",
        "supportsAllDrives": drive_id is not None,
    }
    permissions = service.permissions().list(**params).execute().get("permissions", []) or []
    for perm in permissions:
        if perm.get("role") != role:
            continue
        if perm.get("type") != permission_type:
            continue
        if email and perm.get("emailAddress") != email:
            continue
        return True
    return False


def _app_properties_query(app_properties: dict[str, str]) -> str:
    parts = [
        f"appProperties has {{ key='{key}' and value='{value}' }}"
        for key, value in app_properties.items()
    ]
    return " and ".join(parts)


def _find_drive_by_name(service: Any, name: str) -> dict[str, Any] | None:
    token: str | None = None
    while True:
        response = service.drives().list(pageSize=100, pageToken=token).execute()
        for drive in response.get("drives", []) or []:
            if drive.get("name") == name:
                if isinstance(drive, dict):
                    return drive
        token = response.get("nextPageToken")
        if not token:
            break
    return None
