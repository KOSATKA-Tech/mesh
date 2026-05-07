"""Master-side data model for the smart-routing plane.

Three tables wire together the policy graph the Smart Agent rollout
depends on:

* :class:`RoutingPolicy` — admin-managed rule set: direct whitelists,
  proxy blacklists, latency/loss thresholds, and references into
  :class:`GeositeEntry` rows by ``geosite:<tag>`` syntax. Every mutation
  bumps ``version`` so agents can cheaply detect "must reload".
* :class:`GeositeEntry` — flattened domain/CIDR list imported from
  ``v2fly/domain-list-community``. We don't store the raw protobuf;
  the importer pre-parses the text format and writes one row per
  domain/CIDR pair, indexed by ``(tag, value)`` so the resolver can
  expand ``geosite:category-ru-blocked`` to a concrete list of
  domains in a single query.
* :class:`ClientRoutingProfile` — per-client overrides: which policy
  applies, which mode (smart/always_proxy/always_direct), and which
  region the bot has detected (or the user has manually set).

The agent only ever sees the resolved view via
``GET /api/v1/routing/policy?client_id=…``; this layer is internal and
not part of the agent contract.
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RoutingPolicy(Base):
    """Admin-managed routing policy. ``version`` doubles as a cache key."""

    __tablename__ = "routing_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    # Bumped on every UPDATE; agents poll ``GET /routing/policy`` and
    # short-circuit when their cached ``version`` matches.
    version: Mapped[str] = mapped_column(String(64), default="1")
    # Patterns the agent should *always* route directly. Each entry is
    # one of: a domain glob (``*.ru``), a CIDR (``192.168.0.0/16``), an
    # exact host (``rkn.gov.ru``), or a geosite reference
    # (``geosite:category-ru``) which the resolver expands at fetch time.
    direct_whitelist: Mapped[list] = mapped_column(JSON, default=list)
    # Same format as ``direct_whitelist`` — these go through the proxy
    # unconditionally regardless of probe results.
    proxy_blacklist: Mapped[list] = mapped_column(JSON, default=list)
    # Probe-derived thresholds. The agent picks "direct" only when the
    # measured RTT *and* loss for the target are both below these.
    max_latency_direct_ms: Mapped[int] = mapped_column(Integer, default=200)
    max_packet_loss_direct: Mapped[float] = mapped_column(Float, default=0.05)
    # When direct is rejected, this drives node selection on the master
    # side (the agent itself just tunnels through whichever endpoint
    # the master gave it).
    fallback_strategy: Mapped[str] = mapped_column(String(32), default="least_latency")
    # Exactly one row may have ``is_default=True``; it backs every client
    # that doesn't have an explicit :class:`ClientRoutingProfile`.
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class GeositeEntry(Base):
    """One row per (tag, kind, value) imported from v2fly/domain-list-community.

    Kept denormalised on purpose — joins on ``tag`` are far hotter than
    inserts (we re-import once a day, agents fetch once a minute), and
    a per-row layout lets us serve a tag in a single ``WHERE tag = ?``
    streaming scan with no JSON parsing in the hot path.
    """

    __tablename__ = "geosite_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    # E.g. ``category-ru-blocked``, ``geolocation-ru``, ``category-ads-all``.
    tag: Mapped[str] = mapped_column(String(255), index=True)
    # ``domain`` for full-domain matches, ``keyword`` for substring,
    # ``regexp`` for compiled-once regex, ``ip`` for CIDR. The agent
    # decides matcher per-kind.
    kind: Mapped[str] = mapped_column(String(16), default="domain")
    value: Mapped[str] = mapped_column(String(255))
    # ``vYYYY-MM-DD-rev`` from the upstream release; an importer run
    # records it on every row so we can detect & purge stale entries.
    import_version: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    __table_args__ = (UniqueConstraint("tag", "kind", "value", name="uix_geosite_tag_kind_value"),)


class ClientRoutingProfile(Base):
    """Per-client override of the default policy + region detection.

    The bot writes this row when the user toggles smart/proxy/direct or
    overrides their region. The master's ``/routing/policy`` resolver
    looks it up by ``client_external_id`` (the bot's stable user key)
    and falls back to the default :class:`RoutingPolicy` row when no
    profile is recorded.
    """

    __tablename__ = "client_routing_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_external_id: Mapped[str] = mapped_column(String(255), unique=True)
    policy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("routing_policies.id", ondelete="SET NULL"), nullable=True
    )
    # ``smart`` = run the probe + decision engine.
    # ``always_proxy`` = pin to fallback path (bypass probes).
    # ``always_direct`` = pin to direct path (bypass probes; useful for
    # debugging or for users on a country with no DPI).
    mode: Mapped[str] = mapped_column(String(32), default="smart")
    # GeoIP-derived region (e.g. ``RU-MOW``). Bot may overwrite this
    # via PUT when the user explicitly chooses a different region.
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region_override: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
