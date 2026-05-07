"""Unit tests for the geosite text-format parser + importer.

We don't hit the upstream CDN; instead we feed the parser the exact
syntax v2fly/domain-list-community uses and pin the structural mapping
onto :class:`ParsedRow`. The importer's DB-write loop is exercised
separately in ``test_routing_api.py`` via the ``import-geosite``
endpoint.
"""

from __future__ import annotations

import httpx
import pytest
from kosatka_master.services.geosite_importer import (
    ParsedRow,
    expand_tag,
    fetch_tag,
    fetch_tag_recursive,
    list_tags,
    parse_geosite_text,
    parse_includes,
)


def test_parse_bare_hostname_becomes_domain():
    rows = parse_geosite_text("example.com")
    assert rows == [ParsedRow(kind="domain", value="example.com")]


def test_parse_kind_prefixes():
    body = "\n".join(
        [
            "domain:foo.com",
            "keyword:censor",
            "regexp:^bad-.*\\.example$",
            "bare.example.org",
        ]
    )
    rows = parse_geosite_text(body)
    assert rows == [
        ParsedRow(kind="domain", value="foo.com"),
        ParsedRow(kind="keyword", value="censor"),
        ParsedRow(kind="regexp", value="^bad-.*\\.example$"),
        ParsedRow(kind="domain", value="bare.example.org"),
    ]


def test_parse_strips_attributes_and_comments():
    body = "\n".join(
        [
            "# this is a comment",
            "  ",
            "  example.com  @cn @ru  ",
            "    keyword:foo @ad ",
            "regexp:.* @attr",
        ]
    )
    rows = parse_geosite_text(body)
    assert rows == [
        ParsedRow(kind="domain", value="example.com"),
        ParsedRow(kind="keyword", value="foo"),
        ParsedRow(kind="regexp", value=".*"),
    ]


def test_parse_skips_includes_at_this_layer():
    body = "include:other-tag\nbare.example.com"
    rows = parse_geosite_text(body)
    # include: is resolved by fetch_tag_recursive, not parse_geosite_text.
    assert rows == [ParsedRow(kind="domain", value="bare.example.com")]


def test_parse_includes_extracts_referenced_tags():
    body = "\n".join(["include:cn", "include:ru @attr", "regexp:.*", "include:!geolocation"])
    assert parse_includes(body) == ["cn", "ru", "!geolocation"]


def test_empty_value_after_kind_prefix_is_dropped():
    body = "\n".join(["keyword:", "regexp: ", "domain:", "valid.example"])
    rows = parse_geosite_text(body)
    assert rows == [ParsedRow(kind="domain", value="valid.example")]


@pytest.mark.asyncio
async def test_fetch_tag_recursive_resolves_includes():
    """Cycle-safe and joins includes' rows into the parent tag's row list."""
    pages = {
        "parent": "include:child\ndirect-parent.example",
        "child": "child-only.example\ninclude:grandchild",
        "grandchild": "deep.example",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        # URL ends with the tag name.
        tag = request.url.path.rsplit("/", 1)[-1]
        if tag in pages:
            return httpx.Response(200, text=pages[tag])
        return httpx.Response(404, text="")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        rows = await fetch_tag_recursive(client, "parent")

    values = {r.value for r in rows}
    assert values == {"direct-parent.example", "child-only.example", "deep.example"}


@pytest.mark.asyncio
async def test_fetch_tag_recursive_breaks_cycles():
    pages = {
        "a": "include:b\nfrom-a.example",
        "b": "include:a\nfrom-b.example",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        tag = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, text=pages[tag])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        rows = await fetch_tag_recursive(client, "a")

    values = {r.value for r in rows}
    # Both pages must contribute; cycle must not duplicate or hang.
    assert values == {"from-a.example", "from-b.example"}


@pytest.mark.asyncio
async def test_fetch_tag_raises_on_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_tag(client, "missing")


@pytest.mark.asyncio
async def test_fetch_tag_recursive_swallows_http_errors():
    """A flaky upstream tag returns an empty list, never propagates."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        rows = await fetch_tag_recursive(client, "any")
    assert rows == []


@pytest.mark.asyncio
async def test_import_tags_dedupes_overlapping_includes(db_session):
    """Recursive includes that reference the same domain must not crash.

    Regression test for the IntegrityError on duplicate
    ``(tag, kind, value)`` rows surfaced by Devin Review. Parent and
    child tags both list ``shared.example`` — without dedup, the
    second insert hits ``UniqueConstraint`` and the whole import
    aborts.
    """
    import httpx
    from kosatka_master.services.geosite_importer import import_tags

    pages = {
        "parent": "include:child\nshared.example\nparent-only.example",
        "child": "shared.example\nchild-only.example",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        tag = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(200, text=pages[tag])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        counts = await import_tags(db_session, ["parent"], http_client=http)

    # 3 distinct rows: shared, parent-only, child-only.
    assert counts == {"parent": 3}
    rows = await expand_tag(db_session, "parent")
    assert {r.value for r in rows} == {
        "shared.example",
        "parent-only.example",
        "child-only.example",
    }


@pytest.mark.asyncio
async def test_list_tags_and_expand_tag_roundtrip(db_session):
    """End-to-end DB write/read for the importer's persistence layer."""
    from kosatka_master.models.routing import GeositeEntry

    db_session.add_all(
        [
            GeositeEntry(tag="t1", kind="domain", value="a.example", import_version="v"),
            GeositeEntry(tag="t1", kind="keyword", value="kw", import_version="v"),
            GeositeEntry(tag="t2", kind="domain", value="b.example", import_version="v"),
        ]
    )
    await db_session.commit()

    tags = await list_tags(db_session)
    assert set(tags) == {"t1", "t2"}

    t1 = await expand_tag(db_session, "t1")
    assert {(r.kind, r.value) for r in t1} == {("domain", "a.example"), ("keyword", "kw")}

    empty = await expand_tag(db_session, "missing")
    assert empty == []
