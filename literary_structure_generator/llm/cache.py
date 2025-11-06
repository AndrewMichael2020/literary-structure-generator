"""
SQLite-based cache for LLM responses.

Caches responses keyed by component, model, template version, params hash, and input hash.
Reduces API costs and improves reproducibility.
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional


class LLMCache:
    """SQLite-based cache for LLM responses."""

    def __init__(self, cache_path: Optional[str] = None):
        """
        Initialize cache.

        Args:
            cache_path: Path to SQLite database file. Defaults to runs/llm_cache.db
        """
        if cache_path is None:
            cache_path = Path.cwd() / "runs" / "llm_cache.db"
        else:
            cache_path = Path(cache_path)

        cache_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = str(cache_path)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                component TEXT NOT NULL,
                model TEXT NOT NULL,
                template_version TEXT NOT NULL,
                params_hash TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indices for faster lookups
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_component
            ON llm_cache(component)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_created_at
            ON llm_cache(created_at)
        """
        )

        conn.commit()
        conn.close()

    def _compute_cache_key(
        self,
        component: str,
        model: str,
        template_version: str,
        params: dict,
        input_text: str,
    ) -> str:
        """
        Compute cache key from inputs.

        Args:
            component: Component name
            model: Model identifier
            template_version: Template version string
            params: LLM parameters
            input_text: Input prompt text

        Returns:
            SHA256 hash as cache key
        """
        # Create deterministic params hash
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]

        # Create input hash
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()[:16]

        # Combine all elements
        key_parts = [component, model, template_version, params_hash, input_hash]
        key_string = "|".join(key_parts)

        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(
        self,
        component: str,
        model: str,
        template_version: str,
        params: dict,
        input_text: str,
    ) -> Optional[str]:
        """
        Retrieve cached response if available.

        Args:
            component: Component name
            model: Model identifier
            template_version: Template version
            params: LLM parameters
            input_text: Input prompt

        Returns:
            Cached response or None if not found
        """
        cache_key = self._compute_cache_key(component, model, template_version, params, input_text)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT response FROM llm_cache WHERE cache_key = ?", (cache_key,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def put(
        self,
        component: str,
        model: str,
        template_version: str,
        params: dict,
        input_text: str,
        response: str,
    ):
        """
        Store response in cache.

        Args:
            component: Component name
            model: Model identifier
            template_version: Template version
            params: LLM parameters
            input_text: Input prompt
            response: LLM response to cache
        """
        cache_key = self._compute_cache_key(component, model, template_version, params, input_text)

        # Compute hashes for storage
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO llm_cache
            (cache_key, component, model, template_version, params_hash, input_hash, response)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (cache_key, component, model, template_version, params_hash, input_hash, response),
        )

        conn.commit()
        conn.close()

    def clear(self, component: Optional[str] = None):
        """
        Clear cache entries.

        Args:
            component: If specified, only clear entries for this component.
                      If None, clear all entries.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if component:
            cursor.execute("DELETE FROM llm_cache WHERE component = ?", (component,))
        else:
            cursor.execute("DELETE FROM llm_cache")

        conn.commit()
        conn.close()

    def stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM llm_cache")
        total_entries = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT component, COUNT(*) as count
            FROM llm_cache
            GROUP BY component
        """
        )
        by_component = dict(cursor.fetchall())

        conn.close()

        return {
            "total_entries": total_entries,
            "by_component": by_component,
            "db_path": self.db_path,
        }
