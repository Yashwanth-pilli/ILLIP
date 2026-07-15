"""Print the best-fit model for this machine as: name|size_gb|vram_gb|ram_gb

Used by setup.ps1 so the installer and the running app share ONE
recommendation source (hardware detector + user-overridable model catalog)
instead of a duplicated hardcoded ladder.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.hardware.detector import get_hardware_info
from app.services.model_catalog import load_catalog, recommend_download

hw = get_hardware_info()
cat = load_catalog()
name = recommend_download(cat, set(), hw.gpu_vram_gb, hw.ram_gb) \
    or min(cat, key=lambda e: e.get("size_gb", 99))["name"]
size = next((e.get("size_gb", 0) for e in cat if e["name"] == name), 0)
print(f"{name}|{size}|{hw.gpu_vram_gb}|{hw.ram_gb}")
