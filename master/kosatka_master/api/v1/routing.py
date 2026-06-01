"""HTTP surface for the smart-routing plane.

Three concerns share a single router:

* CRUD on :class:`RoutingPolicy` rows for the operator-facing UI / CLI.
* Per-client profile upserts (``PUT /clients/{external_id}/routing-profile``)
  used by the bot when a user toggles smart/proxy/direct or overrides
  region.
* The hot-path ``GET /routing/policy?client_id=…`` endpoint that every
  connected agent polls. It expands ``geosite:<tag>`` references and
  returns a flat domain/CIDR view sized to be cached on the agent for
  60 s — the version field doubles as the cache key.

Everything is gated by the same ``X-Kosatka-Key`` header that protects
the rest of ``/api/v1/*``; a leaked policy is a privacy issue (it
reveals which sites the operator considers blocked).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.routing import ClientRoutingProfile, GeositeEntry, RoutingPolicy
from ...security import validate_operator
from ...services import geosite_importer

router = APIRouter(prefix="", tags=["routing"], dependencies=[Depends(validate_operator)])


class PolicySchema(BaseModel):
    id: int
    name: str
    version: str
    direct_whitelist: list[str]
    proxy_blacklist: list[str]
    max_latency_direct_ms: int
    max_packet_loss_direct: float
    fallback_strategy: str
    is_default: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_row(cls, row: RoutingPolicy) -> "PolicySchema":
        return cls(
            id=row.id,
            name=row.name,
            version=row.version,
            direct_whitelist=list(row.direct_whitelist or []),
            proxy_blacklist=list(row.proxy_blacklist or []),
            max_latency_direct_ms=row.max_latency_direct_ms,
            max_packet_loss_direct=row.max_packet_loss_direct,
            fallback_strategy=row.fallback_strategy,
            is_default=bool(row.is_default),
        )


class PolicyCreate(BaseModel):
    name: str
    direct_whitelist: list[str] = Field(default_factory=list)
    proxy_blacklist: list[str] = Field(default_factory=list)
    max_latency_direct_ms: int = 200
    max_packet_loss_direct: float = 0.05
    fallback_strategy: str = "least_latency"
    is_default: bool = False


class PolicyPatch(BaseModel):
    name: str | None = None
    direct_whitelist: list[str] | None = None
    proxy_blacklist: list[str] | None = None
    max_latency_direct_ms: int | None = None
    max_packet_loss_direct: float | None = None
    fallback_strategy: str | None = None
    is_default: bool | None = None


def _bump_version(current: str) -> str:
    """Monotonic version bump used after every mutation.

    Numeric-prefix-with-trailing-suffix scheme so an operator's existing
    semver (``2026.05-1``) stays human-readable while we still flip the
    suffix integer on each save. If the suffix isn't a number, we drop
    a fresh ``-N`` onto the back.
    """
    if "-" in current:
        head, _, tail = current.rpartition("-")
        try:
            return f"{head}-{int(tail) + 1}"
        except ValueError:
            pass
    try:
        return str(int(current) + 1)
    except ValueError:
        return f"{current}-1"


def _apply_policy_patch(row: RoutingPolicy, payload: PolicyPatch) -> bool:
    """Copy non-None fields from ``payload`` onto ``row``.

    Pulled out of :func:`patch_policy` to keep its cyclomatic complexity
    under flake8's threshold — the long flat ``if x is not None`` chain
    is structurally simple but trips C901 because each branch counts.
    Returns ``True`` iff at least one field was applied.
    """
    fields: tuple[tuple[str, str], ...] = (
        ("name", "name"),
        ("direct_whitelist", "direct_whitelist"),
        ("proxy_blacklist", "proxy_blacklist"),
        ("max_latency_direct_ms", "max_latency_direct_ms"),
        ("max_packet_loss_direct", "max_packet_loss_direct"),
        ("fallback_strategy", "fallback_strategy"),
    )
    changed = False
    for payload_attr, row_attr in fields:
        value = getattr(payload, payload_attr)
        if value is None:
            continue
        if payload_attr in ("direct_whitelist", "proxy_blacklist"):
            value = list(value)
        setattr(row, row_attr, value)
        changed = True
    if payload.is_default is not None:
        row.is_default = 1 if payload.is_default else 0
        changed = True
    return changed


@router.get("/policies/", response_model=list[PolicySchema])
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RoutingPolicy))
    return [PolicySchema.from_orm_row(p) for p in result.scalars().all()]


@router.post("/policies/", response_model=PolicySchema, status_code=201)
async def create_policy(payload: PolicyCreate, db: AsyncSession = Depends(get_db)):
    if payload.is_default:
        # Demote any existing default — we maintain "exactly one default
        # policy" as an invariant rather than enforcing it via a partial
        # unique index, since SQLite's partial-index support is uneven.
        result = await db.execute(select(RoutingPolicy).where(RoutingPolicy.is_default == 1))
        for existing in result.scalars().all():
            existing.is_default = 0

    row = RoutingPolicy(
        name=payload.name,
        version="1",
        direct_whitelist=list(payload.direct_whitelist),
        proxy_blacklist=list(payload.proxy_blacklist),
        max_latency_direct_ms=payload.max_latency_direct_ms,
        max_packet_loss_direct=payload.max_packet_loss_direct,
        fallback_strategy=payload.fallback_strategy,
        is_default=1 if payload.is_default else 0,
    )
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Policy name already exists: {exc}") from exc
    await db.refresh(row)
    return PolicySchema.from_orm_row(row)


@router.get("/policies/{policy_id}", response_model=PolicySchema)
async def get_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(RoutingPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicySchema.from_orm_row(row)


@router.patch("/policies/{policy_id}", response_model=PolicySchema)
async def patch_policy(policy_id: int, payload: PolicyPatch, db: AsyncSession = Depends(get_db)):
    row = await db.get(RoutingPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Policy not found")

    if payload.is_default is True:
        # Same demote-on-write invariant as create_policy.
        result = await db.execute(
            select(RoutingPolicy).where(
                RoutingPolicy.is_default == 1, RoutingPolicy.id != policy_id
            )
        )
        for existing in result.scalars().all():
            existing.is_default = 0

    changed = _apply_policy_patch(row, payload)
    if changed:
        # Version is the agent-side cache key — bump every time the row
        # actually changes so the next /routing/policy poll forces a
        # cache reload on the agent without us having to push.
        row.version = _bump_version(row.version)

    await db.commit()
    await db.refresh(row)
    return PolicySchema.from_orm_row(row)


@router.delete("/policies/{policy_id}")
async def delete_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(RoutingPolicy, policy_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    if row.is_default:
        # Refuse to delete the default — agents that fall back to "no
        # explicit profile" rely on it. Operator must mark another row
        # default first.
        raise HTTPException(
            status_code=409,
            detail="Cannot delete the default policy; mark another policy default first.",
        )
    await db.delete(row)
    await db.commit()
    return {"status": "success"}


class GeositeImportRequest(BaseModel):
    tags: list[str]


class GeositeImportResponse(BaseModel):
    imported: dict[str, int]


@router.post("/policies/import-geosite", response_model=GeositeImportResponse)
async def import_geosite(payload: GeositeImportRequest, db: AsyncSession = Depends(get_db)):
    """Trigger a synchronous geosite import for the given tags."""
    if not payload.tags:
        raise HTTPException(status_code=400, detail="At least one tag is required")
    counts = await geosite_importer.import_tags(db, payload.tags)
    return GeositeImportResponse(imported=counts)


class ClientProfileSchema(BaseModel):
    client_external_id: str
    policy_id: int | None
    mode: str
    region: str | None
    region_override: bool

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_row(cls, row: ClientRoutingProfile) -> "ClientProfileSchema":
        return cls(
            client_external_id=row.client_external_id,
            policy_id=row.policy_id,
            mode=row.mode,
            region=row.region,
            region_override=bool(row.region_override),
        )


class ClientProfileUpsert(BaseModel):
    policy_id: int | None = None
    mode: str = "smart"
    region: str | None = None
    region_override: bool = False


@router.put("/clients/{external_id}/routing-profile", response_model=ClientProfileSchema)
async def upsert_client_routing_profile(
    external_id: str,
    payload: ClientProfileUpsert,
    db: AsyncSession = Depends(get_db),
):
    if payload.mode not in ("smart", "always_proxy", "always_direct"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {payload.mode!r}")
    if payload.policy_id is not None:
        # Validate FK explicitly — SQLite doesn't enforce by default and
        # we'd rather 400 here than serve a 500 to the bot later when
        # the policy is missing.
        if (await db.get(RoutingPolicy, payload.policy_id)) is None:
            raise HTTPException(status_code=400, detail="Unknown policy_id")

    result = await db.execute(
        select(ClientRoutingProfile).where(ClientRoutingProfile.client_external_id == external_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = ClientRoutingProfile(
            client_external_id=external_id,
            policy_id=payload.policy_id,
            mode=payload.mode,
            region=payload.region,
            region_override=1 if payload.region_override else 0,
        )
        db.add(row)
    else:
        row.policy_id = payload.policy_id
        row.mode = payload.mode
        # Don't overwrite a user-set region with a stale GeoIP detection.
        # If the existing row has region_override=1, keep its region
        # unless the caller explicitly passes region_override=True with
        # a fresh region value.
        if payload.region_override:
            row.region = payload.region
            row.region_override = 1
        elif not row.region_override:
            row.region = payload.region
            row.region_override = 0

    await db.commit()
    await db.refresh(row)
    return ClientProfileSchema.from_orm_row(row)


@router.get("/clients/{external_id}/routing-profile", response_model=ClientProfileSchema)
async def get_client_routing_profile(external_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ClientRoutingProfile).where(ClientRoutingProfile.client_external_id == external_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Client routing profile not found")
    return ClientProfileSchema.from_orm_row(row)


@router.delete("/clients/{external_id}/routing-profile")
async def delete_client_routing_profile(external_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ClientRoutingProfile).where(ClientRoutingProfile.client_external_id == external_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Client routing profile not found")
    await db.delete(row)
    await db.commit()
    return {"status": "success"}


class ResolvedPolicy(BaseModel):
    policy_version: str
    mode: str
    region: str | None
    direct_whitelist: list[str]
    proxy_blacklist: list[str]
    max_latency_direct_ms: int
    max_packet_loss_direct: float
    fallback_strategy: str


async def _resolve_policy_for_client(
    db: AsyncSession,
    client_external_id: str | None,
) -> tuple[RoutingPolicy | None, ClientRoutingProfile | None]:
    """Pick the right :class:`RoutingPolicy` for ``client_external_id``.

    Order:
      1. The policy referenced by the client's profile, if any.
      2. The :class:`RoutingPolicy` flagged ``is_default``.
      3. ``None`` — caller must respond with a sane empty default.
    """
    profile: ClientRoutingProfile | None = None
    if client_external_id:
        result = await db.execute(
            select(ClientRoutingProfile).where(
                ClientRoutingProfile.client_external_id == client_external_id
            )
        )
        profile = result.scalar_one_or_none()

    if profile is not None and profile.policy_id is not None:
        policy = await db.get(RoutingPolicy, profile.policy_id)
        if policy is not None:
            return policy, profile

    result = await db.execute(select(RoutingPolicy).where(RoutingPolicy.is_default == 1))
    return result.scalars().first(), profile


async def _expand_geosite_refs(db: AsyncSession, patterns: list[str]) -> list[str]:
    """Replace ``geosite:<tag>`` entries with the underlying domain list."""
    expanded: list[str] = []
    for pattern in patterns:
        if not pattern.startswith("geosite:"):
            expanded.append(pattern)
            continue
        tag = pattern[len("geosite:") :]
        result = await db.execute(select(GeositeEntry).where(GeositeEntry.tag == tag))
        for entry in result.scalars().all():
            # Annotate keyword/regexp entries so the agent matcher knows
            # which strategy to use; bare hostnames stay unmarked
            # because they're the dominant case and we want that path
            # to be cheap.
            if entry.kind == "domain":
                expanded.append(entry.value)
            else:
                expanded.append(f"{entry.kind}:{entry.value}")
    return expanded


@router.get("/routing/policy", response_model=ResolvedPolicy)
async def get_routing_policy(
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Resolve the effective policy for ``client_id``.

    Called by every connected agent on a 60 s loop; expands geosite
    references inline so the agent never needs to know the geosite
    table exists. ``policy_version`` lets callers short-circuit the
    rest of the response on cache hit.
    """
    policy, profile = await _resolve_policy_for_client(db, client_id)
    if policy is None:
        # No default and no per-client profile — return a permissive
        # empty policy so the agent can still serve traffic. The agent
        # logs a warning when it sees ``policy_version=="<empty>"``.
        return ResolvedPolicy(
            policy_version="<empty>",
            mode=profile.mode if profile is not None else "smart",
            region=profile.region if profile is not None else None,
            direct_whitelist=[],
            proxy_blacklist=[],
            max_latency_direct_ms=200,
            max_packet_loss_direct=0.05,
            fallback_strategy="least_latency",
        )

    direct = await _expand_geosite_refs(db, list(policy.direct_whitelist or []))
    proxy = await _expand_geosite_refs(db, list(policy.proxy_blacklist or []))

    return ResolvedPolicy(
        policy_version=policy.version,
        mode=profile.mode if profile is not None else "smart",
        region=profile.region if profile is not None else None,
        direct_whitelist=direct,
        proxy_blacklist=proxy,
        max_latency_direct_ms=policy.max_latency_direct_ms,
        max_packet_loss_direct=policy.max_packet_loss_direct,
        fallback_strategy=policy.fallback_strategy,
    )
