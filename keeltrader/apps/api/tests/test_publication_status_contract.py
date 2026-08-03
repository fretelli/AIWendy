from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_market_cache_is_versioned_by_publication_and_capability_snapshots():
    router = (ROOT / "routers/markets.py").read_text(encoding="utf-8")
    cache = (ROOT / "services/agent_platform/market_cache.py").read_text(encoding="utf-8")
    reader = (ROOT / "services/agent_platform/publication_status.py").read_text(encoding="utf-8")
    config = (ROOT / "config.py").read_text(encoding="utf-8")
    assert "market_cache_key(key)" in router
    assert 'f"markets:v5:{publication_version()}:{capability_version()}:{key}"' in cache
    assert '"publication": read_publication_status()' in router
    assert "path.stat().st_mtime_ns" in reader
    assert 'market_publication_status_path: str = "/app/market-publication/publication-status.json"' in config
    assert 'market_capability_manifest_path: str = "/app/market-publication/capability-manifest.json"' in config
