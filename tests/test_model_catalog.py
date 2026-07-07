"""Model catalog: fit verdicts, disk guard, recommendation, and API routes."""

from fastapi.testclient import TestClient

from app.services.model_catalog import (
    DEFAULT_CATALOG, disk_ok, fit_verdict, load_catalog, recommend_download,
)

ENTRY = {"name": "x:7b", "size_gb": 4.7, "min_vram_gb": 6, "min_ram_gb": 12, "good_for": ["chat"]}


def test_fit_verdict_tiers():
    assert fit_verdict(ENTRY, vram_gb=8, ram_gb=16) == "full-gpu"
    assert fit_verdict(ENTRY, vram_gb=4, ram_gb=16) == "partial"
    assert fit_verdict(ENTRY, vram_gb=0, ram_gb=16) == "cpu"
    assert fit_verdict(ENTRY, vram_gb=0, ram_gb=4) == "too-big"


def test_disk_ok_margin():
    ok, _ = disk_ok(5.0, free_gb=6.5)
    assert ok
    ok, _ = disk_ok(5.0, free_gb=5.5)  # < 1.2x margin
    assert not ok


def test_recommend_scales_with_hardware():
    # Strong machine gets the biggest full-GPU chat model
    strong = recommend_download(DEFAULT_CATALOG, set(), vram_gb=8, ram_gb=16)
    assert strong in ("llama3.1:8b", "qwen2.5:7b")
    # Weak CPU-only machine gets a tiny model, never a 7B
    weak = recommend_download(DEFAULT_CATALOG, set(), vram_gb=0, ram_gb=4)
    assert weak == "llama3.2:1b"


def test_catalog_override(monkeypatch, tmp_path):
    import app.services.model_catalog as mc
    override = tmp_path / "model_catalog.json"
    override.write_text('[{"name": "custom:1b", "size_gb": 1.0, "min_vram_gb": 0, '
                        '"min_ram_gb": 2, "good_for": ["chat"], "blurb": "", "tier": "low"}]')
    monkeypatch.setattr(mc, "_OVERRIDE_FILE", override)
    cat = load_catalog()
    assert len(cat) == 1 and cat[0]["name"] == "custom:1b"


def test_catalog_route_works_without_ollama():
    from app.main import app
    client = TestClient(app)
    r = client.get("/api/system/models/catalog")
    assert r.status_code == 200
    d = r.json()
    assert d["catalog"] and "fit" in d["catalog"][0]
    assert "free_disk_gb" in d and "hardware_summary" in d


def test_delete_refuses_active_model():
    from app.main import app
    from app.config import settings
    client = TestClient(app)
    r = client.delete(f"/api/system/models/{settings.ollama_model}")
    assert r.status_code == 400
    assert "in use" in r.json()["detail"]
