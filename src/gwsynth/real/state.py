from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RunState:
    run_name: str
    version: int = 1
    drives: dict[str, str] = field(default_factory=dict)
    folders: dict[str, str] = field(default_factory=dict)
    docs: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "run_name": self.run_name,
            "drives": self.drives,
            "folders": self.folders,
            "docs": self.docs,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunState":
        return cls(
            run_name=str(data.get("run_name", "")),
            version=int(data.get("version", 1)),
            drives=dict(data.get("drives", {})),
            folders=dict(data.get("folders", {})),
            docs=dict(data.get("docs", {})),
        )


def load_state(path: str, run_name: str) -> RunState:
    target = Path(path)
    if not target.exists():
        return RunState(run_name=run_name)
    data = json.loads(target.read_text())
    if not isinstance(data, dict):
        return RunState(run_name=run_name)
    state = RunState.from_dict(data)
    if state.run_name != run_name:
        return RunState(run_name=run_name)
    return state


def save_state(path: str, state: RunState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True))
