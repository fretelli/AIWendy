from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from services.agent_platform import capabilities


class CapabilityManifestContractTests(unittest.TestCase):
    def tearDown(self) -> None:
        capabilities._cached = None

    def use_manifest(self, path: Path):
        return mock.patch.object(
            capabilities, "get_settings",
            return_value=SimpleNamespace(market_capability_manifest_path=str(path)),
        )

    def test_missing_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir, self.use_manifest(Path(tmpdir) / "missing.json"):
            self.assertEqual(capabilities.queryable_tables(), frozenset())
            self.assertEqual(capabilities.physical_tables(), frozenset())
            self.assertFalse(capabilities.read_capability_manifest()["available"])

    def test_damaged_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "capability-manifest.json"
            target.write_text("{not-json", encoding="utf-8")
            with self.use_manifest(target):
                self.assertEqual(capabilities.queryable_tables(), frozenset())
                self.assertEqual(capabilities.physical_tables(), frozenset())

    def test_manifest_is_the_only_query_allowlist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "capability-manifest.json"
            target.write_text(json.dumps({
                "schema_version": 3,
                "version": "test-v3",
                "capabilities": [
                    {"table": "daily_basic", "physical": True, "available": True, "exposure": "typed_api"},
                    {"table": "fund_nav", "physical": True, "available": True, "exposure": "agent_query"},
                    {"table": "trade_cal", "physical": True, "available": True, "exposure": "internal"},
                    {"table": "bad-name;drop", "physical": True, "available": True, "exposure": "agent_query"},
                ],
            }), encoding="utf-8")
            with self.use_manifest(target):
                self.assertEqual(capabilities.queryable_tables(), frozenset({"daily_basic", "fund_nav"}))
                self.assertEqual(
                    capabilities.physical_tables(),
                    frozenset({"daily_basic", "fund_nav", "trade_cal"}),
                )


if __name__ == "__main__":
    unittest.main()
