from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ModelVersion:
    name: str
    version: str
    path: str
    created_at: datetime = field(default_factory=datetime.now)
    metrics: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class ModelRegistry:
    """Tracks and serves ML model versions."""

    def __init__(self, base_dir: str = "./models") -> None:
        self.base_dir = Path(base_dir)
        self._models: dict[str, list[ModelVersion]] = {}

    def register(
        self,
        name: str,
        version: str,
        path: str,
        metrics: dict | None = None,
        metadata: dict | None = None,
    ) -> ModelVersion:
        mv = ModelVersion(
            name=name,
            version=version,
            path=path,
            metrics=metrics or {},
            metadata=metadata or {},
        )
        self._models.setdefault(name, []).append(mv)
        return mv

    def get_latest(self, name: str) -> ModelVersion | None:
        versions = self._models.get(name, [])
        if not versions:
            return None
        return max(versions, key=lambda v: v.created_at)

    def get_version(self, name: str, version: str) -> ModelVersion | None:
        for mv in self._models.get(name, []):
            if mv.version == version:
                return mv
        return None

    def list_models(self) -> list[str]:
        return list(self._models.keys())

    def list_versions(self, name: str) -> list[ModelVersion]:
        return list(self._models.get(name, []))
