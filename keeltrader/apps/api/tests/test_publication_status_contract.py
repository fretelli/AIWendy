from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]


def test_market_cache_is_versioned_by_atomic_publication_snapshot():
    router = (ROOT / "routers/markets.py").read_text(encoding="utf-8")
    reader = (ROOT / "services/agent_platform/publication_status.py").read_text(encoding="utf-8")
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    assert 'f"markets:v4:{version}:{key}"' in router
    assert '"publication": read_publication_status()' in router
    assert "path.stat().st_mtime_ns" in reader
    assert "/opt/services/tushare/data/publication-status:/app/market-publication:ro" in compose
