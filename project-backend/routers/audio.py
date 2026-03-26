# =============================================================================
# routers/audio.py — v0.8.0
# Router สำหรับจัดการไฟล์เสียง: Upload, Play, Delete, List
# =============================================================================

import os
import re
import uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse, JSONResponse

from services.file_converter import (
    save_uploaded_file,
    convert_to_wav,
    find_converted_file,
    find_uploaded_file,
    delete_files_by_id,
    check_ffmpeg_available,
    ALL_SUPPORTED_EXTENSIONS,
    UPLOAD_DIR,
    CONVERTED_DIR,
)
from database.mock_db import (
    MOCK_AUDIO_FILES,
    MOCK_SAMPLE_ANALYSIS,
    get_all_audio_files,
    get_audio_file_by_id,
    get_analysis_by_file_id,
    add_audio_file,
    add_sample_analysis,
)

router = APIRouter()

FILE_METADATA_STORE: dict = {}


# =============================================================================
# FILENAME PARSER — ดึงข้อมูลจากชื่อไฟล์
# =============================================================================
# Pattern:
#   20251104173706-1762252614_105999-104-0819979336-Outbound.wav
#   {yyyyMMddHHmmss}-{id}_{id}-{agent}-{customer}-{direction}.{ext}
# =============================================================================

# Pattern: yyyyMMddHHmmss-{ids}-{numA}-{numB}-{direction}.ext
# Outbound: numA=agent, numB=customer
# Inbound:  numA=customer, numB=agent
_PATTERN_LONG = re.compile(
    r'^(\d{14})'                     # group 1: datetime (yyyyMMddHHmmss)
    r'-[\d.]+'                       # skip IDs (digits + dots)
    r'-(\d+)'                        # group 2: number A
    r'-(\d+)'                        # group 3: number B
    r'-(Inbound|Outbound|inbound|outbound)'  # group 4: call direction
    r'\.\w+$'                        # .ext
)


def _parse_filename(filename: str) -> dict:
    """
    ดึง date, customer, agent, call_direction จากชื่อไฟล์
    
    Pattern:
      20251104173706-1762252614.105999-104-0819979336-Outbound.wav
      20251201175254-1764586296.121193-0634654956-102-Inbound.wav
    
    Outbound: ...-{agent}-{customer}-Outbound
    Inbound:  ...-{customer}-{agent}-Inbound
    """
    result = {
        "call_date": None,
        "customer_phone": None,
        "agent_id": None,
        "call_direction": None,
    }

    m = _PATTERN_LONG.match(filename)
    if m:
        dt_str = m.group(1)
        try:
            dt = datetime.strptime(dt_str, "%Y%m%d%H%M%S")
            result["call_date"] = dt.isoformat()
        except ValueError:
            pass

        num_a = m.group(2)
        num_b = m.group(3)
        direction = m.group(4).capitalize()
        result["call_direction"] = direction

        if direction == "Outbound":
            # Outbound: agent-customer
            agent_num = num_a
            phone = num_b
        else:
            # Inbound: customer-agent
            phone = num_a
            agent_num = num_b

        result["agent_id"] = f"AGENT-{agent_num}"
        if len(phone) == 10:
            result["customer_phone"] = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
        else:
            result["customer_phone"] = phone

    return result


# =============================================================================
# GET /list — รายการไฟล์ทั้งหมด (sample + uploaded)
# =============================================================================
@router.get("/list", summary="📋 ดูรายการไฟล์ทั้งหมด")
async def list_files(
    search: Optional[str] = None,
    brand: Optional[str] = None,
    product: Optional[str] = None,
    date_from: Optional[str] = None,   # ISO date: 2025-12-01
    date_to: Optional[str] = None,     # ISO date: 2025-12-31
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
):
    files = []

    # Uploaded files only (ไม่แสดง sample mockup)
    for file_id, record in FILE_METADATA_STORE.items():
        analysis = get_analysis_by_file_id(file_id)
        sentiment = "NEUTRAL"
        brand_names = []
        file_status = record.get("status", "ready")

        if analysis:
            s = analysis.get("sentiment", "neutral").lower()
            sentiment = "POSITIVE" if s == "positive" else "NEGATIVE" if s == "negative" else "NEUTRAL"
            brand_names = analysis.get("brand_names", [])
            if not brand_names:
                bn = analysis.get("brand_name", "")
                brand_names = [bn] if bn and bn != "Unknown" else []
            file_status = "analyzed"

        files.append({
            "file_id": file_id,
            "name": record.get("original_filename", ""),
            "customer": record.get("customer_phone", "N/A"),
            "agent": record.get("agent_id", "N/A"),
            "agent_name": record.get("agent_name", ""),
            "brand": ", ".join(brand_names) if brand_names else "",
            "brands": brand_names,
            "product": analysis.get("product_category", "") if analysis else "",
            "sentiment": sentiment,
            "status": "COMPLETE" if file_status == "analyzed" else "PROCESSING",
            "date": record.get("call_date", record.get("uploaded_at", "")),
            "call_direction": record.get("call_direction", ""),
        })

    # Filters
    if search:
        sl = search.lower()
        files = [f for f in files if
            sl in f["name"].lower() or
            sl in f["customer"].lower() or
            sl in f["agent"].lower() or
            sl in f["brand"].lower() or
            sl in f["status"].lower()
        ]
    if brand:
        bl = brand.lower()
        files = [f for f in files if bl in f["brand"].lower()]
    if product:
        pl = product.lower()
        files = [f for f in files if f.get("product", "").lower() == pl]
    if date_from:
        files = [f for f in files if f["date"] >= date_from]
    if date_to:
        files = [f for f in files if f["date"][:10] <= date_to]
    if status:
        files = [f for f in files if f["status"].lower() == status.lower()]

    total = len(files)
    start = (page - 1) * per_page
    paginated = files[start:start + per_page]

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, (total + per_page - 1) // per_page),
        "files": paginated,
    }


# =============================================================================
# GET /detail/{file_id} — ข้อมูลละเอียดพร้อม AI analysis
# =============================================================================
@router.get("/detail/{file_id}", summary="🔍 ดูรายละเอียดไฟล์พร้อมผลวิเคราะห์ AI")
async def get_file_detail(file_id: str):
    audio = get_audio_file_by_id(file_id)
    if not audio:
        audio = FILE_METADATA_STORE.get(file_id)
    if not audio:
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ ID: {file_id}")

    analysis = get_analysis_by_file_id(file_id)

    return {
        "file": audio,
        "analysis": analysis,
        "play_url": f"/api/v1/audio/play/{file_id}",
    }


# =============================================================================
# POST /upload — อัปโหลดไฟล์เสียง
# =============================================================================
@router.post("/upload", summary="📤 อัปโหลดไฟล์เสียง + เริ่มวิเคราะห์อัตโนมัติ", status_code=201)
async def upload_audio(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    customer_phone: str = Form(default="N/A"),
    agent_id: str = Form(default="N/A"),
    agent_name: str = Form(default=""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="กรุณาเลือกไฟล์")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALL_SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"นามสกุล '{ext}' ไม่รองรับ")

    content = await file.read()
    if len(content) > 60 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="ไฟล์ใหญ่เกิน 60MB")

    try:
        file_id, uploaded_path = save_uploaded_file(content, file.filename)
    except (ValueError, IOError) as e:
        raise HTTPException(status_code=500, detail=str(e))

    converted_path = uploaded_path
    conversion_metadata = {
        "original_format": ext,
        "original_size_mb": round(len(content) / (1024 * 1024), 2),
        "converted_size_mb": round(len(content) / (1024 * 1024), 2),
        "sample_rate": 16000, "channels": 1, "conversion_time_seconds": 0.0,
    }

    if ext != ".wav" and check_ffmpeg_available():
        try:
            converted_path, conversion_metadata = convert_to_wav(uploaded_path)
        except Exception:
            pass

    # ★ Parse ข้อมูลจากชื่อไฟล์ (date, customer, agent, call direction)
    parsed = _parse_filename(file.filename)

    file_record = {
        "file_id": file_id,
        "original_filename": file.filename,
        "uploaded_path": str(uploaded_path),
        "converted_path": str(converted_path),
        "status": "processing",
        "customer_phone": parsed["customer_phone"] or customer_phone,
        "agent_id": parsed["agent_id"] or agent_id,
        "agent_name": agent_name,
        "call_direction": parsed["call_direction"] or "Unknown",
        "call_date": parsed["call_date"] or datetime.now().isoformat(),
        "uploaded_at": datetime.now().isoformat(),
        "conversion_details": conversion_metadata,
    }
    FILE_METADATA_STORE[file_id] = file_record

    # =================================================================
    # AUTO-ANALYZE: เข้าคิววิเคราะห์ AI อัตโนมัติ (ทีละ 1 ไฟล์)
    # =================================================================
    task_id = None
    try:
        import uuid
        from routers.ai_task import TASK_STORE, TaskStatus, _add_to_queue

        task_id = str(uuid.uuid4())
        TASK_STORE[task_id] = {
            "task_id": task_id,
            "file_id": file_id,
            "customer_id": None,
            "priority": "normal",
            "status": TaskStatus.QUEUED,
            "is_retest": False,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "message": "📋 อัปโหลดเสร็จ — รอคิววิเคราะห์...",
            "result": None,
            "error": None,
        }

        # ★ เข้าคิวแทน background_tasks — ประมวลผลทีละ 1 ไฟล์
        await _add_to_queue(
            task_id=task_id,
            file_id=file_id,
            audio_file_path=str(converted_path),
            customer_id=None,
            retest=False,
        )
    except Exception as e:
        print(f"⚠️ Auto-analyze queue error: {e}")

    return JSONResponse(status_code=201, content={
        "success": True,
        "message": "อัปโหลดสำเร็จ — กำลังเริ่มวิเคราะห์อัตโนมัติ",
        "file_id": file_id,
        "original_filename": file.filename,
        "task_id": task_id,  # ส่ง task_id กลับเพื่อให้ frontend poll สถานะได้
        "auto_analyze": True,
    })


# =============================================================================
# GET /play/{file_id} — เล่นไฟล์เสียง
# =============================================================================
@router.get("/play/{file_id}", summary="▶️ เล่นไฟล์เสียง")
async def play_audio(file_id: str):
    # Check sample DB
    audio = get_audio_file_by_id(file_id)
    if audio:
        base_dir = Path(__file__).resolve().parent.parent
        audio_path = base_dir / audio["uploaded_path"]
        if audio_path.exists():
            return FileResponse(
                path=str(audio_path), media_type="audio/wav",
                filename=audio["original_filename"],
                headers={"Accept-Ranges": "bytes", "Content-Disposition": f"inline; filename={audio['original_filename']}"},
            )

    # Check uploaded files
    rec = FILE_METADATA_STORE.get(file_id)
    if rec:
        path = Path(rec.get("converted_path", rec.get("uploaded_path", "")))
        if path.exists():
            return FileResponse(path=str(path), media_type="audio/wav", filename=rec["original_filename"])

    raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ ID: {file_id}")


# =============================================================================
# DELETE /delete/{file_id}
# =============================================================================
@router.delete("/delete/{file_id}", summary="🗑️ ลบไฟล์เสียง")
async def delete_audio(file_id: str):
    if file_id in MOCK_AUDIO_FILES:
        del MOCK_AUDIO_FILES[file_id]
        to_remove = [k for k, v in MOCK_SAMPLE_ANALYSIS.items() if v.get("file_id") == file_id]
        for k in to_remove:
            del MOCK_SAMPLE_ANALYSIS[k]
        return {"success": True, "message": f"ลบไฟล์ {file_id} สำเร็จ"}

    if file_id in FILE_METADATA_STORE:
        FILE_METADATA_STORE.pop(file_id)
        delete_files_by_id(file_id)
        return {"success": True, "message": f"ลบไฟล์ {file_id} สำเร็จ"}

    raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ ID: {file_id}")


# =============================================================================
# GET /info/{file_id}
# =============================================================================
@router.get("/info/{file_id}", summary="ℹ️ ดูข้อมูลไฟล์")
async def get_file_info(file_id: str):
    audio = get_audio_file_by_id(file_id)
    if audio:
        return audio
    rec = FILE_METADATA_STORE.get(file_id)
    if rec:
        return rec
    raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ ID: {file_id}")
