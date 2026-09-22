"""
RuleLoader — loads rule definitions from rules.json.

STATUS: NOT IMPLEMENTED — Stub only.
"""
import json
from pathlib import Path


class RuleLoader:
    def __init__(self, rules_file: str = None):
        self.rules_file = rules_file or (Path(__file__).parent / "rules.json")

    def load(self) -> dict:
        """TODO: Load and validate rules from rules.json."""
        with open(self.rules_file, "r") as f:
            return json.load(f)
