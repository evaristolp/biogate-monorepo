"""
BioGate scoring configuration: load and validate YAML config.
Config is cached in memory; reload on app restart or explicit reload.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "scoring_config.yaml"
_cached_config: "ScoringConfig | None" = None


class TierThresholds(BaseModel):
    red: int
    amber: int
    yellow: int

    @model_validator(mode="after")
    def thresholds_ordered(self) -> "TierThresholds":
        if self.red < self.amber or self.amber < self.yellow:
            raise ValueError("tier_thresholds must satisfy red >= amber >= yellow")
        return self


class ScoreWeights(BaseModel):
    fuzzy_weight: float
    semantic_weight: float
    country_weight: float

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "ScoreWeights":
        total = self.fuzzy_weight + self.semantic_weight + self.country_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError("score_weights must sum to 1.0")
        return self


class ScoringConfig(BaseModel):
    version: str
    last_modified: str
    tier_thresholds: TierThresholds
    score_weights: ScoreWeights
    country_of_concern: list[str]
    hard_red_source_lists: list[str] = Field(default_factory=list)
    generic_tokens: list[str] = Field(default_factory=list)
    hard_red_watchlist_entities: list[str] = Field(default_factory=list)

    @field_validator("country_of_concern")
    @classmethod
    def non_empty_countries(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("country_of_concern must not be empty")
        return v

    @field_validator("hard_red_source_lists", "generic_tokens", "hard_red_watchlist_entities", mode="before")
    @classmethod
    def default_empty_list(cls, v: Any) -> list[str]:
        # Allow these fields to be omitted in older configs; normalize None to [].
        if v is None:
            return []
        return list(v)


def load_scoring_config(path: Path | None = None) -> ScoringConfig:
    """
    Load and validate scoring config from YAML file.
    Uses BIOGATE_SCORING_CONFIG_PATH if set, else default path.
    Caches result in memory; reload on next process start.
    """
    global _cached_config
    if path is None:
        path = Path(os.environ.get("BIOGATE_SCORING_CONFIG_PATH", str(_DEFAULT_CONFIG_PATH)))
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(
            f"Scoring config not found: {path}. "
            "Set BIOGATE_SCORING_CONFIG_PATH or ensure backend/config/scoring_config.yaml exists."
        )
    raw = yaml.safe_load(path.read_text())
    if not raw:
        raise ValueError("Scoring config file is empty")
    _cached_config = ScoringConfig.model_validate(raw)
    return _cached_config


def get_scoring_config() -> ScoringConfig:
    """
    Return cached config; load from default path if not yet loaded.
    Raises if config has never been loaded and load fails.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = load_scoring_config()
    return _cached_config


def clear_scoring_config_cache() -> None:
    """Clear in-memory cache (for tests)."""
    global _cached_config
    _cached_config = None
