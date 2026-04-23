from __future__ import annotations

from pathlib import Path

from dreamhack_local.crawler.parser import parse_detail, parse_listing


def test_listing_parser_avoids_arbitrary_text_leakage():
    html_text = Path("tests/fixtures/listing_sample.html").read_text(encoding="utf-8")
    items, warnings = parse_listing(html_text, base_url="https://dreamhack.io")

    assert warnings == []
    assert len(items) == 2

    first, second = items
    assert first.challenge_id == 123
    assert first.category == "web"
    assert first.difficulty == 4
    assert first.status == "solved"
    assert first.author == "alice"

    assert second.challenge_id == 124
    assert second.category is None
    assert second.difficulty is None
    assert second.title == "Mystery Parsing"


def test_detail_parser_extracts_description_and_downloads():
    html_text = Path("tests/fixtures/detail_sample.html").read_text(encoding="utf-8")
    detail = parse_detail(html_text, challenge_id=123, url="https://dreamhack.io/wargame/challenges/123")

    assert detail.challenge_id == 123
    assert detail.title == "Neat Web Challenge"
    assert detail.category == "web"
    assert detail.difficulty == 4
    assert detail.author == "alice"
    assert detail.solvers == 314
    assert "Hello world." in detail.description_text
    assert detail.downloads[0].url.startswith("https://files.example.com/attachment.zip")
