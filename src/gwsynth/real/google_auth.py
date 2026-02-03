from __future__ import annotations

import os
from typing import Any

GOOGLE_ADMIN_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/admin.directory.group",
    "https://www.googleapis.com/auth/admin.directory.orgunit",
    "https://www.googleapis.com/auth/apps.groups.settings",
    "https://www.googleapis.com/auth/apps.licensing",
    "https://www.googleapis.com/auth/drive",
]

GOOGLE_USER_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def service_account_path() -> str:
    path = os.environ.get("GOOGLE_SA_JSON", "").strip()
    if not path:
        raise ValueError("Missing GOOGLE_SA_JSON path")
    return path


def admin_subject() -> str:
    subject = os.environ.get("GOOGLE_ADMIN_SUBJECT", "").strip()
    if not subject:
        raise ValueError("Missing GOOGLE_ADMIN_SUBJECT")
    return subject


def customer_id() -> str:
    value = os.environ.get("GOOGLE_CUSTOMER_ID", "").strip()
    if not value:
        raise ValueError("Missing GOOGLE_CUSTOMER_ID")
    return value


def google_domain() -> str:
    value = os.environ.get("GOOGLE_DOMAIN", "").strip()
    if not value:
        raise ValueError("Missing GOOGLE_DOMAIN")
    return value


def _load_service_account() -> Any:
    import importlib

    module = importlib.import_module("google.oauth2.service_account")
    return module.Credentials


def _load_discovery() -> Any:
    import importlib

    return importlib.import_module("googleapiclient.discovery")

def build_credentials(scopes: list[str], subject: str | None) -> Any:
    credentials_cls = _load_service_account()
    credentials = credentials_cls.from_service_account_file(service_account_path(), scopes=scopes)
    if subject:
        credentials = credentials.with_subject(subject)
    return credentials


def build_service(name: str, version: str, credentials: Any) -> Any:
    discovery = _load_discovery()
    return discovery.build(name, version, credentials=credentials, cache_discovery=False)


def admin_directory_service() -> Any:
    credentials = build_credentials(GOOGLE_ADMIN_SCOPES, admin_subject())
    return build_service("admin", "directory_v1", credentials)


def licensing_service() -> Any:
    credentials = build_credentials(GOOGLE_ADMIN_SCOPES, admin_subject())
    return build_service("licensing", "v1", credentials)


def drive_service_for_admin() -> Any:
    credentials = build_credentials(GOOGLE_ADMIN_SCOPES, admin_subject())
    return build_service("drive", "v3", credentials)


def drive_service_for_user(user_email: str) -> Any:
    credentials = build_credentials(GOOGLE_USER_DRIVE_SCOPES, user_email)
    return build_service("drive", "v3", credentials)


def docs_service_for_user(user_email: str) -> Any:
    credentials = build_credentials(GOOGLE_USER_DRIVE_SCOPES, user_email)
    return build_service("docs", "v1", credentials)
