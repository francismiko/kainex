"""Model version management with persistence.

Models are serialized via joblib to ``data/models/<name>/<version>.joblib``.
Metadata (name, version, metrics, timestamps) is stored in a SQLite database
alongside the model files so that the registry survives process restarts.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

_DEFAULT_BASE_DIR = Path(__file__).resolve().parents[3] / "data" / "models"


@dataclass
class ModelVersion:
    name: str
    version: str
    path: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


class ModelRegistry:
    """Tracks and serves ML model versions.

    Models are persisted to disk via joblib.  A lightweight SQLite database
    (``registry.db``) in the base directory stores the metadata so that model
    listings and version lookups do not require scanning the filesystem.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else _DEFAULT_BASE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self.base_dir / "registry.db"
        self._init_db()

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    name       TEXT NOT NULL,
                    version    TEXT NOT NULL,
                    path       TEXT NOT NULL,
                    metrics    TEXT DEFAULT '{}',
                    metadata   TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (name, version)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        model: Any,
        metadata: dict | None = None,
        metrics: dict | None = None,
        version: str | None = None,
    ) -> ModelVersion:
        """Serialize *model* to disk and record metadata.

        Parameters
        ----------
        name : str
            Logical model name (e.g. ``"rf_classifier"``).
        model : Any
            A picklable / joblib-serializable model object.
        metadata : dict, optional
            Arbitrary key-value metadata.
        metrics : dict, optional
            Evaluation metrics (accuracy, f1, etc.).
        version : str, optional
            Explicit version tag.  If ``None``, an auto-incrementing integer
            is used (``"1"``, ``"2"``, ...).

        Returns
        -------
        ModelVersion
        """
        if version is None:
            version = str(self._next_version(name))

        model_dir = self.base_dir / name
        model_dir.mkdir(parents=True, exist_ok=True)
        model_path = model_dir / f"{version}.joblib"
        joblib.dump(model, model_path)
        logger.info("Saved model %s v%s -> %s", name, version, model_path)

        now = datetime.now(timezone.utc)
        mv = ModelVersion(
            name=name,
            version=version,
            path=str(model_path),
            created_at=now,
            metrics=metrics or {},
            metadata=metadata or {},
        )

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO models
                   (name, version, path, metrics, metadata, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    mv.name,
                    mv.version,
                    mv.path,
                    json.dumps(mv.metrics),
                    json.dumps(mv.metadata),
                    mv.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return mv

    def load(self, name: str, version: str | None = None) -> Any:
        """Load a model object from disk.

        Parameters
        ----------
        name : str
            Logical model name.
        version : str, optional
            Specific version.  If ``None``, the latest version is loaded.

        Returns
        -------
        The deserialized model object.

        Raises
        ------
        FileNotFoundError
            If the model/version does not exist.
        """
        mv = self.get_version(name, version) if version else self.get_latest(name)
        if mv is None:
            raise FileNotFoundError(
                f"Model '{name}' version '{version or 'latest'}' not found in registry"
            )
        path = Path(mv.path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        return joblib.load(path)

    def get_latest(self, name: str) -> ModelVersion | None:
        """Return the most recent ``ModelVersion`` for *name*, or ``None``."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM models WHERE name = ? ORDER BY created_at DESC LIMIT 1",
                (name,),
            ).fetchone()
        finally:
            conn.close()
        return self._row_to_mv(row) if row else None

    def get_version(self, name: str, version: str) -> ModelVersion | None:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM models WHERE name = ? AND version = ?",
                (name, version),
            ).fetchone()
        finally:
            conn.close()
        return self._row_to_mv(row) if row else None

    def list_models(self) -> list[str]:
        """Return distinct model names registered."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT DISTINCT name FROM models ORDER BY name"
            ).fetchall()
        finally:
            conn.close()
        return [r["name"] for r in rows]

    def list_versions(self, name: str) -> list[ModelVersion]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM models WHERE name = ? ORDER BY created_at",
                (name,),
            ).fetchall()
        finally:
            conn.close()
        return [self._row_to_mv(r) for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_version(self, name: str) -> int:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT MAX(CAST(version AS INTEGER)) as max_v FROM models WHERE name = ?",
                (name,),
            ).fetchone()
        finally:
            conn.close()
        current = row["max_v"] if row and row["max_v"] is not None else 0
        return current + 1

    @staticmethod
    def _row_to_mv(row: sqlite3.Row) -> ModelVersion:
        return ModelVersion(
            name=row["name"],
            version=row["version"],
            path=row["path"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metrics=json.loads(row["metrics"]),
            metadata=json.loads(row["metadata"]),
        )
