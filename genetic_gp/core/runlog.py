"""Structured logging for evolution runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


@dataclass
class RunLogger:
    """Write structured JSONL events for reconstruction and analysis."""

    path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)
    _handle: Optional[Any] = field(default=None, init=False, repr=False)

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("a", encoding="utf-8")
        self.log_event("log_started", {"metadata": self.metadata})

    def close(self) -> None:
        if self._handle is None:
            return
        self.log_event("log_closed", {})
        self._handle.close()
        self._handle = None

    def log_event(self, event: str, payload: Dict[str, Any]) -> None:
        if self._handle is None:
            self.open()
        record = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "payload": payload,
        }
        self._handle.write(json.dumps(record, default=str) + "\n")
        self._handle.flush()

    def log_population(self, generation: int, population: Iterable[tuple[Any, float]]) -> None:
        self.log_event(
            "population",
            {
                "generation": generation,
                "members": [
                    {
                        "expr": repr(expr),
                        "fitness": fitness,
                        "complexity": getattr(expr, "complexity", lambda: None)(),
                    }
                    for expr, fitness in population
                ],
            },
        )
