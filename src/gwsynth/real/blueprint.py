from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TenantGuard:
    google_customer_id: str
    google_domain: str


@dataclass(frozen=True)
class RunConfig:
    name: str
    seed: int
    resource_prefix: str
    ou_path: str


@dataclass(frozen=True)
class EntraConfig:
    user_filter: str
    group_filter: str
    max_users: int
    max_groups: int


@dataclass(frozen=True)
class MappingConfig:
    email_source: str
    require_domain_match: bool


@dataclass(frozen=True)
class IdentityConfig:
    entra: EntraConfig
    mapping: MappingConfig


@dataclass(frozen=True)
class LicenseConfig:
    assign: bool
    product_id: str
    sku_id: str


@dataclass(frozen=True)
class SharedDriveConfig:
    count_per_department: int
    departments_source: str
    naming: str


@dataclass(frozen=True)
class MyDriveConfig:
    enabled: bool
    docs_per_user: int


@dataclass(frozen=True)
class DrivesConfig:
    shared_drives: SharedDriveConfig
    my_drive: MyDriveConfig


@dataclass(frozen=True)
class FoldersConfig:
    shared_drive_tree: tuple[str, ...]


@dataclass(frozen=True)
class DocsGenerationConfig:
    mode: str
    max_tokens: int
    temperature: float
    cache_dir: str
    prompt_version: str


@dataclass(frozen=True)
class DocsConfig:
    archetypes: tuple[str, ...]
    generation: DocsGenerationConfig


@dataclass(frozen=True)
class SharedDriveDefaults:
    department_group_role: str
    all_hands_group_role: str


@dataclass(frozen=True)
class DocAclRules:
    my_drive_docs_share_with_manager: bool
    policy_docs_share_to_all_hands: bool


@dataclass(frozen=True)
class SharingConfig:
    reviewer_group_email: str
    shared_drive_defaults: SharedDriveDefaults
    doc_acl_rules: DocAclRules


@dataclass(frozen=True)
class Blueprint:
    version: int
    tenant_guard: TenantGuard
    run: RunConfig
    identity: IdentityConfig
    licenses: LicenseConfig
    drives: DrivesConfig
    folders: FoldersConfig
    docs: DocsConfig
    sharing: SharingConfig

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "tenant_guard": {
                "google_customer_id": self.tenant_guard.google_customer_id,
                "google_domain": self.tenant_guard.google_domain,
            },
            "run": {
                "name": self.run.name,
                "seed": self.run.seed,
                "resource_prefix": self.run.resource_prefix,
                "ou_path": self.run.ou_path,
            },
            "identity": {
                "entra": {
                    "user_filter": self.identity.entra.user_filter,
                    "group_filter": self.identity.entra.group_filter,
                    "max_users": self.identity.entra.max_users,
                    "max_groups": self.identity.entra.max_groups,
                },
                "mapping": {
                    "email_source": self.identity.mapping.email_source,
                    "require_domain_match": self.identity.mapping.require_domain_match,
                },
            },
            "licenses": {
                "assign": self.licenses.assign,
                "product_id": self.licenses.product_id,
                "sku_id": self.licenses.sku_id,
            },
            "drives": {
                "shared_drives": {
                    "count_per_department": self.drives.shared_drives.count_per_department,
                    "departments_source": self.drives.shared_drives.departments_source,
                    "naming": self.drives.shared_drives.naming,
                },
                "my_drive": {
                    "enabled": self.drives.my_drive.enabled,
                    "docs_per_user": self.drives.my_drive.docs_per_user,
                },
            },
            "folders": {"shared_drive_tree": list(self.folders.shared_drive_tree)},
            "docs": {
                "archetypes": list(self.docs.archetypes),
                "generation": {
                    "mode": self.docs.generation.mode,
                    "max_tokens": self.docs.generation.max_tokens,
                    "temperature": self.docs.generation.temperature,
                    "cache_dir": self.docs.generation.cache_dir,
                    "prompt_version": self.docs.generation.prompt_version,
                },
            },
            "sharing": {
                "reviewer_group_email": self.sharing.reviewer_group_email,
                "shared_drive_defaults": {
                    "department_group_role": (
                        self.sharing.shared_drive_defaults.department_group_role
                    ),
                    "all_hands_group_role": (
                        self.sharing.shared_drive_defaults.all_hands_group_role
                    ),
                },
                "doc_acl_rules": {
                    "my_drive_docs_share_with_manager": (
                        self.sharing.doc_acl_rules.my_drive_docs_share_with_manager
                    ),
                    "policy_docs_share_to_all_hands": (
                        self.sharing.doc_acl_rules.policy_docs_share_to_all_hands
                    ),
                },
            },
        }


DEFAULT_ARCHETYPES = (
    "policy",
    "prd",
    "runbook",
    "incident_report",
    "meeting_notes",
    "onboarding",
    "qbr",
)


def default_blueprint() -> Blueprint:
    return Blueprint(
        version=1,
        tenant_guard=TenantGuard(
            google_customer_id="C0123abc",
            google_domain="company.com",
        ),
        run=RunConfig(
            name="northwind-synth",
            seed=1337,
            resource_prefix="[synth:northwind]",
            ou_path="/Synthetic/Northwind",
        ),
        identity=IdentityConfig(
            entra=EntraConfig(
                user_filter="accountEnabled eq true",
                group_filter="",
                max_users=100,
                max_groups=50,
            ),
            mapping=MappingConfig(
                email_source="mail_or_upn",
                require_domain_match=True,
            ),
        ),
        licenses=LicenseConfig(
            assign=True,
            product_id="<required>",
            sku_id="<required>",
        ),
        drives=DrivesConfig(
            shared_drives=SharedDriveConfig(
                count_per_department=1,
                departments_source="entra.department",
                naming="{prefix} {department} Shared Drive",
            ),
            my_drive=MyDriveConfig(
                enabled=True,
                docs_per_user=5,
            ),
        ),
        folders=FoldersConfig(
            shared_drive_tree=(
                "00 - Admin",
                "01 - Projects/{department}",
                "02 - Process & Policy",
                "03 - Meeting Notes/{year}",
            )
        ),
        docs=DocsConfig(
            archetypes=DEFAULT_ARCHETYPES,
            generation=DocsGenerationConfig(
                mode="openai_cached",
                max_tokens=1800,
                temperature=0.4,
                cache_dir="./data/llm_cache",
                prompt_version="v1",
            ),
        ),
        sharing=SharingConfig(
            reviewer_group_email="synth-reviewers@company.com",
            shared_drive_defaults=SharedDriveDefaults(
                department_group_role="organizer",
                all_hands_group_role="reader",
            ),
            doc_acl_rules=DocAclRules(
                my_drive_docs_share_with_manager=True,
                policy_docs_share_to_all_hands=True,
            ),
        ),
    )


def default_blueprint_dict() -> dict[str, Any]:
    return default_blueprint().to_dict()


def write_default_blueprint(path: str) -> None:
    target = Path(path)
    payload = default_blueprint_dict()
    yaml = _load_yaml()
    target.write_text(yaml.safe_dump(payload, sort_keys=False))


def load_blueprint(path: str) -> Blueprint:
    yaml = _load_yaml()
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("Blueprint must be a YAML object")
    return _parse_blueprint(data)


def _parse_blueprint(data: dict[str, Any]) -> Blueprint:
    version = _require_int(data, "version")
    if version != 1:
        raise ValueError("Blueprint version must be 1")

    tenant_guard = _require_dict(data, "tenant_guard")
    run = _require_dict(data, "run")
    identity = _require_dict(data, "identity")
    licenses = _require_dict(data, "licenses")
    drives = _require_dict(data, "drives")
    folders = _require_dict(data, "folders")
    docs = _require_dict(data, "docs")
    sharing = _require_dict(data, "sharing")

    blueprint = Blueprint(
        version=version,
        tenant_guard=TenantGuard(
            google_customer_id=_require_str(tenant_guard, "google_customer_id"),
            google_domain=_require_str(tenant_guard, "google_domain"),
        ),
        run=RunConfig(
            name=_require_str(run, "name"),
            seed=_require_int(run, "seed"),
            resource_prefix=_require_str(run, "resource_prefix"),
            ou_path=_require_str(run, "ou_path"),
        ),
        identity=_parse_identity(identity),
        licenses=_parse_licenses(licenses),
        drives=_parse_drives(drives),
        folders=_parse_folders(folders),
        docs=_parse_docs(docs),
        sharing=_parse_sharing(sharing),
    )
    _validate_blueprint(blueprint)
    return blueprint


def _parse_identity(data: dict[str, Any]) -> IdentityConfig:
    entra = _require_dict(data, "entra")
    mapping = _require_dict(data, "mapping")
    return IdentityConfig(
        entra=EntraConfig(
            user_filter=_optional_str(entra, "user_filter") or "",
            group_filter=_optional_str(entra, "group_filter") or "",
            max_users=_require_int(entra, "max_users"),
            max_groups=_require_int(entra, "max_groups"),
        ),
        mapping=MappingConfig(
            email_source=_require_str(mapping, "email_source"),
            require_domain_match=_require_bool(mapping, "require_domain_match"),
        ),
    )


def _parse_licenses(data: dict[str, Any]) -> LicenseConfig:
    return LicenseConfig(
        assign=_require_bool(data, "assign"),
        product_id=_optional_str(data, "product_id") or "",
        sku_id=_optional_str(data, "sku_id") or "",
    )


def _parse_drives(data: dict[str, Any]) -> DrivesConfig:
    shared_drives = _require_dict(data, "shared_drives")
    my_drive = _require_dict(data, "my_drive")
    return DrivesConfig(
        shared_drives=SharedDriveConfig(
            count_per_department=_require_int(shared_drives, "count_per_department"),
            departments_source=_require_str(shared_drives, "departments_source"),
            naming=_require_str(shared_drives, "naming"),
        ),
        my_drive=MyDriveConfig(
            enabled=_require_bool(my_drive, "enabled"),
            docs_per_user=_require_int(my_drive, "docs_per_user"),
        ),
    )


def _parse_folders(data: dict[str, Any]) -> FoldersConfig:
    tree = data.get("shared_drive_tree", [])
    if not isinstance(tree, list) or not all(isinstance(x, str) for x in tree):
        raise ValueError("folders.shared_drive_tree must be a list of strings")
    return FoldersConfig(shared_drive_tree=tuple(tree))


def _parse_docs(data: dict[str, Any]) -> DocsConfig:
    archetypes = data.get("archetypes", [])
    if not isinstance(archetypes, list) or not all(isinstance(x, str) for x in archetypes):
        raise ValueError("docs.archetypes must be a list of strings")
    generation = _require_dict(data, "generation")
    return DocsConfig(
        archetypes=tuple(archetypes),
        generation=DocsGenerationConfig(
            mode=_require_str(generation, "mode"),
            max_tokens=_require_int(generation, "max_tokens"),
            temperature=_require_float(generation, "temperature"),
            cache_dir=_require_str(generation, "cache_dir"),
            prompt_version=_require_str(generation, "prompt_version"),
        ),
    )


def _parse_sharing(data: dict[str, Any]) -> SharingConfig:
    shared_drive_defaults = _require_dict(data, "shared_drive_defaults")
    doc_acl_rules = _require_dict(data, "doc_acl_rules")
    return SharingConfig(
        reviewer_group_email=_require_str(data, "reviewer_group_email"),
        shared_drive_defaults=SharedDriveDefaults(
            department_group_role=_require_str(shared_drive_defaults, "department_group_role"),
            all_hands_group_role=_require_str(shared_drive_defaults, "all_hands_group_role"),
        ),
        doc_acl_rules=DocAclRules(
            my_drive_docs_share_with_manager=_require_bool(
                doc_acl_rules, "my_drive_docs_share_with_manager"
            ),
            policy_docs_share_to_all_hands=_require_bool(
                doc_acl_rules, "policy_docs_share_to_all_hands"
            ),
        ),
    )


def _validate_blueprint(blueprint: Blueprint) -> None:
    if blueprint.identity.mapping.email_source not in {"mail_or_upn"}:
        raise ValueError("identity.mapping.email_source must be 'mail_or_upn'")
    if blueprint.licenses.assign:
        if not blueprint.licenses.product_id or blueprint.licenses.product_id == "<required>":
            raise ValueError("licenses.product_id is required when licenses.assign is true")
        if not blueprint.licenses.sku_id or blueprint.licenses.sku_id == "<required>":
            raise ValueError("licenses.sku_id is required when licenses.assign is true")
    if blueprint.drives.shared_drives.count_per_department < 1:
        raise ValueError("drives.shared_drives.count_per_department must be >= 1")
    if blueprint.drives.my_drive.docs_per_user < 0:
        raise ValueError("drives.my_drive.docs_per_user must be >= 0")
    if blueprint.docs.generation.mode not in {"openai_cached"}:
        raise ValueError("docs.generation.mode must be 'openai_cached'")
    if blueprint.docs.generation.max_tokens <= 0:
        raise ValueError("docs.generation.max_tokens must be > 0")
    if not (0.0 <= blueprint.docs.generation.temperature <= 2.0):
        raise ValueError("docs.generation.temperature must be between 0 and 2")
    if not blueprint.docs.archetypes:
        raise ValueError("docs.archetypes must not be empty")
    if not blueprint.sharing.reviewer_group_email:
        raise ValueError("sharing.reviewer_group_email is required")


def _require_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip()


def _require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _require_float(data: dict[str, Any], key: str) -> float:
    value = data.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _require_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _load_yaml() -> Any:
    import importlib

    return importlib.import_module("yaml")
