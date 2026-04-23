"""Typer CLI for local crawling and downloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(help="DreamHack local crawler, downloader, and localhost API.")
session_app = typer.Typer(help="Inspect and manage the stored DreamHack session.")
crawl_app = typer.Typer(help="Crawl listing pages and challenge detail pages.")
config_app = typer.Typer(help="Persist local application settings.")
export_app = typer.Typer(help="Export compatibility artifacts.")

app.add_typer(session_app, name="session")
app.add_typer(crawl_app, name="crawl")
app.add_typer(config_app, name="config")
app.add_typer(export_app, name="export")


def emit(payload: Any, *, as_json: bool = False) -> None:
    if as_json:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        return
    if isinstance(payload, str):
        typer.echo(payload)
        return
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


def get_context():
    try:
        from dreamhack_local.app import build_app_context
    except ModuleNotFoundError as exc:
        typer.echo(
            "Project dependencies are not installed for this Python interpreter. "
            'Use a local virtualenv, for example: `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e ".[dev]"`',
            err=True,
        )
        raise typer.Exit(code=1) from exc
    return build_app_context()


def downloaded_filter(downloaded: bool, not_downloaded: bool) -> bool | None:
    if downloaded and not_downloaded:
        raise typer.BadParameter("Use only one of --downloaded or --not-downloaded.")
    if downloaded:
        return True
    if not_downloaded:
        return False
    return None


@app.command()
def login(
    cookie: str | None = typer.Option(None, "--cookie", help="Raw Cookie header value."),
    cookie_file: Path | None = typer.Option(
        None, "--cookie-file", help="Cookie header, JSON, or Netscape cookie file."
    ),
    browser: bool = typer.Option(False, "--browser", help="Open a local browser and capture cookies after you log in."),
    refresh: bool = typer.Option(True, "--refresh/--no-refresh", help="Refresh session status after import."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    try:
        if browser:
            result = context.session_service.interactive_browser_login()
        elif cookie:
            result = context.session_service.import_cookie_header(cookie)
        elif cookie_file:
            result = context.session_service.import_cookie_file(cookie_file.expanduser())
        else:
            raise typer.BadParameter("Provide --cookie, --cookie-file, or --browser.")
        context.client.refresh_session()
        if refresh:
            result = context.session_service.refresh_status(context.client)
    except Exception as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1)

    emit(result.model_dump(mode="json"), as_json=as_json)


@session_app.command("status")
def session_status(
    refresh: bool = typer.Option(True, "--refresh/--no-refresh", help="Re-check DreamHack with the stored cookies."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    info = context.session_service.refresh_status(context.client) if refresh else context.session_service.get_status()
    emit(info.model_dump(mode="json"), as_json=as_json)
    if info.status == "invalid":
        raise typer.Exit(code=1)


@session_app.command("clear")
def session_clear(as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON.")) -> None:
    context = get_context()
    info = context.session_service.clear()
    context.client.refresh_session()
    emit(info.model_dump(mode="json"), as_json=as_json)


@crawl_app.command("sync")
def crawl_sync(
    category: str | None = typer.Option(None, "--category", help="Filter by normalized category."),
    difficulty: int | None = typer.Option(None, "--difficulty", help="Filter by normalized difficulty 0-10."),
    status: str | None = typer.Option(None, "--status", help="Filter by DreamHack status."),
    max_pages: int | None = typer.Option(None, "--max-pages", help="Stop after N listing pages."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    result = context.crawl_service.sync(category=category, difficulty=difficulty, status=status, max_pages=max_pages)
    emit(result, as_json=as_json)


@crawl_app.command("challenge")
def crawl_challenge(
    identifier: str = typer.Argument(..., help="Challenge ID or DreamHack URL."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    result = context.crawl_service.crawl_challenge(identifier)
    emit(result, as_json=as_json)


@app.command("list")
def list_challenges(
    category: str | None = typer.Option(None, "--category"),
    difficulty: int | None = typer.Option(None, "--difficulty"),
    status: str | None = typer.Option(None, "--status"),
    author: str | None = typer.Option(None, "--author"),
    downloaded: bool = typer.Option(False, "--downloaded", help="Only downloaded challenges."),
    not_downloaded: bool = typer.Option(False, "--not-downloaded", help="Only not-downloaded challenges."),
    search: str | None = typer.Option(None, "--search", help="Search title, slug, and description text."),
    limit: int = typer.Option(100, "--limit", min=1, max=10_000),
    offset: int = typer.Option(0, "--offset", min=0),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    records = context.challenge_service.list_challenges(
        category=category,
        difficulty=difficulty,
        status=status,
        author=author,
        downloaded=downloaded_filter(downloaded, not_downloaded),
        search=search,
        limit=limit,
        offset=offset,
    )
    emit([record.model_dump(mode="json") for record in records], as_json=as_json)


@app.command()
def show(
    identifier: str = typer.Argument(..., help="Challenge ID, slug, title, or URL."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    challenge = context.challenge_service.get_challenge(identifier)
    if challenge is None:
        typer.echo(f"Challenge {identifier} was not found.")
        raise typer.Exit(code=1)
    payload = challenge.model_dump(mode="json")
    payload["files"] = [
        record.model_dump(mode="json") for record in context.repository.list_challenge_files(challenge.challenge_id)
    ]
    emit(payload, as_json=as_json)


@app.command()
def download(
    identifier: str | None = typer.Argument(None, help="Challenge ID, slug, title, or URL. Omit for bulk download."),
    category: str | None = typer.Option(None, "--category"),
    difficulty: int | None = typer.Option(None, "--difficulty"),
    status: str | None = typer.Option(None, "--status"),
    downloaded: bool = typer.Option(False, "--downloaded", help="Only downloaded challenges for bulk mode."),
    not_downloaded: bool = typer.Option(
        False, "--not-downloaded", help="Only not-downloaded challenges for bulk mode."
    ),
    search: str | None = typer.Option(None, "--search"),
    mode: str = typer.Option("resume", "--mode", help="skip, overwrite, or resume"),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    mode = mode.lower()
    if mode not in {"skip", "overwrite", "resume"}:
        typer.echo("Mode must be one of: skip, overwrite, resume.")
        raise typer.Exit(code=1)

    if identifier:
        result = context.download_service.download_challenge(identifier, mode=mode)
    else:
        result = context.download_service.bulk_download(
            category=category,
            difficulty=difficulty,
            status=status,
            downloaded=downloaded_filter(downloaded, not_downloaded),
            search=search,
            mode=mode,
        )
    emit(result, as_json=as_json)


@app.command("sync-files")
def sync_files(as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON.")) -> None:
    context = get_context()
    result = context.challenge_service.sync_files()
    emit(result, as_json=as_json)


@export_app.command("manifest")
def export_manifest(
    output: Path | None = typer.Option(None, "--output", help="Path to write manifest.json."),
    sort_by: str = typer.Option("id", "--sort-by"),
    sort_order: str = typer.Option("desc", "--sort-order"),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    path = context.challenge_service.export_manifest(output_path=output, sort_by=sort_by, sort_order=sort_order)
    emit({"path": str(path)}, as_json=as_json)


@app.command()
def doctor(as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON.")) -> None:
    context = get_context()
    report = context.challenge_service.doctor()
    emit(report.model_dump(mode="json"), as_json=as_json)
    if report.error_count:
        raise typer.Exit(code=1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Setting key. Currently: workspace"),
    value: str = typer.Argument(..., help="New setting value."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
) -> None:
    context = get_context()
    if key != "workspace":
        typer.echo("Only `workspace` is supported here.")
        raise typer.Exit(code=1)
    updated = context.challenge_service.update_settings(workspace_root=value)
    emit(updated.model_dump(mode="json"), as_json=as_json)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    try:
        import uvicorn
        from dreamhack_local.api.app import create_api_app
    except ModuleNotFoundError as exc:
        typer.echo(
            "The API stack is not installed. Use a local virtualenv and install the project dependencies, "
            'for example: `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e ".[dev]"`',
            err=True,
        )
        raise typer.Exit(code=1) from exc

    uvicorn.run(create_api_app, host=host, port=port, reload=reload, factory=True)


def main() -> None:
    app()
