from __future__ import annotations

import json

from gwsynth.real import cli
from gwsynth.real.blueprint import default_blueprint_dict
from gwsynth.real.entra import EntraGroup, EntraUser
from gwsynth.real.google_admin import GroupSyncResult, UserSyncResult


def test_real_cli_plan_smoke_runs_without_network(tmp_path, monkeypatch, capsys):
    # Create a blueprint that passes validation (licenses require values when assign=true).
    data = default_blueprint_dict()
    data["licenses"]["product_id"] = "PROD"
    data["licenses"]["sku_id"] = "SKU"
    path = tmp_path / "blueprint.yaml"
    import yaml

    path.write_text(yaml.safe_dump(data, sort_keys=False))

    # Tenant guard checks read env via gwsynth.real.google_auth.
    monkeypatch.setenv("GOOGLE_CUSTOMER_ID", data["tenant_guard"]["google_customer_id"])
    monkeypatch.setenv("GOOGLE_DOMAIN", data["tenant_guard"]["google_domain"])

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
                ),
                EntraUser(
                    id="u2",
                    email=f"bob@{data['tenant_guard']['google_domain']}",
                    display_name="Bob",
                    department="Security",
                    job_title="Eng",
                ),
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

    # Patch all external-touching helpers in the CLI module. The goal is a smoke
    # check that the plan command runs end-to-end without requiring real creds.
    monkeypatch.setattr(cli.GraphClient, "from_env", classmethod(lambda cls: FakeGraph()))
    monkeypatch.setattr(cli, "admin_directory_service", lambda: object())
    monkeypatch.setattr(cli, "drive_service_for_admin", lambda: object())
    monkeypatch.setattr(cli, "_find_drive_by_name", lambda _service, _name: None)
    monkeypatch.setattr(cli, "find_file_by_app_properties", lambda *_a, **_k: None)

    monkeypatch.setattr(
        cli,
        "ensure_org_unit",
        lambda _svc, _customer_id, _ou_path, *, dry_run: True if dry_run else False,
    )
    monkeypatch.setattr(
        cli,
        "ensure_group",
        lambda _svc, *, group_email, display_name, description, run_name, dry_run: GroupSyncResult(
            email=group_email, created=True
        ),
    )
    monkeypatch.setattr(
        cli,
        "ensure_user",
        lambda _svc,
        *,
        email,
        display_name,
        department,
        job_title,
        ou_path,
        dry_run: UserSyncResult(email=email, created=True),
    )

    cli.main(["plan", "--blueprint", str(path), "--json"])
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)

    counts = payload["counts"]
    assert counts["users_create"] == 2
    # reviewer_group + entra group
    assert counts["groups_create"] == 2
    assert counts["licenses_assign"] == 2
    assert counts["drives_create"] == 2
    assert counts["folders_create"] == 8
    assert counts["docs_create"] == 24
    assert payload["prerequisites"]
