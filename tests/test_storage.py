from __future__ import annotations

from dreamhack_local.app import build_app_context


def test_database_upsert_merges_and_preserves_first_seen():
    context = build_app_context()
    first = context.repository.upsert_challenge(
        {
            "challenge_id": 321,
            "title": "Initial Title",
            "slug": "initial-title",
            "url": "https://dreamhack.io/wargame/challenges/321",
            "category": "web",
            "category_display": "Web",
            "difficulty": 2,
            "difficulty_label": "2",
            "first_seen": "2026-01-01T00:00:00+00:00",
        }
    )
    second = context.repository.upsert_challenge(
        {
            "challenge_id": 321,
            "title": "Updated Title",
            "slug": "updated-title",
            "url": "https://dreamhack.io/wargame/challenges/321",
            "description_text": "Saved description",
        }
    )

    assert first.first_seen == second.first_seen
    assert second.title == "Updated Title"
    assert second.description_text == "Saved description"
    assert context.repository.resolve_challenge("321").challenge_id == 321
    assert context.repository.resolve_challenge("updated-title").challenge_id == 321
