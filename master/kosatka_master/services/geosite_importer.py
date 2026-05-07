"""Import domain blocklists from v2fly/domain-list-community.

The upstream v2ray-rules-dat repo publishes ``geosite.dat`` as a
protobuf binary, but the *source-of-truth* is the plaintext files
under ``data/<tag>`` in
https://github.com/v2fly/domain-list-community — one tag per file,
one entry per line, with a small DSL:

* ``example.com``                 — full-domain match (default kind)
* ``keyword:foo``                 — substring match (kind=keyword)
* ``regexp:^...``                 — regex match (kind=regexp)
* ``include:other-tag``           — pull all rows from ``other-tag``
* ``# comment``                   — ignored
* trailing ``  @attr1 @attr2``    — ignored (we don't honour attrs in MVP)

Importing the text format lets us avoid pulling ``protobuf`` as a
dependency just for one parse, and keeps each row source-traceable
(the protobuf format flattens all of this into anonymous bytes).

The importer runs as a daily APScheduler job; an explicit
``POST /api/v1/policies/import-geosite`` handler also wires it up so
operators can force a refresh after editing tags.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.routing import GeositeEntry

logger = logging.getLogger(__name__)


_BASE_URL = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/{tag}"
# Conservative default — the master fetch path is admin-triggered, not
# in any client hot path, so we trade latency for correctness.
_HTTP_TIMEOUT = 30.0


@dataclass(frozen=True)
class ParsedRow:
    """One row that should land in the ``geosite_entries`` table."""

    kind: str  # "domain" | "keyword" | "regexp" | "ip"
    value: str


_KIND_PREFIXES: tuple[tuple[str, str], ...] = (
    ("keyword:", "keyword"),
    ("regexp:", "regexp"),
    ("domain:", "domain"),
)


def _parse_geosite_line(line: str) -> ParsedRow | None:
    """Pure-text parse of a single ``data/<tag>`` line.

    Returns ``None`` for lines that don't contribute a row (comments,
    blanks, ``include:`` directives, kind prefixes with empty values).
    Splitting this out keeps :func:`parse_geosite_text` simple enough
    to satisfy flake8's complexity check.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Strip ``  @attribute1 @attribute2`` suffix — we don't honour
    # attributes (they gate domains by client/region/...). The default
    # v2fly behaviour is to include every domain regardless of
    # attribute, which matches what we want.
    if " " in line:
        line = line.split(" ", 1)[0]
    if not line or line.startswith("include:"):
        return None
    for prefix, kind in _KIND_PREFIXES:
        if line.startswith(prefix):
            value = line[len(prefix) :].strip()
            return ParsedRow(kind=kind, value=value) if value else None
    # Bare hostname is treated as ``domain:<host>``.
    return ParsedRow(kind="domain", value=line)


def parse_geosite_text(body: str) -> list[ParsedRow]:
    """Convert the raw ``data/<tag>`` text body into rows.

    ``include:other-tag`` directives are *not* expanded here — the
    importer resolves them recursively after every referenced tag is
    fetched. This keeps each fetch idempotent and lets us cache
    individual tag fetches without inheriting their dependency graph.
    """
    rows: list[ParsedRow] = []
    for raw in body.splitlines():
        parsed = _parse_geosite_line(raw)
        if parsed is not None:
            rows.append(parsed)
    return rows


def parse_includes(body: str) -> list[str]:
    """Return the list of tag names referenced via ``include:other``."""
    out: list[str] = []
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("include:"):
            tag = line[len("include:") :].split(" ", 1)[0].strip()
            if tag:
                out.append(tag)
    return out


async def fetch_tag(client: httpx.AsyncClient, tag: str) -> str:
    """HTTP GET a single ``data/<tag>`` file. Raises on non-200."""
    url = _BASE_URL.format(tag=tag)
    resp = await client.get(url, timeout=_HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text


async def fetch_tag_recursive(
    client: httpx.AsyncClient,
    tag: str,
    seen: set[str] | None = None,
) -> list[ParsedRow]:
    """Resolve ``include:`` directives by re-fetching referenced tags.

    Cycle-safe: a tag visited once is not refetched even if a sibling
    ``include:``s it again.
    """
    if seen is None:
        seen = set()
    if tag in seen:
        return []
    seen.add(tag)
    try:
        body = await fetch_tag(client, tag)
    except httpx.HTTPError as exc:
        logger.warning("Geosite tag %r unreachable: %s", tag, exc)
        return []

    direct = parse_geosite_text(body)
    for include in parse_includes(body):
        direct.extend(await fetch_tag_recursive(client, include, seen))
    return direct


def _format_version() -> str:
    """Stamp imported rows with a UTC date so a re-run can purge stale ones."""
    return datetime.now(timezone.utc).strftime("v%Y-%m-%d")


async def import_tags(
    db: AsyncSession,
    tags: Iterable[str],
    *,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, int]:
    """Import ``tags`` from upstream into ``geosite_entries``.

    Returns a ``{tag: row_count}`` map. Every existing row for a tag is
    deleted before the new batch is inserted — domain-list-community's
    files are append-only in practice but occasionally remove dead
    domains, and we don't want stale entries to leak through.
    """
    own_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=_HTTP_TIMEOUT)
    counts: dict[str, int] = {}
    version = _format_version()
    try:
        for tag in tags:
            rows = await fetch_tag_recursive(client, tag)
            if not rows:
                counts[tag] = 0
                continue
            # ``counts`` reports how many *distinct* rows landed in the
            # DB, not how many were fetched — duplicates are a
            # property of the upstream tag graph, not of our import,
            # and operators care about the visible state.
            # Replace the old set in one batch. Keep this scoped to a
            # single tag at a time so a partial failure on tag N doesn't
            # wipe the still-current rows of tag N+1.
            # Deduplicate before insert: a parent tag and an ``include:``d
            # child tag can independently list the same domain, and the
            # ``UniqueConstraint("tag", "kind", "value")`` on
            # ``GeositeEntry`` would turn that into an IntegrityError that
            # rolls back the transaction (already-deleted rows are gone,
            # the session goes into a failed state, and every subsequent
            # tag in the same call also fails). ``ParsedRow`` is
            # ``frozen=True`` so it's hashable; ``dict.fromkeys`` keeps
            # the first-seen order which preserves source-line ordering
            # for any debug dumps.
            unique_rows = list(dict.fromkeys(rows))
            await db.execute(delete(GeositeEntry).where(GeositeEntry.tag == tag))
            db.add_all(
                GeositeEntry(tag=tag, kind=r.kind, value=r.value, import_version=version)
                for r in unique_rows
            )
            await db.commit()
            counts[tag] = len(unique_rows)
            logger.info("Imported %d rows for geosite tag %r", len(unique_rows), tag)
    finally:
        if own_client:
            await client.aclose()
    return counts


async def list_tags(db: AsyncSession) -> list[str]:
    """Return every distinct tag currently stored. Used by the resolver."""
    result = await db.execute(select(GeositeEntry.tag).distinct())
    return [row[0] for row in result.all()]


async def expand_tag(db: AsyncSession, tag: str) -> list[GeositeEntry]:
    """Stream every entry for ``tag`` in import order. Empty if unknown."""
    result = await db.execute(select(GeositeEntry).where(GeositeEntry.tag == tag))
    return list(result.scalars().all())
