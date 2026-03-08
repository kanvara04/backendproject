# =============================================================================
# database/mock_db.py
# Mock Database สำหรับ AI Voice Intelligence System
#
# อธิบาย: เนื่องจากทีม Database ยังพัฒนาไม่เสร็จ เราจึงใช้ Python Dictionary
# แทน Database จริง เพื่อให้ทีม Backend พัฒนาและทดสอบ API ได้ก่อน
# =============================================================================

from datetime import datetime
from typing import Optional

# =============================================================================
# SECTION 1: CUSTOMER PROFILES (ข้อมูลลูกค้า)
# =============================================================================
# โครงสร้าง: { "customer_id": { ...ข้อมูลลูกค้า... } }
# Key สำคัญ: "phone_numbers" เป็น List เพราะลูกค้า 1 คน มีหลายเบอร์ได้
# =============================================================================

MOCK_CUSTOMERS: dict = {
    "CUST-001": {
        "customer_id": "CUST-001",
        "full_name": "สมชาย ใจดี",
        "email": "somchai.jaidee@email.com",
        # --- จุดสำคัญ ---
        # phone_numbers เป็น List เพื่อรองรับลูกค้าที่มีหลายเบอร์โทร
        # เช่น เบอร์บ้าน, มือถือส่วนตัว, มือถือที่ทำงาน
        "phone_numbers": ["0812345678", "0898765432", "026541234"],
        "primary_phone": "0812345678",   # เบอร์หลักที่ใช้ติดต่อ
        "account_type": "Premium",        # ประเภทบัญชี: Premium, Standard, Basic
        "registration_date": "2021-03-15",
        "address": "123 ถ.สุขุมวิท แขวงคลองเตย เขตคลองเตย กรุงเทพฯ 10110",
        "is_active": True,                # สถานะลูกค้า: True = ยังใช้งานอยู่
    },
    "CUST-002": {
        "customer_id": "CUST-002",
        "full_name": "สุดา มีสุข",
        "email": "suda.meesuk@email.com",
        "phone_numbers": ["0923456789"],  # ลูกค้ารายนี้มีแค่เบอร์เดียว
        "primary_phone": "0923456789",
        "account_type": "Standard",
        "registration_date": "2022-07-20",
        "address": "456 ถ.รัชดาภิเษก แขวงดินแดง เขตดินแดง กรุงเทพฯ 10400",
        "is_active": True,
    },
    "CUST-003": {
        "customer_id": "CUST-003",
        "full_name": "วิชัย ธรรมดี",
        "email": "wichai.thamdi@email.com",
        "phone_numbers": ["0634567890", "0812223334"],
        "primary_phone": "0634567890",
        "account_type": "Basic",
        "registration_date": "2023-01-10",
        "address": "789 ถ.พหลโยธิน แขวงลาดยาว เขตจตุจักร กรุงเทพฯ 10900",
        "is_active": False,               # ลูกค้าที่ไม่ได้ใช้งานแล้ว
    },
    "CUST-004": {
        "customer_id": "CUST-004",
        "full_name": "นภาพร สวัสดิ์",
        "email": "napaporn.sawat@email.com",
        "phone_numbers": ["0745678901", "0891112233", "022334455"],
        "primary_phone": "0745678901",
        "account_type": "Premium",
        "registration_date": "2020-11-05",
        "address": "321 ถ.เพชรบุรี แขวงมักกะสัน เขตราษฎร์บูรณะ กรุงเทพฯ 10120",
        "is_active": True,
    },
}

# =============================================================================
# SECTION 2: PHONE NUMBER INDEX (ดัชนีเบอร์โทรศัพท์)
# =============================================================================
# ปัญหา: ถ้าเราได้รับเบอร์โทร เราจะหาข้อมูลลูกค้าได้ยังไง?
# วิธีแก้: สร้าง "ดัชนี" (Index) ที่ Map จากเบอร์โทร -> customer_id
# ทำให้ค้นหาลูกค้าจากเบอร์โทรได้เร็ว O(1) แทนที่จะ loop ทุก customer O(n)
# =============================================================================

# สร้าง Phone-to-CustomerID Index อัตโนมัติจาก MOCK_CUSTOMERS
# วิธีอ่าน: "สำหรับลูกค้าทุกคน ให้เอาทุกเบอร์โทรของเขา Map ไปยัง customer_id"
PHONE_TO_CUSTOMER_ID: dict = {
    phone: customer_id
    for customer_id, customer_data in MOCK_CUSTOMERS.items()
    for phone in customer_data["phone_numbers"]
}

# ผลลัพธ์ที่ได้จะมีหน้าตาแบบนี้:
# {
#   "0812345678": "CUST-001",
#   "0898765432": "CUST-001",
#   "026541234":  "CUST-001",
#   "0923456789": "CUST-002",
#   ...และต่อไปเรื่อยๆ
# }


# =============================================================================
# SECTION 3: AI AUDIO ANALYSIS RESULTS (ผลการวิเคราะห์เสียงจาก AI)
# =============================================================================
# ตารางนี้เก็บผลลัพธ์ที่ได้จากการให้ AI วิเคราะห์ไฟล์เสียงการโทร
#
# ฟิลด์ที่สำคัญ:
#   - csat_score    : Customer Satisfaction Score (1-5 ดาว)
#   - intent        : สิ่งที่ลูกค้าต้องการ เช่น "สอบถามบิล", "แจ้งปัญหา"
#   - qa_score      : คะแนน QA ของเจ้าหน้าที่ (0.0 - 10.0)
#   - sentiment     : ความรู้สึกของลูกค้า (positive/neutral/negative)
#   - summary       : สรุปการสนทนาโดย AI
# =============================================================================

MOCK_ANALYSIS_RESULTS: dict = {
    "ANALYSIS-001": {
        "analysis_id": "ANALYSIS-001",
        "call_id": "CALL-20240101-001",      # ID ของการโทรที่เชื่อมโยง
        "customer_id": "CUST-001",
        "agent_id": "AGENT-005",             # รหัสเจ้าหน้าที่ที่รับสาย
        "phone_number_used": "0812345678",   # เบอร์ที่ลูกค้าโทรมา
        "call_duration_seconds": 245,        # ระยะเวลาการโทร (วินาที)
        "call_timestamp": "2024-01-15T09:30:00",

        # --- ผลการวิเคราะห์จาก AI ---
        "csat_score": 4,                     # 1-5 (5 = พอใจมากที่สุด)
        "intent": "สอบถามค่าบริการรายเดือน", # Intent ที่ AI ตรวจจับได้
        "qa_score": 8.5,                     # 0.0-10.0 (10 = ดีที่สุด)
        "sentiment": "positive",             # positive / neutral / negative
        "sentiment_score": 0.72,             # ค่าความมั่นใจของ AI (0.0-1.0)
        "summary": "ลูกค้าสอบถามเกี่ยวกับค่าบริการรายเดือนที่เพิ่มขึ้น เจ้าหน้าที่อธิบายรายละเอียดแพ็กเกจและเสนอโปรโมชั่นพิเศษ ลูกค้าพอใจและขอบคุณ",
        "keywords": ["ค่าบริการ", "แพ็กเกจ", "โปรโมชั่น"],
        "is_escalated": False,               # มีการโอนสายไปผู้จัดการหรือไม่
        "created_at": "2024-01-15T09:34:12",
        "model_version": "whisper-v3",       # เวอร์ชันของ AI Model ที่ใช้
    },
    "ANALYSIS-002": {
        "analysis_id": "ANALYSIS-002",
        "call_id": "CALL-20240102-003",
        "customer_id": "CUST-002",
        "agent_id": "AGENT-012",
        "phone_number_used": "0923456789",
        "call_duration_seconds": 480,
        "call_timestamp": "2024-01-16T14:15:00",

        "csat_score": 2,
        "intent": "แจ้งปัญหาสินค้าชำรุด",
        "qa_score": 6.0,
        "sentiment": "negative",
        "sentiment_score": 0.85,
        "summary": "ลูกค้าแจ้งปัญหาสินค้าชำรุดหลังใช้งาน 2 สัปดาห์ เจ้าหน้าที่ขอเวลาตรวจสอบแต่ไม่สามารถแก้ปัญหาได้ทันที ลูกค้าไม่พอใจและขอคุยกับผู้จัดการ",
        "keywords": ["สินค้าชำรุด", "คืนสินค้า", "ผู้จัดการ"],
        "is_escalated": True,
        "created_at": "2024-01-16T14:23:45",
        "model_version": "whisper-v3",
    },
    "ANALYSIS-003": {
        "analysis_id": "ANALYSIS-003",
        "call_id": "CALL-20240103-007",
        "customer_id": "CUST-004",
        "agent_id": "AGENT-005",
        "phone_number_used": "0745678901",
        "call_duration_seconds": 120,
        "call_timestamp": "2024-01-17T11:00:00",

        "csat_score": 5,
        "intent": "ขอบคุณและให้คำชมเจ้าหน้าที่",
        "qa_score": 9.8,
        "sentiment": "positive",
        "sentiment_score": 0.95,
        "summary": "ลูกค้าโทรมาขอบคุณเจ้าหน้าที่ที่ช่วยแก้ปัญหาได้อย่างรวดเร็วในครั้งก่อน แสดงความพึงพอใจสูงมาก",
        "keywords": ["ขอบคุณ", "พอใจมาก", "บริการดี"],
        "is_escalated": False,
        "created_at": "2024-01-17T11:02:05",
        "model_version": "whisper-v3",
    },
}

# =============================================================================
# SECTION 4: HELPER FUNCTIONS (ฟังก์ชันช่วยเหลือ)
# =============================================================================
# ฟังก์ชันเหล่านี้ทำหน้าที่คล้าย "Query" ใน Database จริง
# ช่วยให้ Router/Service ไม่ต้องจัดการ Logic การค้นหาเอง
# =============================================================================

def find_customer_by_phone(phone_number: str) -> Optional[dict]:
    """
    ค้นหาข้อมูลลูกค้าจากเบอร์โทรศัพท์
    คล้ายกับ: SELECT * FROM customers WHERE phone_number = ?
    
    Args:
        phone_number: เบอร์โทรที่ต้องการค้นหา เช่น "0812345678"
    
    Returns:
        dict ของข้อมูลลูกค้า หรือ None ถ้าไม่พบ
    """
    # ขั้นที่ 1: หา customer_id จาก Phone Index ก่อน (เร็วกว่า loop)
    customer_id = PHONE_TO_CUSTOMER_ID.get(phone_number)
    
    # ขั้นที่ 2: ถ้าหาไม่เจอ return None
    if not customer_id:
        return None
    
    # ขั้นที่ 3: ดึงข้อมูล Customer เต็มๆ จาก customer_id
    return MOCK_CUSTOMERS.get(customer_id)


def find_customer_by_id(customer_id: str) -> Optional[dict]:
    """
    ค้นหาข้อมูลลูกค้าจาก Customer ID
    คล้ายกับ: SELECT * FROM customers WHERE customer_id = ?
    """
    return MOCK_CUSTOMERS.get(customer_id)


def get_all_customers() -> list:
    """
    ดึงข้อมูลลูกค้าทั้งหมด
    คล้ายกับ: SELECT * FROM customers
    """
    return list(MOCK_CUSTOMERS.values())


def save_analysis_result(analysis_data: dict) -> dict:
    """
    บันทึกผลการวิเคราะห์เสียงลงใน Mock Database
    คล้ายกับ: INSERT INTO analysis_results VALUES (...)
    
    Args:
        analysis_data: dict ที่มีข้อมูลผลการวิเคราะห์
    
    Returns:
        dict ของข้อมูลที่บันทึกแล้ว พร้อม analysis_id และ created_at
    """
    # สร้าง ID ใหม่โดยนับจำนวนรายการที่มีอยู่ + 1
    new_id = f"ANALYSIS-{len(MOCK_ANALYSIS_RESULTS) + 1:03d}"
    
    # เพิ่มข้อมูล Metadata ที่จำเป็น
    analysis_data["analysis_id"] = new_id
    analysis_data["created_at"] = datetime.now().isoformat()
    
    # บันทึกลง Mock Database (Dictionary)
    MOCK_ANALYSIS_RESULTS[new_id] = analysis_data
    
    return analysis_data


def get_analysis_by_customer(customer_id: str) -> list:
    """
    ดึงผลการวิเคราะห์ทั้งหมดของลูกค้าคนนึง
    คล้ายกับ: SELECT * FROM analysis_results WHERE customer_id = ?
    """
    return [
        result for result in MOCK_ANALYSIS_RESULTS.values()
        if result.get("customer_id") == customer_id
    ]


def get_analysis_by_id(analysis_id: str) -> Optional[dict]:
    """
    ดึงผลการวิเคราะห์จาก ID
    คล้ายกับ: SELECT * FROM analysis_results WHERE analysis_id = ?
    """
    return MOCK_ANALYSIS_RESULTS.get(analysis_id)
