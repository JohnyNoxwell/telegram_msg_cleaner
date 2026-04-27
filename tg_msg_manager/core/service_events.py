from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass(frozen=True)
class ServiceEvent:
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)


ServiceEventSink = Optional[Callable[[ServiceEvent], None]]


def emit_service_event(sink: ServiceEventSink, event_name: str, **payload: Any) -> None:
    if sink is None:
        return
    sink(ServiceEvent(name=event_name, payload=payload))
