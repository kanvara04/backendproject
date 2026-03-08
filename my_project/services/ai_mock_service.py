# =============================================================================
# services/ai_mock_service.py
# Mock AI Service — จำลองการทำงานของ AI Models 3 ตัว
#
# อธิบาย: ในขณะที่ยังไม่มี GPU Server หรือ Model จริง เราจำลองผลลัพธ์
# ด้วย asyncio.sleep() เพื่อให้ระบบ Backend ทำงานได้ครบถ้วนก่อน
#
# AI Models ที่จำลอง:
#   1. Whisper      → Speech-to-Text (แปลงเสียงเป็นข้อความ)
#   2. Wav2Vec2     → Audio Sentiment (วิเคราะห์อารมณ์จากเสียงโดยตรง)
#   3. Llama 3.3    → NLP / QA Scoring (วิเคราะห์ข้อความ, ให้คะแนน QA)
# =============================================================================

import asyncio
import random
import re
from datetime import datetime
from typing import Optional


# =============================================================================
# STEP 1: ชุดข้อมูลจำลอง (Mock Datasets)
# =============================================================================
# ข้อมูลเหล่านี้จะถูกสุ่มเลือกเพื่อสร้าง Mock Result ที่ดูสมจริง
# =============================================================================

# ตัวอย่างบทสนทนา Call Center ที่ Whisper อาจถอดเสียงได้
_MOCK_TRANSCRIPTS = [
    {
        "text": (
            "สวัสดีครับ ผมโทรมาสอบถามเรื่องค่าบริการรายเดือนครับ "
            "เดือนนี้ผมสังเกตว่ายอดสูงขึ้นผิดปกติ "
            "อยากทราบว่ามีการเปลี่ยนแปลงอะไรหรือเปล่าครับ"
        ),
        "language": "th",
        "intent_hint": "billing_inquiry",
    },
    {
        "text": (
            "หนูโทรมาแจ้งว่าสินค้าที่สั่งซื้อไปเมื่อสัปดาห์ที่แล้ว "
            "ได้รับมาแล้วแต่ชำรุดค่ะ กล่องบุบและตัวสินค้ามีรอยร้าว "
            "อยากขอเปลี่ยนสินค้าใหม่ค่ะ"
        ),
        "language": "th",
        "intent_hint": "product_damage",
    },
    {
        "text": (
            "ผมอยากยกเลิกการสมัครสมาชิกครับ ใช้งานมาสักพักแล้ว "
            "รู้สึกว่าไม่คุ้มกับราคาที่จ่ายไป "
            "ขอทราบขั้นตอนการยกเลิกหน่อยได้ไหมครับ"
        ),
        "language": "th",
        "intent_hint": "cancellation",
    },
    {
        "text": (
            "สวัสดีค่ะ หนูโทรมาขอบคุณเจ้าหน้าที่ที่ช่วยแก้ปัญหาให้เมื่อวานค่ะ "
            "แก้ได้เร็วมากและบริการดีมากๆ เลยอยากโทรมาชมค่ะ"
        ),
        "language": "th",
        "intent_hint": "compliment",
    },
    {
        "text": (
            "ผมมีปัญหาเรื่อง Internet ช้ามากครับ ใช้งานไม่ได้เลย "
            "ลองรีสตาร์ท Router แล้วยังไม่ดีขึ้น "
            "ช่วยส่งช่างมาตรวจสอบได้ไหมครับ"
        ),
        "language": "th",
        "intent_hint": "technical_support",
    },
]

# Intent Categories ที่ระบบรองรับ
_INTENT_MAP = {
    "billing_inquiry":  {"label": "สอบถามค่าบริการ/ใบแจ้งหนี้", "category": "billing"},
    "product_damage":   {"label": "แจ้งสินค้าชำรุด/เสียหาย",    "category": "complaint"},
    "cancellation":     {"label": "ขอยกเลิกบริการ",              "category": "retention"},
    "compliment":       {"label": "ชมเชยเจ้าหน้าที่/บริการ",     "category": "feedback"},
    "technical_support":{"label": "แจ้งปัญหาด้านเทคนิค",         "category": "support"},
}

# QA Criteria ที่ใช้ประเมิน (Llama จะ "ตรวจ" เหล่านี้)
_QA_CRITERIA = [
    "การทักทายและแนะนำตัว",
    "การรับฟังและทำความเข้าใจปัญหา",
    "ความถูกต้องของข้อมูลที่ให้",
    "การเสนอทางแก้ไขที่เหมาะสม",
    "การยืนยันความพึงพอใจก่อนวางสาย",
    "ความสุภาพและมืออาชีพตลอดการสนทนา",
]


# =============================================================================
# STEP 2: Mock Whisper — Speech-to-Text
# =============================================================================
# Whisper จริงๆ รับ audio file → คืน text transcript
# Mock นี้: sleep() จำลองเวลาประมวลผล → คืน transcript สุ่ม
#
# เวลาจริง: Whisper large-v3 ใช้เวลาประมาณ 1x ของความยาวไฟล์เสียง
# (ไฟล์ 4 นาที ใช้เวลาประมาณ 4 นาที บน CPU, ~20 วินาทีบน GPU)
# =============================================================================

async def mock_whisper_transcribe(
    file_id: str,
    audio_duration_seconds: Optional[float] = None,
) -> dict:
    """
    จำลองการทำงานของ OpenAI Whisper (Speech-to-Text)
    
    Whisper จริง:
      from faster_whisper import WhisperModel
      model = WhisperModel("large-v3")
      segments, info = model.transcribe("audio.wav")
    
    Args:
        file_id: ID ของไฟล์เสียง
        audio_duration_seconds: ความยาวเสียง (ถ้าไม่ระบุ จะสุ่ม 60-300 วินาที)
    
    Returns:
        dict: ผลการถอดเสียงพร้อม metadata
    """
    # จำลองความยาวเสียง
    if audio_duration_seconds is None:
        audio_duration_seconds = random.uniform(60, 300)

    # =========================================================================
    # asyncio.sleep() — หัวใจของ Async Processing
    # =========================================================================
    # sleep() จำลองเวลาที่ AI ใช้ประมวลผล
    # "async" sleep ไม่ Block เธรด — ระหว่างรอ server ยังรับ request อื่นได้
    # เวลา Mock: 0.3x ของความยาวเสียง (เร็วกว่า real Whisper มาก)
    processing_time = audio_duration_seconds * 0.3
    processing_time = max(2.0, min(processing_time, 10.0))  # clamp 2-10 วินาที
    await asyncio.sleep(processing_time)

    # สุ่มเลือก transcript จาก dataset
    transcript_sample = random.choice(_MOCK_TRANSCRIPTS)

    # สร้าง word-level timestamps (จำลอง)
    words = transcript_sample["text"].split()
    time_per_word = audio_duration_seconds / max(len(words), 1)
    word_timestamps = [
        {
            "word": word,
            "start": round(i * time_per_word, 2),
            "end": round((i + 1) * time_per_word, 2),
            "confidence": round(random.uniform(0.82, 0.99), 3),
        }
        for i, word in enumerate(words)
    ]

    return {
        "model": "whisper-large-v3",
        "status": "completed",
        "file_id": file_id,
        "transcript": transcript_sample["text"],
        "language_detected": transcript_sample["language"],
        "language_confidence": round(random.uniform(0.92, 0.99), 3),
        "audio_duration_seconds": round(audio_duration_seconds, 1),
        "processing_time_seconds": round(processing_time, 2),
        "word_count": len(words),
        "word_timestamps": word_timestamps[:5],  # แสดงแค่ 5 คำแรก (ประหยัด payload)
        "intent_hint": transcript_sample["intent_hint"],  # ส่งต่อให้ NLP ต่อไป
        "completed_at": datetime.now().isoformat(),
    }


# =============================================================================
# STEP 3: Mock Wav2Vec2 — Audio Sentiment Analysis
# =============================================================================
# Wav2Vec2 จริงๆ วิเคราะห์ "โทนเสียง" โดยตรง ไม่ต้องแปลงเป็น text ก่อน
# ทำให้จับ emotion ได้แม้แต่เสียงที่ถอดความไม่ออก เช่น เสียงร้องไห้, เสียงโกรธ
#
# ข้อดีของ Wav2Vec2:
#   - วิเคราะห์ Prosody (จังหวะ, น้ำเสียง, ความดัง)
#   - จับ emotion จาก paraverbal cues
#   - ไม่ขึ้นกับภาษา (ใช้ได้กับทุกภาษา)
# =============================================================================

async def mock_wav2vec2_sentiment(
    file_id: str,
    transcript: Optional[str] = None,
) -> dict:
    """
    จำลองการทำงานของ Wav2Vec2 (Audio Emotion/Sentiment Analysis)
    
    Wav2Vec2 จริง:
      from transformers import pipeline
      classifier = pipeline("audio-classification", model="ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition")
      result = classifier("audio.wav")
    
    Args:
        file_id: ID ของไฟล์เสียง
        transcript: ข้อความจาก Whisper (ช่วย bias sentiment ให้สมเหตุสมผล)
    
    Returns:
        dict: ผลการวิเคราะห์อารมณ์พร้อม confidence scores
    """
    # Wav2Vec2 เร็วกว่า Whisper เพราะไม่ต้อง decode audio เป็น text
    await asyncio.sleep(random.uniform(1.5, 4.0))

    # กำหนด sentiment distribution ตาม transcript hint
    # (ในระบบจริง ค่านี้มาจากโมเดล โดยไม่ต้องใช้ rule-based)
    if transcript:
        text_lower = transcript.lower()
        if any(w in text_lower for w in ["ขอบคุณ", "ชม", "ดีมาก", "พอใจ"]):
            dominant = "positive"
        elif any(w in text_lower for w in ["ชำรุด", "เสีย", "ปัญหา", "ยกเลิก", "ช้า"]):
            dominant = "negative"
        else:
            dominant = random.choice(["neutral", "positive", "negative"])
    else:
        dominant = random.choice(["positive", "neutral", "negative"])

    # สร้าง probability distribution ที่รวมกัน = 1.0
    if dominant == "positive":
        pos = round(random.uniform(0.55, 0.85), 3)
        neg = round(random.uniform(0.05, 0.20), 3)
        neu = round(1.0 - pos - neg, 3)
    elif dominant == "negative":
        neg = round(random.uniform(0.55, 0.85), 3)
        pos = round(random.uniform(0.05, 0.15), 3)
        neu = round(1.0 - neg - pos, 3)
    else:  # neutral
        neu = round(random.uniform(0.45, 0.70), 3)
        pos = round(random.uniform(0.15, 0.30), 3)
        neg = round(1.0 - neu - pos, 3)

    # Emotion breakdown (ละเอียดกว่า sentiment ทั่วไป)
    emotion_scores = {
        "anger":    round(neg * random.uniform(0.3, 0.7), 3),
        "sadness":  round(neg * random.uniform(0.1, 0.4), 3),
        "fear":     round(neg * random.uniform(0.05, 0.2), 3),
        "joy":      round(pos * random.uniform(0.5, 0.9), 3),
        "surprise": round(random.uniform(0.02, 0.1), 3),
        "neutral":  round(neu, 3),
    }

    # Vocal features ที่ Wav2Vec2 สกัดได้จาก audio waveform
    vocal_features = {
        "speech_rate_wpm":    round(random.uniform(100, 200), 1),   # คำต่อนาที
        "avg_pitch_hz":       round(random.uniform(85, 255), 1),    # ความถี่เสียง
        "pitch_variance":     round(random.uniform(10, 80), 2),     # ความผันผวน
        "energy_level":       round(random.uniform(0.3, 0.9), 3),   # ความดัง
        "speaking_ratio":     round(random.uniform(0.55, 0.85), 3), # สัดส่วนที่พูด vs เงียบ
        "pause_count":        random.randint(3, 20),                 # จำนวนหยุด
    }

    return {
        "model": "wav2vec2-large-xlsr-sentiment",
        "status": "completed",
        "file_id": file_id,
        "sentiment": {
            "label": dominant,
            "scores": {
                "positive": pos,
                "neutral":  neu,
                "negative": neg,
            },
            "confidence": max(pos, neu, neg),
        },
        "emotions": emotion_scores,
        "vocal_features": vocal_features,
        "analysis_note": "วิเคราะห์จาก audio waveform โดยตรง (ไม่ขึ้นกับ transcript)",
        "completed_at": datetime.now().isoformat(),
    }


# =============================================================================
# STEP 4: Mock Llama 3.3 — NLP Analysis + QA Scoring
# =============================================================================
# Llama 3.3 จริงๆ รับ transcript → วิเคราะห์เชิง NLP ขั้นสูง
# งานที่ทำ: Intent Classification, Entity Extraction, QA Scoring, Summary
#
# ทำไมใช้ Llama แทน rule-based?
#   - เข้าใจบริบทได้ดีกว่า (context-aware)
#   - รองรับภาษาไทยโดยธรรมชาติ
#   - ให้คำอธิบายได้ (explainable scoring)
# =============================================================================

async def mock_llama_nlp_analysis(
    file_id: str,
    transcript: str,
    sentiment_label: str,
    intent_hint: Optional[str] = None,
) -> dict:
    """
    จำลองการทำงานของ Llama 3.3 (NLP Analysis + QA Scoring)
    
    Llama 3.3 จริง (via Ollama):
      import ollama
      response = ollama.chat(model="llama3.3", messages=[{
          "role": "user",
          "content": f"วิเคราะห์บทสนทนา Call Center นี้: {transcript}"
      }])
    
    Args:
        file_id: ID ของไฟล์
        transcript: ข้อความถอดเสียงจาก Whisper
        sentiment_label: ผล sentiment จาก Wav2Vec2
        intent_hint: คำใบ้ intent จาก Whisper
    
    Returns:
        dict: ผลการวิเคราะห์ NLP + คะแนน QA + สรุปการสนทนา
    """
    # LLM ใช้เวลานานสุด เพราะต้อง generate text
    await asyncio.sleep(random.uniform(3.0, 7.0))

    # --- Intent Detection ---
    detected_intent = intent_hint or random.choice(list(_INTENT_MAP.keys()))
    intent_info = _INTENT_MAP[detected_intent]

    # --- Entity Extraction (Named Entity Recognition) ---
    # จำลองการดึง entities สำคัญออกจาก transcript
    entities = []
    if "บิล" in transcript or "ค่าบริการ" in transcript:
        entities.append({"type": "ISSUE_TYPE", "value": "ค่าบริการ/บิล", "confidence": 0.94})
    if "สินค้า" in transcript or "ชำรุด" in transcript:
        entities.append({"type": "ISSUE_TYPE", "value": "สินค้าชำรุด", "confidence": 0.91})
    if "ยกเลิก" in transcript:
        entities.append({"type": "ACTION_REQUEST", "value": "ยกเลิกบริการ", "confidence": 0.96})
    if not entities:
        entities.append({"type": "ISSUE_TYPE", "value": "ปัญหาทั่วไป", "confidence": 0.75})

    # --- QA Scoring (คะแนน 0-10) ---
    # สร้างคะแนนที่สัมพันธ์กับ sentiment
    # (ในระบบจริง Llama จะ evaluate จาก transcript โดยตรง)
    base_score = {
        "positive": random.uniform(7.5, 10.0),
        "neutral":  random.uniform(5.5, 8.0),
        "negative": random.uniform(3.0, 6.5),
    }.get(sentiment_label, random.uniform(5.0, 8.0))

    # คะแนนแต่ละ criteria
    criteria_scores = {}
    for criterion in _QA_CRITERIA:
        # สุ่มคะแนนรอบๆ base_score
        score = base_score + random.uniform(-1.5, 1.5)
        criteria_scores[criterion] = round(max(0.0, min(10.0, score)), 1)

    final_qa_score = round(sum(criteria_scores.values()) / len(criteria_scores), 2)

    # --- CSAT Prediction (1-5) ---
    # แปลง QA Score เป็น CSAT prediction
    if final_qa_score >= 8.5:
        csat_predicted = 5
    elif final_qa_score >= 7.0:
        csat_predicted = 4
    elif final_qa_score >= 5.5:
        csat_predicted = 3
    elif final_qa_score >= 4.0:
        csat_predicted = 2
    else:
        csat_predicted = 1

    # --- AI Summary (จำลองการ generate ของ LLM) ---
    summary_templates = {
        "billing_inquiry":  f"ลูกค้าสอบถามเรื่องค่าบริการที่เปลี่ยนแปลง เจ้าหน้าที่อธิบายรายละเอียดและเสนอโปรโมชั่น ลูกค้ารู้สึก{_sentiment_to_th(sentiment_label)}",
        "product_damage":   f"ลูกค้าแจ้งสินค้าชำรุด เจ้าหน้าที่รับเรื่องและดำเนินการเปลี่ยนสินค้า ลูกค้ารู้สึก{_sentiment_to_th(sentiment_label)}",
        "cancellation":     f"ลูกค้าต้องการยกเลิกบริการ เจ้าหน้าที่พยายาม retain ด้วยการเสนอโปรโมชั่น ลูกค้ารู้สึก{_sentiment_to_th(sentiment_label)}",
        "compliment":       f"ลูกค้าโทรมาชมเชยการบริการ แสดงความพึงพอใจสูง เจ้าหน้าที่ขอบคุณและบันทึกคำชม",
        "technical_support":f"ลูกค้าแจ้งปัญหาด้านเทคนิค เจ้าหน้าที่ troubleshoot และนัดช่างเข้าตรวจสอบ ลูกค้ารู้สึก{_sentiment_to_th(sentiment_label)}",
    }
    summary = summary_templates.get(detected_intent, f"ลูกค้าติดต่อสอบถามปัญหาทั่วไป เจ้าหน้าที่ให้ความช่วยเหลือ ลูกค้ารู้สึก{_sentiment_to_th(sentiment_label)}")

    # --- Key Issues & Action Items ---
    action_items = []
    if sentiment_label == "negative":
        action_items.append("🔴 ติดตามลูกค้าภายใน 24 ชั่วโมง")
    if detected_intent == "cancellation":
        action_items.append("⚠️ ส่งต่อทีม Retention ดำเนินการ")
    if final_qa_score < 6.0:
        action_items.append("📋 แจ้ง Supervisor ตรวจสอบคุณภาพการบริการ")
    if not action_items:
        action_items.append("✅ ไม่มี Action พิเศษ — ปิดเคสได้")

    return {
        "model": "llama-3.3-70b-instruct",
        "status": "completed",
        "file_id": file_id,
        "intent": {
            "detected": detected_intent,
            "label_th": intent_info["label"],
            "category": intent_info["category"],
            "confidence": round(random.uniform(0.78, 0.97), 3),
        },
        "entities": entities,
        "qa_scoring": {
            "final_score": final_qa_score,
            "max_score": 10.0,
            "grade": _score_to_grade(final_qa_score),
            "criteria_breakdown": criteria_scores,
        },
        "csat_predicted": csat_predicted,
        "summary": summary,
        "action_items": action_items,
        "keywords_extracted": _extract_keywords(transcript),
        "completed_at": datetime.now().isoformat(),
    }


# =============================================================================
# STEP 5: Pipeline รวม — รันทั้ง 3 โมเดลต่อเนื่องกัน
# =============================================================================
# Pipeline นี้เรียกใช้ทั้ง Whisper → Wav2Vec2 → Llama ตามลำดับ
# ทำไมไม่รันพร้อมกัน (parallel)?
#   - Wav2Vec2 ต้องการ audio file (ไม่ขึ้นกับ Whisper → รัน parallel ได้)
#   - Llama ต้องการ transcript จาก Whisper → ต้องรอ Whisper เสร็จก่อน
#
# Optimal Pipeline:
#   Whisper ─┬──────────────────── Llama (รอ transcript)
#   Wav2Vec2 ─┘ (รันพร้อม Whisper)
# =============================================================================

async def run_full_analysis_pipeline(
    file_id: str,
    audio_duration_seconds: Optional[float] = None,
    on_step_complete=None,  # Callback เมื่อแต่ละ step เสร็จ
) -> dict:
    """
    รัน AI Pipeline ทั้งหมด: Whisper + Wav2Vec2 → Llama
    
    ขั้นตอน:
    1. รัน Whisper และ Wav2Vec2 พร้อมกัน (asyncio.gather)
    2. รัน Llama หลังจากได้ transcript จาก Whisper
    3. รวมผลทั้งหมดเป็น final result
    
    Args:
        file_id: ID ของไฟล์ที่วิเคราะห์
        audio_duration_seconds: ความยาวเสียง
        on_step_complete: async callback function รับ (step_name, result)
    """
    pipeline_start = datetime.now()

    # =========================================================================
    # PHASE 1: Whisper + Wav2Vec2 รันพร้อมกัน
    # =========================================================================
    # asyncio.gather() = รัน coroutines หลายตัวพร้อมกัน (concurrent)
    # ประหยัดเวลา: ถ้าแต่ละตัวใช้ 5 วินาที รัน 2 ตัวพร้อมกันใช้เวลา ~5 วินาที
    # (ไม่ใช่ 10 วินาที ถ้ารันทีละตัว)
    whisper_result, wav2vec_result = await asyncio.gather(
        mock_whisper_transcribe(file_id, audio_duration_seconds),
        mock_wav2vec2_sentiment(file_id),
    )

    # แจ้ง callback ว่า Phase 1 เสร็จ (ถ้ามี)
    if on_step_complete:
        await on_step_complete("whisper_wav2vec2", {
            "whisper": whisper_result,
            "wav2vec2": wav2vec_result,
        })

    # =========================================================================
    # PHASE 2: Llama — ต้องรอ transcript จาก Whisper
    # =========================================================================
    llama_result = await mock_llama_nlp_analysis(
        file_id=file_id,
        transcript=whisper_result["transcript"],
        sentiment_label=wav2vec_result["sentiment"]["label"],
        intent_hint=whisper_result.get("intent_hint"),
    )

    if on_step_complete:
        await on_step_complete("llama", llama_result)

    # =========================================================================
    # PHASE 3: รวมผลลัพธ์ทั้งหมด
    # =========================================================================
    pipeline_duration = (datetime.now() - pipeline_start).total_seconds()

    return {
        "file_id": file_id,
        "pipeline_status": "completed",
        "pipeline_duration_seconds": round(pipeline_duration, 2),
        "completed_at": datetime.now().isoformat(),

        # ผลรวมสรุป (สำหรับแสดงใน Dashboard)
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
        },

        # ผลดิบจากแต่ละโมเดล
        "model_results": {
            "whisper": whisper_result,
            "wav2vec2": wav2vec_result,
            "llama": llama_result,
        },
    }


# =============================================================================
# STEP 6: Helper Functions
# =============================================================================

def _sentiment_to_th(sentiment: str) -> str:
    """แปลง sentiment label เป็นภาษาไทย"""
    return {"positive": "พึงพอใจ", "neutral": "เป็นกลาง", "negative": "ไม่พึงพอใจ"}.get(sentiment, "ไม่ทราบ")


def _score_to_grade(score: float) -> str:
    """แปลง QA Score เป็น Grade"""
    if score >= 9.0: return "A+ (ยอดเยี่ยม)"
    if score >= 8.0: return "A  (ดีมาก)"
    if score >= 7.0: return "B  (ดี)"
    if score >= 6.0: return "C  (พอใช้)"
    if score >= 5.0: return "D  (ต้องปรับปรุง)"
    return "F  (ต่ำกว่ามาตรฐาน)"


def _extract_keywords(text: str) -> list:
    """สกัด keywords จาก text (จำลอง)"""
    keyword_pool = [
        "ค่าบริการ", "สินค้า", "ปัญหา", "ยกเลิก", "ขอบคุณ",
        "บิล", "โปรโมชั่น", "เจ้าหน้าที่", "ช่าง", "อินเตอร์เน็ต",
    ]
    found = [kw for kw in keyword_pool if kw in text]
    return found if found else random.sample(keyword_pool, 2)
