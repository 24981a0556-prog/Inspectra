"""
RuleLoader — loads and indexes rules from rules.json.

Rules are indexed by engine type (declaration / measurement) for fast lookup.
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RULES_FILE = Path(__file__).parent / "rules.json"


class RuleLoader:
    def __init__(self, rules_file: str | Path | None = None):
        self._rules_file = Path(rules_file) if rules_file else _RULES_FILE
        self._data: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load and return the raw rules dict."""
        if self._data is None:
            with open(self._rules_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(
                "RuleLoader: loaded rules v%s from %s",
                self._data.get("version", "unknown"),
                self._rules_file
            )
        return self._data

    @property
    def version(self) -> str:
        return self.load().get("version", "unknown")

    def get_declaration_rules(self) -> list[dict[str, Any]]:
        """Return all declaration rules."""
        return self.load().get("declaration_rules", [])

    def get_measurement_rules(self) -> list[dict[str, Any]]:
        """Return all measurement/presentation rules."""
        return self.load().get("measurement_rules", [])

    def get_rule_by_id(self, rule_id: str) -> dict[str, Any] | None:
        """Look up a single rule by ID across all engines."""
        for rule in self.get_declaration_rules() + self.get_measurement_rules():
            if rule.get("id") == rule_id:
                return rule
        return None


# Module-level singleton
_loader: RuleLoader | None = None


def get_rule_loader() -> RuleLoader:
    global _loader
    if _loader is None:
        _loader = RuleLoader()
    return _loader
