from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class EntraUser:
    id: str
    email: str
    display_name: str
    department: str
    job_title: str


@dataclass(frozen=True)
class EntraGroup:
    id: str
    email: str
    display_name: str
    description: str


class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None
        self._manager_cache: dict[str, str | None] = {}

    @classmethod
    def from_env(cls) -> "GraphClient":
        tenant_id = os.environ.get("ENTRA_TENANT_ID", "").strip()
        client_id = os.environ.get("ENTRA_CLIENT_ID", "").strip()
        client_secret = os.environ.get("ENTRA_CLIENT_SECRET", "").strip()
        if not tenant_id or not client_id or not client_secret:
            raise ValueError("Missing Entra credentials (ENTRA_TENANT_ID/CLIENT_ID/CLIENT_SECRET)")
        return cls(tenant_id, client_id, client_secret)

    def _token_endpoint(self) -> str:
        return f"https://login.microsoftonline.com/{self._tenant_id}"

    def _get_token(self) -> str:
        if self._token:
            return self._token
        msal = _load_msal()
        app = msal.ConfidentialClientApplication(
            self._client_id,
            authority=self._token_endpoint(),
            client_credential=self._client_secret,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        token = result.get("access_token")
        if not isinstance(token, str):
            raise ValueError("Failed to acquire Graph access token")
        self._token = token
        return token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        requests = _load_requests()
        response = requests.get(url, headers=self._headers(), params=params, timeout=60)
        if response.status_code >= 400:
            raise ValueError(f"Graph API error {response.status_code}: {response.text}")
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Graph API returned non-object response")
        return data

    def _paginate(self, url: str, params: dict[str, Any] | None = None) -> Iterable[dict[str, Any]]:
        next_url = url
        next_params = dict(params or {})
        while next_url:
            data = self._get(next_url, next_params)
            value = data.get("value", [])
            if not isinstance(value, list):
                break
            for item in value:
                if isinstance(item, dict):
                    yield item
            next_url = data.get("@odata.nextLink", "")
            next_params = {}

    def list_users(self, *, max_users: int, user_filter: str) -> list[EntraUser]:
        params = {
            "$select": "id,displayName,mail,userPrincipalName,department,jobTitle,accountEnabled",
            "$top": min(max_users, 999),
        }
        if user_filter:
            params["$filter"] = user_filter
        users: list[EntraUser] = []
        for item in self._paginate("https://graph.microsoft.com/v1.0/users", params):
            if len(users) >= max_users:
                break
            email = str(item.get("mail") or item.get("userPrincipalName") or "").strip()
            if not email:
                continue
            display_name = str(item.get("displayName") or email.split("@")[0]).strip()
            users.append(
                EntraUser(
                    id=str(item.get("id") or ""),
                    email=email,
                    display_name=display_name,
                    department=str(item.get("department") or "General").strip() or "General",
                    job_title=str(item.get("jobTitle") or "").strip(),
                )
            )
        return users

    def list_groups(self, *, max_groups: int, group_filter: str) -> list[EntraGroup]:
        params = {
            "$select": "id,displayName,mail,description,mailEnabled",
            "$top": min(max_groups, 999),
        }
        if group_filter:
            params["$filter"] = group_filter
        groups: list[EntraGroup] = []
        for item in self._paginate("https://graph.microsoft.com/v1.0/groups", params):
            if len(groups) >= max_groups:
                break
            email = str(item.get("mail") or "").strip()
            if not email:
                continue
            display_name = str(item.get("displayName") or email.split("@")[0]).strip()
            groups.append(
                EntraGroup(
                    id=str(item.get("id") or ""),
                    email=email,
                    display_name=display_name,
                    description=str(item.get("description") or "").strip(),
                )
            )
        return groups

    def list_group_members(self, group_id: str) -> list[str]:
        members: list[str] = []
        params = {"$select": "id,mail,userPrincipalName"}
        url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members"
        for item in self._paginate(url, params):
            email = str(item.get("mail") or item.get("userPrincipalName") or "").strip()
            if email:
                members.append(email)
        return members

    def get_manager_email(self, user_id: str) -> str | None:
        if user_id in self._manager_cache:
            return self._manager_cache[user_id]
        url = f"https://graph.microsoft.com/v1.0/users/{user_id}/manager"
        params = {"$select": "mail,userPrincipalName"}
        try:
            data = self._get(url, params)
            email = str(data.get("mail") or data.get("userPrincipalName") or "").strip() or None
        except ValueError:
            email = None
        self._manager_cache[user_id] = email
        return email

    def export_snapshot(
        self,
        *,
        max_users: int,
        max_groups: int,
        user_filter: str,
        group_filter: str,
    ) -> dict[str, Any]:
        users = self.list_users(max_users=max_users, user_filter=user_filter)
        groups = self.list_groups(max_groups=max_groups, group_filter=group_filter)
        memberships: dict[str, list[str]] = {}
        for group in groups:
            memberships[group.id] = self.list_group_members(group.id)
        return {
            "users": [user.__dict__ for user in users],
            "groups": [group.__dict__ for group in groups],
            "memberships": memberships,
        }

    def export_snapshot_file(
        self,
        path: str,
        *,
        max_users: int,
        max_groups: int,
        user_filter: str,
        group_filter: str,
    ) -> None:
        payload = self.export_snapshot(
            max_users=max_users,
            max_groups=max_groups,
            user_filter=user_filter,
            group_filter=group_filter,
        )
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)


def _load_msal() -> Any:
    import importlib

    return importlib.import_module("msal")


def _load_requests() -> Any:
    import importlib

    return importlib.import_module("requests")
