"""Typed domain records used between Discord adapters and services."""
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class PlannedAction:
    op: str
    name: str
    type: str | None = None
    category: str | None = None
    preset: str = "publico"
    roles: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        values = {"op": self.op, "name": self.name, "type": self.type, "category": self.category,
                  "preset": self.preset, "roles": list(self.roles)}
        return {key: value for key, value in values.items() if value is not None}


@dataclass(slots=True)
class ApplyResults:
    created: int = 0
    failed: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class MemberRecord:
    guild_id: str
    user_id: str
    username: str
    display_name: str
    birthday: str | None
    rank: str
    platoon: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True, frozen=True)
class ApplicationRecord:
    id: int
    guild_id: str
    user_id: str
    username: str
    answers: dict[str, str]
    message_id: str | None
    status: str
    created_at: str
