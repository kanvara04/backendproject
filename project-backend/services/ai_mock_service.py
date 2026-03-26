# =============================================================================
# services/ai_mock_service.py — v0.6.0
# Mock AI Service — จำลอง AI Models 3 ตัว
#
# === UPDATE v0.6.0 ===
# Llama NLP ตอนนี้ extract 3 ข้อมูลใหม่:
#   1. brand_name       → แบรนด์จริง 12 แบรนด์
#   2. product_category → 6 หมวดสินค้า
#   3. sale_channel     → 4 ช่องทางซื้อขาย
# =============================================================================

import asyncio
import random
from datetime import datetime
from typing import Optional


# =============================================================================
# STEP 1: Mock Transcript Dataset
# =============================================================================
# แต่ละ transcript มี hint สำหรับ brand, product, channel
# เพื่อให้ Llama NLP ใช้ extract ข้อมูล

_MOCK_TRANSCRIPTS = [
    {
        "text": "สวัสดีครับ ผมโทรมาสอบถามเรื่องที่นอน Omazz ที่สั่งจาก Shopee ครับ อยากทราบว่ารุ่นไหนเหมาะกับคนปวดหลัง",
        "language": "th", "intent_hint": "product_inquiry",
        "brand_hint": "Omazz", "product_hint": "Mattress", "channel_hint": "Online",
    },
    {
        "text": "หนูซื้อหมอน Lotus จาก Central มาค่ะ ใช้ได้ 2 สัปดาห์แล้วมันยุบตัว อยากขอเปลี่ยนค่ะ",
        "language": "th", "intent_hint": "product_damage",
        "brand_hint": "Lotus", "product_hint": "Pillow", "channel_hint": "Department Store",
    },
    {
        "text": "ผมซื้อที่นอน Dunlopillo จากหน้าร้าน Official ครับ นอนสบายมาก โทรมาชมเจ้าหน้าที่ที่แนะนำครับ",
        "language": "th", "intent_hint": "compliment",
        "brand_hint": "Dunlopillo", "product_hint": "Mattress", "channel_hint": "Official Store",
    },
    {
        "text": "สั่งชุดเครื่องนอน Midas จาก Lazada ครับ ยังไม่ได้รับสินค้าเลย สั่งไปตั้ง 5 วันแล้ว",
        "language": "th", "intent_hint": "delivery_inquiry",
        "brand_hint": "Midas", "product_hint": "Bedding", "channel_hint": "Online",
    },
    {
        "text": "ซื้อหมอน Bedgear จากร้านตัวแทนจำหน่ายค่ะ อยากสอบถามวิธีดูแลรักษาหมอนค่ะ",
        "language": "th", "intent_hint": "product_inquiry",
        "brand_hint": "Bedgear", "product_hint": "Pillow", "channel_hint": "Dealer",
    },
    {
        "text": "โครงเตียง Zinus ที่สั่ง Online มาถึงแล้วแต่ชิ้นส่วนหักครับ ต้องการคืนเงิน",
        "language": "th", "intent_hint": "product_damage",
        "brand_hint": "Zinus", "product_hint": "Bed Frame", "channel_hint": "Online",
    },
    {
        "text": "สนใจโปรโมชั่นที่นอน Restonic ที่ห้าง The Mall ค่ะ เห็นว่าลดราคา อยากทราบรายละเอียด",
        "language": "th", "intent_hint": "promotion_inquiry",
        "brand_hint": "Restonic", "product_hint": "Mattress", "channel_hint": "Department Store",
    },
    {
        "text": "Topper LaLaBed ที่สั่งจาก TikTok Shop ยุบตัวเร็วมากครับ ใช้ได้สัปดาห์เดียว อยากขอเปลี่ยน",
        "language": "th", "intent_hint": "product_damage",
        "brand_hint": "LaLaBed", "product_hint": "Topper", "channel_hint": "Online",
    },
    {
        "text": "สอบถามเรื่องรับประกันที่นอน Eastman House ที่ซื้อจากหน้าร้านครับ รับประกันกี่ปี",
        "language": "th", "intent_hint": "warranty_inquiry",
        "brand_hint": "Eastman House", "product_hint": "Mattress", "channel_hint": "Official Store",
    },
    {
        "text": "ซื้อผ้ารองกันเปื้อน Malouf จาก Shopee ค่ะ อยากทราบวิธีซักที่ถูกต้อง",
        "language": "th", "intent_hint": "product_inquiry",
        "brand_hint": "Malouf", "product_hint": "Protector", "channel_hint": "Online",
    },
    {
        "text": "เตียง Woodfield ที่ซื้อจากตัวแทนจำหน่ายครับ สีไม่ตรงตามที่สั่ง ต้องการเปลี่ยน",
        "language": "th", "intent_hint": "product_damage",
        "brand_hint": "Woodfield", "product_hint": "Bed Frame", "channel_hint": "Dealer",
    },
    {
        "text": "ชุดเครื่องนอน Loto mobili ที่ซื้อจาก Robinson ค่ะ ขอเปลี่ยนไซส์จาก 5 ฟุตเป็น 6 ฟุต",
        "language": "th", "intent_hint": "exchange_request",
        "brand_hint": "Loto mobili", "product_hint": "Bedding", "channel_hint": "Department Store",
    },
    {
        "text": "ผมโทรมาสอบถามทั่วไปครับ ไม่ได้ระบุตัวสินค้า แค่อยากรู้เงื่อนไขรับประกันทั่วไป",
        "language": "th", "intent_hint": "general_inquiry",
        "brand_hint": None, "product_hint": None, "channel_hint": None,
    },
]

# Intent Map
_INTENT_MAP = {
    "product_inquiry":   {"label": "สอบถามข้อมูลสินค้า",    "category": "inquiry"},
    "product_damage":    {"label": "แจ้งสินค้าชำรุด/เสียหาย", "category": "complaint"},
    "delivery_inquiry":  {"label": "สอบถามสถานะจัดส่ง",      "category": "inquiry"},
    "promotion_inquiry": {"label": "สอบถามโปรโมชั่น",        "category": "sales"},
    "warranty_inquiry":  {"label": "สอบถามการรับประกัน",      "category": "inquiry"},
    "exchange_request":  {"label": "ขอเปลี่ยนสินค้า",        "category": "service"},
    "compliment":        {"label": "ชมเชยเจ้าหน้าที่/สินค้า", "category": "feedback"},
    "general_inquiry":   {"label": "สอบถามทั่วไป",           "category": "inquiry"},
    "cancellation":      {"label": "ขอยกเลิก/คืนสินค้า",     "category": "retention"},
}

# QA Criteria
_QA_CRITERIA = [
    "การทักทายและแนะนำตัว",
    "การรับฟังและทำความเข้าใจปัญหา",
    "ความถูกต้องของข้อมูลที่ให้",
    "การเสนอทางแก้ไขที่เหมาะสม",
    "การยืนยันความพึงพอใจก่อนวางสาย",
    "ความสุภาพและมืออาชีพตลอดการสนทนา",
]


# =============================================================================
# STEP 2: Brand / Product / Channel Detection (จำลอง NER)
# =============================================================================
# keyword matching เพื่อจำลอง Named Entity Recognition
# ในระบบจริง Llama 3.3 จะทำ NER ได้เองโดยไม่ต้อง keyword

_BRAND_KEYWORDS = {
    "Lotus":         ["lotus", "โลตัส"],
    "Omazz":         ["omazz", "โอแมส"],
    "Midas":         ["midas", "ไมดาส"],
    "Dunlopillo":    ["dunlopillo", "ดันล็อปปิลโล", "ดันล็อป"],
    "Bedgear":       ["bedgear", "เบดเกียร์"],
    "LaLaBed":       ["lalabed", "ลาล่าเบด"],
    "Zinus":         ["zinus", "ซีนัส"],
    "Eastman House": ["eastman house", "eastman", "อีสต์แมน"],
    "Malouf":        ["malouf", "มาลูฟ"],
    "Loto mobili":   ["loto mobili", "loto", "โลโต้"],
    "Woodfield":     ["woodfield", "วู้ดฟิลด์"],
    "Restonic":      ["restonic", "เรสโตนิค"],
}

_PRODUCT_KEYWORDS = {
    "Mattress":   ["ที่นอน", "mattress", "ฟูก"],
    "Pillow":     ["หมอน", "pillow"],
    "Bedding":    ["เครื่องนอน", "bedding", "ผ้าปู", "ผ้านวม", "ชุดเครื่องนอน", "ปลอกหมอน"],
    "Topper":     ["topper", "ท็อปเปอร์", "แผ่นรองนอน"],
    "Bed Frame":  ["เตียง", "bed frame", "โครงเตียง", "หัวเตียง"],
    "Protector":  ["protector", "ผ้ารองกันเปื้อน", "แผ่นกันเปื้อน", "กันไรฝุ่น", "ผ้ารอง"],
}

_CHANNEL_KEYWORDS = {
    "Official Store":   ["official", "หน้าร้าน", "สาขา", "ร้านแบรนด์"],
    "Online":           ["shopee", "lazada", "online", "ออนไลน์", "tiktok", "jd central", "สั่ง online"],
    "Department Store": ["ห้าง", "central", "the mall", "robinson", "เซ็นทรัล", "เดอะมอลล์", "โรบินสัน", "ห้างสรรพสินค้า"],
    "Dealer":           ["ตัวแทน", "dealer", "ร้านค้าปลีก", "ร้านตัวแทน", "จำหน่าย"],
}


def _detect_brand(transcript: str, brand_hint: Optional[str] = None) -> str:
    """สกัดชื่อแบรนด์ — ใช้ hint ก่อน, fallback keyword matching"""
    if brand_hint:
        return brand_hint
    text_lower = transcript.lower()
    for name, keywords in _BRAND_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return name
    return "Unknown"


def _detect_product(transcript: str, product_hint: Optional[str] = None) -> str:
    """สกัดหมวดสินค้า — ใช้ hint ก่อน, fallback keyword matching"""
    if product_hint:
        return product_hint
    text_lower = transcript.lower()
    for name, keywords in _PRODUCT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return name
    return "Unknown"


def _detect_channel(transcript: str, channel_hint: Optional[str] = None) -> str:
    """สกัดช่องทางซื้อ — ใช้ hint ก่อน, fallback keyword matching"""
    if channel_hint:
        return channel_hint
    text_lower = transcript.lower()
    for name, keywords in _CHANNEL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return name
    return "Unknown"


# =============================================================================
# STEP 3: Mock Whisper — Speech-to-Text
# =============================================================================

async def mock_whisper_transcribe(file_id: str, audio_duration_seconds: Optional[float] = None) -> dict:
    if audio_duration_seconds is None:
        audio_duration_seconds = random.uniform(60, 300)

    processing_time = max(2.0, min(audio_duration_seconds * 0.3, 10.0))
    await asyncio.sleep(processing_time)

    sample = random.choice(_MOCK_TRANSCRIPTS)
    words = sample["text"].split()
    time_per_word = audio_duration_seconds / max(len(words), 1)

    return {
        "model": "whisper-large-v3",
        "status": "completed",
        "file_id": file_id,
        "transcript": sample["text"],
        "language_detected": sample["language"],
        "language_confidence": round(random.uniform(0.92, 0.99), 3),
        "audio_duration_seconds": round(audio_duration_seconds, 1),
        "processing_time_seconds": round(processing_time, 2),
        "word_count": len(words),
        "word_timestamps": [{"word": w, "start": round(i * time_per_word, 2), "end": round((i+1) * time_per_word, 2), "confidence": round(random.uniform(0.82, 0.99), 3)} for i, w in enumerate(words[:5])],
        "intent_hint": sample["intent_hint"],
        "brand_hint": sample.get("brand_hint"),
        "product_hint": sample.get("product_hint"),
        "channel_hint": sample.get("channel_hint"),
        "completed_at": datetime.now().isoformat(),
    }


# =============================================================================
# STEP 4: Mock Wav2Vec2 — Audio Sentiment
# =============================================================================

async def mock_wav2vec2_sentiment(file_id: str, transcript: Optional[str] = None) -> dict:
    await asyncio.sleep(random.uniform(1.5, 4.0))

    if transcript:
        tl = transcript.lower()
        if any(w in tl for w in ["ขอบคุณ", "ชม", "ดีมาก", "พอใจ", "สบาย"]):
            dominant = "positive"
        elif any(w in tl for w in ["ชำรุด", "เสีย", "ปัญหา", "ยกเลิก", "ช้า", "หัก", "ยุบ", "คืนเงิน"]):
            dominant = "negative"
        else:
            dominant = random.choice(["neutral", "positive"])
    else:
        dominant = random.choice(["positive", "neutral", "negative"])

    if dominant == "positive":
        pos, neg = round(random.uniform(0.55, 0.85), 3), round(random.uniform(0.05, 0.20), 3)
    elif dominant == "negative":
        neg, pos = round(random.uniform(0.55, 0.85), 3), round(random.uniform(0.05, 0.15), 3)
    else:
        pos, neg = round(random.uniform(0.15, 0.30), 3), round(random.uniform(0.10, 0.25), 3)
    neu = round(1.0 - pos - neg, 3)

    return {
        "model": "wav2vec2-large-xlsr-sentiment", "status": "completed", "file_id": file_id,
        "sentiment": {"label": dominant, "scores": {"positive": pos, "neutral": neu, "negative": neg}, "confidence": max(pos, neu, neg)},
        "completed_at": datetime.now().isoformat(),
    }


# =============================================================================
# STEP 5: Mock Llama 3.3 — NLP + QA + Brand/Product/Channel Extraction
# =============================================================================

async def mock_llama_nlp_analysis(
    file_id: str, transcript: str, sentiment_label: str,
    intent_hint: Optional[str] = None,
    brand_hint: Optional[str] = None,
    product_hint: Optional[str] = None,
    channel_hint: Optional[str] = None,
) -> dict:
    await asyncio.sleep(random.uniform(3.0, 7.0))

    detected_intent = intent_hint or random.choice(list(_INTENT_MAP.keys()))
    intent_info = _INTENT_MAP.get(detected_intent, _INTENT_MAP["general_inquiry"])

    # Entity Extraction
    entities = []
    extracted_brand = _detect_brand(transcript, brand_hint)
    extracted_product = _detect_product(transcript, product_hint)
    extracted_channel = _detect_channel(transcript, channel_hint)

    if extracted_brand != "Unknown":
        entities.append({"type": "BRAND", "value": extracted_brand, "confidence": round(random.uniform(0.85, 0.98), 3)})
    if extracted_product != "Unknown":
        entities.append({"type": "PRODUCT", "value": extracted_product, "confidence": round(random.uniform(0.80, 0.96), 3)})
    if extracted_channel != "Unknown":
        entities.append({"type": "SALE_CHANNEL", "value": extracted_channel, "confidence": round(random.uniform(0.82, 0.95), 3)})

    # QA Scoring
    base_score = {"positive": random.uniform(7.5, 10.0), "neutral": random.uniform(5.5, 8.0), "negative": random.uniform(3.0, 6.5)}.get(sentiment_label, random.uniform(5.0, 8.0))
    criteria_scores = {c: round(max(0.0, min(10.0, base_score + random.uniform(-1.5, 1.5))), 1) for c in _QA_CRITERIA}
    final_qa = round(sum(criteria_scores.values()) / len(criteria_scores), 2)

    # CSAT
    csat = 5 if final_qa >= 8.5 else 4 if final_qa >= 7.0 else 3 if final_qa >= 5.5 else 2 if final_qa >= 4.0 else 1

    # Summary
    b_str = f" {extracted_brand}" if extracted_brand != "Unknown" else ""
    p_str = f" ({extracted_product})" if extracted_product != "Unknown" else ""
    c_str = f" ซื้อจาก {extracted_channel}" if extracted_channel != "Unknown" else ""
    sent_th = {"positive": "พึงพอใจ", "neutral": "เป็นกลาง", "negative": "ไม่พึงพอใจ"}.get(sentiment_label, "ไม่ทราบ")
    summary = f"ลูกค้าติดต่อเรื่อง{p_str}{b_str}{c_str} — {intent_info['label']} ลูกค้ารู้สึก{sent_th}"

    # Action Items
    actions = []
    if sentiment_label == "negative": actions.append("🔴 ติดตามลูกค้าภายใน 24 ชั่วโมง")
    if detected_intent == "cancellation": actions.append("⚠️ ส่งต่อทีม Retention")
    if final_qa < 6.0: actions.append("📋 แจ้ง Supervisor ตรวจสอบคุณภาพ")
    if not actions: actions.append("✅ ปิดเคสได้")

    return {
        "model": "llama-3.3-70b-instruct", "status": "completed", "file_id": file_id,
        "intent": {"detected": detected_intent, "label_th": intent_info["label"], "category": intent_info["category"], "confidence": round(random.uniform(0.78, 0.97), 3)},
        "entities": entities,
        "qa_scoring": {"final_score": final_qa, "max_score": 10.0, "grade": _score_to_grade(final_qa), "criteria_breakdown": criteria_scores},
        "csat_predicted": csat, "summary": summary, "action_items": actions,
        "keywords_extracted": _extract_keywords(transcript),
        "brand_name": extracted_brand,
        "product_category": extracted_product,
        "sale_channel": extracted_channel,
        "completed_at": datetime.now().isoformat(),
    }


# =============================================================================
# STEP 6: Full Pipeline
# =============================================================================

async def run_full_analysis_pipeline(file_id: str, audio_duration_seconds: Optional[float] = None, on_step_complete=None) -> dict:
    pipeline_start = datetime.now()

    whisper_result, wav2vec_result = await asyncio.gather(
        mock_whisper_transcribe(file_id, audio_duration_seconds),
        mock_wav2vec2_sentiment(file_id),
    )
    if on_step_complete:
        await on_step_complete("whisper_wav2vec2", {"whisper": whisper_result, "wav2vec2": wav2vec_result})

    llama_result = await mock_llama_nlp_analysis(
        file_id=file_id, transcript=whisper_result["transcript"],
        sentiment_label=wav2vec_result["sentiment"]["label"],
        intent_hint=whisper_result.get("intent_hint"),
        brand_hint=whisper_result.get("brand_hint"),
        product_hint=whisper_result.get("product_hint"),
        channel_hint=whisper_result.get("channel_hint"),
    )
    if on_step_complete:
        await on_step_complete("llama", llama_result)

    return {
        "file_id": file_id, "pipeline_status": "completed",
        "pipeline_duration_seconds": round((datetime.now() - pipeline_start).total_seconds(), 2),
        "completed_at": datetime.now().isoformat(),
        "summary": {
            "transcript": whisper_result["transcript"],
            "language": whisper_result["language_detected"],
            "sentiment": wav2vec_result["sentiment"]["label"],
            "sentiment_confidence": wav2vec_result["sentiment"]["confidence"],
            "intent": llama_result["intent"]["label_th"],
            "qa_score": llama_result["qa_scoring"]["final_score"],
            "qa_grade": llama_result["qa_scoring"]["grade"],
            "csat_predicted": llama_result["csat_predicted"],
            "summary_text": llama_result["summary"],
            "action_items": llama_result["action_items"],
            "brand_name": llama_result["brand_name"],
            "product_category": llama_result["product_category"],
            "sale_channel": llama_result["sale_channel"],
        },
        "model_results": {"whisper": whisper_result, "wav2vec2": wav2vec_result, "llama": llama_result},
    }


# =============================================================================
# Helpers
# =============================================================================

def _score_to_grade(s):
    if s >= 9.0: return "A+ (ยอดเยี่ยม)"
    if s >= 8.0: return "A  (ดีมาก)"
    if s >= 7.0: return "B  (ดี)"
    if s >= 6.0: return "C  (พอใช้)"
    if s >= 5.0: return "D  (ต้องปรับปรุง)"
    return "F  (ต่ำกว่ามาตรฐาน)"

def _extract_keywords(text):
    pool = ["ที่นอน", "หมอน", "เครื่องนอน", "เตียง", "Topper", "Protector",
            "ปัญหา", "ชำรุด", "คืนสินค้า", "โปรโมชั่น", "รับประกัน", "จัดส่ง",
            "Shopee", "Lazada", "Central", "Official", "ตัวแทน",
            "Lotus", "Omazz", "Dunlopillo", "Midas", "Bedgear", "Restonic", "Zinus"]
    found = [kw for kw in pool if kw.lower() in text.lower()]
    return found if found else random.sample(pool, 3)
