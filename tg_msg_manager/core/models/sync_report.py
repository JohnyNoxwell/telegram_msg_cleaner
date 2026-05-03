from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass()
class TrackedSyncUserStat:
    name: str
    count: int = 0
    dirty: bool = False

    @classmethod
    def coerce(cls, value: Any) -> "TrackedSyncUserStat":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                name=str(value.get("name") or ""),
                count=int(value.get("count", 0) or 0),
                dirty=bool(value.get("dirty", False)),
            )
        raise TypeError(f"Unsupported tracked sync stat payload: {type(value)!r}")

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


@dataclass()
class TrackedSyncRunReport:
    user_stats: dict[int, TrackedSyncUserStat] = field(default_factory=dict)

    @classmethod
    def coerce(cls, value: Any) -> "TrackedSyncRunReport":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            normalized: dict[int, TrackedSyncUserStat] = {}
            for uid, item in value.items():
                try:
                    normalized_uid = int(uid)
                except (TypeError, ValueError) as exc:
                    raise TypeError(
                        f"Unsupported tracked sync user id: {uid!r}"
                    ) from exc
                normalized[normalized_uid] = TrackedSyncUserStat.coerce(item)
            return cls(user_stats=normalized)
        raise TypeError(f"Unsupported tracked sync report payload: {type(value)!r}")

    @property
    def total_processed(self) -> int:
        return sum(item.count for item in self.user_stats.values())

    def dirty_user_ids(self) -> list[int]:
        return [
            uid for uid, stat in self.user_stats.items() if stat.dirty or stat.count > 0
        ]

    def __getitem__(self, key: int) -> TrackedSyncUserStat:
        return self.user_stats[key]

    def __setitem__(self, key: int, value: Any) -> None:
        self.user_stats[int(key)] = TrackedSyncUserStat.coerce(value)

    def __contains__(self, key: object) -> bool:
        return key in self.user_stats

    def __iter__(self):
        return iter(self.user_stats)

    def __len__(self) -> int:
        return len(self.user_stats)

    def get(self, key: int, default: Any = None) -> Any:
        return self.user_stats.get(key, default)

    def items(self):
        return self.user_stats.items()

    def values(self):
        return self.user_stats.values()

    def keys(self):
        return self.user_stats.keys()
