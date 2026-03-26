# =============================================================================
# main.py  (v0.5.0 — เพิ่ม Brand & Product Category Filtering)
# =============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Import Routers ทั้งหมด ---
from routers.audio    import router as audio_router
from routers.ai_task  import router as ai_task_router
from routers.dashboard import router as dashboard_router
# from routers.customers import router as customers_router  # [PLACEHOLDER]

app = FastAPI(
    title="AI Voice Intelligence System API",
    description="""
## 🎙️ AI Voice Intelligence System — Full Backend

ระบบ Backend ครบถ้วนสำหรับวิเคราะห์เสียง Call Center ด้วย AI

### Modules
| Module | Prefix | หน้าที่ |
|--------|--------|---------|
| 🎙️ Audio | `/api/v1/audio` | Upload, Play, Delete ไฟล์เสียง |
| 🤖 AI Analysis | `/api/v1/ai` | สั่งวิเคราะห์ + ติดตามสถานะ (Async) |
| 📊 Dashboard | `/api/v1/dashboard` | KPIs, Trends, Recommendations, Export |

> ⚠️ Mock Database Mode — รอ Database จริงจากทีม DB
    """,
    version="0.5.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# CORS Configuration
# =============================================================================
ALLOWED_ORIGINS = [
    "http://localhost:3000",   # React CRA
    "http://localhost:5173",   # React Vite
    "http://localhost:5174",   # React Vite (สำรอง)
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Register ALL Routers
# =============================================================================

app.include_router(
    audio_router,
    prefix="/api/v1/audio",
    tags=["🎙️ Audio Files"],
)

app.include_router(
    ai_task_router,
    prefix="/api/v1/ai",
    tags=["🤖 AI Analysis"],
)

app.include_router(
    dashboard_router,
    prefix="/api/v1/dashboard",
    tags=["📊 Dashboard & Export"],
)

# [PLACEHOLDER — เพิ่มเมื่อพร้อม]
# app.include_router(customers_router, prefix="/api/v1/customers", tags=["👤 Customers"])


# =============================================================================
# Root Endpoint — API Map
# =============================================================================

@app.get("/", tags=["🏠 System"], summary="API Map ทั้งหมด")
async def root():
    return {
        "system":  "AI Voice Intelligence System",
        "version": "0.6.0",
        "status":  "online",
        "database_mode": "mock",
        "all_endpoints": {
            "audio": {
                "POST   /api/v1/audio/upload":          "อัปโหลดและแปลงไฟล์เสียง → .wav",
                "GET    /api/v1/audio/play/{file_id}":  "เล่นไฟล์เสียง",
                "GET    /api/v1/audio/info/{file_id}":  "ข้อมูลไฟล์",
                "GET    /api/v1/audio/list":             "รายการไฟล์ทั้งหมด",
                "DELETE /api/v1/audio/delete/{file_id}":"ลบไฟล์",
            },
            "ai_analysis": {
                "POST /api/v1/ai/analyze/{file_id}":    "สั่งวิเคราะห์ (Async, คืน task_id)",
                "POST /api/v1/ai/retest/{file_id}":     "วิเคราะห์ซ้ำ",
                "GET  /api/v1/ai/status/{task_id}":     "ตรวจสถานะ Task",
                "GET  /api/v1/ai/tasks":                "รายการ Task ทั้งหมด",
            },
            "dashboard": {
                "GET /api/v1/dashboard/filters":        "ดูตัวเลือก Brand/Product/Channel สำหรับ filter",
                "GET /api/v1/dashboard/summary":        "สรุป KPIs + filter ?brand=&product=&channel=",
                "GET /api/v1/dashboard/overview":       "ภาพรวม KPIs + distribution",
                "GET /api/v1/dashboard/trends":         "แนวโน้มรายวัน",
                "GET /api/v1/dashboard/intent-analysis":"วิเคราะห์ประเภทปัญหา",
                "GET /api/v1/dashboard/recommendations":"คำแนะนำ AI",
                "GET /api/v1/dashboard/export":         "Export CSV / XLSX",
            },
        },
        "docs": "/docs",
        "redoc": "/redoc",
    }


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 AI Voice Intelligence System v0.6.0")
    print("📖 Docs: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
