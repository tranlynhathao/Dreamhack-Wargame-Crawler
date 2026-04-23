from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dreamhack_local.app import build_app_context
from dreamhack_local.cli.app import app


def test_cli_list_and_config(tmp_path):
    context = build_app_context()
    context.repository.upsert_challenge(
        {
            "challenge_id": 77,
            "title": "CLI Sample",
            "slug": "cli-sample",
            "url": "https://dreamhack.io/wargame/challenges/77",
            "category": "crypto",
            "category_display": "Cryptography",
            "difficulty": 3,
            "difficulty_label": "3",
        }
    )

    runner = CliRunner()
    list_result = runner.invoke(app, ["list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.stdout)
    assert payload[0]["challenge_id"] == 77

    new_workspace = tmp_path / "alt-workspace"
    config_result = runner.invoke(app, ["config", "set", "workspace", str(new_workspace), "--json"])
    assert config_result.exit_code == 0
    config_payload = json.loads(config_result.stdout)
    assert Path(config_payload["workspace_root"]) == new_workspace.resolve()
