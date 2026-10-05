"""Provider-neutral interaction contract. Production adapter intentionally unconfigured."""
from itertools import combinations
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Normalization(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    index: int = Field(ge=0)
    status: Literal['resolved', 'ambiguous', 'unmatched']
    ingredient_ids: list[str] = Field(max_length=20)


class PairAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    left: int = Field(ge=0)
    right: int = Field(ge=0)
    status: Literal['alert', 'no_alert', 'not_assessed']
    description: str = Field(min_length=1, max_length=2000)
    source_reference: str = Field(min_length=1, max_length=2000)
    severity: Literal['CRITICAL', 'HIGH', 'MODERATE', 'LOW'] | None = None

    @model_validator(mode='after')
    def alert_severity(self):
        if (self.status == 'alert') != (self.severity is not None):
            raise ValueError('Only alerts require an explicit provider severity')
        return self


class InteractionResult(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    provider: str = Field(min_length=1, max_length=200)
    source_version: str = Field(min_length=1, max_length=200)
    scope: str = Field(min_length=1, max_length=2000)
    normalization: list[Normalization] = Field(max_length=100)
    pairs: list[PairAssessment] = Field(max_length=4950)


class InteractionProvider(Protocol):
    def check(self, medications: list[str]) -> dict: ...


def configured_provider():
    return None


def assess_interactions(medications, provider=None):
    if provider is None:
        return {'status':'NOT_CONFIGURED', 'result':None}
    if len(medications) > 100:
        return {'status':'INPUT_LIMIT_EXCEEDED', 'result':None}
    try:
        result = InteractionResult.model_validate(provider.check(list(medications)))
        normalized = {item.index:item for item in result.normalization}
        if len(normalized) != len(result.normalization) or set(normalized) != set(range(len(medications))):
            raise ValueError('Normalization must cover each input exactly once')
        for item in normalized.values():
            if (item.status == 'resolved') != bool(item.ingredient_ids) or any(not key.strip() for key in item.ingredient_ids):
                raise ValueError('Unresolved names must not select ingredients')
        expected = set(combinations(range(len(medications)), 2))
        seen = set()
        for pair in result.pairs:
            key = (pair.left, pair.right)
            if key not in expected or key in seen:
                raise ValueError('Invalid or duplicate medication pair')
            seen.add(key)
            if pair.status != 'not_assessed' and any(normalized[i].status != 'resolved' for i in key):
                raise ValueError('Cannot assess ambiguously normalized medication')
        partial = seen != expected or any(p.status == 'not_assessed' for p in result.pairs) or any(n.status != 'resolved' for n in normalized.values())
        return {'status':'PARTIAL' if partial else 'ASSESSED_WITHIN_PROVIDER_SCOPE', 'result':result.model_dump()}
    except Exception:
        # Do not persist raw provider errors or patient text from transport failures.
        return {'status':'FAILED', 'result':None}
