# =============================================================================
# routers/ai_task.py
# Router สำหรับสั่งงาน AI และดูสถานะ — ใช้ BackgroundTasks
#
# =========================================================================
# 🔑 BackgroundTasks คืออะไร และทำงานอย่างไร?
# =========================================================================
#
# ปัญหา: AI Processing ใช้เวลานาน (10-30+ วินาที)
# ถ้าเราบล็อก HTTP Response จนกว่า AI จะเสร็จ:
#   - User รอนาน → UX แย่
#   - Browser timeout (โดยปกติ 30-60 วินาที)
#   - Server thread ถูก block ไม่รับ request ใหม่ได้
#
# วิธีแก้ด้วย BackgroundTasks:
#   1. รับ Request เข้ามา
#   2. เพิ่มงาน AI ลงใน BackgroundTasks queue
#   3. ส่ง Response กลับทันที (202 Accepted) "รับงานแล้ว กำลังทำ"
#   4. FastAPI รัน Background Task หลังจากส่ง Response แล้ว
#   5. User poll /status/{task_id} เพื่อตรวจสอบว่าเสร็จหรือยัง
#
# Timeline:
#   t=0s  : POST /analyze → ส่ง 202 กลับทันที
#   t=0s  : Background Task เริ่มทำงาน (Whisper + Wav2Vec2)
#   t=8s  : Whisper เสร็จ, Llama เริ่ม
#   t=15s : Llama เสร็จ, Task Status → "completed"
#   t=?s  : User GET /status → เห็นผลลัพธ์
#
# =========================================================================

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse

from services.ai_mock_service import run_full_analysis_pipeline
from database.mock_db import save_analysis_result, find_customer_by_id

# =============================================================================
# STEP 1: สร้าง Router และ In-Memory Task Store
# =============================================================================

router = APIRouter()

# Task Store: เก็บสถานะและผลลัพธ์ของทุก Task
# Key: task_id (UUID), Value: dict สถานะ
# ในระบบ Production จะใช้ Redis แทน (shared across workers)
TASK_STORE: dict = {}

# สถานะที่เป็นไปได้ของ Task
class TaskStatus:
    QUEUED     = "queued"       # รับคำสั่งแล้ว รอคิว
    PROCESSING = "processing"   # กำลังประมวลผล
    COMPLETED  = "completed"    # เสร็จสมบูรณ์
    FAILED     = "failed"       # เกิดข้อผิดพลาด


# =============================================================================
# STEP 2: Background Task Function (ฟังก์ชันที่รันเบื้องหลัง)
# =============================================================================
# ⚠️ สำคัญมาก: BackgroundTasks ของ FastAPI รัน SYNCHRONOUS functions
# แต่เรามี async pipeline → ต้องใช้ asyncio.run() หรือ create_task()
# =============================================================================

async def _run_ai_pipeline_task(
    task_id: str,
    file_id: str,
    customer_id: Optional[str],
    retest: bool = False,
):
    """
    Background Task จริงๆ ที่รัน AI Pipeline
    
    ฟังก์ชันนี้ถูกเรียกโดย FastAPI BackgroundTasks หลังจากส่ง Response แล้ว
    ไม่มี user รอ response จากฟังก์ชันนี้โดยตรง
    
    Args:
        task_id: UUID ของ task นี้
        file_id: ไฟล์เสียงที่จะวิเคราะห์
        customer_id: ลูกค้าเจ้าของการโทร (optional)
        retest: True ถ้าเป็นการ retest (ไม่ใช่ครั้งแรก)
    """
    # อัปเดตสถานะเป็น "processing"
    TASK_STORE[task_id].update({
        "status": TaskStatus.PROCESSING,
        "started_at": datetime.now().isoformat(),
        "message": "🔄 AI กำลังประมวลผล กรุณารอสักครู่...",
    })

    try:
        # =========================================================
        # เรียก AI Pipeline จริง (ใช้เวลา 10-20+ วินาที)
        # =========================================================
        # ในระหว่างนี้ FastAPI server ยังรับ Request อื่นได้ปกติ
        # เพราะ Python asyncio ทำ cooperative multitasking
        result = await run_full_analysis_pipeline(
            file_id=file_id,
            audio_duration_seconds=None,  # ให้ mock สุ่มเอง
        )

        # บันทึกผลลงใน Mock Database
        db_record = {
            "task_id": task_id,
            "file_id": file_id,
            "customer_id": customer_id,
            "is_retest": retest,

            # ผลสรุปจาก AI
            "transcript": result["summary"]["transcript"],
            "sentiment": result["summary"]["sentiment"],
            "sentiment_confidence": result["summary"]["sentiment_confidence"],
            "intent": result["summary"]["intent"],
            "qa_score": result["summary"]["qa_score"],
            "csat_predicted": result["summary"]["csat_predicted"],
            "summary": result["summary"]["summary_text"],
            "action_items": result["summary"]["action_items"],

            # Raw results จากแต่ละโมเดล
            "model_results": result["model_results"],
        }
        saved = save_analysis_result(db_record)

        # อัปเดตสถานะเป็น "completed" พร้อมผลลัพธ์
        TASK_STORE[task_id].update({
            "status": TaskStatus.COMPLETED,
            "completed_at": datetime.now().isoformat(),
            "message": "✅ วิเคราะห์เสร็จสมบูรณ์",
            "result": result["summary"],
            "analysis_id": saved.get("analysis_id"),
            "pipeline_duration_seconds": result["pipeline_duration_seconds"],
        })

    except Exception as e:
        # ถ้าเกิด error ใดๆ ให้บันทึกและอัปเดตสถานะ
        TASK_STORE[task_id].update({
            "status": TaskStatus.FAILED,
            "failed_at": datetime.now().isoformat(),
            "message": "❌ เกิดข้อผิดพลาดระหว่างวิเคราะห์",
            "error": str(e),
        })


# =============================================================================
# ENDPOINT 1: POST /analyze/{file_id}
# =============================================================================
# รับคำสั่งวิเคราะห์ → ส่ง Response 202 ทันที → รัน AI ใน Background
#
# URL เต็ม: POST /api/v1/ai/analyze/{file_id}
# =============================================================================

@router.post(
    "/analyze/{file_id}",
    status_code=202,  # 202 Accepted = "รับคำสั่งแล้ว แต่ยังไม่เสร็จ"
    summary="🚀 สั่งวิเคราะห์ไฟล์เสียง (Async)",
    description="""
ส่งคำสั่งวิเคราะห์ไฟล์เสียงด้วย AI Pipeline (Whisper → Wav2Vec2 → Llama)

**Response:** ส่งกลับทันที พร้อม `task_id` สำหรับติดตามสถานะ

**ติดตามสถานะ:** `GET /api/v1/ai/status/{task_id}`

**ขั้นตอน AI:**
1. 🎙️ Whisper — แปลงเสียงเป็นข้อความ
2. 🎭 Wav2Vec2 — วิเคราะห์อารมณ์จากเสียง  
3. 🧠 Llama 3.3 — วิเคราะห์ NLP และให้คะแนน QA
    """,
)
async def analyze_audio(
    file_id: str,
    background_tasks: BackgroundTasks,          # FastAPI inject อัตโนมัติ
    customer_id: Optional[str] = None,          # Query param: ?customer_id=CUST-001
    priority: str = "normal",                   # Query param: ?priority=high
):
    """
    =========================================================================
    วิธีทำงานของ BackgroundTasks (อธิบายแบบละเอียด):
    =========================================================================
    
    1. FastAPI รับ POST request เข้ามา
    2. เราสร้าง task_id และบันทึก task ใน TASK_STORE (สถานะ: queued)
    3. เรียก background_tasks.add_task(func, *args)
       → FastAPI "จด" ว่าจะรัน func(*args) ทีหลัง
    4. ฟังก์ชันนี้ return JSONResponse ทันที (202)
       → User ได้ task_id กลับไปแล้ว!
    5. FastAPI ส่ง HTTP Response ออกไปให้ client
    6. หลังส่ง Response เสร็จ → FastAPI เรียก func(*args) ที่จดไว้
       → _run_ai_pipeline_task() เริ่มทำงาน
    7. งาน AI ใช้เวลา 10-20 วินาที (ไม่มีใครรออยู่แล้ว)
    8. เมื่อเสร็จ TASK_STORE[task_id] อัปเดตเป็น "completed"
    9. User poll GET /status/{task_id} → เห็นผล
    =========================================================================
    """

    # ตรวจสอบ priority
    if priority not in ("high", "normal", "low"):
        raise HTTPException(status_code=400, detail="priority ต้องเป็น high, normal, หรือ low")

    # สร้าง Task ID ใหม่
    task_id = str(uuid.uuid4())

    # บันทึก Task ใน Store (สถานะเริ่มต้น = queued)
    TASK_STORE[task_id] = {
        "task_id": task_id,
        "file_id": file_id,
        "customer_id": customer_id,
        "priority": priority,
        "status": TaskStatus.QUEUED,
        "is_retest": False,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "message": "📋 งานอยู่ในคิว รอเริ่มประมวลผล...",
        "result": None,
        "error": None,
    }

    # =========================================================
    # 🔑 จุดสำคัญ: add_task() — ลงทะเบียนงานใน BackgroundTasks
    # =========================================================
    # add_task(function, arg1, arg2, kwarg=value)
    # FastAPI จะรัน function(arg1, arg2, kwarg=value)
    # หลังจาก Response ถูกส่งออกไปแล้ว
    # =========================================================
    background_tasks.add_task(
        _run_ai_pipeline_task,   # ฟังก์ชันที่จะรันใน background
        task_id=task_id,         # arguments ที่ส่งให้ฟังก์ชัน
        file_id=file_id,
        customer_id=customer_id,
        retest=False,
    )

    # ส่ง Response ทันที ไม่รอ AI เสร็จ
    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "message": "📋 รับคำสั่งแล้ว AI กำลังเริ่มประมวลผลใน Background",
            "task_id": task_id,
            "file_id": file_id,
            "priority": priority,
            "estimated_time_seconds": "15-30",
            "how_to_check_status": f"GET /api/v1/ai/status/{task_id}",
            "created_at": TASK_STORE[task_id]["created_at"],
        }
    )


# =============================================================================
# ENDPOINT 2: POST /retest/{file_id}
# =============================================================================
# วิเคราะห์ไฟล์ใหม่อีกครั้ง (เช่น หลังจาก QA ตรวจสอบและต้องการผล 2nd opinion)
# URL เต็ม: POST /api/v1/ai/retest/{file_id}
# =============================================================================

@router.post(
    "/retest/{file_id}",
    status_code=202,
    summary="🔄 วิเคราะห์ซ้ำ (Retest)",
    description="""
สั่งให้ AI วิเคราะห์ไฟล์เดิมอีกครั้ง พร้อม flag ว่าเป็นการ retest

**กรณีใช้งาน:**
- QA ต้องการ second opinion
- หลัง fine-tune model ใหม่และต้องการเปรียบเทียบผล  
- พบว่าผลเดิมผิดพลาด ต้องการผลที่ถูกต้อง

**หมายเหตุ:** ผลเดิมจะยังอยู่ในระบบ (ไม่ overwrite)
    """,
)
async def retest_audio(
    file_id: str,
    background_tasks: BackgroundTasks,
    customer_id: Optional[str] = None,
    reason: Optional[str] = None,           # เหตุผลที่ retest
):
    """
    Retest ทำงานเหมือน analyze แต่:
    1. บันทึก flag is_retest=True ใน database
    2. บันทึก reason ว่าทำไมถึง retest
    3. ไม่ลบผลเดิม → เก็บทั้ง original และ retest result
    """

    task_id = str(uuid.uuid4())

    TASK_STORE[task_id] = {
        "task_id": task_id,
        "file_id": file_id,
        "customer_id": customer_id,
        "priority": "normal",
        "status": TaskStatus.QUEUED,
        "is_retest": True,
        "retest_reason": reason or "ไม่ระบุเหตุผล",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "message": "📋 [RETEST] งานอยู่ในคิว...",
        "result": None,
        "error": None,
    }

    # BackgroundTasks เหมือนกันทุกอย่าง เพียงแต่ retest=True
    background_tasks.add_task(
        _run_ai_pipeline_task,
        task_id=task_id,
        file_id=file_id,
        customer_id=customer_id,
        retest=True,
    )

    return JSONResponse(
        status_code=202,
        content={
            "accepted": True,
            "message": "🔄 [RETEST] รับคำสั่งแล้ว กำลัง retest ใน Background",
            "task_id": task_id,
            "file_id": file_id,
            "is_retest": True,
            "retest_reason": reason,
            "how_to_check_status": f"GET /api/v1/ai/status/{task_id}",
            "created_at": TASK_STORE[task_id]["created_at"],
        }
    )


# =============================================================================
# ENDPOINT 3: GET /status/{task_id}
# =============================================================================
# ตรวจสอบสถานะของ Background Task
# Frontend จะ "poll" endpoint นี้ทุก 2-3 วินาที จนกว่าจะ completed
# URL เต็ม: GET /api/v1/ai/status/{task_id}
# =============================================================================

@router.get(
    "/status/{task_id}",
    summary="📊 ตรวจสอบสถานะ Task",
    description="""
ตรวจสอบสถานะของ AI Task โดยใช้ task_id ที่ได้จาก /analyze หรือ /retest

**สถานะที่เป็นไปได้:**
- `queued` — อยู่ในคิว รอเริ่ม
- `processing` — AI กำลังทำงาน
- `completed` — เสร็จสมบูรณ์ (มีผลลัพธ์)
- `failed` — เกิดข้อผิดพลาด

**Polling Strategy แนะนำ (Frontend):**
```javascript
const pollStatus = async (taskId) => {
  const res = await fetch(`/api/v1/ai/status/${taskId}`);
  const data = await res.json();
  if (data.status === 'completed') return data.result;
  if (data.status === 'failed') throw new Error(data.error);
  await sleep(3000); // รอ 3 วินาทีแล้วลองใหม่
  return pollStatus(taskId);
};
```
    """,
)
async def get_task_status(task_id: str):
    """ดูสถานะและผลลัพธ์ของ Task"""

    task = TASK_STORE.get(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "task_not_found",
                "message": f"ไม่พบ Task ID: {task_id}",
            }
        )

    # คำนวณเวลาที่ผ่านไป
    created_at = datetime.fromisoformat(task["created_at"])
    elapsed_seconds = round((datetime.now() - created_at).total_seconds(), 1)

    response = {
        "task_id": task_id,
        "file_id": task["file_id"],
        "status": task["status"],
        "is_retest": task.get("is_retest", False),
        "message": task["message"],
        "elapsed_seconds": elapsed_seconds,
        "created_at": task["created_at"],
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
    }

    # เพิ่ม result ถ้าเสร็จแล้ว
    if task["status"] == TaskStatus.COMPLETED:
        response["result"] = task.get("result")
        response["analysis_id"] = task.get("analysis_id")
        response["pipeline_duration_seconds"] = task.get("pipeline_duration_seconds")

    # เพิ่ม error ถ้าล้มเหลว
    if task["status"] == TaskStatus.FAILED:
        response["error"] = task.get("error")

    return response


# =============================================================================
# ENDPOINT 4: GET /tasks
# =============================================================================
# แสดงรายการ Task ทั้งหมด (สำหรับ Admin / Debug)
# URL เต็ม: GET /api/v1/ai/tasks
# =============================================================================

@router.get(
    "/tasks",
    summary="📋 รายการ Task ทั้งหมด",
)
async def list_tasks(
    status_filter: Optional[str] = None,   # ?status_filter=completed
    limit: int = 20,
):
    """แสดงรายการ AI Tasks ทั้งหมด พร้อม filter ตาม status"""

    tasks = list(TASK_STORE.values())

    # กรองตาม status ถ้ามี filter
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]

    # เรียงจากใหม่ไปเก่า
    tasks.sort(key=lambda t: t["created_at"], reverse=True)

    # จำกัดจำนวน
    tasks = tasks[:limit]

    # สรุป stats
    all_tasks = list(TASK_STORE.values())
    stats = {
        "total": len(all_tasks),
        "queued":     sum(1 for t in all_tasks if t["status"] == TaskStatus.QUEUED),
        "processing": sum(1 for t in all_tasks if t["status"] == TaskStatus.PROCESSING),
        "completed":  sum(1 for t in all_tasks if t["status"] == TaskStatus.COMPLETED),
        "failed":     sum(1 for t in all_tasks if t["status"] == TaskStatus.FAILED),
    }

    return {
        "stats": stats,
        "filter": status_filter,
        "showing": len(tasks),
        "tasks": [
            {
                "task_id": t["task_id"],
                "file_id": t["file_id"],
                "status": t["status"],
                "is_retest": t.get("is_retest", False),
                "created_at": t["created_at"],
                "message": t["message"],
            }
            for t in tasks
        ],
    }
