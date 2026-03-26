# =============================================================================
# database/mock_db.py — v0.6.0
# Mock Database สำหรับ AI Voice Intelligence System
#
# === UPDATE v0.6.0 — Real Brands + Sales Channel + Product Filter ===
#
# ฟิลด์ใหม่ใน MOCK_ANALYSIS_RESULTS:
#   - brand_name       : แบรนด์จริง (Lotus, Omazz, Midas, Dunlopillo, ...)
#   - product_category : หมวดสินค้า (Mattress, Pillow, Bedding, Bed Frame, Topper, ...)
#   - sale_channel     : ช่องทางซื้อ (Official Store, Online, Department Store, Dealer)
#
# Brands ที่รองรับ (12 แบรนด์):
#   Lotus, Omazz, Midas, Dunlopillo, Bedgear, LaLaBed,
#   Zinus, Eastman House, Malouf, Loto mobili, Woodfield, Restonic
#
# Sale Channels (4 ช่องทาง):
#   Official Store  = ซื้อจากหน้าร้าน/เว็บของแบรนด์โดยตรง
#   Online          = Shopee, Lazada, JD Central, etc.
#   Department Store = ห้างสรรพสินค้า (Central, The Mall, Robinson, etc.)
#   Dealer          = ตัวแทนจำหน่าย / ร้านค้าปลีก
#
# Product Categories (6 หมวด):
#   Mattress, Pillow, Bedding, Topper, Bed Frame, Protector
# =============================================================================

from datetime import datetime
from typing import Optional


# =============================================================================
# SECTION 1: CUSTOMER PROFILES
# =============================================================================

MOCK_CUSTOMERS: dict = {
    "CUST-001": {
        "customer_id": "CUST-001",
        "full_name": "สมชาย ใจดี",
        "email": "somchai.jaidee@email.com",
        "phone_numbers": ["0911111111", "0898765432"],
        "primary_phone": "0911111111",
        "account_type": "Premium",
        "registration_date": "2021-03-15",
        "address": "123 ถ.สุขุมวิท กรุงเทพฯ 10110",
        "is_active": True,
    },
    "CUST-002": {
        "customer_id": "CUST-002",
        "full_name": "สุดา มีสุข",
        "email": "suda.meesuk@email.com",
        "phone_numbers": ["0922222222"],
        "primary_phone": "0922222222",
        "account_type": "Standard",
        "registration_date": "2022-07-20",
        "address": "456 ถ.รัชดาภิเษก กรุงเทพฯ 10400",
        "is_active": True,
    },
    "CUST-003": {
        "customer_id": "CUST-003",
        "full_name": "วิชัย ธรรมดี",
        "email": "wichai.thamdi@email.com",
        "phone_numbers": ["0633333333", "0812223334"],
        "primary_phone": "0633333333",
        "account_type": "Basic",
        "registration_date": "2023-01-10",
        "address": "789 ถ.พหลโยธิน กรุงเทพฯ 10900",
        "is_active": True,
    },
    "CUST-004": {
        "customer_id": "CUST-004",
        "full_name": "นภาพร สวัสดิ์",
        "email": "napaporn.sawat@email.com",
        "phone_numbers": ["0744444444", "0891112233"],
        "primary_phone": "0744444444",
        "account_type": "Premium",
        "registration_date": "2020-11-05",
        "address": "321 ถ.เพชรบุรี กรุงเทพฯ 10120",
        "is_active": True,
    },
    "CUST-005": {
        "customer_id": "CUST-005",
        "full_name": "ปรีชา วงษ์สุวรรณ",
        "email": "preecha.wong@email.com",
        "phone_numbers": ["0855555555"],
        "primary_phone": "0855555555",
        "account_type": "Standard",
        "registration_date": "2023-06-12",
        "address": "55 ถ.ลาดพร้าว กรุงเทพฯ 10230",
        "is_active": True,
    },
}


# =============================================================================
# SECTION 2: PHONE NUMBER INDEX
# =============================================================================

PHONE_TO_CUSTOMER_ID: dict = {
    phone: customer_id
    for customer_id, customer_data in MOCK_CUSTOMERS.items()
    for phone in customer_data["phone_numbers"]
}


# =============================================================================
# SECTION 3: CONSTANTS — Brands, Products, Channels
# =============================================================================
# ค่าคงที่สำหรับใช้ทั้ง Mock DB, AI Service, และ Dashboard

SUPPORTED_BRANDS = [
    "Lotus", "Omazz", "Midas", "Dunlopillo", "Bedgear", "LaLaBed",
    "Zinus", "Eastman House", "Malouf", "Loto mobili", "Woodfield", "Restonic",
]

SUPPORTED_PRODUCTS = [
    "Mattress",       # ที่นอน
    "Pillow",         # หมอน
    "Bedding",        # ชุดเครื่องนอน (ผ้าปู, ผ้านวม, ปลอกหมอน)
    "Topper",         # ท็อปเปอร์
    "Bed Frame",      # โครงเตียง / เตียง
    "Protector",      # ผ้ารองกันเปื้อน / Mattress Protector
]

SUPPORTED_CHANNELS = [
    "Official Store",    # ซื้อจากหน้าร้าน/เว็บของแบรนด์โดยตรง
    "Online",            # Shopee, Lazada, JD Central, TikTok Shop
    "Department Store",  # ห้างสรรพสินค้า (Central, The Mall, Robinson)
    "Dealer",            # ตัวแทนจำหน่าย / ร้านค้าปลีก
]


# =============================================================================
# SECTION 3.5: MOCK AUDIO FILES (Sample Database)
# =============================================================================
# ไฟล์เสียงตัวอย่าง 2 ไฟล์ที่ถูก pre-load ในระบบ
# พร้อม metadata สมมุติ: เบอร์ผู้โทร, Agent ที่รับสาย
# =============================================================================

MOCK_AUDIO_FILES: dict = {
    "SAMPLE-001": {
        "file_id": "SAMPLE-001",
        "original_filename": "20251104173706-1762252614_105999-104-0819979336-Outbound.wav",
        "uploaded_path": "storage/uploads/20251104173706-1762252614_105999-104-0819979336-Outbound.wav",
        "converted_path": "storage/uploads/20251104173706-1762252614_105999-104-0819979336-Outbound.wav",
        "status": "analyzed",
        "customer_phone": "081-997-9336",
        "agent_id": "AGENT-104",
        "agent_name": "สมศักดิ์ วงษ์สว่าง",
        "call_direction": "Outbound",
        "call_date": "2025-11-04T17:37:06",
        "call_duration_seconds": 345,
        "conversion_details": {
            "original_format": ".wav",
            "original_size_mb": 10.52,
            "converted_size_mb": 10.52,
            "sample_rate": 16000,
            "channels": 1,
            "conversion_time_seconds": 0.0,
        },
    },
    "SAMPLE-002": {
        "file_id": "SAMPLE-002",
        "original_filename": "20260131135423-1769842455_164218-102-0819979336-Outbound.wav",
        "uploaded_path": "storage/uploads/20260131135423-1769842455_164218-102-0819979336-Outbound.wav",
        "converted_path": "storage/uploads/20260131135423-1769842455_164218-102-0819979336-Outbound.wav",
        "status": "analyzed",
        "customer_phone": "081-997-9336",
        "agent_id": "AGENT-102",
        "agent_name": "ปรีชา ธนพัฒน์",
        "call_direction": "Outbound",
        "call_date": "2026-01-31T13:54:23",
        "call_duration_seconds": 142,
        "conversion_details": {
            "original_format": ".wav",
            "original_size_mb": 4.35,
            "converted_size_mb": 4.35,
            "sample_rate": 16000,
            "channels": 1,
            "conversion_time_seconds": 0.0,
        },
    },
}


# Analysis results linked to the sample audio files
MOCK_SAMPLE_ANALYSIS: dict = {
    "ANALYSIS-SAMPLE-001": {
        "analysis_id": "ANALYSIS-SAMPLE-001",
        "file_id": "SAMPLE-001",
        "call_id": "CALL-20251104-001",
        "customer_id": "CUST-001",
        "agent_id": "AGENT-104",
        "agent_name": "สมศักดิ์ วงษ์สว่าง",
        "phone_number_used": "0819979336",
        "call_duration_seconds": 345,
        "call_timestamp": "2025-11-04T17:37:06",
        "brand_name": "Omazz",
        "product_category": "Mattress",
        "sale_channel": "Online",
        "csat_score": 3,
        "intent": "สอบถามสถานะการจัดส่ง",
        "qa_score": 7.2,
        "sentiment": "neutral",
        "sentiment_score": 0.58,
        "summary": "ลูกค้าโทรสอบถามสถานะการจัดส่งที่นอน Omazz ที่สั่งผ่าน Shopee 5 วันก่อน ยังไม่ได้รับสินค้า เจ้าหน้าที่ตรวจสอบพบว่ามีปัญหาที่คลังสินค้า ได้ดำเนินการเร่งจัดส่งให้",
        "summary_points": [
            "ลูกค้าโทรสอบถามสถานะจัดส่งที่นอน Omazz สั่งผ่าน Shopee เมื่อ 5 วันก่อน",
            "เจ้าหน้าที่ตรวจสอบพบว่าเกิดปัญหาที่คลังสินค้าทำให้จัดส่งล่าช้า",
            "เจ้าหน้าที่ประสานงานเร่งจัดส่ง คาดว่าจะได้รับภายใน 2 วัน",
            "ลูกค้ารับทราบแต่ยังไม่พอใจกับความล่าช้า",
        ],
        "transcription": [
            {"id": 0, "start": 5.0, "end": 11.5, "text": "สวัสดีครับ ผมสมศักดิ์ครับ ยินดีให้บริการ ไม่ทราบว่ามีเรื่องอะไรให้ช่วยเหลือครับ?"},
            {"id": 1, "start": 12.0, "end": 33.0, "text": "ค่ะ พอดีสั่งที่นอน Omazz จาก Shopee ไปเมื่อวันศุกร์ที่แล้ว ยังไม่ได้รับเลยค่ะ เลขพัสดุเช็คแล้วยังไม่มีอัปเดตมาสองวันค่ะ"},
            {"id": 2, "start": 35.0, "end": 41.5, "text": "ต้องขออภัยด้วยนะครับ ผมขอเลขคำสั่งซื้อเพื่อตรวจสอบให้ได้เลยครับ"},
            {"id": 3, "start": 42.0, "end": 46.0, "text": "เลขออเดอร์ SP-20251101-78543 ค่ะ"},
            {"id": 4, "start": 65.0, "end": 90.0, "text": "รับทราบครับ ผมตรวจสอบให้แล้วพบว่าตอนนี้สินค้ายังอยู่ที่คลังสินค้าครับ เนื่องจากมีปัญหาระบบจัดส่งช่วงต้นเดือน ต้องขออภัยจริงๆ ครับ"},
            {"id": 5, "start": 85.0, "end": 92.0, "text": "แล้วจะได้รับเมื่อไหร่คะ? รอนานมากแล้วค่ะ"},
            {"id": 6, "start": 95.0, "end": 110.0, "text": "ผมจะประสานงานเร่งให้ครับ คาดว่าจะจัดส่งได้ภายในวันนี้และลูกค้าจะได้รับภายใน 1-2 วันครับ"},
        ],
        "key_insights": "ลูกค้ามีอาการไม่พอใจกับความล่าช้าในการจัดส่ง แต่เจ้าหน้าที่สามารถอธิบายสาเหตุและเสนอทางแก้ไขได้ดี ควรติดตามผลหลังจัดส่งภายใน 24 ชั่วโมง",
        "keywords": ["Omazz", "ที่นอน", "Shopee", "จัดส่งล่าช้า", "คลังสินค้า"],
        "is_escalated": False,
        "created_at": "2025-11-04T17:45:00",
        "model_version": "whisper-v3",
    },
    "ANALYSIS-SAMPLE-002": {
        "analysis_id": "ANALYSIS-SAMPLE-002",
        "file_id": "SAMPLE-002",
        "call_id": "CALL-20260131-001",
        "customer_id": "CUST-002",
        "agent_id": "AGENT-102",
        "agent_name": "ปรีชา ธนพัฒน์",
        "phone_number_used": "0819979336",
        "call_duration_seconds": 142,
        "call_timestamp": "2026-01-31T13:54:23",
        "brand_name": "Lotus",
        "product_category": "Pillow",
        "sale_channel": "Department Store",
        "csat_score": 4,
        "intent": "แจ้งปัญหาสินค้าชำรุด",
        "qa_score": 8.5,
        "sentiment": "positive",
        "sentiment_score": 0.72,
        "summary": "ลูกค้าโทรแจ้งปัญหาหมอน Lotus ที่ซื้อจาก Central ชำรุดหลังใช้ 3 สัปดาห์ เจ้าหน้าที่เสนอเปลี่ยนสินค้าใหม่และให้คูปองส่วนลด 15% ลูกค้าพอใจกับการแก้ไข",
        "summary_points": [
            "ลูกค้าแจ้งปัญหาหมอน Lotus ที่ซื้อจาก Central เมื่อ 3 สัปดาห์ก่อน ยุบตัวผิดปกติ",
            "เจ้าหน้าที่ตรวจสอบแล้วยังอยู่ในระยะรับประกัน สามารถเปลี่ยนชิ้นใหม่ได้",
            "เจ้าหน้าที่เสนอคูปองส่วนลด 15% เพิ่มเติมเพื่อชดเชยความไม่สะดวก",
            "ลูกค้ายอมรับข้อเสนอและพอใจกับการแก้ไขปัญหา",
        ],
        "transcription": [
            {"id": 0, "start": 3.0, "end": 9.5, "text": "สวัสดีครับ ผมปรีชาครับ จากฝ่ายบริการลูกค้า Lotus ครับ วันนี้มีเรื่องอะไรให้ช่วยเหลือครับ?"},
            {"id": 1, "start": 10.0, "end": 21.0, "text": "สวัสดีค่ะ หนูซื้อหมอน Lotus รุ่น Premium จาก Central ลาดพร้าวมาค่ะ ใช้ได้ 3 สัปดาห์แล้วมันยุบตัวผิดปกติค่ะ"},
            {"id": 2, "start": 22.0, "end": 29.5, "text": "ต้องขออภัยด้วยครับ ขอสอบถามเลขใบเสร็จหรือเบอร์สมาชิกเพื่อตรวจสอบได้เลยครับ"},
            {"id": 3, "start": 30.0, "end": 34.0, "text": "เบอร์สมาชิก LT-2025-98765 ค่ะ"},
            {"id": 4, "start": 48.0, "end": 68.0, "text": "ตรวจสอบแล้วครับ สินค้ายังอยู่ในระยะรับประกัน 1 ปี สามารถเปลี่ยนชิ้นใหม่ได้เลยครับ และผมขอเสนอคูปองส่วนลด 15% สำหรับการซื้อครั้งถัดไปเป็นการชดเชยด้วยครับ"},
            {"id": 5, "start": 70.0, "end": 82.0, "text": "ขอบคุณมากค่ะ ดีใจที่ได้รับการดูแลดีค่ะ แล้วจะไปเปลี่ยนที่สาขาเดิมได้เลยใช่ไหมคะ?"},
            {"id": 6, "start": 80.0, "end": 90.0, "text": "ได้เลยครับ นำหมอนพร้อมใบเสร็จไปที่สาขา Central ลาดพร้าวได้เลยครับ"},
        ],
        "key_insights": "ลูกค้าเริ่มต้นด้วยอารมณ์ไม่พอใจจากปัญหาสินค้า แต่เปลี่ยนเป็นพอใจหลังเจ้าหน้าที่เสนอการแก้ไขอย่างรวดเร็วพร้อมคูปองชดเชย เป็นตัวอย่าง Service Recovery ที่ดี",
        "keywords": ["Lotus", "หมอน", "Central", "ชำรุด", "เปลี่ยนสินค้า", "คูปอง"],
        "is_escalated": False,
        "created_at": "2026-01-31T14:02:00",
        "model_version": "whisper-v3",
    },
}


# =============================================================================
# SECTION 4: AI AUDIO ANALYSIS RESULTS — 15 Mock Records
# =============================================================================
# ทุก record มี 3 ฟิลด์ใหม่: brand_name, product_category, sale_channel
# ข้อมูลครอบคลุมหลายแบรนด์, สินค้า, ช่องทาง เพื่อให้ทดสอบ filter ได้ครบ
# =============================================================================

MOCK_ANALYSIS_RESULTS: dict = {

    # ── Omazz / Mattress / Shopee (Online) ──
    "ANALYSIS-001": {
        "analysis_id": "ANALYSIS-001",
        "call_id": "CALL-20241015-001",
        "customer_id": "CUST-001",
        "agent_id": "AGENT-01",
        "phone_number_used": "0911111111",
        "call_duration_seconds": 245,
        "call_timestamp": "2024-10-21T09:30:00",
        "brand_name": "Omazz",
        "product_category": "Mattress",
        "sale_channel": "Online",
        "csat_score": 4,
        "intent": "สอบถามข้อมูลสินค้า",
        "qa_score": 8.5,
        "sentiment": "positive",
        "sentiment_score": 0.72,
        "summary": "ลูกค้าสอบถามเรื่องที่นอน Omazz ที่ซื้อผ่าน Shopee เจ้าหน้าที่แนะนำข้อมูลครบถ้วน",
        "keywords": ["Omazz", "ที่นอน", "Shopee"],
        "is_escalated": False,
        "created_at": "2024-10-21T09:34:12",
        "model_version": "whisper-v3",
    },

    # ── Lotus / Pillow / Department Store ──
    "ANALYSIS-002": {
        "analysis_id": "ANALYSIS-002",
        "call_id": "CALL-20241016-003",
        "customer_id": "CUST-002",
        "agent_id": "AGENT-02",
        "phone_number_used": "0922222222",
        "call_duration_seconds": 480,
        "call_timestamp": "2024-10-22T14:15:00",
        "brand_name": "Lotus",
        "product_category": "Pillow",
        "sale_channel": "Department Store",
        "csat_score": 2,
        "intent": "แจ้งปัญหาสินค้าชำรุด",
        "qa_score": 5.8,
        "sentiment": "negative",
        "sentiment_score": 0.85,
        "summary": "ลูกค้าแจ้งหมอน Lotus ที่ซื้อจาก Central ชำรุดหลังใช้ 2 สัปดาห์ ขอเปลี่ยนสินค้าใหม่",
        "keywords": ["Lotus", "หมอน", "Central", "ชำรุด"],
        "is_escalated": True,
        "created_at": "2024-10-22T14:23:45",
        "model_version": "whisper-v3",
    },

    # ── Dunlopillo / Mattress / Official Store ──
    "ANALYSIS-003": {
        "analysis_id": "ANALYSIS-003",
        "call_id": "CALL-20241017-007",
        "customer_id": "CUST-004",
        "agent_id": "AGENT-01",
        "phone_number_used": "0744444444",
        "call_duration_seconds": 120,
        "call_timestamp": "2024-10-23T11:00:00",
        "brand_name": "Dunlopillo",
        "product_category": "Mattress",
        "sale_channel": "Official Store",
        "csat_score": 5,
        "intent": "ชมเชยเจ้าหน้าที่",
        "qa_score": 9.8,
        "sentiment": "positive",
        "sentiment_score": 0.95,
        "summary": "ลูกค้าชมที่นอน Dunlopillo ที่ซื้อจากหน้าร้าน Official นอนสบายมาก ชมเจ้าหน้าที่ที่แนะนำ",
        "keywords": ["Dunlopillo", "ที่นอน", "Official", "ชม"],
        "is_escalated": False,
        "created_at": "2024-10-23T11:02:05",
        "model_version": "whisper-v3",
    },

    # ── Midas / Bedding / Online (Lazada) ──
    "ANALYSIS-004": {
        "analysis_id": "ANALYSIS-004",
        "call_id": "CALL-20241018-010",
        "customer_id": "CUST-001",
        "agent_id": "AGENT-03",
        "phone_number_used": "0911111111",
        "call_duration_seconds": 310,
        "call_timestamp": "2024-10-24T10:00:00",
        "brand_name": "Midas",
        "product_category": "Bedding",
        "sale_channel": "Online",
        "csat_score": 3,
        "intent": "สอบถามสถานะการจัดส่ง",
        "qa_score": 7.2,
        "sentiment": "neutral",
        "sentiment_score": 0.60,
        "summary": "ลูกค้าสอบถามสถานะจัดส่งชุดเครื่องนอน Midas ที่สั่งจาก Lazada ยังไม่ได้รับ",
        "keywords": ["Midas", "เครื่องนอน", "Lazada", "จัดส่ง"],
        "is_escalated": False,
        "created_at": "2024-10-24T10:05:30",
        "model_version": "whisper-v3",
    },

    # ── Bedgear / Pillow / Dealer ──
    "ANALYSIS-005": {
        "analysis_id": "ANALYSIS-005",
        "call_id": "CALL-20241019-012",
        "customer_id": "CUST-003",
        "agent_id": "AGENT-02",
        "phone_number_used": "0633333333",
        "call_duration_seconds": 190,
        "call_timestamp": "2024-10-25T15:30:00",
        "brand_name": "Bedgear",
        "product_category": "Pillow",
        "sale_channel": "Dealer",
        "csat_score": 4,
        "intent": "สอบถามข้อมูลสินค้า",
        "qa_score": 8.0,
        "sentiment": "positive",
        "sentiment_score": 0.78,
        "summary": "ลูกค้าสอบถามหมอน Bedgear ที่ซื้อจากตัวแทนจำหน่าย เจ้าหน้าที่อธิบายวิธีดูแลรักษา",
        "keywords": ["Bedgear", "หมอน", "ตัวแทน"],
        "is_escalated": False,
        "created_at": "2024-10-25T15:33:20",
        "model_version": "whisper-v3",
    },

    # ── Zinus / Bed Frame / Online ──
    "ANALYSIS-006": {
        "analysis_id": "ANALYSIS-006",
        "call_id": "CALL-20241020-015",
        "customer_id": "CUST-004",
        "agent_id": "AGENT-01",
        "phone_number_used": "0891112233",
        "call_duration_seconds": 400,
        "call_timestamp": "2024-10-26T09:00:00",
        "brand_name": "Zinus",
        "product_category": "Bed Frame",
        "sale_channel": "Online",
        "csat_score": 1,
        "intent": "แจ้งปัญหาสินค้าชำรุด",
        "qa_score": 4.5,
        "sentiment": "negative",
        "sentiment_score": 0.92,
        "summary": "ลูกค้าแจ้งโครงเตียง Zinus ที่สั่ง Online ชิ้นส่วนหักเสียหาย ต้องการคืนเงิน",
        "keywords": ["Zinus", "เตียง", "หัก", "คืนเงิน"],
        "is_escalated": True,
        "created_at": "2024-10-26T09:07:00",
        "model_version": "whisper-v3",
    },

    # ── Restonic / Mattress / Department Store ──
    "ANALYSIS-007": {
        "analysis_id": "ANALYSIS-007",
        "call_id": "CALL-20241021-018",
        "customer_id": "CUST-002",
        "agent_id": "AGENT-03",
        "phone_number_used": "0922222222",
        "call_duration_seconds": 350,
        "call_timestamp": "2024-10-27T13:45:00",
        "brand_name": "Restonic",
        "product_category": "Mattress",
        "sale_channel": "Department Store",
        "csat_score": 5,
        "intent": "สอบถามโปรโมชั่น",
        "qa_score": 9.2,
        "sentiment": "positive",
        "sentiment_score": 0.88,
        "summary": "ลูกค้าสนใจโปรโมชั่นที่นอน Restonic ที่ห้าง The Mall เจ้าหน้าที่แนะนำ ลูกค้าตัดสินใจซื้อ",
        "keywords": ["Restonic", "ที่นอน", "The Mall", "โปรโมชั่น"],
        "is_escalated": False,
        "created_at": "2024-10-27T13:51:00",
        "model_version": "whisper-v3",
    },

    # ── LaLaBed / Topper / Online ──
    "ANALYSIS-008": {
        "analysis_id": "ANALYSIS-008",
        "call_id": "CALL-20241022-020",
        "customer_id": "CUST-003",
        "agent_id": "AGENT-02",
        "phone_number_used": "0812223334",
        "call_duration_seconds": 220,
        "call_timestamp": "2024-10-28T16:00:00",
        "brand_name": "LaLaBed",
        "product_category": "Topper",
        "sale_channel": "Online",
        "csat_score": 3,
        "intent": "แจ้งปัญหาสินค้าชำรุด",
        "qa_score": 6.8,
        "sentiment": "neutral",
        "sentiment_score": 0.55,
        "summary": "ลูกค้าแจ้ง Topper LaLaBed ที่สั่งจาก TikTok Shop ยุบตัวเร็ว เจ้าหน้าที่แนะนำวิธีดูแล",
        "keywords": ["LaLaBed", "Topper", "TikTok", "ยุบตัว"],
        "is_escalated": False,
        "created_at": "2024-10-28T16:04:00",
        "model_version": "whisper-v3",
    },

    # ── Eastman House / Mattress / Official Store ──
    "ANALYSIS-009": {
        "analysis_id": "ANALYSIS-009",
        "call_id": "CALL-20241023-022",
        "customer_id": "CUST-005",
        "agent_id": "AGENT-01",
        "phone_number_used": "0855555555",
        "call_duration_seconds": 280,
        "call_timestamp": "2024-10-29T08:30:00",
        "brand_name": "Eastman House",
        "product_category": "Mattress",
        "sale_channel": "Official Store",
        "csat_score": 4,
        "intent": "สอบถามการรับประกัน",
        "qa_score": 7.5,
        "sentiment": "neutral",
        "sentiment_score": 0.50,
        "summary": "ลูกค้าสอบถามเงื่อนไขรับประกันที่นอน Eastman House ที่ซื้อจาก Official Store",
        "keywords": ["Eastman House", "รับประกัน", "Official"],
        "is_escalated": False,
        "created_at": "2024-10-29T08:35:30",
        "model_version": "whisper-v3",
    },

    # ── Malouf / Protector / Online ──
    "ANALYSIS-010": {
        "analysis_id": "ANALYSIS-010",
        "call_id": "CALL-20241024-025",
        "customer_id": "CUST-004",
        "agent_id": "AGENT-03",
        "phone_number_used": "0744444444",
        "call_duration_seconds": 160,
        "call_timestamp": "2024-10-30T14:00:00",
        "brand_name": "Malouf",
        "product_category": "Protector",
        "sale_channel": "Online",
        "csat_score": 4,
        "intent": "สอบถามข้อมูลสินค้า",
        "qa_score": 8.3,
        "sentiment": "positive",
        "sentiment_score": 0.70,
        "summary": "ลูกค้าสอบถาม Mattress Protector ของ Malouf ที่ซื้อจาก Shopee เจ้าหน้าที่แนะนำวิธีซัก",
        "keywords": ["Malouf", "Protector", "Shopee", "วิธีซัก"],
        "is_escalated": False,
        "created_at": "2024-10-30T14:04:30",
        "model_version": "whisper-v3",
    },

    # ── Woodfield / Bed Frame / Dealer ──
    "ANALYSIS-011": {
        "analysis_id": "ANALYSIS-011",
        "call_id": "CALL-20241025-028",
        "customer_id": "CUST-001",
        "agent_id": "AGENT-02",
        "phone_number_used": "0898765432",
        "call_duration_seconds": 520,
        "call_timestamp": "2024-10-31T10:30:00",
        "brand_name": "Woodfield",
        "product_category": "Bed Frame",
        "sale_channel": "Dealer",
        "csat_score": 2,
        "intent": "ขอคืนสินค้า",
        "qa_score": 5.0,
        "sentiment": "negative",
        "sentiment_score": 0.88,
        "summary": "ลูกค้าต้องการคืนเตียง Woodfield ที่ซื้อจากตัวแทนจำหน่าย สีไม่ตรงตามที่สั่ง ลูกค้าไม่พอใจ",
        "keywords": ["Woodfield", "เตียง", "คืนสินค้า", "สีไม่ตรง"],
        "is_escalated": True,
        "created_at": "2024-10-31T10:39:00",
        "model_version": "whisper-v3",
    },

    # ── Lotus / Mattress / Online ──
    "ANALYSIS-012": {
        "analysis_id": "ANALYSIS-012",
        "call_id": "CALL-20241101-030",
        "customer_id": "CUST-005",
        "agent_id": "AGENT-01",
        "phone_number_used": "0855555555",
        "call_duration_seconds": 195,
        "call_timestamp": "2024-11-01T09:15:00",
        "brand_name": "Lotus",
        "product_category": "Mattress",
        "sale_channel": "Online",
        "csat_score": 4,
        "intent": "สอบถามโปรโมชั่น",
        "qa_score": 8.1,
        "sentiment": "positive",
        "sentiment_score": 0.75,
        "summary": "ลูกค้าสนใจโปรที่นอน Lotus 11.11 บน Lazada เจ้าหน้าที่แนะนำรุ่นที่เหมาะสม",
        "keywords": ["Lotus", "ที่นอน", "Lazada", "11.11"],
        "is_escalated": False,
        "created_at": "2024-11-01T09:18:30",
        "model_version": "whisper-v3",
    },

    # ── Loto mobili / Bedding / Department Store ──
    "ANALYSIS-013": {
        "analysis_id": "ANALYSIS-013",
        "call_id": "CALL-20241102-033",
        "customer_id": "CUST-002",
        "agent_id": "AGENT-03",
        "phone_number_used": "0922222222",
        "call_duration_seconds": 270,
        "call_timestamp": "2024-11-02T11:20:00",
        "brand_name": "Loto mobili",
        "product_category": "Bedding",
        "sale_channel": "Department Store",
        "csat_score": 3,
        "intent": "ขอเปลี่ยนสินค้า",
        "qa_score": 7.0,
        "sentiment": "neutral",
        "sentiment_score": 0.58,
        "summary": "ลูกค้าขอเปลี่ยนไซส์ชุดเครื่องนอน Loto mobili ที่ซื้อจาก Robinson เจ้าหน้าที่ดำเนินการ",
        "keywords": ["Loto mobili", "เครื่องนอน", "Robinson", "เปลี่ยนไซส์"],
        "is_escalated": False,
        "created_at": "2024-11-02T11:24:30",
        "model_version": "whisper-v3",
    },

    # ── Omazz / Topper / Official Store ──
    "ANALYSIS-014": {
        "analysis_id": "ANALYSIS-014",
        "call_id": "CALL-20241103-035",
        "customer_id": "CUST-003",
        "agent_id": "AGENT-02",
        "phone_number_used": "0633333333",
        "call_duration_seconds": 340,
        "call_timestamp": "2024-11-03T15:00:00",
        "brand_name": "Omazz",
        "product_category": "Topper",
        "sale_channel": "Official Store",
        "csat_score": 5,
        "intent": "ชมเชยเจ้าหน้าที่",
        "qa_score": 9.5,
        "sentiment": "positive",
        "sentiment_score": 0.93,
        "summary": "ลูกค้าชม Topper Omazz ที่ซื้อจาก Official Store นุ่มสบายมาก ชมเจ้าหน้าที่บริการดี",
        "keywords": ["Omazz", "Topper", "Official", "ชม"],
        "is_escalated": False,
        "created_at": "2024-11-03T15:06:00",
        "model_version": "whisper-v3",
    },

    # ── Dunlopillo / Pillow / Dealer ──
    "ANALYSIS-015": {
        "analysis_id": "ANALYSIS-015",
        "call_id": "CALL-20241104-038",
        "customer_id": "CUST-005",
        "agent_id": "AGENT-01",
        "phone_number_used": "0855555555",
        "call_duration_seconds": 180,
        "call_timestamp": "2024-11-04T10:45:00",
        "brand_name": "Dunlopillo",
        "product_category": "Pillow",
        "sale_channel": "Dealer",
        "csat_score": 4,
        "intent": "สอบถามข้อมูลสินค้า",
        "qa_score": 8.0,
        "sentiment": "positive",
        "sentiment_score": 0.72,
        "summary": "ลูกค้าสอบถามหมอน Dunlopillo ที่ซื้อจากร้านตัวแทนจำหน่าย สนใจซื้อเพิ่ม",
        "keywords": ["Dunlopillo", "หมอน", "ตัวแทน", "ซื้อเพิ่ม"],
        "is_escalated": False,
        "created_at": "2024-11-04T10:48:20",
        "model_version": "whisper-v3",
    },
}


# =============================================================================
# SECTION 5: HELPER FUNCTIONS (เดิม)
# =============================================================================

def find_customer_by_phone(phone_number: str) -> Optional[dict]:
    customer_id = PHONE_TO_CUSTOMER_ID.get(phone_number)
    if not customer_id:
        return None
    return MOCK_CUSTOMERS.get(customer_id)

def find_customer_by_id(customer_id: str) -> Optional[dict]:
    return MOCK_CUSTOMERS.get(customer_id)

def get_all_customers() -> list:
    return list(MOCK_CUSTOMERS.values())

def save_analysis_result(analysis_data: dict) -> dict:
    """
    บันทึกผลวิเคราะห์ — default brand/product/channel เป็น "Unknown"
    """
    new_id = f"ANALYSIS-{len(MOCK_ANALYSIS_RESULTS) + 1:03d}"
    analysis_data["analysis_id"] = new_id
    analysis_data["created_at"] = datetime.now().isoformat()
    if "brand_name" not in analysis_data:
        analysis_data["brand_name"] = "Unknown"
    if "product_category" not in analysis_data:
        analysis_data["product_category"] = "Unknown"
    if "sale_channel" not in analysis_data:
        analysis_data["sale_channel"] = "Unknown"
    MOCK_ANALYSIS_RESULTS[new_id] = analysis_data
    return analysis_data

def get_analysis_by_customer(customer_id: str) -> list:
    return [r for r in MOCK_ANALYSIS_RESULTS.values() if r.get("customer_id") == customer_id]

def get_analysis_by_id(analysis_id: str) -> Optional[dict]:
    return MOCK_ANALYSIS_RESULTS.get(analysis_id)


# =============================================================================
# SECTION 6: FILTER FUNCTIONS (v0.6.0 — Brand + Product + Channel)
# =============================================================================
# ใช้โดย Dashboard Router สำหรับ filter ข้อมูลตาม 3 เงื่อนไข:
#   1. brand_name       → แบรนด์สินค้า
#   2. product_category → หมวดหมู่สินค้า
#   3. sale_channel     → ช่องทางการซื้อ
#
# ทุก filter เป็น AND condition + case-insensitive
# ถ้าไม่ส่ง filter → ดึงข้อมูลทั้งหมด
# =============================================================================

def get_filtered_analysis(
    brand: Optional[str] = None,
    product: Optional[str] = None,
    channel: Optional[str] = None,
) -> list[dict]:
    """
    กรองผลวิเคราะห์ตาม brand / product / channel (AND, case-insensitive)

    คล้าย SQL:
      SELECT * FROM analysis_results
      WHERE (brand_name = :brand OR :brand IS NULL)
        AND (product_category = :product OR :product IS NULL)
        AND (sale_channel = :channel OR :channel IS NULL)

    Args:
        brand:   เช่น "Omazz", "Lotus" (optional)
        product: เช่น "Mattress", "Pillow" (optional)
        channel: เช่น "Online", "Official Store" (optional)
    """
    results = list(MOCK_ANALYSIS_RESULTS.values())

    if brand:
        results = [r for r in results if r.get("brand_name", "").lower() == brand.lower()]

    if product:
        results = [r for r in results if r.get("product_category", "").lower() == product.lower()]

    if channel:
        results = [r for r in results if r.get("sale_channel", "").lower() == channel.lower()]

    return results


def get_available_brands() -> list[str]:
    """ดึงรายชื่อแบรนด์ที่มีในข้อมูลจริง (ไม่รวม Unknown)"""
    brands = set()
    for r in MOCK_ANALYSIS_RESULTS.values():
        b = r.get("brand_name")
        if b and b != "Unknown":
            brands.add(b)
    return sorted(brands)

def get_available_products() -> list[str]:
    """ดึงรายชื่อ product_category ที่มีในข้อมูลจริง"""
    products = set()
    for r in MOCK_ANALYSIS_RESULTS.values():
        p = r.get("product_category")
        if p and p != "Unknown":
            products.add(p)
    return sorted(products)

def get_all_audio_files() -> list[dict]:
    """ดึงรายการไฟล์เสียงทั้งหมดพร้อมข้อมูล analysis"""
    files = []
    for file_id, audio in MOCK_AUDIO_FILES.items():
        # หา analysis ที่ตรงกับ file_id
        analysis = None
        for a in MOCK_SAMPLE_ANALYSIS.values():
            if a.get("file_id") == file_id:
                analysis = a
                break
        files.append({
            **audio,
            "analysis": analysis,
        })
    return files

def get_audio_file_by_id(file_id: str) -> Optional[dict]:
    """ดึงข้อมูลไฟล์เสียงจาก file_id"""
    return MOCK_AUDIO_FILES.get(file_id)

def get_analysis_by_file_id(file_id: str) -> Optional[dict]:
    """ดึงผลวิเคราะห์ล่าสุดจาก file_id"""
    all_matches = []

    for a in MOCK_SAMPLE_ANALYSIS.values():
        if a.get("file_id") == file_id:
            all_matches.append(a)

    for a in MOCK_ANALYSIS_RESULTS.values():
        if a.get("file_id") == file_id:
            all_matches.append(a)

    if not all_matches:
        return None

    # เรียงตาม created_at แล้วคืนอันล่าสุด
    all_matches.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return all_matches[0]

def add_audio_file(file_data: dict) -> dict:
    """เพิ่มไฟล์เสียงใหม่เข้า database"""
    file_id = file_data.get("file_id", f"FILE-{len(MOCK_AUDIO_FILES) + 1:03d}")
    file_data["file_id"] = file_id
    MOCK_AUDIO_FILES[file_id] = file_data
    return file_data

def add_sample_analysis(analysis_data: dict) -> dict:
    """เพิ่มผลวิเคราะห์ใหม่เข้า sample analysis"""
    analysis_id = analysis_data.get("analysis_id", f"ANALYSIS-{len(MOCK_SAMPLE_ANALYSIS) + len(MOCK_ANALYSIS_RESULTS) + 1:03d}")
    analysis_data["analysis_id"] = analysis_id
    MOCK_SAMPLE_ANALYSIS[analysis_id] = analysis_data
    return analysis_data


def get_available_channels() -> list[str]:
    """ดึงรายชื่อ sale_channel ที่มีในข้อมูลจริง"""
    channels = set()
    for r in MOCK_ANALYSIS_RESULTS.values():
        c = r.get("sale_channel")
        if c and c != "Unknown":
            channels.add(c)
    return sorted(channels)
