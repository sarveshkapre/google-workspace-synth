from __future__ import annotations

import pytest

from gwsynth.real.blueprint import default_blueprint_dict, load_blueprint, write_default_blueprint


def test_default_blueprint_roundtrip(tmp_path):
    path = tmp_path / "blueprint.yaml"
    write_default_blueprint(str(path))
    with pytest.raises(ValueError):
        load_blueprint(str(path))


def test_blueprint_loads_with_license_values(tmp_path):
    data = default_blueprint_dict()
    data["licenses"]["product_id"] = "PROD"
    data["licenses"]["sku_id"] = "SKU"
    path = tmp_path / "blueprint.yaml"
    import yaml

    path.write_text(yaml.safe_dump(data, sort_keys=False))
    blueprint = load_blueprint(str(path))
    assert blueprint.version == 1
    assert blueprint.run.name
    assert blueprint.docs.archetypes


def test_blueprint_requires_license_fields(tmp_path):
    data = default_blueprint_dict()
    data["licenses"]["product_id"] = ""
    data["licenses"]["sku_id"] = ""
    path = tmp_path / "blueprint.yaml"
    import yaml

    path.write_text(yaml.safe_dump(data, sort_keys=False))
    with pytest.raises(ValueError):
        load_blueprint(str(path))
