"""
Risk scoring engine: combine fuzzy match, semantic score, country-of-concern, and parent chain
into a four-tier classification (Red/Amber/Yellow/Green) with evidence and reasoning.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.config.scoring_config import get_scoring_config

logger = logging.getLogger(__name__)

Tier = Literal["red", "amber", "yellow", "green"]


# Explicitly named entities in BIOSECURE / BCC context (NDAA Sec. 851). Substring match → RED.
# Huawei is NOT a BCC (telecom/IT); flag via BIS_ENTITY_LIST/OFAC only.
BIOSECURE_NAMED_ENTITIES: frozenset[str] = frozenset(
    {
        "BGI",
        "MGI",
        "Complete Genomics",
        "WuXi Apptec",
        "WuXi AppTec",
        "WuXi Biologics",
    }
)

# Subsidiary / alias → parent for BIOSECURE. Check normalized name (lowercase, no punctuation).
# Used before fuzzy matching so known subsidiaries short-circuit to RED.
BIOSECURE_SUBSIDIARIES: dict[str, str] = {
    "wuxi sta": "WuXi AppTec",
    "shanghai syntheall": "WuXi AppTec",
    "syntheall": "WuXi AppTec",
    "wuxi advanced therapies": "WuXi AppTec",
    "wuxi biologics": "WuXi AppTec",
    "wuxi apptec": "WuXi AppTec",
    "wuxi xdc": "WuXi AppTec",
    "apptec": "WuXi AppTec",
    "bgi genomics": "BGI Group",
    "bgi procare": "BGI Group",
    "bgi americas": "BGI Group",
    "bgi europe": "BGI Group",
    "beijing genomics institute": "BGI Group",
    "complete genomics": "BGI Group",
    "mgi tech": "BGI Group",
    "mgi": "BGI Group",
    "shenzhen mgi": "BGI Group",
}

# High-cardinality corporate suffixes stripped before fuzzy matching to reduce false positives.
CORPORATE_SUFFIXES: list[str] = [
    "Corporation",
    "Corp",
    "Inc",
    "Incorporated",
    "Technologies",
    "Technology",
    "Co Ltd",
    "Ltd",
    "LLC",
    "Group",
    "SA",
    "SE",
    "NV",
]


class MatchEvidenceItem(BaseModel):
    matched_entity: str
    source_list: str
    similarity_score: int
    match_type: str = "name"
    country: str | None = None
    risk_category: str | None = None


class RiskTier(BaseModel):
    tier: Tier
    confidence_score: int = Field(ge=0, le=100)
    match_evidence: list[MatchEvidenceItem] = Field(default_factory=list)
    country_flags: list[str] = Field(default_factory=list)
    reasoning: str = ""


def strip_corporate_suffixes(name: str | None) -> str:
    """
    Strip corporate suffixes before fuzzy matching so we match root entity name
    (e.g. "Agilent" not "Agilent Technologies"). Reduces false positives from
    generic suffix matches like "Technologies" or "Group".
    """
    if not name or not isinstance(name, str):
        return ""
    s = " ".join(name.split()).strip()
    if not s:
        return ""
    # Try longest suffixes first so "Co Ltd" strips before "Ltd"
    sorted_suffixes = sorted(CORPORATE_SUFFIXES, key=len, reverse=True)
    changed = True
    while changed:
        changed = False
        lower = s.lower()
        for suffix in sorted_suffixes:
            suf_lower = suffix.lower()
            # Prefer " Suffix" so "Foo Co Ltd" -> "Foo" not "Foo Co"
            if lower.endswith(" " + suf_lower):
                s = s[: -len(suffix) - 1].strip().rstrip(",").strip()
                changed = True
                break
            if lower.endswith(suf_lower):
                s = s[: -len(suffix)].strip().rstrip(",").strip()
                changed = True
                break
    return " ".join(s.split()).strip() or name.strip()


def is_biosecure_direct_match(name: str | None) -> bool:
    """
    True if name contains any explicitly named BIOSECURE Act entity (case-insensitive).
    Uses substring matching on the raw or normalized vendor name.
    """
    if not name or not isinstance(name, str):
        return False
    lower = name.lower()
    return any(entity.lower() in lower for entity in BIOSECURE_NAMED_ENTITIES)


def _normalize_for_subsidiary(name: str | None) -> str:
    """Lowercase, strip punctuation and common suffixes for subsidiary key lookup."""
    if not name or not isinstance(name, str):
        return ""
    s = re.sub(r"[^\w\s]", " ", name).lower()
    s = " ".join(s.split()).strip()
    # Strip corporate suffixes so "WuXi STA (Shanghai SynTheAll)" -> "wuxi sta shanghai syntheall"
    for suffix in ["co", "ltd", "llc", "inc", "corp", "limited", "corporation"]:
        if s.endswith(" " + suffix):
            s = s[: -len(suffix) - 1].strip()
    return s


def resolve_biosecure_subsidiary(vendor_name: str | None) -> str | None:
    """
    If vendor name matches a known BIOSECURE subsidiary/alias, return the parent name.
    Runs before fuzzy matching so e.g. WuXi STA -> Red / WuXi AppTec.
    """
    if not vendor_name or not isinstance(vendor_name, str):
        return None
    normalized = _normalize_for_subsidiary(vendor_name)
    if not normalized:
        return None
    for key, parent in BIOSECURE_SUBSIDIARIES.items():
        if key in normalized or normalized in key:
            return parent
    return None


def canonical_biosecure_entity_for_grouping(name: str | None) -> str | None:
    """
    For BIOSECURE direct match, return a canonical entity name for dedup grouping
    so all BGI/MGI/WuXi variants group under one row. Returns None if not a named entity.
    """
    if not name or not isinstance(name, str):
        return None
    lower = name.lower()
    if "wuxi" in lower or "apptec" in lower:
        return "WuXi AppTec"
    if "bgi" in lower or "mgi" in lower or "beijing genomics" in lower or "complete genomics" in lower:
        return "BGI Group"
    return None


def _best_fuzzy_score(matches: list[dict[str, Any]]) -> int:
    if not matches:
        return 0
    return max((m.get("score") or 0) for m in matches)


# Common country strings -> ISO 3166-1 alpha-2 for country_of_concern check
_COUNTRY_ALIASES: dict[str, str] = {
    "USA": "US", "UNITED STATES": "US", "U.S.": "US", "U.S.A.": "US",
    "CHINA": "CN", "PEOPLE'S REPUBLIC OF CHINA": "CN", "RUSSIA": "RU",
    "IRAN": "IR", "NORTH KOREA": "KP", "UK": "GB", "UNITED KINGDOM": "GB",
}


def _country_in_concern(country: str | None, codes: list[str]) -> bool:
    if not country or not codes:
        return False
    code = _normalize_country_code(country)
    return code in [c.upper() for c in codes]


def _normalize_country_code(country: str | None) -> str:
    """Return 2-letter ISO code for country-of-concern checks and flags."""
    if not country or not isinstance(country, str):
        return ""
    s = country.strip().upper()
    if len(s) <= 2:
        return s[:2]
    return _COUNTRY_ALIASES.get(s, s[:2])


# Allied countries: vendors from these need a much higher fuzzy score to trigger a flag.
ALLIED_COUNTRIES: frozenset[str] = frozenset({
    "united states", "us", "usa", "united kingdom", "uk", "canada",
    "germany", "france", "netherlands", "switzerland", "japan",
    "south korea", "australia", "sweden", "denmark", "norway",
    "finland", "ireland", "belgium", "austria", "italy", "spain",
    "luxembourg", "israel", "singapore", "taiwan", "new zealand",
})


def get_fuzzy_threshold(vendor_country: str | None) -> int:
    """Allied-country vendors need a much higher fuzzy score to trigger a flag."""
    if vendor_country and vendor_country.strip().lower() in ALLIED_COUNTRIES:
        return 95  # Near-exact match required for allied countries
    return 80  # Standard threshold for others


# Major lab supply / life science vendors that should never be flagged unless EXACT watchlist match.
KNOWN_SAFE_VENDORS: frozenset[str] = frozenset({
    "illumina", "thermo fisher", "fisher scientific", "agilent",
    "bio-rad", "bio rad", "corning", "perkinelmer", "beckman coulter",
    "10x genomics", "idt", "integrated dna technologies", "promega",
    "new england biolabs", "neb", "twist bioscience", "biolegend",
    "eurofins", "charles river", "lonza", "sartorius", "eppendorf",
    "qiagen", "cytiva", "milliporesigma", "milliporeroche", "abcam",
    "takara", "samsung biologics", "novatek",
})


def is_known_safe(normalized_name: str | None) -> bool:
    """True if vendor is a known safe lab/life-science supplier (suppress fuzzy-only flags)."""
    if not normalized_name or not isinstance(normalized_name, str):
        return False
    name_lower = normalized_name.lower()
    return any(safe in name_lower for safe in KNOWN_SAFE_VENDORS)


def _parent_chain_max_depth(chain: list[dict[str, Any]]) -> int:
    if not chain:
        return -1
    return max((c.get("depth") or 0) for c in chain)


def _match_is_plausible(vendor_name: str | None, matched_entity: str | None) -> bool:
    """
    True if the matched watchlist entity shares at least one significant token
    with the vendor name. Used to avoid counting spurious fuzzy matches (e.g.
    "Agilent" matching an unrelated 55% watchlist hit) toward amber/yellow.
    """
    if not vendor_name or not matched_entity:
        return False

    def tokens(s: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]{3,}", (s or "").lower()))

    # Generic tokens are loaded from scoring config so we can ignore
    # high-frequency corporate words like "group" or "international"
    # when determining plausibility.
    config = get_scoring_config()
    generic = {t.lower() for t in (config.generic_tokens or [])}

    vt_all = tokens(vendor_name)
    if not vt_all:
        return False
    mt_all = tokens(matched_entity)

    vt = {t for t in vt_all if t not in generic}
    mt = {t for t in mt_all if t not in generic}

    if not vt:
        # All vendor tokens were generic; treat as implausible match.
        return False
    return bool(vt & mt)


def score_vendor(
    vendor_match_results: list[dict[str, Any]],
    *,
    country: str | None = None,
    parent_chain: list[dict[str, Any]] | None = None,
    parent_company_is_biosecure_named: bool = False,
    semantic_score: float | None = None,
    vendor_name: str | None = None,
) -> RiskTier:
    """
    Score a vendor from fuzzy match results, optional semantic score, country, and parent chain.
    Returns RiskTier with tier, confidence_score, match_evidence, country_flags, and reasoning.
    Fails safe: ambiguous cases default to amber, never green when match or parent evidence exists.
    """
    config = get_scoring_config()
    thresholds = config.tier_thresholds
    weights = config.score_weights
    country_of_concern = config.country_of_concern

    best_fuzzy = _best_fuzzy_score(vendor_match_results)
    best_source = (vendor_match_results[0].get("source_list") or "") if vendor_match_results else ""
    semantic = semantic_score if semantic_score is not None else 0.0
    country_flag = 100 if _country_in_concern(country, country_of_concern) else 0

    composite = (
        weights.fuzzy_weight * best_fuzzy
        + weights.semantic_weight * semantic
        + weights.country_weight * country_flag
    )
    confidence_score = min(100, max(0, int(round(composite))))

    match_evidence = [
        MatchEvidenceItem(
            matched_entity=str(m.get("matched_name") or m.get("matched_entity") or ""),
            source_list=str(m.get("source_list") or ""),
            similarity_score=int(round((m.get("score") or m.get("similarity_score") or 0))),
            match_type=str(m.get("match_type") or "name"),
            country=m.get("country") if m.get("country") is not None else None,
            risk_category=str(m.get("risk_category")) if m.get("risk_category") is not None else None,
        )
        for m in (vendor_match_results or [])
    ]
    country_flags: list[str] = []
    if country and _country_in_concern(country, country_of_concern):
        code = _normalize_country_code(country)
        if code:
            country_flags.append(code)

    chain = parent_chain or []
    max_depth = _parent_chain_max_depth(chain)

    reasoning_parts: list[str] = []

    # 1. Hardcoded BIOSECURE name override: direct match on vendor name → RED, bypass fuzzy.
    if vendor_name and is_biosecure_direct_match(vendor_name):
        tier = "red"
        reasoning_parts.append(
            "Direct match to explicitly named BIOSECURE Act (NDAA Sec. 851) entity."
        )
    # 2. Programmatic subsidiary: parent company is named BCC → RED
    elif parent_company_is_biosecure_named:
        tier = "red"
        reasoning_parts.append("Parent company is explicitly named BIOSECURE Act entity.")
    else:
        # Country-adjusted fuzzy threshold: allied-country vendors need near-exact match to flag.
        fuzzy_threshold = get_fuzzy_threshold(country)
        if best_fuzzy < fuzzy_threshold:
            # Fuzzy match below threshold does not count; tier from country only.
            if country_flags:
                tier = "yellow"
                reasoning_parts.append("No watchlist match but vendor country is country-of-concern.")
            else:
                tier = "green"
                reasoning_parts.append("No watchlist match; no country-of-concern flag.")
        else:
            # 3. Tier from fuzzy: thresholds configured via scoring_config.yaml.
            # Only treat fuzzy match as amber/yellow if the matched entity is plausible
            # (shares a token with vendor name) to avoid false positives from weak matches.
            # When vendor_name is not passed (e.g. unit tests), allow fuzzy tier as before.
            best_match = vendor_match_results[0] if vendor_match_results else None
            best_matched_entity = (
                (best_match.get("matched_name") or best_match.get("matched_entity") or "")
                if best_match else ""
            )
            fuzzy_plausible = (vendor_name is None) or _match_is_plausible(vendor_name, best_matched_entity)

            # 3a. Hard-red escalation for high-severity watchlists when match is strong and plausible.
            hard_red_sources = {s.upper() for s in (config.hard_red_source_lists or [])}
            hard_red_entities = {e.lower() for e in (config.hard_red_watchlist_entities or [])}
            hard_red_applied = False
            if best_match and vendor_name and best_matched_entity:
                best_source_upper = best_source.upper()
                is_hard_source = best_source_upper in hard_red_sources
                is_hard_entity = best_matched_entity.lower() in hard_red_entities
                if fuzzy_plausible and best_fuzzy >= 90 and is_hard_source:
                    tier = "red"
                    reasoning_parts.append(
                        f"Direct watchlist match from {best_source} with high similarity; treated as hard RED."
                    )
                    hard_red_applied = True
                elif is_hard_entity:
                    tier = "red"
                    reasoning_parts.append(
                        f"Direct watchlist match to configured hard-red watchlist entity {best_matched_entity!r}."
                    )
                    hard_red_applied = True

            if not hard_red_applied:
                if best_fuzzy >= thresholds.red:
                    tier = "red"
                    if best_source == "BIOSECURE_NAMED":
                        reasoning_parts.append(
                            "Direct match to explicitly named BIOSECURE Act (NDAA Sec. 851) entity."
                        )
                    else:
                        reasoning_parts.append(
                            f"Direct/watchlist match score {best_fuzzy} >= red threshold {thresholds.red}."
                        )
                elif best_fuzzy >= thresholds.amber and fuzzy_plausible:
                    tier = "amber"
                    reasoning_parts.append("Strong alias match (>70% fuzzy score); human review required.")
                elif best_fuzzy >= thresholds.yellow and fuzzy_plausible:
                    tier = "yellow"
                    reasoning_parts.append(f"Partial match or country-of-concern; score {best_fuzzy} in yellow range.")
                else:
                    if country_flags:
                        tier = "yellow"
                        reasoning_parts.append("No watchlist match but vendor country is country-of-concern.")
                    else:
                        tier = "green"
                        reasoning_parts.append("No watchlist match; no country-of-concern flag.")

    # Parent chain overrides: first-degree → RED, second-degree → AMBER; third-degree → amber (fail safe)
    if not parent_company_is_biosecure_named and chain:
        if max_depth >= 1 and max_depth < 2:
            tier = "red"
            reasoning_parts.append("First-degree subsidiary of known BCC in parent graph.")
        elif max_depth >= 2 and max_depth < 3:
            if tier != "red":
                tier = "amber"
            reasoning_parts.append("Second-degree subsidiary of known BCC.")
        elif max_depth >= 3:
            if tier not in ("red", "amber"):
                tier = "amber"
            reasoning_parts.append("Third-degree or deeper subsidiary chain.")

    if not reasoning_parts:
        reasoning_parts.append("No match evidence.")
    reasoning = " ".join(reasoning_parts)

    logger.info(
        "score_vendor: best_fuzzy=%s composite=%s tier=%s reasoning=%s",
        best_fuzzy,
        confidence_score,
        tier,
        reasoning[:80],
    )
    return RiskTier(
        tier=tier,
        confidence_score=confidence_score,
        match_evidence=match_evidence,
        country_flags=country_flags,
        reasoning=reasoning,
    )
