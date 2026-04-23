from __future__ import annotations

from pathlib import Path

import requests

from dreamhack_local.utils.files import infer_filename
from dreamhack_local.utils.normalization import normalize_category, normalize_difficulty
from dreamhack_local.utils.paths import challenge_workspace_path


def test_normalization_strictness():
    assert normalize_category("Cryptography") == "crypto"
    assert normalize_category("2023 web chal") is None
    assert normalize_difficulty("Level 3") == 3
    assert normalize_difficulty("3760") is None


def test_filename_inference_prefers_content_disposition():
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Disposition"] = 'attachment; filename="challenge.zip"'
    filename = infer_filename(response, "https://example.com/download?id=1")
    assert filename == "challenge.zip"


def test_workspace_path_generation(tmp_path):
    path = challenge_workspace_path(tmp_path, category="crypto", difficulty=2, title="My Challenge", challenge_id=123)
    assert path == tmp_path / "Cryptography" / "Level_2" / "My_Challenge"
