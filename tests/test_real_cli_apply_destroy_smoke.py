from __future__ import annotations

import json

import pytest

from gwsynth.real import cli
from gwsynth.real.blueprint import default_blueprint_dict
from gwsynth.real.entra import EntraGroup, EntraUser
from gwsynth.real.google_admin import GroupSyncResult, UserSyncResult


def _write_blueprint(tmp_path, data: dict) -> str:
    import yaml

    path = tmp_path / "blueprint.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return str(path)


def _set_tenant_guard_env(monkeypatch, data: dict) -> None:
    monkeypatch.setenv("GOOGLE_CUSTOMER_ID", data["tenant_guard"]["google_customer_id"])
    monkeypatch.setenv("GOOGLE_DOMAIN", data["tenant_guard"]["google_domain"])


def test_real_cli_apply_smoke_runs_without_network(tmp_path, monkeypatch, capsys):
    data = default_blueprint_dict()
    # Keep the smoke path tight: skip licensing and My Drive seeding.
    data["licenses"]["assign"] = False
    data["drives"]["my_drive"]["enabled"] = False

    path = _write_blueprint(tmp_path, data)
    _set_tenant_guard_env(monkeypatch, data)

    class FakeGraph:
        def list_users(self, *, max_users: int, user_filter: str):
            _ = (max_users, user_filter)
            return [
                EntraUser(
                    id="u1",
                    email=f"alice@{data['tenant_guard']['google_domain']}",
                    display_name="Alice",
                    department="Engineering",
                    job_title="Dev",
                )
            ]

        def list_groups(self, *, max_groups: int, group_filter: str):
            _ = (max_groups, group_filter)
            return [
                EntraGroup(
                    id="g1",
                    email=f"all-hands@{data['tenant_guard']['google_domain']}",
                    display_name="All Hands",
                    description="All hands group",
                )
            ]

        def list_group_members(self, group_id: str):
            assert group_id == "g1"
            return [f"alice@{data['tenant_guard']['google_domain']}"]

    # Patch all external-touching helpers in the CLI module. This is a smoke check
    # for wiring + tenant guard + report serialization; it must not require creds.
    monkeypatch.setattr(cli.GraphClient, "from_env", classmethod(lambda cls: FakeGraph()))
    monkeypatch.setattr(cli, "admin_directory_service", lambda: object())
    monkeypatch.setattr(cli, "drive_service_for_admin", lambda: object())

    monkeypatch.setattr(cli, "ensure_org_unit", lambda *_a, **_k: None)
    monkeypatch.setattr(
        cli,
        "ensure_group",
        lambda *_a, group_email, **_k: GroupSyncResult(email=group_email, created=True),
    )
    monkeypatch.setattr(
        cli,
        "ensure_user",
        lambda *_a, email, **_k: UserSyncResult(email=email, created=True),
    )
    monkeypatch.setattr(cli, "sync_group_members", lambda *_a, **_k: 1)

    # Skip Drive/Docs seeding entirely.
    monkeypatch.setattr(cli, "_ensure_shared_drives", lambda *_a, **_k: [])
    monkeypatch.setattr(cli, "_ensure_shared_drive_permissions", lambda *_a, **_k: None)
    monkeypatch.setattr(cli, "_ensure_shared_drive_folders", lambda *_a, **_k: None)
    monkeypatch.setattr(cli, "_ensure_shared_drive_docs", lambda *_a, **_k: None)
    monkeypatch.setattr(cli, "_ensure_my_drive_docs", lambda *_a, **_k: None)

    cli.main(["apply", "--blueprint", path, "--yes"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert payload["created"]
    # reviewer_group + entra group + user
    assert any(x.startswith("group:") for x in payload["created"])
    assert any(x.startswith("user:") for x in payload["created"])
    assert any(x.startswith("group_members:") for x in payload["updated"])


def test_real_cli_destroy_smoke_content_only_runs_without_network(tmp_path, monkeypatch, capsys):
    data = default_blueprint_dict()
    data["licenses"]["assign"] = False
    data["drives"]["my_drive"]["enabled"] = False
    path = _write_blueprint(tmp_path, data)
    _set_tenant_guard_env(monkeypatch, data)

    class FakeGraph:
        def list_users(self, *, max_users: int, user_filter: str):
            _ = (max_users, user_filter)
            return [
                EntraUser(
                    id="u1",
                    email=f"alice@{data['tenant_guard']['google_domain']}",
                    display_name="Alice",
                    department="Engineering",
                    job_title="Dev",
                )
            ]

        def list_groups(self, *, max_groups: int, group_filter: str):
            _ = (max_groups, group_filter)
            return []

        def list_group_members(self, group_id: str):
            assert group_id == "g1"
            return []

    monkeypatch.setattr(cli.GraphClient, "from_env", classmethod(lambda cls: FakeGraph()))
    monkeypatch.setattr(cli, "drive_service_for_admin", lambda: object())
    monkeypatch.setattr(cli, "drive_service_for_user", lambda _email: object())

    # Provide a fake shared drive result so destroy exercises both drive and my-drive loops.
    monkeypatch.setattr(
        cli,
        "_ensure_shared_drives",
        lambda *_a, **_k: [
            cli._DriveResult(
                drive_id="drive1",
                name="Drive 1",
                department="Engineering",
                marker_id="marker1",
                folders={},
                docs=[],
            )
        ],
    )

    def _fake_list_files(_svc, *, app_properties, drive_id):
        assert app_properties == {"gwsynth_run": data["run"]["name"]}
        # include one marker which must be skipped
        if drive_id:
            return [
                {"id": "marker-file", "appProperties": {"gwsynth_kind": "drive_marker"}},
                {"id": "f1", "appProperties": {"gwsynth_kind": "doc"}},
            ]
        return [{"id": "u1f1", "appProperties": {"gwsynth_kind": "doc"}}]

    monkeypatch.setattr(cli, "list_files_by_app_properties", _fake_list_files)

    deleted: list[tuple[str, str | None]] = []
    monkeypatch.setattr(
        cli,
        "delete_file",
        lambda _svc, *, file_id, drive_id, dry_run: deleted.append((file_id, drive_id)),
    )
    monkeypatch.setattr(
        cli,
        "delete_drive",
        lambda *_a, **_k: pytest.fail("delete_drive should not run in content-only"),
    )
    monkeypatch.setattr(
        cli,
        "admin_directory_service",
        lambda: pytest.fail("admin_directory_service should not run in content-only"),
    )

    cli.main(["destroy", "--blueprint", path, "--mode", "content-only", "--yes"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert ("f1", "drive1") in deleted
    assert ("u1f1", None) in deleted
    assert not any(x.startswith("deleted_drive:") for x in payload["updated"])


def test_real_cli_destroy_smoke_all_runs_without_network(tmp_path, monkeypatch, capsys):
    data = default_blueprint_dict()
    data["licenses"]["assign"] = False
    data["drives"]["my_drive"]["enabled"] = False
    path = _write_blueprint(tmp_path, data)
    _set_tenant_guard_env(monkeypatch, data)

    class FakeGraph:
        def list_users(self, *, max_users: int, user_filter: str):
            _ = (max_users, user_filter)
            return [
                EntraUser(
                    id="u1",
                    email=f"alice@{data['tenant_guard']['google_domain']}",
                    display_name="Alice",
                    department="Engineering",
                    job_title="Dev",
                )
            ]

        def list_groups(self, *, max_groups: int, group_filter: str):
            _ = (max_groups, group_filter)
            return [
                EntraGroup(
                    id="g1",
                    email=f"all-hands@{data['tenant_guard']['google_domain']}",
                    display_name="All Hands",
                    description="All hands group",
                )
            ]

        def list_group_members(self, group_id: str):
            assert group_id == "g1"
            return []

    monkeypatch.setattr(cli.GraphClient, "from_env", classmethod(lambda cls: FakeGraph()))
    monkeypatch.setattr(cli, "drive_service_for_admin", lambda: object())
    monkeypatch.setattr(cli, "drive_service_for_user", lambda _email: object())

    monkeypatch.setattr(
        cli,
        "_ensure_shared_drives",
        lambda *_a, **_k: [
            cli._DriveResult(
                drive_id="drive1",
                name="Drive 1",
                department="Engineering",
                marker_id="marker1",
                folders={},
                docs=[],
            )
        ],
    )
    monkeypatch.setattr(
        cli,
        "list_files_by_app_properties",
        lambda *_a, **_k: [],
    )

    deleted_drives: list[str] = []
    monkeypatch.setattr(cli, "delete_file", lambda *_a, **_k: None)
    monkeypatch.setattr(
        cli,
        "delete_drive",
        lambda *_a, drive_id, **_k: deleted_drives.append(drive_id),
    )

    class _Call:
        def __init__(self, payload):
            self._payload = payload

        def execute(self):
            return self._payload

    class _Groups:
        def get(self, *, groupKey):
            # Only delete groups that are clearly part of the run.
            assert groupKey
            return _Call({"description": f"created by {data['run']['name']}"})

        def delete(self, *, groupKey):
            assert groupKey
            return _Call({})

    class _Users:
        def get(self, *, userKey):
            assert userKey
            return _Call({"orgUnitPath": data["run"]["ou_path"]})

        def delete(self, *, userKey):
            assert userKey
            return _Call({})

    class FakeAdmin:
        def groups(self):
            return _Groups()

        def users(self):
            return _Users()

    monkeypatch.setattr(cli, "admin_directory_service", lambda: FakeAdmin())

    cli.main(["destroy", "--blueprint", path, "--mode", "all", "--yes"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    assert deleted_drives == ["drive1"]
    assert any(x == "deleted_drive:drive1" for x in payload["updated"])
    assert any(x.startswith("deleted_group:") for x in payload["updated"])
    assert any(x.startswith("deleted_user:") for x in payload["updated"])
