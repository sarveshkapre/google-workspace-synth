from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .blueprint import Blueprint, load_blueprint, write_default_blueprint
from .entra import EntraGroup, EntraUser, GraphClient
from .google_admin import (
    GroupSyncResult,
    UserSyncResult,
    ensure_group,
    ensure_org_unit,
    ensure_user,
    sync_group_members,
)
from .google_auth import (
    admin_directory_service,
    customer_id,
    drive_service_for_admin,
    drive_service_for_user,
    google_domain,
    licensing_service,
)
from .google_docs import DocContent, apply_doc_content
from .google_drive import (
    build_app_properties,
    delete_drive,
    delete_file,
    ensure_doc_file,
    ensure_drive_marker,
    ensure_folder,
    ensure_permission,
    ensure_shared_drive,
    find_file_by_app_properties,
    list_files_by_app_properties,
)
from .google_licensing import ensure_license
from .llm_openai import LlmConfig, generate_doc_content
from .report import ApplyReport, PlanCounts, PlanReport
from .stable_ids import content_hash, stable_uuid


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="GWSynth Real Workspace CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init-blueprint", help="Write a starter blueprint.yaml")
    init_cmd.add_argument("--out", default="blueprint.yaml")
    init_cmd.add_argument("--force", action="store_true")

    plan_cmd = sub.add_parser("plan", help="Show what would change")
    plan_cmd.add_argument("--blueprint", required=True)
    plan_cmd.add_argument("--json", action="store_true")

    apply_cmd = sub.add_parser("apply", help="Apply provisioning + seeding")
    apply_cmd.add_argument("--blueprint", required=True)
    apply_cmd.add_argument("--yes", action="store_true")
    apply_cmd.add_argument("--regen", action="store_true")

    destroy_cmd = sub.add_parser("destroy", help="Delete synthetic content/users")
    destroy_cmd.add_argument("--blueprint", required=True)
    destroy_cmd.add_argument("--mode", choices=["content-only", "all"], default="content-only")
    destroy_cmd.add_argument("--yes", action="store_true")

    entra_cmd = sub.add_parser("entra", help="Entra helpers")
    entra_sub = entra_cmd.add_subparsers(dest="entra_command", required=True)
    export_cmd = entra_sub.add_parser("export", help="Export Entra snapshot")
    export_cmd.add_argument("--out", required=True)
    export_cmd.add_argument("--max-users", type=int, default=100)
    export_cmd.add_argument("--max-groups", type=int, default=50)
    export_cmd.add_argument("--user-filter", default="accountEnabled eq true")
    export_cmd.add_argument("--group-filter", default="")

    args = parser.parse_args(argv)

    if args.command == "init-blueprint":
        _cmd_init_blueprint(args.out, args.force)
        return
    if args.command == "entra" and args.entra_command == "export":
        _cmd_entra_export(args)
        return
    if args.command == "plan":
        _cmd_plan(args)
        return
    if args.command == "apply":
        _cmd_apply(args)
        return
    if args.command == "destroy":
        _cmd_destroy(args)
        return


def _cmd_init_blueprint(path: str, force: bool) -> None:
    target = Path(path)
    if target.exists() and not force:
        raise SystemExit(f"{path} already exists. Use --force to overwrite.")
    write_default_blueprint(path)
    print(f"Wrote blueprint to {path}")


def _cmd_entra_export(args: argparse.Namespace) -> None:
    client = GraphClient.from_env()
    client.export_snapshot_file(
        args.out,
        max_users=args.max_users,
        max_groups=args.max_groups,
        user_filter=args.user_filter,
        group_filter=args.group_filter,
    )
    print(f"Wrote Entra snapshot to {args.out}")


def _cmd_plan(args: argparse.Namespace) -> None:
    blueprint = load_blueprint(args.blueprint)
    _validate_tenant_guard(blueprint)
    report = _build_plan(blueprint)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        _print_plan_summary(report)


def _cmd_apply(args: argparse.Namespace) -> None:
    if not args.yes:
        raise SystemExit("Apply requires --yes")
    blueprint = load_blueprint(args.blueprint)
    _validate_tenant_guard(blueprint)
    report = _apply(blueprint, regen=args.regen)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))


def _cmd_destroy(args: argparse.Namespace) -> None:
    if not args.yes:
        raise SystemExit("Destroy requires --yes")
    blueprint = load_blueprint(args.blueprint)
    _validate_tenant_guard(blueprint)
    report = _destroy(blueprint, mode=args.mode)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))


def _validate_tenant_guard(blueprint: Blueprint) -> None:
    env_customer_id = customer_id()
    env_domain = google_domain()
    if env_customer_id != blueprint.tenant_guard.google_customer_id:
        raise SystemExit("GOOGLE_CUSTOMER_ID does not match blueprint tenant_guard")
    if env_domain != blueprint.tenant_guard.google_domain:
        raise SystemExit("GOOGLE_DOMAIN does not match blueprint tenant_guard")


def _build_plan(blueprint: Blueprint) -> PlanReport:
    report = PlanReport(run_name=blueprint.run.name)
    counts = report.counts
    graph = GraphClient.from_env()
    users, groups, memberships = _load_entra_data(blueprint, graph)

    admin_service = admin_directory_service()
    if ensure_org_unit(
        admin_service,
        customer_id(),
        blueprint.run.ou_path,
        dry_run=True,
    ):
        report.prerequisites.append(f"Create OU {blueprint.run.ou_path}")

    reviewer_group_result = ensure_group(
        admin_service,
        group_email=blueprint.sharing.reviewer_group_email,
        display_name="Synthetic Reviewers",
        description="Synthetic reviewers group",
        run_name=blueprint.run.name,
        dry_run=True,
    )
    _tally_group_result(reviewer_group_result, counts, report)

    for group in groups:
        group_result = ensure_group(
            admin_service,
            group_email=group.email,
            display_name=group.display_name,
            description=group.description,
            run_name=blueprint.run.name,
            dry_run=True,
        )
        _tally_group_result(group_result, counts, report)

    for user in users:
        user_result = ensure_user(
            admin_service,
            email=user.email,
            display_name=user.display_name,
            department=user.department,
            job_title=user.job_title,
            ou_path=blueprint.run.ou_path,
            dry_run=True,
        )
        _tally_user_result(user_result, counts, report)

    if blueprint.licenses.assign:
        counts.licenses_assign = len(users)

    drives_admin = drive_service_for_admin()
    drive_plan = _plan_shared_drives(blueprint, drives_admin, users)
    counts.drives_create += drive_plan["to_create"]
    counts.drives_conflict += drive_plan["conflicts"]

    folder_plan = _plan_folders(blueprint, drives_admin, drive_plan["drives"])
    counts.folders_create += folder_plan

    doc_plan = _plan_docs(blueprint, drives_admin, drive_plan["drives"], users)
    counts.docs_create += doc_plan["to_create"]
    counts.docs_update += doc_plan["to_update"]

    return report


def _apply(blueprint: Blueprint, *, regen: bool) -> ApplyReport:
    report = ApplyReport(run_name=blueprint.run.name)
    graph = GraphClient.from_env()
    users, groups, memberships = _load_entra_data(blueprint, graph)

    admin_service = admin_directory_service()
    ensure_org_unit(admin_service, customer_id(), blueprint.run.ou_path, dry_run=False)

    reviewer_group = ensure_group(
        admin_service,
        group_email=blueprint.sharing.reviewer_group_email,
        display_name="Synthetic Reviewers",
        description="Synthetic reviewers group",
        run_name=blueprint.run.name,
        dry_run=False,
    )
    _record_group_result(reviewer_group, report)

    for group in groups:
        group_result = ensure_group(
            admin_service,
            group_email=group.email,
            display_name=group.display_name,
            description=group.description,
            run_name=blueprint.run.name,
            dry_run=False,
        )
        _record_group_result(group_result, report)

    for group in groups:
        members = memberships.get(group.id, [])
        added = sync_group_members(
            admin_service,
            group_email=group.email,
            members=members,
            run_name=blueprint.run.name,
            dry_run=False,
        )
        if added:
            report.updated.append(f"group_members:{group.email}+{added}")

    active_users: list[EntraUser] = []
    for user in users:
        user_result = ensure_user(
            admin_service,
            email=user.email,
            display_name=user.display_name,
            department=user.department,
            job_title=user.job_title,
            ou_path=blueprint.run.ou_path,
            dry_run=False,
        )
        _record_user_result(user_result, report)
        if not user_result.conflict:
            active_users.append(user)

    if blueprint.licenses.assign:
        licensing = licensing_service()
        for user in active_users:
            if ensure_license(
                licensing,
                product_id=blueprint.licenses.product_id,
                sku_id=blueprint.licenses.sku_id,
                user_email=user.email,
                dry_run=False,
            ):
                report.updated.append(f"license:{user.email}")

    drives_admin = drive_service_for_admin()
    drive_data = _ensure_shared_drives(blueprint, drives_admin, active_users, report)
    _ensure_shared_drive_permissions(blueprint, drives_admin, drive_data, groups, active_users)
    _ensure_shared_drive_folders(blueprint, drives_admin, drive_data, report)
    _ensure_shared_drive_docs(blueprint, drive_data, active_users, groups, regen, report)
    _ensure_my_drive_docs(blueprint, active_users, regen, report, graph)

    return report


def _destroy(blueprint: Blueprint, *, mode: str) -> ApplyReport:
    report = ApplyReport(run_name=blueprint.run.name)
    graph = GraphClient.from_env()
    users, groups, _ = _load_entra_data(blueprint, graph)
    drive_admin = drive_service_for_admin()
    drive_data = _ensure_shared_drives(blueprint, drive_admin, users, report, dry_run=True)

    for drive in drive_data:
        for item in list_files_by_app_properties(
            drive_admin,
            app_properties={"gwsynth_run": blueprint.run.name},
            drive_id=drive.drive_id,
        ):
            if item.get("appProperties", {}).get("gwsynth_kind") == "drive_marker":
                continue
            delete_file(
                drive_admin,
                file_id=str(item.get("id") or ""),
                drive_id=drive.drive_id,
                dry_run=False,
            )
            report.updated.append(f"deleted_file:{item.get('id')}")
        if mode == "all":
            delete_drive(drive_admin, drive_id=drive.drive_id, dry_run=False)
            report.updated.append(f"deleted_drive:{drive.drive_id}")

    for user in users:
        drive_service = drive_service_for_user(user.email)
        for item in list_files_by_app_properties(
            drive_service,
            app_properties={"gwsynth_run": blueprint.run.name},
            drive_id=None,
        ):
            delete_file(
                drive_service,
                file_id=str(item.get("id") or ""),
                drive_id=None,
                dry_run=False,
            )
            report.updated.append(f"deleted_user_file:{item.get('id')}")

    if mode == "all":
        admin_service = admin_directory_service()
        for group in groups:
            existing = admin_service.groups().get(groupKey=group.email).execute()
            description = str(existing.get("description") or "")
            if blueprint.run.name in description:
                admin_service.groups().delete(groupKey=group.email).execute()
                report.updated.append(f"deleted_group:{group.email}")
        for user in users:
            try:
                existing = admin_service.users().get(userKey=user.email).execute()
            except Exception:
                continue
            if existing.get("orgUnitPath") != blueprint.run.ou_path:
                continue
            try:
                admin_service.users().delete(userKey=user.email).execute()
                report.updated.append(f"deleted_user:{user.email}")
            except Exception:
                continue
    return report


def _load_entra_data(
    blueprint: Blueprint, graph: GraphClient
) -> tuple[list[EntraUser], list[EntraGroup], dict[str, list[str]]]:
    users = graph.list_users(
        max_users=blueprint.identity.entra.max_users,
        user_filter=blueprint.identity.entra.user_filter,
    )
    groups = graph.list_groups(
        max_groups=blueprint.identity.entra.max_groups,
        group_filter=blueprint.identity.entra.group_filter,
    )
    if blueprint.identity.mapping.require_domain_match:
        users = _filter_by_domain(users, blueprint.tenant_guard.google_domain)
        groups = _filter_groups_by_domain(groups, blueprint.tenant_guard.google_domain)
    memberships: dict[str, list[str]] = {}
    for group in groups:
        members = graph.list_group_members(group.id)
        if blueprint.identity.mapping.require_domain_match:
            members = [m for m in members if m.endswith(f"@{blueprint.tenant_guard.google_domain}")]
        memberships[group.id] = members
    return users, groups, memberships


def _filter_by_domain(users: list[EntraUser], domain: str) -> list[EntraUser]:
    suffix = f"@{domain}"
    return [user for user in users if user.email.endswith(suffix)]


def _filter_groups_by_domain(groups: list[EntraGroup], domain: str) -> list[EntraGroup]:
    suffix = f"@{domain}"
    return [group for group in groups if group.email.endswith(suffix)]


def _tally_user_result(result: UserSyncResult, counts: PlanCounts, report: PlanReport) -> None:
    if result.conflict:
        counts.users_conflict += 1
        report.conflicts.append(f"user:{result.email}")
    elif result.created:
        counts.users_create += 1
    elif result.updated:
        counts.users_update += 1
    else:
        counts.users_skip += 1


def _tally_group_result(result: GroupSyncResult, counts: PlanCounts, report: PlanReport) -> None:
    if result.conflict:
        counts.groups_conflict += 1
        report.conflicts.append(f"group:{result.email}")
    elif result.created:
        counts.groups_create += 1
    elif result.updated:
        counts.groups_update += 1
    else:
        counts.groups_skip += 1


def _record_user_result(result: UserSyncResult, report: ApplyReport) -> None:
    if result.conflict:
        report.conflicts.append(f"user:{result.email}")
    elif result.created:
        report.created.append(f"user:{result.email}")
    elif result.updated:
        report.updated.append(f"user:{result.email}")
    else:
        report.skipped.append(f"user:{result.email}")


def _record_group_result(result: GroupSyncResult, report: ApplyReport) -> None:
    if result.conflict:
        report.conflicts.append(f"group:{result.email}")
    elif result.created:
        report.created.append(f"group:{result.email}")
    elif result.updated:
        report.updated.append(f"group:{result.email}")
    else:
        report.skipped.append(f"group:{result.email}")


def _plan_shared_drives(
    blueprint: Blueprint, drive_service: Any, users: list[EntraUser]
) -> dict[str, Any]:
    drives = _desired_drives(blueprint, users)
    to_create = 0
    conflicts = 0
    for drive in drives:
        existing_drive = _find_drive_by_name(drive_service, drive.name)
        if not existing_drive:
            to_create += 1
            continue
        marker = find_file_by_app_properties(
            drive_service,
            app_properties={"gwsynth_id": drive.marker_id, "gwsynth_kind": "drive_marker"},
            drive_id=str(existing_drive.get("id") or ""),
        )
        if marker:
            drive.existing_drive_id = str(existing_drive.get("id") or "")
        else:
            conflicts += 1
    return {"drives": drives, "to_create": to_create, "conflicts": conflicts}


def _plan_folders(blueprint: Blueprint, drive_service: Any, drives: list["_DrivePlan"]) -> int:
    to_create = 0
    for drive in drives:
        if not drive.existing_drive_id and not drive.drive_id:
            to_create += len(drive.folder_paths)
            continue
        for path, stable_id in drive.folder_paths.items():
            props = build_app_properties(
                run_name=blueprint.run.name,
                stable_id=stable_id,
                kind="folder",
                path=path,
            )
            existing = find_file_by_app_properties(
                drive_service,
                app_properties=props,
                drive_id=drive.drive_id or drive.existing_drive_id,
            )
            if not existing:
                to_create += 1
    return to_create


def _plan_docs(
    blueprint: Blueprint, drive_service: Any, drives: list["_DrivePlan"], users: list[EntraUser]
) -> dict[str, int]:
    to_create = 0
    to_update = 0
    for drive in drives:
        if not drive.existing_drive_id and not drive.drive_id:
            to_create += len(drive.docs)
            continue
        for doc in drive.docs:
            existing = find_file_by_app_properties(
                drive_service,
                app_properties={"gwsynth_id": doc.stable_id, "gwsynth_kind": "doc"},
                drive_id=drive.drive_id or drive.existing_drive_id,
            )
            if not existing:
                to_create += 1
            else:
                existing_props = existing.get("appProperties", {}) or {}
                if (
                    existing_props.get("gwsynth_prompt_version")
                    != blueprint.docs.generation.prompt_version
                ):
                    to_update += 1
    if blueprint.drives.my_drive.enabled:
        for _user in users:
            to_create += blueprint.drives.my_drive.docs_per_user
    return {"to_create": to_create, "to_update": to_update}


def _print_plan_summary(report: PlanReport) -> None:
    counts = report.counts
    print("Plan summary")
    print(
        f"- Users: create {counts.users_create}, update {counts.users_update}, "
        f"conflicts {counts.users_conflict}"
    )
    print(
        f"- Groups: create {counts.groups_create}, update {counts.groups_update}, "
        f"conflicts {counts.groups_conflict}"
    )
    print(f"- Licenses: assign {counts.licenses_assign}")
    print(f"- Drives: create {counts.drives_create}, conflicts {counts.drives_conflict}")
    print(f"- Folders: create {counts.folders_create}")
    print(f"- Docs: create {counts.docs_create}, update {counts.docs_update}")
    if report.prerequisites:
        print("Prerequisites:")
        for item in report.prerequisites:
            print(f"- {item}")
    if report.conflicts:
        print("Conflicts:")
        for item in report.conflicts:
            print(f"- {item}")


@dataclass
class _DocPlan:
    stable_id: str
    name: str
    path: str
    archetype: str
    folder_path: str


@dataclass
class _DrivePlan:
    name: str
    department: str
    marker_id: str
    drive_id: str | None
    existing_drive_id: str | None
    folder_paths: dict[str, str]
    docs: list[_DocPlan]


@dataclass
class _DriveResult:
    drive_id: str
    name: str
    department: str
    marker_id: str
    folders: dict[str, str]
    docs: list[_DocPlan]


def _desired_drives(blueprint: Blueprint, users: list[EntraUser]) -> list[_DrivePlan]:
    departments = _departments_from_users(users)
    plans: list[_DrivePlan] = []
    year = datetime.now(UTC).year
    for department in departments:
        for index in range(blueprint.drives.shared_drives.count_per_department):
            name = blueprint.drives.shared_drives.naming.format(
                prefix=blueprint.run.resource_prefix,
                department=department,
            )
            if (
                blueprint.drives.shared_drives.count_per_department > 1
                and "{index}" not in blueprint.drives.shared_drives.naming
            ):
                name = f"{name} {index + 1}"
            marker_id = stable_uuid(blueprint.run.name, "drive_marker", name)
            folder_paths = {}
            for path in blueprint.folders.shared_drive_tree:
                folder_paths[_format_path(path, department, year)] = stable_uuid(
                    blueprint.run.name, "folder", f"{name}:{path}"
                )
            docs = _docs_for_drive(blueprint, name, department, year)
            plans.append(
                _DrivePlan(
                    name=name,
                    department=department,
                    marker_id=marker_id,
                    drive_id=None,
                    existing_drive_id=None,
                    folder_paths=folder_paths,
                    docs=docs,
                )
            )
    return plans


def _docs_for_drive(
    blueprint: Blueprint, drive_name: str, department: str, year: int
) -> list[_DocPlan]:
    docs: list[_DocPlan] = []
    for archetype in blueprint.docs.archetypes:
        folder_path = _folder_for_archetype(archetype, department, year)
        name = _title_for_archetype(archetype, department)
        path = f"{folder_path}/{name}"
        stable_id = stable_uuid(blueprint.run.name, "doc", f"{drive_name}:{path}")
        docs.append(
            _DocPlan(
                stable_id=stable_id,
                name=name,
                path=path,
                archetype=archetype,
                folder_path=folder_path,
            )
        )
    return docs


def _folder_for_archetype(archetype: str, department: str, year: int) -> str:
    mapping = {
        "policy": "02 - Process & Policy",
        "runbook": "02 - Process & Policy",
        "incident_report": f"01 - Projects/{department}",
        "meeting_notes": f"03 - Meeting Notes/{year}",
        "prd": f"01 - Projects/{department}",
        "onboarding": "00 - Admin",
        "qbr": f"01 - Projects/{department}",
    }
    return mapping.get(archetype, f"01 - Projects/{department}")


def _title_for_archetype(archetype: str, department: str) -> str:
    title_map = {
        "policy": "Policy Overview",
        "prd": "Product Requirements",
        "runbook": "Operational Runbook",
        "incident_report": "Incident Report",
        "meeting_notes": "Meeting Notes",
        "onboarding": "Onboarding Guide",
        "qbr": "Quarterly Business Review",
    }
    base = title_map.get(archetype, "Team Document")
    return f"{base} - {department}"


def _departments_from_users(users: list[EntraUser]) -> list[str]:
    departments = sorted({user.department or "General" for user in users})
    return departments or ["General"]


def _format_path(path: str, department: str, year: int) -> str:
    return path.format(department=department, year=year)


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


def _ensure_shared_drives(
    blueprint: Blueprint,
    drive_service: Any,
    users: list[EntraUser],
    report: ApplyReport,
    dry_run: bool = False,
) -> list[_DriveResult]:
    plans = _desired_drives(blueprint, users)
    results: list[_DriveResult] = []
    for plan in plans:
        drive = _find_drive_by_name(drive_service, plan.name)
        existing_id = str(drive.get("id")) if drive else None
        marker = None
        if drive:
            marker = find_file_by_app_properties(
                drive_service,
                app_properties={"gwsynth_id": plan.marker_id, "gwsynth_kind": "drive_marker"},
                drive_id=existing_id,
            )
        if drive and marker:
            plan.existing_drive_id = existing_id
            assert existing_id is not None
            results.append(
                _DriveResult(
                    drive_id=existing_id,
                    name=plan.name,
                    department=plan.department,
                    marker_id=plan.marker_id,
                    folders={},
                    docs=plan.docs,
                )
            )
            continue
        if drive and not marker:
            report.conflicts.append(f"drive:{plan.name}")
            continue
        if dry_run:
            continue
        sync = ensure_shared_drive(
            drive_service,
            drive_name=plan.name,
            request_id=stable_uuid(blueprint.run.name, "drive_request", plan.name),
            dry_run=False,
        )
        if not sync.drive_id:
            report.conflicts.append(f"drive:{plan.name}")
            continue
        marker_id = ensure_drive_marker(
            drive_service,
            drive_id=sync.drive_id,
            run_name=blueprint.run.name,
            stable_id=plan.marker_id,
            prefix=blueprint.run.resource_prefix,
            dry_run=False,
        )
        if marker_id:
            report.created.append(f"drive:{plan.name}")
            results.append(
                _DriveResult(
                    drive_id=sync.drive_id,
                    name=plan.name,
                    department=plan.department,
                    marker_id=plan.marker_id,
                    folders={},
                    docs=plan.docs,
                )
            )
    return results


def _ensure_shared_drive_permissions(
    blueprint: Blueprint,
    drive_service: Any,
    drives: list[_DriveResult],
    groups: list[EntraGroup],
    users: list[EntraUser],
) -> None:
    dept_groups = _department_group_map(groups)
    all_hands = _find_all_hands_group(groups)
    owners = _department_owner(users)
    for drive in drives:
        dept_group = dept_groups.get(_normalize(drive.department))
        if dept_group:
            ensure_permission(
                drive_service,
                file_id=drive.drive_id,
                role=blueprint.sharing.shared_drive_defaults.department_group_role,
                permission_type="group",
                email=dept_group,
                drive_id=drive.drive_id,
                dry_run=False,
            )
        owner = owners.get(drive.department)
        if owner:
            ensure_permission(
                drive_service,
                file_id=drive.drive_id,
                role="organizer",
                permission_type="user",
                email=owner.email,
                drive_id=drive.drive_id,
                dry_run=False,
            )
        ensure_permission(
            drive_service,
            file_id=drive.drive_id,
            role="reader",
            permission_type="group",
            email=blueprint.sharing.reviewer_group_email,
            drive_id=drive.drive_id,
            dry_run=False,
        )
        if all_hands:
            ensure_permission(
                drive_service,
                file_id=drive.drive_id,
                role=blueprint.sharing.shared_drive_defaults.all_hands_group_role,
                permission_type="group",
                email=all_hands,
                drive_id=drive.drive_id,
                dry_run=False,
            )


def _ensure_shared_drive_folders(
    blueprint: Blueprint, drive_service: Any, drives: list[_DriveResult], report: ApplyReport
) -> None:
    year = datetime.now(UTC).year
    for drive in drives:
        path_to_id: dict[str, str] = {}
        for raw_path in blueprint.folders.shared_drive_tree:
            path = _format_path(raw_path, drive.department, year)
            parent_id = None
            parts = [p for p in path.split("/") if p]
            running_path = ""
            for part in parts:
                running_path = f"{running_path}/{part}" if running_path else part
                stable_id = stable_uuid(
                    blueprint.run.name, "folder", f"{drive.name}:{running_path}"
                )
                props = build_app_properties(
                    run_name=blueprint.run.name,
                    stable_id=stable_id,
                    kind="folder",
                    path=running_path,
                )
                folder_id = ensure_folder(
                    drive_service,
                    name=part,
                    parent_id=parent_id,
                    drive_id=drive.drive_id,
                    app_properties=props,
                    dry_run=False,
                )
                if folder_id:
                    path_to_id[running_path] = folder_id
                    parent_id = folder_id
        drive.folders.update(path_to_id)
        if path_to_id:
            report.updated.append(f"folders:{drive.name}")


def _ensure_shared_drive_docs(
    blueprint: Blueprint,
    drives: list[_DriveResult],
    users: list[EntraUser],
    groups: list[EntraGroup],
    regen: bool,
    report: ApplyReport,
) -> None:
    llm_config = LlmConfig(
        model=os.environ.get("OPENAI_MODEL", "gpt-5.2"),
        max_tokens=blueprint.docs.generation.max_tokens,
        temperature=blueprint.docs.generation.temperature,
        cache_dir=blueprint.docs.generation.cache_dir,
        prompt_version=blueprint.docs.generation.prompt_version,
    )
    owner_by_department = _department_owner(users)
    all_hands = _find_all_hands_group(groups)
    for drive in drives:
        owner = owner_by_department.get(drive.department)
        if not owner:
            continue
        drive_service = drive_service_for_user(owner.email)
        docs_service = _docs_service_for_user(owner.email)
        for doc in drive.docs:
            folder_id = drive.folders.get(doc.folder_path)
            props = build_app_properties(
                run_name=blueprint.run.name,
                stable_id=doc.stable_id,
                kind="doc",
                path=doc.path,
                prompt_version=blueprint.docs.generation.prompt_version,
            )
            file_id, created = ensure_doc_file(
                drive_service,
                name=doc.name,
                parent_id=folder_id,
                drive_id=drive.drive_id,
                app_properties=props,
                dry_run=False,
            )
            if not file_id:
                continue
            existing = find_file_by_app_properties(
                drive_service,
                app_properties={"gwsynth_id": doc.stable_id, "gwsynth_kind": "doc"},
                drive_id=drive.drive_id,
            )
            if not created and existing:
                app_props = existing.get("appProperties", {}) or {}
                if (
                    app_props.get("gwsynth_prompt_version")
                    == blueprint.docs.generation.prompt_version
                    and app_props.get("gwsynth_content_hash")
                ):
                    continue
            content = generate_doc_content(
                config=llm_config,
                stable_doc_id=doc.stable_id,
                archetype=doc.archetype,
                company_name=_company_name_from_run(blueprint.run.name),
                department=drive.department,
                title_hint=doc.name,
                run_name=blueprint.run.name,
                regen=regen,
            )
            apply_doc_content(docs_service, document_id=file_id, content=content, dry_run=False)
            props["gwsynth_content_hash"] = content_hash(_flatten_doc_content(content))
            props["gwsynth_prompt_version"] = blueprint.docs.generation.prompt_version
            drive_service.files().update(
                fileId=file_id,
                body={"appProperties": props},
                supportsAllDrives=True,
            ).execute()
            if (
                doc.archetype == "policy"
                and blueprint.sharing.doc_acl_rules.policy_docs_share_to_all_hands
                and all_hands
            ):
                ensure_permission(
                    drive_service,
                    file_id=file_id,
                    role="reader",
                    permission_type="group",
                    email=all_hands,
                    drive_id=drive.drive_id,
                    dry_run=False,
                )
            report.updated.append(f"doc:{file_id}")


def _ensure_my_drive_docs(
    blueprint: Blueprint,
    users: list[EntraUser],
    regen: bool,
    report: ApplyReport,
    graph: GraphClient,
) -> None:
    if not blueprint.drives.my_drive.enabled:
        return
    llm_config = LlmConfig(
        model=os.environ.get("OPENAI_MODEL", "gpt-5.2"),
        max_tokens=blueprint.docs.generation.max_tokens,
        temperature=blueprint.docs.generation.temperature,
        cache_dir=blueprint.docs.generation.cache_dir,
        prompt_version=blueprint.docs.generation.prompt_version,
    )
    for user in users:
        drive_service = drive_service_for_user(user.email)
        docs_service = _docs_service_for_user(user.email)
        root_path = f"{blueprint.run.resource_prefix} My Work"
        root_id = ensure_folder(
            drive_service,
            name=root_path,
            parent_id=None,
            drive_id=None,
            app_properties=build_app_properties(
                run_name=blueprint.run.name,
                stable_id=stable_uuid(blueprint.run.name, "mydrive_root", user.email),
                kind="mydrive_root",
                path=root_path,
            ),
            dry_run=False,
        )
        rng = _user_rng(blueprint.run.seed, user.email)
        for idx in range(blueprint.drives.my_drive.docs_per_user):
            archetype = rng.choice(list(blueprint.docs.archetypes))
            name = f"{_title_for_archetype(archetype, user.department)} ({idx + 1})"
            path = f"{root_path}/{name}"
            stable_id = stable_uuid(blueprint.run.name, "doc", f"{user.email}:{path}")
            props = build_app_properties(
                run_name=blueprint.run.name,
                stable_id=stable_id,
                kind="doc",
                path=path,
                prompt_version=blueprint.docs.generation.prompt_version,
            )
            file_id, created = ensure_doc_file(
                drive_service,
                name=name,
                parent_id=root_id,
                drive_id=None,
                app_properties=props,
                dry_run=False,
            )
            if not file_id:
                continue
            existing = find_file_by_app_properties(
                drive_service,
                app_properties={"gwsynth_id": stable_id, "gwsynth_kind": "doc"},
                drive_id=None,
            )
            if not created and existing:
                app_props = existing.get("appProperties", {}) or {}
                if (
                    app_props.get("gwsynth_prompt_version")
                    == blueprint.docs.generation.prompt_version
                    and app_props.get("gwsynth_content_hash")
                ):
                    continue
            content = generate_doc_content(
                config=llm_config,
                stable_doc_id=stable_id,
                archetype=archetype,
                company_name=_company_name_from_run(blueprint.run.name),
                department=user.department,
                title_hint=name,
                run_name=blueprint.run.name,
                regen=regen,
            )
            apply_doc_content(docs_service, document_id=file_id, content=content, dry_run=False)
            props["gwsynth_content_hash"] = content_hash(_flatten_doc_content(content))
            props["gwsynth_prompt_version"] = blueprint.docs.generation.prompt_version
            drive_service.files().update(fileId=file_id, body={"appProperties": props}).execute()
            ensure_permission(
                drive_service,
                file_id=file_id,
                role="reader",
                permission_type="group",
                email=blueprint.sharing.reviewer_group_email,
                drive_id=None,
                dry_run=False,
            )
            if blueprint.sharing.doc_acl_rules.my_drive_docs_share_with_manager:
                manager_email = graph.get_manager_email(user.id)
                if manager_email and manager_email.endswith(
                    f"@{blueprint.tenant_guard.google_domain}"
                ):
                    ensure_permission(
                        drive_service,
                        file_id=file_id,
                        role="reader",
                        permission_type="user",
                        email=manager_email,
                        drive_id=None,
                        dry_run=False,
                    )
            report.updated.append(f"mydrive_doc:{file_id}")


def _docs_service_for_user(email: str) -> Any:
    from .google_auth import docs_service_for_user

    return docs_service_for_user(email)


def _department_group_map(groups: list[EntraGroup]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in groups:
        key = _normalize(group.display_name)
        mapping[key] = group.email
    return mapping


def _find_all_hands_group(groups: list[EntraGroup]) -> str | None:
    for group in groups:
        name = _normalize(group.display_name)
        if "all hands" in name or "allhands" in name:
            return group.email
    return None


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())


def _department_owner(users: list[EntraUser]) -> dict[str, EntraUser]:
    owners: dict[str, EntraUser] = {}
    for user in users:
        if user.department not in owners:
            owners[user.department] = user
    return owners


def _company_name_from_run(run_name: str) -> str:
    return " ".join(word.capitalize() for word in run_name.replace("-", " ").split())


def _user_rng(seed: int, email: str) -> random.Random:
    return random.Random(int(content_hash(f"{seed}:{email}")[:8], 16))


def _flatten_doc_content(content: DocContent) -> str:
    parts = [content.title, content.summary]
    for section in content.sections:
        parts.append(section.heading)
        parts.extend(section.paragraphs)
        parts.extend(section.bullets)
    parts.extend(content.metadata)
    return "\n".join(parts)
