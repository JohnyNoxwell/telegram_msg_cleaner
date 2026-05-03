from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AliasHelpEntry:
    alias: str
    label_key: str


@dataclass(frozen=True)
class AliasInstallResult:
    success: bool
    platform: str
    rc_path: Optional[str] = None
    bin_dir: Optional[str] = None
    error_kind: Optional[str] = None
    error_detail: Optional[str] = None


@dataclass(frozen=True)
class SchedulerSetupRequest:
    hour: int = 5
    minute: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.hour <= 23:
            raise ValueError("hour must be between 0 and 23")
        if not 0 <= self.minute <= 59:
            raise ValueError("minute must be between 0 and 59")


@dataclass(frozen=True)
class SchedulerSetupResult:
    success: bool
    plist_path: str
    logs_dir: str
    hour: int
    minute: int
    error_kind: Optional[str] = None
    error_detail: Optional[str] = None
