from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from dreamhack_local.api.app import create_api_app


def test_api_smoke_routes():
    app = create_api_app()
    context = app.state.context
    context.repository.upsert_challenge(
        {
            "challenge_id": 55,
            "title": "API Sample",
            "slug": "api-sample",
            "url": "https://dreamhack.io/wargame/challenges/55",
            "category": "web",
            "category_display": "Web",
            "difficulty": 1,
            "difficulty_label": "1",
            "local_path": str(context.settings.workspace_root),
        }
    )
    opened: list[str] = []
    context.challenge_service.open_folder = lambda **_: (
        opened.append(str(context.settings.workspace_root)) or Path(context.settings.workspace_root)
    )

    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/session/test").status_code == 200
    assert client.get("/api/challenges").status_code == 200
    challenges = client.get("/api/challenges").json()
    assert challenges[0]["challenge_id"] == 55
    detail = client.get("/api/challenges/55")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["challenge"]["challenge_id"] == 55
    assert detail_payload["files"] == []
    assert client.get("/api/settings").status_code == 200
    stats = client.get("/api/stats").json()
    assert stats["challenges_total"] == 1
    assert stats["difficulties"]["1"] == 1
    assert client.post("/api/doctor").status_code == 200
    open_folder = client.post("/api/open-folder", json={"challenge_id": "55"})
    assert open_folder.status_code == 200
    assert open_folder.json()["path"] == str(context.settings.workspace_root)
    assert opened == [str(context.settings.workspace_root)]
