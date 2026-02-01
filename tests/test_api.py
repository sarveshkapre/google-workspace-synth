from __future__ import annotations

import importlib


def _build_client(tmp_path, monkeypatch):
    monkeypatch.setenv("GWSYNTH_DB_PATH", str(tmp_path / "test.db"))
    import gwsynth.main

    importlib.reload(gwsynth.main)
    app = gwsynth.main.create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def test_end_to_end(tmp_path, monkeypatch):
    client = _build_client(tmp_path, monkeypatch)

    user_resp = client.post(
        "/users", json={"email": "demo@example.com", "display_name": "Demo User"}
    )
    assert user_resp.status_code == 201
    user = user_resp.get_json()
    assert user["email"] == "demo@example.com"

    group_resp = client.post("/groups", json={"name": "Team", "description": "Core team"})
    assert group_resp.status_code == 201
    group = group_resp.get_json()
    client.post(f"/groups/{group['id']}/members", json={"user_id": user["id"]})

    folder = client.post(
        "/items",
        json={"name": "Root", "item_type": "folder", "owner_user_id": user["id"]},
    ).get_json()
    doc = client.post(
        "/items",
        json={
            "name": "Spec",
            "item_type": "doc",
            "parent_id": folder["id"],
            "owner_user_id": user["id"],
            "content_text": "Hello",
        },
    ).get_json()

    updated = client.put(
        f"/items/{doc['id']}/content", json={"content_text": "Updated"}
    ).get_json()
    assert updated["content_text"] == "Updated"

    permission = client.post(
        f"/items/{doc['id']}/permissions",
        json={"principal_type": "group", "principal_id": group["id"], "role": "viewer"},
    ).get_json()
    assert permission["role"] == "viewer"

    link = client.post(
        f"/items/{doc['id']}/share-links", json={"role": "viewer"}
    ).get_json()
    assert link["token"]

    results = client.get("/search", query_string={"q": "Spec"}).get_json()
    assert results["items"]
