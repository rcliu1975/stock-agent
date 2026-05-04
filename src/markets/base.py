from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MarketProfile:
    code: str
    name: str
    currency: str
    timezone: str

