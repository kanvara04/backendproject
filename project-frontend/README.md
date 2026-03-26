# FontAI — AI Voice Intelligence System

ระบบวิเคราะห์เสียง Call Center ด้วย AI สำหรับบริษัทเครื่องนอน

---

## สถาปัตยกรรมระบบ

```
Frontend (Next.js 16 + React 19 + Tailwind 4)
  │
  │  HTTP REST API
  │
Backend (FastAPI + Python)
  │
  ├── Groq Whisper large-v3  → ถอดเสียงเป็นข้อความ
  ├── Groq Llama 3.3 70B     → แก้ transcript + วิเคราะห์ + สรุป
  └── Mock Database           → เก็บข้อมูล (รอเปลี่ยน DB จริง)
```

---

## วิธีติดตั้งและรัน

### 1. สมัคร Groq API Key (ฟรี)

ไปที่ https://console.groq.com/keys แล้วสร้าง key

### 2. Backend

```bash
cd project-backend

# ติดตั้ง dependencies
pip install fastapi uvicorn python-multipart groq

# ตั้งค่า API Key (เลือก 1 วิธี)

# Windows PowerShell:
$env:GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxx"

# macOS / Linux:
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx

# รัน server
uvicorn main:app --reload --port 8000
```

เปิด API Docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd project-frontend

npm install
npm run dev
```

เปิดเว็บ: http://localhost:3000

---

## หน้าจอหลัก (Frontend)

| หน้า | Path | ฟีเจอร์ |
|------|------|---------|
| Dashboard | `/dashboard` | KPIs, Sentiment distribution, Trends, Filter Day/Week/Month |
| Upload | `/upload` | Drag & Drop หลายไฟล์, File Queue, อัปโหลด+วิเคราะห์อัตโนมัติ (จำกัด 60MB) |
| Files | `/files` | รายการไฟล์, ค้นหา (ชื่อ/เบอร์โทร/Agent/Brand), Dropdown filter (Date/Brand/Product), Pagination, auto-refresh |
| File Detail | `/files/[id]` | Conversation Summary, Transcription+Audio Player (subtitle sync), Metadata+Inbound/Outbound badge, หลายแบรนด์, Key Insights, Keywords, re-Analyze, Delete |

---

## Flow การทำงาน

```
User อัปโหลดไฟล์เสียง (.wav/.mp3 ฯลฯ)
        │
        ▼
  POST /api/v1/audio/upload
        │
        ├── ★ ดึง date/customer/agent/direction จากชื่อไฟล์อัตโนมัติ
        ├── บันทึกไฟล์ + แปลงเป็น .wav (ถ้าจำเป็น)
        ├── สร้าง file_id, status = "processing"
        └── ★ เข้าคิววิเคราะห์อัตโนมัติ
                │
                ▼
        ┌────────────────────────────┐
        │  Queue Worker              │
        │  ประมวลผลทีละ 1 ไฟล์       │
        │  พัก 15 วินาทีระหว่างไฟล์   │
        └─────────┬──────────────────┘
                  │
                  ▼
        ┌───────────────────────────────────┐
        │  ตรวจขนาดไฟล์                      │
        │  < 5 นาที / < 24MB → ส่งทั้งไฟล์   │
        │  ≥ 5 นาที / ≥ 24MB → ตัด chunk     │
        └───────────────┬───────────────────┘
                        │
                        ▼
        ┌───────────────────┐
        │  Groq Whisper API │  Speech-to-Text
        │  (large-v3)       │  ส่งทีละ chunk / ทั้งไฟล์
        └───────┬───────────┘
                │
                ▼
        ┌───────────────────────────────┐
        │  Language Filter (3 ชั้น)      │
        │  1. กรอง segment ภาษาอื่นทิ้ง  │
        │  2. ลบคำแปลกในแต่ละ segment   │
        │  3. ลบ hallucination words     │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │  Groq Llama 3.3 70B          │
        │  (รวม 2 งานใน call เดียว)      │
        │  1. แก้ transcript ให้ถูกต้อง  │
        │  2. วิเคราะห์ + สรุปบทสนทนา   │
        └───────────────┬───────────────┘
                        │
                        ▼
        บันทึกผลลง Mock DB (brand_names array)
        File status → "analyzed"
        │
        ▼
  Frontend auto-poll → แสดงผล
```

---

## ฟีเจอร์หลัก

### AI Pipeline (Whisper + Llama)
- **Whisper large-v3** — ถอดเสียงภาษาไทย/อังกฤษ, temperature 0.0 (deterministic)
- **Llama 3.3 70B** — แก้คำผิด + แก้ชื่อแบรนด์/สินค้าเป็นอังกฤษ + วิเคราะห์รวมใน call เดียว:
  - Conversation Summary (4 จุดสรุป)
  - Sentiment (positive / neutral / negative)
  - Intent (สอบถามสินค้า, แจ้งชำรุด, สอบถามจัดส่ง ฯลฯ)
  - Brand (รองรับหลายแบรนด์ต่อไฟล์) / Product Category / Sale Channel
  - QA Score (เกณฑ์ 6 ข้อ, คะแนน 0-10)
  - CSAT Prediction (1-5)
  - Key Insights + Keywords
- **re-Analyze** — กดวิเคราะห์ซ้ำได้ เข้าคิวอัตโนมัติ แสดงผลล่าสุดเสมอ

### Filename Parser — ดึงข้อมูลจากชื่อไฟล์อัตโนมัติ
- Pattern: `{yyyyMMddHHmmss}-{ids}-{numA}-{numB}-{direction}.wav`
- **Outbound**: `...-{agent}-{customer}-Outbound.wav`
- **Inbound**: `...-{customer}-{agent}-Inbound.wav`
- ดึงได้: วันที่โทร, เบอร์ลูกค้า (format xxx-xxx-xxxx), Agent ID, ทิศทางสาย
- ไม่ต้องกรอก customer/agent เอง — parse จากชื่อไฟล์ให้ทันที

### หน้า Files — Search + Dropdown Filters
- **Search bar** — ค้นหาด้วย: ชื่อไฟล์, เบอร์โทร, Agent, Brand
- **Date filter** — dropdown เลือกช่วงวันที่ (date picker from ~ to)
- **Brand filter** — dropdown 12 แบรนด์
- **Product filter** — dropdown 6 หมวดสินค้า
- ปุ่ม "ล้างตัวกรอง" เมื่อมี filter active
- Filter ส่งไป backend จริง (server-side filtering)

### หน้า File Detail
- **Inbound/Outbound badge** ข้าง Customer Phone (สีเขียว/ส้ม)
- **หลายแบรนด์** แสดงเป็น tag badges สีฟ้า
- **Audio Player** หยุดอัตโนมัติเมื่อออกจากหน้า (ไม่เล่นต่อเมื่อกลับไปหน้าอื่น)

### Audio Chunking
- ไฟล์ > 5 นาที หรือ > 24MB → ตัดเป็น chunk ละ 5 นาทีอัตโนมัติ
- ใช้ Python `wave` module (built-in ไม่ต้องติดตั้งเพิ่ม)
- รวม transcript + ปรับ timestamp ให้ต่อเนื่อง

### Language Filter
- กรอง segment ที่ไม่ใช่ไทย/อังกฤษออก (Cyrillic, CJK, Arabic ฯลฯ)
- ลบคำแปลก / Whisper hallucination ~80 คำ (ฝรั่งเศส, สเปน, เยอรมัน ฯลฯ)
- เพิ่มคำ hallucination ได้ที่ `_WHISPER_HALLUCINATIONS` ใน `groq_ai_service.py`

### Queue System
- อัปโหลดหลายไฟล์พร้อมกัน → เข้าคิวอัตโนมัติ
- ประมวลผลทีละ 1 ไฟล์ → ป้องกัน Groq rate limit
- พัก 15 วินาทีระหว่างไฟล์
- แสดงลำดับคิว ("รอคิว ลำดับที่ 2 จาก 5")

### Multi API Key Rotation
- ใส่ได้หลาย key → สลับอัตโนมัติแบบ round-robin
- retry 3 ครั้งเมื่อเจอ rate limit 429 (สลับ key + รอ 5 วินาที)
- วิธีตั้งค่า:

```bash
# วิธี 1: ใส่ทีละ key
$env:GROQ_API_KEY="gsk_key1"
$env:GROQ_API_KEY_2="gsk_key2"
$env:GROQ_API_KEY_3="gsk_key3"

# วิธี 2: ใส่หลาย key คั่นด้วย comma
$env:GROQ_API_KEYS="gsk_key1,gsk_key2,gsk_key3"
```

### Auto-Analyze หลังอัปโหลด
- อัปโหลดเสร็จ → เข้าคิววิเคราะห์ทันที (ไม่ต้องกดปุ่ม)
- Upload API คืน `task_id` ให้ frontend poll สถานะ
- จำกัดขนาดไฟล์ 60MB

### Frontend Auto-Polling
- หน้า Files — auto-refresh ทุก 5 วินาทีถ้ามีไฟล์ PROCESSING
- หน้า File Detail — poll ทุก 3 วินาที + animation "กำลังวิเคราะห์"
- Audio Player — play/pause, seek, skip ±10 วินาที, subtitle sync auto-scroll

---

## โครงสร้างไฟล์

```
project-backend/
├── main.py                          # FastAPI entry point (3 routers)
├── database/
│   └── mock_db.py                   # Mock DB: 12 brands, 6 products, 4 channels
├── routers/
│   ├── audio.py                     # Upload+auto-analyze, Filename parser, List+filters, Detail, Play, Delete
│   ├── ai_task.py                   # Queue worker (10s delay), Analyze, re-Analyze, Status, Tasks
│   └── dashboard.py                 # Filters, Summary, Overview, Trends, Intent, Recommendations, Export
├── services/
│   ├── groq_ai_service.py           # ★ Groq AI Pipeline
│   │                                #   Whisper+Chunking, Language Filter, Llama Fix+Analyze
│   │                                #   Multi Key Rotation, Retry, Multi-brand support
│   ├── ai_mock_service.py           # Mock AI Pipeline (fallback)
│   └── file_converter.py            # แปลงไฟล์เสียง → .wav (ffmpeg)
├── storage/
│   ├── uploads/                     # ไฟล์เสียงที่อัปโหลด
│   ├── converted/                   # ไฟล์ที่แปลงแล้ว
│   └── exports/                     # ไฟล์ export CSV/XLSX
└── test_local_ai.py                 # ตรวจ faster-whisper, CUDA, Ollama (สำหรับ local mode อนาคต)

project-frontend/
├── app/
│   ├── dashboard/page.tsx           # Dashboard: KPIs, Sentiment, Trends
│   ├── upload/page.tsx              # Upload: Drag&Drop, File Queue (60MB limit)
│   ├── files/page.tsx               # Files: Search+Dropdown filters (Date/Brand/Product), auto-refresh
│   ├── files/[id]/page.tsx          # File Detail: Summary, Transcription+Audio, multi-brand, Inbound/Outbound
│   ├── layout.tsx                   # Root layout
│   ├── page.tsx                     # Home (redirect)
│   └── globals.css                  # Tailwind styles
├── components/
│   └── Sidebar.tsx                  # Navigation: Dashboard, Upload, Files
├── package.json                     # Next.js 16, React 19, Tailwind 4, Lucide React
└── tsconfig.json
```

---

## API Endpoints

### Audio (`/api/v1/audio`)

| Method | URL | หน้าที่ |
|--------|-----|---------|
| GET | `/list` | รายการไฟล์ (search, brand, product, date_from, date_to, status, pagination) |
| GET | `/detail/{file_id}` | ข้อมูลไฟล์ + ผลวิเคราะห์ AI (brand_names array) |
| POST | `/upload` | อัปโหลด (60MB limit) + parse ชื่อไฟล์ + เข้าคิววิเคราะห์ (คืน task_id) |
| GET | `/play/{file_id}` | Stream เล่นไฟล์เสียง |
| GET | `/info/{file_id}` | ข้อมูลไฟล์ (metadata) |
| DELETE | `/delete/{file_id}` | ลบไฟล์ |

### AI Analysis (`/api/v1/ai`)

| Method | URL | หน้าที่ |
|--------|-----|---------|
| POST | `/analyze/{file_id}` | สั่งวิเคราะห์ / re-Analyze (เข้าคิว, คืน task_id) |
| POST | `/retest/{file_id}` | วิเคราะห์ซ้ำ (flag retest) |
| GET | `/status/{task_id}` | ตรวจสถานะ Task + ลำดับคิว |
| GET | `/tasks` | รายการ Task ทั้งหมด + stats |

### Dashboard (`/api/v1/dashboard`)

| Method | URL | หน้าที่ |
|--------|-----|---------|
| GET | `/filters` | ตัวเลือก Brand/Product/Channel สำหรับ filter |
| GET | `/summary` | สรุป KPIs (filter ได้) |
| GET | `/overview` | ภาพรวม KPIs + distribution |
| GET | `/trends` | แนวโน้มรายวัน |
| GET | `/intent-analysis` | วิเคราะห์ประเภทปัญหา |
| GET | `/recommendations` | คำแนะนำ AI |
| GET | `/export` | Export CSV / XLSX |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq API Key หลัก |
| `GROQ_API_KEY_2` ... `_20` | Optional | Key เพิ่มเติม (สลับ round-robin) |
| `GROQ_API_KEYS` | Optional | หลาย key คั่นด้วย comma |
| `NEXT_PUBLIC_API_URL` | Optional | URL Backend (default: `http://localhost:8000`) |

---

## AI Models

| Model | Task | หมายเหตุ |
|-------|------|----------|
| `whisper-large-v3` | Speech-to-Text | full model (แม่นกว่า turbo), temperature 0.0 |
| `llama-3.3-70b-versatile` | NLP Analysis | แก้ transcript + วิเคราะห์รวมใน call เดียว |

---

## Config ที่ปรับได้ (`groq_ai_service.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WHISPER_MODEL` | `whisper-large-v3` | Groq Whisper model |
| `LLAMA_MODEL` | `llama-3.3-70b-versatile` | Groq Llama model |
| `WHISPER_MAX_FILE_SIZE_MB` | 24 | chunk ถ้าเกินขนาดนี้ |
| `CHUNK_DURATION_SECONDS` | 300 | ตัดทุกกี่วินาที (300 = 5 นาที) |
| `DELAY_BETWEEN_STEPS` | 1 | พักระหว่าง Whisper → Llama (วินาที) |
| `_WHISPER_HALLUCINATIONS` | ~80 คำ | คำที่ Whisper มักถอดผิด (เพิ่มได้) |

---

## รูปแบบชื่อไฟล์ (Filename Pattern)

ระบบดึง date, customer, agent, call direction จากชื่อไฟล์อัตโนมัติ:

```
Outbound: {yyyyMMddHHmmss}-{ids}-{agent}-{customer}-Outbound.wav
Inbound:  {yyyyMMddHHmmss}-{ids}-{customer}-{agent}-Inbound.wav
```

| ตัวอย่าง | ได้ |
|---------|-----|
| `20251104173706-...-104-0819979336-Outbound.wav` | date=Nov 4 2025, agent=AGENT-104, phone=081-997-9336, Outbound |
| `20251201175254-...-0634654956-102-Inbound.wav` | date=Dec 1 2025, phone=063-465-4956, agent=AGENT-102, Inbound |

ไฟล์ที่ชื่อไม่ตรง pattern → fallback เป็น N/A ทุกค่า

---

## แบรนด์ที่รองรับ (12 แบรนด์)

Lotus, Omazz, Midas, Dunlopillo, Bedgear, LaLaBed, Zinus, Eastman House, Malouf, Loto Mobili, Woodfield, Restonic

รองรับหลายแบรนด์ต่อ 1 ไฟล์ (เก็บเป็น `brand_names` array)

## หมวดสินค้า (6 หมวด)

| ภาษาไทย | เก็บเป็น (English) |
|----------|-------------------|
| ที่นอน, ฟูก | Mattress |
| หมอน | Pillow |
| เครื่องนอน, ผ้าปู, ผ้านวม, ชุดเครื่องนอน | Bedding |
| โครงเตียง, เตียง, หัวเตียง | Bed Frame |
| ท็อปเปอร์, แผ่นรองนอน | Topper |
| แผ่นกันเปื้อน, ผ้ารองกันเปื้อน, กันไรฝุ่น | Protector |

AI จะแปลงชื่อสินค้าภาษาไทยเป็นภาษาอังกฤษก่อนบันทึกเสมอ

## ช่องทางขาย (4 ช่องทาง)

Official Store, Online, Department Store, Dealer

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, Tailwind CSS 4, Lucide React |
| Backend | FastAPI, Python 3.12+, Uvicorn |
| AI (Cloud) | Groq API (Whisper large-v3 + Llama 3.3 70B) |
| Database | Mock (In-memory dict) — รอเปลี่ยน DB จริง |
| Audio | Python `wave` module (chunking), ffmpeg (conversion) |

---

## สำหรับนักพัฒนาที่รับต่อ

### สิ่งที่ต้องรู้
1. **ทุกอย่างยังเป็น Mock DB** — ข้อมูลหายเมื่อ restart server
2. **Groq free tier มี rate limit** — ใส่หลาย key เพื่อสลับอัตโนมัติ
3. **Queue ทำงานทีละ 1 ไฟล์** — พัก 15 วินาทีระหว่างไฟล์ ไฟล์ถัดไปรอจนไฟล์ก่อนหน้าเสร็จ
4. **Dashboard ใช้ข้อมูล mock** — ยังไม่ได้ดึงจาก API จริง (static mockup)
5. **Filename parser** — ดึง date/customer/agent/direction จากชื่อไฟล์อัตโนมัติ (Inbound สลับ customer-agent กับ Outbound)
6. **Brand เก็บเป็น array** — `brand_names: ["Lotus", "Omazz"]` รองรับหลายแบรนด์ต่อไฟล์
7. **re-Analyze** — กดแล้วเข้าคิว ระบบคืนผลวิเคราะห์ล่าสุดเสมอ (เรียงตาม created_at)
8. **Upload limit** — 60MB
9. **test_local_ai.py** — เตรียมไว้สำหรับเปลี่ยนเป็น local AI (faster-whisper + Ollama) ในอนาคต

### สิ่งที่ยังไม่ได้ทำ
- เชื่อม Database จริง (PostgreSQL / MongoDB)
- Dashboard ดึงข้อมูลจาก API จริง
- Authentication / Login
- Typhoon ASR (เตรียมเปลี่ยนจาก Groq Whisper)
- Local AI mode (faster-whisper + Ollama)
- Customer management module
