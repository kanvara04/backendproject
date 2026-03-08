# =============================================================================
# routers/audio.py
# Router สำหรับจัดการไฟล์เสียง: Upload, Play, Delete
#
# อธิบาย: Router นี้รับ HTTP Request เกี่ยวกับไฟล์เสียงทั้งหมด
# แล้วเรียกใช้ services/file_converter.py เพื่อทำงานจริง
# Pattern นี้เรียกว่า "Separation of Concerns" - Router รับ/ส่ง Request,
# Service ทำ Business Logic
# =============================================================================

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

# Import service ที่เราสร้างไว้
from services.file_converter import (
    save_uploaded_file,
    convert_to_wav,
    find_converted_file,
    find_uploaded_file,
    delete_files_by_id,
    check_ffmpeg_available,
    ALL_SUPPORTED_EXTENSIONS,
)

# =============================================================================
# STEP 1: สร้าง APIRouter
# =============================================================================
# APIRouter คือ "mini app" ที่รวม endpoints ที่เกี่ยวข้องกันไว้ด้วยกัน
# ใน main.py เราจะ include router นี้พร้อม prefix="/api/v1/audio"
# ผลลัพธ์: endpoints ทั้งหมดจะมี URL นำหน้าด้วย /api/v1/audio
# =============================================================================

router = APIRouter()

# Mock storage สำหรับเก็บ metadata ของไฟล์ที่ upload
# (รอ Database จริงพร้อม)
# Key: file_id, Value: dict ข้อมูลไฟล์
FILE_METADATA_STORE: dict = {}


# =============================================================================
# ENDPOINT 1: POST /upload
# =============================================================================
# รับไฟล์เสียง/วิดีโอ → บันทึก → แปลงเป็น .wav → คืนผลลัพธ์
#
# URL เต็ม (เมื่อ include ใน main.py): POST /api/v1/audio/upload
# Content-Type: multipart/form-data (สำหรับ file upload)
# =============================================================================

@router.post(
    "/upload",
    summary="📤 อัปโหลดและแปลงไฟล์เสียง",
    description="""
อัปโหลดไฟล์เสียงหรือวิดีโอ แล้วระบบจะแปลงให้เป็น WAV (16kHz, Mono) โดยอัตโนมัติ

**ไฟล์ที่รองรับ:**
- เสียง: .mp3, .wav, .m4a, .aac, .ogg, .flac, .wma, .opus
- วิดีโอ: .mp4, .mkv, .avi, .mov, .webm, .3gp

**ขนาดสูงสุด:** 500MB
    """,
    status_code=201,
)
async def upload_audio(
    file: UploadFile = File(
        ...,  # ... = required (บังคับต้องส่งมา)
        description="ไฟล์เสียงหรือวิดีโอที่ต้องการอัปโหลด"
    ),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    กระบวนการทำงาน:
    1. รับไฟล์จาก Frontend (multipart/form-data)
    2. ตรวจสอบนามสกุลไฟล์
    3. บันทึกไฟล์ต้นฉบับลงดิสก์พร้อม UUID
    4. เรียก ffmpeg แปลงเป็น .wav 16kHz Mono
    5. บันทึก metadata ลง Mock Store
    6. คืนค่า file_id และข้อมูลการแปลง
    """

    # --- ขั้นที่ 1: ตรวจสอบ ffmpeg ---
    if not check_ffmpeg_available():
        raise HTTPException(
            status_code=503,  # 503 = Service Unavailable
            detail={
                "error": "ffmpeg_not_installed",
                "message": "ffmpeg ไม่ได้ติดตั้งในระบบ กรุณาติดต่อ System Admin",
                "install_guide": "sudo apt install ffmpeg",
            }
        )

    # --- ขั้นที่ 2: ตรวจสอบว่าส่งไฟล์มาจริงๆ ---
    if not file.filename:
        raise HTTPException(status_code=400, detail="กรุณาเลือกไฟล์ก่อน upload")

    # ตรวจสอบนามสกุล
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALL_SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,  # 415 = Unsupported Media Type
            detail={
                "error": "unsupported_format",
                "message": f"นามสกุล '{file_extension}' ไม่รองรับ",
                "supported_formats": sorted(list(ALL_SUPPORTED_EXTENSIONS)),
            }
        )

    # --- ขั้นที่ 3: อ่านเนื้อหาไฟล์และตรวจสอบขนาด ---
    # file.read() อ่านไฟล์ทั้งหมดเป็น bytes
    # ⚠️ ข้อควรระวัง: สำหรับไฟล์ใหญ่มาก ควรใช้ streaming แทน
    file_content = await file.read()

    # ตรวจสอบขนาดไฟล์ (500 MB max)
    max_size_bytes = 500 * 1024 * 1024  # 500 MB in bytes
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=413,  # 413 = Request Entity Too Large
            detail={
                "error": "file_too_large",
                "message": f"ไฟล์ใหญ่เกิน 500MB (ขนาดที่ส่งมา: {len(file_content) / 1024 / 1024:.1f} MB)",
            }
        )

    # --- ขั้นที่ 4: บันทึกไฟล์ต้นฉบับ ---
    try:
        file_id, uploaded_path = save_uploaded_file(file_content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"บันทึกไฟล์ไม่สำเร็จ: {e}")

    # --- ขั้นที่ 5: แปลงไฟล์เป็น .wav ---
    # ขั้นนี้คือหัวใจหลัก: เรียก ffmpeg ผ่าน service
    try:
        converted_path, conversion_metadata = convert_to_wav(uploaded_path)
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        # ถ้าแปลงไม่สำเร็จ ให้ลบไฟล์ต้นฉบับออกก่อน (ไม่ทิ้งขยะ)
        if uploaded_path.exists():
            uploaded_path.unlink()
        raise HTTPException(status_code=500, detail=f"การแปลงไฟล์ล้มเหลว: {e}")

    # --- ขั้นที่ 6: บันทึก Metadata ---
    file_record = {
        "file_id": file_id,
        "original_filename": file.filename,
        "original_content_type": file.content_type,
        "uploaded_path": str(uploaded_path),
        "converted_path": str(converted_path),
        "status": "ready",  # ready = แปลงแล้ว พร้อมให้ AI วิเคราะห์
        "conversion_details": conversion_metadata,
    }
    FILE_METADATA_STORE[file_id] = file_record

    # --- ขั้นที่ 7: ส่งผลลัพธ์กลับ ---
    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "message": "อัปโหลดและแปลงไฟล์สำเร็จ",
            "file_id": file_id,
            "original_filename": file.filename,
            "converted_filename": converted_path.name,
            "conversion_details": {
                "original_format": conversion_metadata["original_format"],
                "original_size_mb": conversion_metadata["original_size_mb"],
                "converted_size_mb": conversion_metadata["converted_size_mb"],
                "sample_rate": f"{conversion_metadata['sample_rate']}Hz",
                "channels": "Mono" if conversion_metadata["channels"] == 1 else "Stereo",
                "conversion_time_seconds": conversion_metadata["conversion_time_seconds"],
            },
            "next_steps": {
                "play_url": f"/api/v1/audio/play/{file_id}",
                "analyze_url": f"/api/v1/analysis/process/{file_id}",
                "delete_url": f"/api/v1/audio/delete/{file_id}",
            },
        }
    )


# =============================================================================
# ENDPOINT 2: GET /play/{file_id}
# =============================================================================
# ส่งไฟล์ .wav กลับไปให้ผู้ใช้ฟัง
#
# URL เต็ม: GET /api/v1/audio/play/{file_id}
# Response: ไฟล์ audio (audio/wav) แบบ streaming
# =============================================================================

@router.get(
    "/play/{file_id}",
    summary="▶️ เล่นไฟล์เสียงที่แปลงแล้ว",
    description="ส่งไฟล์ .wav กลับไปให้ Browser เล่น หรือสำหรับนำไปวิเคราะห์ต่อ",
)
async def play_audio(file_id: str):
    """
    ค้นหาไฟล์ .wav ที่แปลงแล้วตาม file_id แล้วส่งกลับเป็น FileResponse
    
    FileResponse: FastAPI จะส่งไฟล์จริงๆ กลับไป (ไม่ใช่แค่ path)
    Browser รับแล้วสามารถเล่นเสียงได้ทันที
    """

    # ตรวจสอบใน metadata store ก่อน
    file_record = FILE_METADATA_STORE.get(file_id)
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "file_not_found",
                "message": f"ไม่พบไฟล์ ID: {file_id}",
            }
        )

    # หาไฟล์ .wav จริงๆ บนดิสก์
    converted_path = find_converted_file(file_id)
    if not converted_path or not converted_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error": "converted_file_missing",
                "message": "พบ metadata แต่ไม่พบไฟล์ .wav จริงๆ บนดิสก์ (อาจถูกลบไปแล้ว)",
            }
        )

    # FileResponse: FastAPI ส่งไฟล์กลับเป็น HTTP response
    # media_type="audio/wav": บอก Browser ว่านี่คือไฟล์เสียง WAV
    # filename: ชื่อไฟล์ที่จะแสดงเมื่อ download
    # headers Range: รองรับการ seek (กรอไปข้างหน้า/ข้างหลัง) ใน audio player
    return FileResponse(
        path=str(converted_path),
        media_type="audio/wav",
        filename=f"audio_{file_id}.wav",
        headers={
            # Accept-Ranges: bytes = บอก browser ว่ารองรับการ seek ในไฟล์
            "Accept-Ranges": "bytes",
            # Content-Disposition: inline = เล่นใน browser (ไม่ download อัตโนมัติ)
            "Content-Disposition": f"inline; filename=audio_{file_id}.wav",
        }
    )


# =============================================================================
# ENDPOINT 3: GET /info/{file_id}
# =============================================================================
# ดู metadata ของไฟล์ที่ upload
# URL เต็ม: GET /api/v1/audio/info/{file_id}
# =============================================================================

@router.get(
    "/info/{file_id}",
    summary="ℹ️ ดูข้อมูลรายละเอียดของไฟล์",
)
async def get_file_info(file_id: str):
    """คืนค่า metadata ของไฟล์ที่ upload และแปลงแล้ว"""

    file_record = FILE_METADATA_STORE.get(file_id)
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail=f"ไม่พบไฟล์ ID: {file_id}"
        )

    # ตรวจสอบว่าไฟล์ยังอยู่บนดิสก์จริงๆ
    converted_exists = find_converted_file(file_id) is not None
    uploaded_exists = find_uploaded_file(file_id) is not None

    return {
        "file_id": file_id,
        "original_filename": file_record["original_filename"],
        "status": file_record["status"],
        "files_on_disk": {
            "uploaded_file_exists": uploaded_exists,
            "converted_wav_exists": converted_exists,
        },
        "conversion_details": file_record.get("conversion_details", {}),
        "urls": {
            "play": f"/api/v1/audio/play/{file_id}",
            "delete": f"/api/v1/audio/delete/{file_id}",
        }
    }


# =============================================================================
# ENDPOINT 4: DELETE /delete/{file_id}
# =============================================================================
# ลบไฟล์ต้นฉบับและไฟล์ .wav ออกจากระบบ
#
# URL เต็ม: DELETE /api/v1/audio/delete/{file_id}
# =============================================================================

@router.delete(
    "/delete/{file_id}",
    summary="🗑️ ลบไฟล์เสียงออกจากระบบ",
    description="ลบทั้งไฟล์ต้นฉบับที่อัปโหลดและไฟล์ .wav ที่แปลงแล้ว",
)
async def delete_audio(file_id: str):
    """
    ลบไฟล์ทั้งหมดที่เกี่ยวข้องกับ file_id นี้:
    1. ไฟล์ต้นฉบับ (storage/uploads/)
    2. ไฟล์ .wav ที่แปลงแล้ว (storage/converted/)
    3. Metadata ใน Mock Store
    """

    # ตรวจสอบว่า file_id นี้มีอยู่จริง
    file_record = FILE_METADATA_STORE.get(file_id)
    if not file_record:
        raise HTTPException(
            status_code=404,
            detail=f"ไม่พบไฟล์ ID: {file_id}"
        )

    # เรียก service ให้ลบไฟล์จริงบนดิสก์
    deletion_result = delete_files_by_id(file_id)

    # ลบ Metadata ออกจาก Mock Store ด้วย
    # pop() = ดึงค่าออกแล้วลบ key นั้น (ไม่ error ถ้า key ไม่มี)
    FILE_METADATA_STORE.pop(file_id, None)

    # แจ้งผลการลบ
    if deletion_result["errors"]:
        # มีบางอย่างผิดพลาด แต่ลบได้บางส่วน
        return JSONResponse(
            status_code=207,  # 207 = Multi-Status (บางส่วนสำเร็จ)
            content={
                "success": False,
                "message": "ลบได้บางส่วน มีข้อผิดพลาดเกิดขึ้น",
                "details": deletion_result,
            }
        )

    return {
        "success": True,
        "message": f"ลบไฟล์ ID: {file_id} สำเร็จทั้งหมด",
        "deleted": {
            "uploaded_file": deletion_result["uploaded_file_deleted"],
            "converted_wav": deletion_result["converted_file_deleted"],
            "metadata": True,
        }
    }


# =============================================================================
# ENDPOINT 5: GET /list
# =============================================================================
# แสดงรายการไฟล์ทั้งหมดที่อยู่ใน Mock Store
# URL เต็ม: GET /api/v1/audio/list
# =============================================================================

@router.get(
    "/list",
    summary="📋 ดูรายการไฟล์ทั้งหมด",
)
async def list_files():
    """แสดงไฟล์ทั้งหมดที่ upload ไว้ในระบบ"""

    files = []
    for file_id, record in FILE_METADATA_STORE.items():
        files.append({
            "file_id": file_id,
            "original_filename": record["original_filename"],
            "status": record["status"],
            "size_mb": record.get("conversion_details", {}).get("converted_size_mb", "N/A"),
            "play_url": f"/api/v1/audio/play/{file_id}",
        })

    return {
        "total_files": len(files),
        "files": files,
    }
