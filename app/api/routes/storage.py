"""Telegram cloud storage endpoints — backup, restore, snapshot management."""

import tempfile
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.telegram_storage import get_telegram_storage

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/status")
async def storage_status():
    """Telegram storage config status + snapshot count."""
    ts = get_telegram_storage()
    configured = ts.is_configured()
    count = 0
    if configured:
        try:
            snapshots = await ts.list_snapshots()
            count = len(snapshots)
        except Exception:
            count = -1
    return {
        "configured": configured,
        "snapshot_count": count,
        "requires": ["TELEGRAM_STORAGE_TOKEN", "TELEGRAM_STORAGE_CHAT_ID"],
    }


@router.get("/snapshots")
async def list_snapshots():
    """List all stored snapshots."""
    ts = get_telegram_storage()
    if not ts.is_configured():
        raise HTTPException(status_code=503, detail="Telegram storage not configured")
    return {"snapshots": await ts.list_snapshots()}


@router.post("/backup/memory")
async def backup_memory():
    """Upload all memory files to Telegram storage."""
    ts = get_telegram_storage()
    if not ts.is_configured():
        raise HTTPException(status_code=503, detail="Telegram storage not configured")
    ok = await ts.backup_memory()
    if not ok:
        raise HTTPException(status_code=500, detail="Backup failed or no memory files found")
    return {"success": True, "backup": "memory_backup"}


@router.post("/backup/kg")
async def backup_knowledge_graph():
    """Upload knowledge graph to Telegram storage."""
    ts = get_telegram_storage()
    if not ts.is_configured():
        raise HTTPException(status_code=503, detail="Telegram storage not configured")
    ok = await ts.backup_knowledge_graph()
    if not ok:
        raise HTTPException(status_code=500, detail="Backup failed or no KG files found")
    return {"success": True, "backup": "kg_backup"}


@router.post("/restore/{name}")
async def restore_snapshot(name: str):
    """Restore latest snapshot by name."""
    ts = get_telegram_storage()
    if not ts.is_configured():
        raise HTTPException(status_code=503, detail="Telegram storage not configured")
    data = await ts.restore_latest(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No snapshot found for '{name}'")
    return {"restored": name, "keys": list(data.keys()), "data": data}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload arbitrary file to Telegram storage."""
    ts = get_telegram_storage()
    if not ts.is_configured():
        raise HTTPException(status_code=503, detail="Telegram storage not configured")
    suffix = os.path.splitext(file.filename or "")[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        file_id = await ts.upload_file(tmp_path, caption=file.filename or "upload")
    finally:
        os.unlink(tmp_path)
    if not file_id:
        raise HTTPException(status_code=500, detail="Upload failed")
    return {"success": True, "file_id": file_id, "filename": file.filename}
