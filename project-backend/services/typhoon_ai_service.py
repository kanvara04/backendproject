# =============================================================================
# services/typhoon_ai_service.py — v1.0.0
# Real AI Service — Typhoon API (Audio STT + Typhoon v2 LLM)
#
# Typhoon Audio: ถอดเสียงเป็นข้อความ (Speech-to-Text) — รองรับ Chunking ไฟล์ยาว
# Typhoon v2:    สรุปบทสนทนา + วิเคราะห์ Sentiment, Intent, Brand, Product, Channel
#
# Chunking: ไฟล์เสียง >5 นาที หรือ >24MB จะถูกตัดเป็น chunk ละ 5 นาที
#           ส่ง STT ทีละ chunk แล้วรวม transcript กลับเป็นอันเดียว
#
# ⚠️ ต้องตั้งค่า Environment Variable:
#   TYPHOON_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#
# ติดตั้ง:
#   pip install openai httpx
# =============================================================================

import os
import asyncio
import json
import re
import wave
import math
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List

try:
    from openai import OpenAI
    TYPHOON_AVAILABLE = True
except ImportError:
    TYPHOON_AVAILABLE = False
    print("⚠️ openai package not installed. Run: pip install openai")

# =============================================================================
# CONFIG
# =============================================================================

TYPHOON_BASE_URL  = "https://api.opentyphoon.ai/v1"
TYPHOON_STT_MODEL = "typhoon-audio-preview"          # Typhoon Audio STT model
TYPHOON_LLM_MODEL = "typhoon-v2-70b-instruct"        # Typhoon v2 LLM model

# =============================================================================
# ★ MULTI API KEY ROTATION — สลับ key อัตโนมัติเมื่อชน rate limit
# =============================================================================
# วิธีใช้: set environment variables แบบนี้
#   $env:TYPHOON_API_KEY="sk-key1"
#   $env:TYPHOON_API_KEY_2="sk-key2"
#   $env:TYPHOON_API_KEY_3="sk-key3"
#   (เพิ่มได้เรื่อยๆ: TYPHOON_API_KEY_4, TYPHOON_API_KEY_5, ...)
#
# หรือใส่หลาย key คั่นด้วย comma ใน TYPHOON_API_KEYS:
#   $env:TYPHOON_API_KEYS="sk-key1,sk-key2,sk-key3"
# =============================================================================

def _load_api_keys() -> list:
    """โหลด API keys ทั้งหมดจาก environment variables"""
    keys = []

    # วิธี 1: TYPHOON_API_KEYS (comma-separated)
    multi_keys = os.environ.get("TYPHOON_API_KEYS", "")
    if multi_keys:
        keys.extend([k.strip() for k in multi_keys.split(",") if k.strip()])

    # วิธี 2: TYPHOON_API_KEY, TYPHOON_API_KEY_2, TYPHOON_API_KEY_3, ...
    main_key = os.environ.get("TYPHOON_API_KEY", "")
    if main_key and main_key not in keys:
        keys.insert(0, main_key)

    for i in range(2, 20):  # รองรับสูงสุด 20 keys
        key = os.environ.get(f"TYPHOON_API_KEY_{i}", "")
        if key and key not in keys:
            keys.append(key)

    return keys


_ALL_API_KEYS = _load_api_keys()
_current_key_index = 0

if _ALL_API_KEYS:
    print(f"🔑 Loaded {len(_ALL_API_KEYS)} Typhoon API key(s)")
    for i, k in enumerate(_ALL_API_KEYS):
        print(f"   Key {i+1}: {k[:8]}...{k[-4:]}")
else:
    print("⚠️ No Typhoon API keys found! Set TYPHOON_API_KEY environment variable.")

TYPHOON_API_KEY = _ALL_API_KEYS[0] if _ALL_API_KEYS else ""


def _get_next_client() -> "OpenAI":
    """สร้าง OpenAI client (ชี้ไป Typhoon) โดยสลับ key แบบ round-robin"""
    global _current_key_index

    if not _ALL_API_KEYS:
        raise RuntimeError("No Typhoon API keys configured.")

    key = _ALL_API_KEYS[_current_key_index % len(_ALL_API_KEYS)]
    _current_key_index += 1

    key_num = ((_current_key_index - 1) % len(_ALL_API_KEYS)) + 1
    print(f"   🔑 Using Key {key_num}/{len(_ALL_API_KEYS)}: {key[:8]}...")

    return OpenAI(api_key=key, base_url=TYPHOON_BASE_URL)


# Chunking Config
TYPHOON_MAX_FILE_SIZE_MB = 24          # Limit ไฟล์ต่อ request = 24MB
CHUNK_DURATION_SECONDS   = 300         # ตัดทุก 5 นาที

# Delay ระหว่าง step (วินาที)
DELAY_BETWEEN_STEPS = 1


# =============================================================================
# RETRY HELPER — retry แบบเบา (สลับ key + รอสั้นๆ)
# =============================================================================

def _retry_on_rate_limit(func, *args, **kwargs):
    """เรียก function แล้ว retry ถ้าเจอ 429 (สลับ key + รอ 5 วินาที)"""
    import time
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            is_rate_limit = ("429" in error_str or "rate_limit" in error_str.lower()
                             or "Rate limit" in error_str)
            if is_rate_limit and attempt < max_retries:
                print(f"  ⏳ Rate limit (attempt {attempt}/{max_retries}), switching key & retry in 5s...")
                time.sleep(5)
            else:
                raise


# QA Criteria (ใช้ให้ Typhoon v2 ประเมิน)
QA_CRITERIA = [
    "การทักทายและแนะนำตัว",
    "การรับฟังและทำความเข้าใจปัญหา",
    "ความถูกต้องของข้อมูลที่ให้",
    "การเสนอทางแก้ไขที่เหมาะสม",
    "การยืนยันความพึงพอใจก่อนวางสาย",
    "ความสุภาพและมืออาชีพตลอดการสนทนา",
]


# =============================================================================
# LANGUAGE FILTER — เอาเฉพาะภาษาไทยกับอังกฤษ
# =============================================================================

_THAI_RANGE         = range(0x0E00, 0x0E7F + 1)
_ENGLISH_RANGE_UPPER = range(0x0041, 0x005A + 1)
_ENGLISH_RANGE_LOWER = range(0x0061, 0x007A + 1)
_DIGIT_RANGE        = range(0x0030, 0x0039 + 1)
_ALLOWED_SYMBOLS    = set(' .,!?;:\'"- ()[]{}@#$%&*+=/\\<>~`^_|฿๏๐๑๒๓๔๕๖๗๘๙\n\t')


def _is_thai_or_english_char(ch: str) -> bool:
    code = ord(ch)
    if code in _THAI_RANGE:
        return True
    if code in _ENGLISH_RANGE_UPPER or code in _ENGLISH_RANGE_LOWER:
        return True
    if code in _DIGIT_RANGE:
        return True
    if ch in _ALLOWED_SYMBOLS:
        return True
    return False


def _is_thai_or_english(text: str) -> bool:
    if not text.strip():
        return False
    countable = 0
    valid = 0
    for ch in text:
        if ch in _ALLOWED_SYMBOLS:
            continue
        code = ord(ch)
        if code in _DIGIT_RANGE:
            continue
        countable += 1
        if code in _THAI_RANGE or code in _ENGLISH_RANGE_UPPER or code in _ENGLISH_RANGE_LOWER:
            valid += 1
    if countable == 0:
        return True
    if countable < 3:
        return valid == countable
    return (valid / countable) >= 0.6


def _clean_foreign_text(text: str) -> str:
    """กรองคำแปลก/hallucination ออก"""
    words = text.split()
    cleaned_words = []
    for word in words:
        stripped = word.strip('.,!?;:\'"()-[]{}')
        if not stripped:
            cleaned_words.append(word)
            continue
        if stripped.lower() in _STT_HALLUCINATIONS:
            continue
        has_foreign  = False
        thai_count   = 0
        eng_count    = 0
        letter_count = 0
        for ch in stripped:
            if ch in _ALLOWED_SYMBOLS:
                continue
            code = ord(ch)
            if code in _DIGIT_RANGE:
                continue
            letter_count += 1
            if code in _THAI_RANGE:
                thai_count += 1
            elif code in _ENGLISH_RANGE_UPPER or code in _ENGLISH_RANGE_LOWER:
                eng_count += 1
            else:
                has_foreign = True
                break
        if has_foreign:
            continue
        if thai_count > 0:
            cleaned_words.append(word)
            continue
        if eng_count >= 3 and thai_count == 0:
            if stripped.lower() not in _ENGLISH_WHITELIST:
                continue
        cleaned_words.append(word)
    return " ".join(cleaned_words).strip()


# ★ คำอังกฤษที่อนุญาตให้ผ่าน
_ENGLISH_WHITELIST = {
    "lotus", "omazz", "midas", "dunlopillo", "bedgear", "lalabed",
    "zinus", "malouf", "woodfield", "restonic", "eastman", "house",
    "loto", "mobili",
    "mattress", "pillow", "bedding", "topper", "bed", "frame",
    "protector", "pocket", "spring", "coil", "latex", "memory", "foam",
    "king", "queen", "single", "size", "super", "firm", "soft", "medium",
    "panel", "cover", "sheet", "pad", "set",
    "call", "center", "line", "email", "website", "online", "offline",
    "order", "tracking", "delivery", "cancel", "refund", "return",
    "promotion", "sale", "discount", "warranty", "guarantee",
    "bill", "receipt", "invoice", "card", "credit", "debit", "transfer",
    "code", "number", "model", "type", "brand", "price",
    "service", "customer", "agent", "support",
    "yes", "yep", "nope", "okay",
    "central", "robinson", "lazada", "shopee", "homepro", "ikea",
    "facebook", "instagram", "tiktok", "google", "youtube",
    "express", "post", "flash", "kerry",
}

# STT Hallucination words (ภาษาต่างประเทศ + STT artifacts)
_STT_HALLUCINATIONS = {
    "merci", "bonjour", "bonsoir", "voilà", "très",
    "laisse", "laissez", "avec", "dans", "pour", "comme",
    "cette", "être", "avoir", "faire", "aller",
    "sont", "suis", "êtes", "sommes",
    "pourquoi", "quand", "comment",
    "mencionar", "entonces", "también",
    "passe", "tiem",
    "hola", "gracias", "buenos", "buenas", "señor", "señora",
    "favor", "está", "aquí", "puede", "tiene", "quiero",
    "gasido", "tantito", "los",
    "danke", "bitte", "guten", "morgen", "herr", "frau",
    "nicht", "auch", "noch", "schon",
    "lekker", "mae",
    "grazie", "buongiorno", "buonasera", "prego", "signore",
    "obrigado", "obrigada", "senhora", "ajuda",
    "subtitle", "subtitles", "subtítulos", "sous-titres",
    "subscribe", "subscribed", "subscription",
    "copyright", "reserved",
    "ethnicity", "contestant",
    "bastards", "bastard", "outro", "preview",
    "listing", "content", "clear", "please",
    "people", "ohio", "labor", "doing",
}


# =============================================================================
# AUDIO CHUNKING — ตัดไฟล์เสียงเป็นท่อนๆ สำหรับไฟล์ใหญ่
# =============================================================================

def _get_wav_info(audio_file_path: str) -> dict:
    try:
        with wave.open(audio_file_path, 'rb') as wf:
            return {
                "channels": wf.getnchannels(),
                "sample_width": wf.getsampwidth(),
                "frame_rate": wf.getframerate(),
                "n_frames": wf.getnframes(),
                "duration_seconds": wf.getnframes() / wf.getframerate(),
            }
    except wave.Error:
        file_size = os.path.getsize(audio_file_path)
        return {
            "channels": 1, "sample_width": 2, "frame_rate": 16000,
            "n_frames": 0, "duration_seconds": 0,
            "file_size_bytes": file_size, "is_non_wav": True,
        }


def _needs_chunking(audio_file_path: str) -> bool:
    file_size_mb = os.path.getsize(audio_file_path) / (1024 * 1024)
    if file_size_mb > TYPHOON_MAX_FILE_SIZE_MB:
        return True
    info = _get_wav_info(audio_file_path)
    if info.get("duration_seconds", 0) > CHUNK_DURATION_SECONDS:
        return True
    return False


def _split_wav_to_chunks(audio_file_path: str, chunk_seconds: int = CHUNK_DURATION_SECONDS) -> List[str]:
    chunk_paths = []
    try:
        with wave.open(audio_file_path, 'rb') as wf:
            channels     = wf.getnchannels()
            sample_width = wf.getsampwidth()
            frame_rate   = wf.getframerate()
            total_frames = wf.getnframes()
            frames_per_chunk = chunk_seconds * frame_rate
            num_chunks = math.ceil(total_frames / frames_per_chunk)
            for i in range(num_chunks):
                frames_to_read = min(frames_per_chunk, total_frames - (i * frames_per_chunk))
                audio_data = wf.readframes(frames_to_read)
                tmp = tempfile.NamedTemporaryFile(
                    suffix=f"_chunk{i:03d}.wav", delete=False, dir=tempfile.gettempdir()
                )
                with wave.open(tmp.name, 'wb') as chunk_wf:
                    chunk_wf.setnchannels(channels)
                    chunk_wf.setsampwidth(sample_width)
                    chunk_wf.setframerate(frame_rate)
                    chunk_wf.writeframes(audio_data)
                chunk_paths.append(tmp.name)
    except wave.Error:
        return [audio_file_path]
    return chunk_paths


def _cleanup_chunks(chunk_paths: List[str], original_path: str):
    for path in chunk_paths:
        if path != original_path:
            try:
                os.unlink(path)
            except OSError:
                pass


# =============================================================================
# STEP 1: Typhoon Audio — Speech-to-Text (with Chunking)
# =============================================================================

def _transcribe_single_file(file_path: str, time_offset: float = 0.0) -> dict:
    """
    ส่งไฟล์เดียวไปให้ Typhoon Audio API (sync function)

    Args:
        file_path:   path ไปยังไฟล์เสียง
        time_offset: offset เวลา (วินาที) สำหรับ chunk ที่ไม่ใช่ chunk แรก
    Returns:
        dict: { text, segments, duration, language }
    """
    with open(file_path, "rb") as f:
        audio_data = f.read()

    def _stt_call():
        c = _get_next_client()
        return c.audio.transcriptions.create(
            file=(Path(file_path).name, audio_data),
            model=TYPHOON_STT_MODEL,
            response_format="verbose_json",
            language="th",
            temperature=0.0,
            prompt=(
                "สวัสดีครับ สวัสดีค่ะ ฮัลโหลครับ ขอบคุณที่โทรมาครับ ได้ค่ะ ได้ครับ "
                "รบกวนด้วยค่ะ ที่นอน หมอน ผ้าปูที่นอน ท็อปเปอร์ ผ้าห่ม โลตัส โอมาซ "
                "ไมดาส เบดเกียร์ ดันลอปพิลโล่ ลาลาเบด ซีนัส มารูฟ เรสโทนิค "
                "วูดฟิลด์ โลโต้โมบิลี่ อีสแมนเฮาส์ เครื่องนอน โปรโมชั่น การจัดส่ง รับประกัน"
            ),
        )

    transcription = _retry_on_rate_limit(_stt_call)

    # --- ดึง text ---
    if hasattr(transcription, 'text'):
        text = transcription.text
    elif isinstance(transcription, dict):
        text = transcription.get("text", str(transcription))
    else:
        text = str(transcription)

    # --- ดึง segments ---
    raw_segments = None
    if hasattr(transcription, 'segments'):
        raw_segments = transcription.segments
    elif isinstance(transcription, dict):
        raw_segments = transcription.get("segments")

    segments = []
    if raw_segments:
        for seg in raw_segments:
            if isinstance(seg, dict):
                seg_start = float(seg.get("start", 0))
                seg_end   = float(seg.get("end", 0))
                seg_text  = seg.get("text", "")
            else:
                seg_start = float(getattr(seg, 'start', 0) or 0)
                seg_end   = float(getattr(seg, 'end', 0) or 0)
                seg_text  = getattr(seg, 'text', "") or ""
            segments.append({
                "start": round(seg_start + time_offset, 2),
                "end":   round(seg_end + time_offset, 2),
                "text":  seg_text.strip(),
            })

    # --- ดึง duration ---
    duration = 0.0
    if hasattr(transcription, 'duration') and transcription.duration:
        duration = float(transcription.duration)
    elif isinstance(transcription, dict) and transcription.get("duration"):
        duration = float(transcription["duration"])
    elif segments:
        duration = segments[-1]["end"] - time_offset

    # --- ดึงภาษา ---
    language = "th"
    if hasattr(transcription, 'language') and transcription.language:
        language = transcription.language
    elif isinstance(transcription, dict):
        language = transcription.get("language", "th")

    # ถ้าไม่มี segments แต่มี text → สร้าง segment เดียว
    if not segments and text.strip():
        segments = [{
            "start": round(time_offset, 2),
            "end":   round(time_offset + duration, 2),
            "text":  text.strip(),
        }]

    return {"text": text, "segments": segments, "duration": duration, "language": language}


async def typhoon_stt_transcribe(file_id: str, audio_file_path: str) -> dict:
    """
    ใช้ Typhoon Audio API ถอดเสียงเป็นข้อความ — รองรับ Chunking สำหรับไฟล์ยาว

    ไฟล์สั้น (<5 นาที / <24MB)  → ส่งทั้งไฟล์ครั้งเดียว
    ไฟล์ยาว (≥5 นาที / ≥24MB) → ตัด chunk ละ 5 นาที → รวม transcript + ปรับ timestamp
    """
    start_time = datetime.now()

    if not TYPHOON_AVAILABLE or not _ALL_API_KEYS:
        raise RuntimeError(
            "Typhoon API not configured. "
            "Set TYPHOON_API_KEY environment variable and install: pip install openai"
        )

    loop = asyncio.get_event_loop()
    needs_chunk = _needs_chunking(audio_file_path)
    chunk_paths = []

    try:
        if needs_chunk:
            wav_info       = _get_wav_info(audio_file_path)
            total_duration = wav_info.get("duration_seconds", 0)
            num_expected   = math.ceil(total_duration / CHUNK_DURATION_SECONDS) if total_duration > 0 else 1
            print(f"📦 Chunking: {total_duration:.0f}s → {num_expected} chunks (ทีละ {CHUNK_DURATION_SECONDS}s)")

            chunk_paths = await loop.run_in_executor(
                None, _split_wav_to_chunks, audio_file_path, CHUNK_DURATION_SECONDS
            )

            all_text_parts       = []
            all_segments         = []
            total_audio_duration = 0.0
            detected_language    = "th"

            for i, chunk_path in enumerate(chunk_paths):
                time_offset  = i * CHUNK_DURATION_SECONDS
                print(f"  🎙️ Transcribing chunk {i+1}/{len(chunk_paths)} (offset={time_offset}s)...")
                chunk_result = await loop.run_in_executor(
                    None, _transcribe_single_file, chunk_path, time_offset
                )
                all_text_parts.append(chunk_result["text"])
                all_segments.extend(chunk_result["segments"])
                total_audio_duration += chunk_result["duration"]
                detected_language     = chunk_result["language"]

            transcript_text = " ".join(all_text_parts)
            segments        = all_segments
            duration        = total_audio_duration
            language        = detected_language

        else:
            print("🎙️ Transcribing single file (no chunking needed)")
            result          = await loop.run_in_executor(None, _transcribe_single_file, audio_file_path, 0.0)
            transcript_text = result["text"]
            segments        = result["segments"]
            duration        = result["duration"]
            language        = result["language"]

    finally:
        if chunk_paths:
            _cleanup_chunks(chunk_paths, audio_file_path)

    # === Post-process: filter language + clean hallucinations ===
    final_segments = []
    idx = 0
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        if not _is_thai_or_english(text):
            continue
        cleaned = _clean_foreign_text(text)
        if not cleaned:
            continue
        thai_chars    = sum(1 for ch in cleaned if ord(ch) in _THAI_RANGE)
        total_letters = sum(1 for ch in cleaned if not ch.isspace() and ch not in '.,!?;:\'"()-[]{}')
        if total_letters > 5 and thai_chars / max(total_letters, 1) < 0.3:
            print(f"  ⚠️ Filtered (low Thai %): {cleaned[:60]}...")
            continue
        final_segments.append({
            "id":    idx,
            "start": seg.get("start", 0),
            "end":   seg.get("end", 0),
            "text":  cleaned,
        })
        idx += 1

    transcript_text  = " ".join(s["text"] for s in final_segments)
    processing_time  = (datetime.now() - start_time).total_seconds()

    return {
        "model":                    TYPHOON_STT_MODEL,
        "status":                   "completed",
        "file_id":                  file_id,
        "transcript":               transcript_text,
        "segments":                 final_segments,
        "language_detected":        language,
        "language_confidence":      0.95,
        "audio_duration_seconds":   round(duration, 1),
        "processing_time_seconds":  round(processing_time, 2),
        "word_count":               len(transcript_text.split()),
        "chunked":                  needs_chunk,
        "num_chunks":               len(chunk_paths) if needs_chunk else 1,
        "completed_at":             datetime.now().isoformat(),
    }


# =============================================================================
# STEP 2: Typhoon v2 — NLP Analysis + Summary
# =============================================================================

async def typhoon_llm_analyze(file_id: str, transcript: str, segments: list = None) -> dict:
    """
    ใช้ Typhoon v2 วิเคราะห์บทสนทนา:
    - สรุปบทสนทนา + แก้ transcript
    - Sentiment / Intent / Brand / Product / Channel
    - QA Score + CSAT Prediction
    """
    start_time = datetime.now()

    if not TYPHOON_AVAILABLE or not _ALL_API_KEYS:
        raise RuntimeError("Typhoon API not configured.")

    loop = asyncio.get_event_loop()

    system_prompt = """คุณเป็น AI ผู้เชี่ยวชาญด้านการวิเคราะห์บทสนทนา Call Center ของบริษัทเครื่องนอน
คุณต้องทำ 2 งานพร้อมกัน แล้วส่งผลลัพธ์เป็น JSON เท่านั้น ห้ามมีข้อความอื่นนอกจาก JSON

★ งานที่ 1: แก้ไข Transcript
- แก้คำที่สะกดผิด/ถอดผิดให้ถูกต้อง
- แก้ชื่อแบรนด์เป็นภาษาอังกฤษเสมอ (ดูรายชื่อด้านล่าง)
- ลบคำที่เป็น noise / ไม่มีความหมายออก

★ งานที่ 2: วิเคราะห์บทสนทนา
- สรุปบทสนทนา, Sentiment, Intent, Brand, Product, QA Score

★ แบรนด์ที่รองรับ (ต้องตอบเป็นชื่อภาษาอังกฤษเท่านั้น):
- โลตัส = Lotus
- โอมาซ = Omazz
- ดันลอปพิลโล่ / ดันลอป = Dunlopillo
- ไมดาส = Midas
- เบดเกียร์ / เบสเกียร์ = Bedgear
- ลาลาเบด = LaLaBed
- ซีนัส = Zinus
- อีสแมน เฮาส์ = Eastman House
- มารูฟ / มาลูฟ = Malouf
- โลโต้ โมบิลี่ = Loto Mobili
- วูดฟิลด์ = Woodfield
- เรสโทนิค = Restonic

หมวดสินค้า (ต้องตอบเป็นชื่อภาษาอังกฤษเท่านั้น):
- ที่นอน / ฟูก = Mattress
- หมอน = Pillow
- เครื่องนอน / ผ้าปู / ผ้านวม / ชุดเครื่องนอน = Bedding
- โครงเตียง / เตียง / หัวเตียง = Bed Frame
- ท็อปเปอร์ / แผ่นรองนอน = Topper
- แผ่นกันเปื้อน / ผ้ารองกันเปื้อน / กันไรฝุ่น = Protector
ช่องทางขาย: Official Store, Online, Department Store, Dealer

Intent ที่เป็นไปได้:
- สอบถามข้อมูลสินค้า
- แจ้งสินค้าชำรุด/เสียหาย
- สอบถามสถานะจัดส่ง
- สอบถามโปรโมชั่น
- สอบถามการรับประกัน
- ขอเปลี่ยนสินค้า
- ชมเชยเจ้าหน้าที่/สินค้า
- สอบถามทั่วไป
- ขอยกเลิก/คืนสินค้า"""

    user_prompt = f"""วิเคราะห์บทสนทนา Call Center ต่อไปนี้ ทำ 2 งานพร้อมกัน แล้วตอบเป็น JSON เท่านั้น:

--- บทสนทนา (จาก STT อาจมีคำผิด) ---
{transcript}
--- จบบทสนทนา ---

ส่งผลลัพธ์เป็น JSON format ดังนี้ (ตอบเป็น JSON เท่านั้น ไม่ต้องมี markdown):
{{
  "corrected_transcript": "transcript ที่แก้คำผิดแล้วทั้งหมด (แก้ชื่อแบรนด์เป็นอังกฤษ ลบ noise)",
  "summary_points": ["จุดสรุปที่ 1", "จุดสรุปที่ 2", "จุดสรุปที่ 3", "จุดสรุปที่ 4"],
  "summary_text": "สรุปรวมสั้นๆ 1-2 ประโยค",
  "sentiment": "positive" หรือ "neutral" หรือ "negative",
  "sentiment_score": 0.0 ถึง 1.0,
  "intent": "intent ภาษาไทย",
  "brand_names": ["แบรนด์ที่ 1", "แบรนด์ที่ 2"] หรือ ["Unknown"] (ตอบเป็น array ภาษาอังกฤษ — อาจมีหลายแบรนด์),
  "product_category": "Mattress/Pillow/Bedding/Bed Frame/Topper/Protector หรือ Unknown",
  "sale_channel": "ช่องทาง หรือ Unknown",
  "qa_scores": {{
    "การทักทายและแนะนำตัว": 0.0-10.0,
    "การรับฟังและทำความเข้าใจปัญหา": 0.0-10.0,
    "ความถูกต้องของข้อมูลที่ให้": 0.0-10.0,
    "การเสนอทางแก้ไขที่เหมาะสม": 0.0-10.0,
    "การยืนยันความพึงพอใจก่อนวางสาย": 0.0-10.0,
    "ความสุภาพและมืออาชีพตลอดการสนทนา": 0.0-10.0
  }},
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "key_insights": "ข้อมูลเชิงลึกที่สำคัญ 1-2 ประโยค"
}}"""

    def _analyze():
        c = _get_next_client()
        try:
            chat_completion = c.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=TYPHOON_LLM_MODEL,
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            # บาง model ไม่รองรับ response_format → fallback ไม่ใส่
            if "response_format" in str(e).lower() or "json_object" in str(e).lower():
                chat_completion = c.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    model=TYPHOON_LLM_MODEL,
                    temperature=0.1,
                    max_tokens=4096,
                )
            else:
                raise
        return chat_completion.choices[0].message.content

    raw_response = await loop.run_in_executor(None, lambda: _retry_on_rate_limit(_analyze))

    # Parse JSON response
    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError(f"Cannot parse Typhoon response as JSON: {raw_response[:200]}")

    # Extract & normalize fields
    sentiment       = result.get("sentiment", "neutral").lower()
    sentiment_score = float(result.get("sentiment_score", 0.5))

    qa_scores  = result.get("qa_scores", {})
    qa_values  = [float(v) for v in qa_scores.values() if isinstance(v, (int, float))]
    final_qa   = round(sum(qa_values) / max(len(qa_values), 1), 2)

    if final_qa >= 8.5:
        csat = 5
    elif final_qa >= 7.0:
        csat = 4
    elif final_qa >= 5.5:
        csat = 3
    elif final_qa >= 4.0:
        csat = 2
    else:
        csat = 1

    grade = _score_to_grade(final_qa)

    action_items = []
    if sentiment == "negative":
        action_items.append("🔴 ติดตามลูกค้าภายใน 24 ชั่วโมง")
    intent_text = result.get("intent", "")
    if "ยกเลิก" in intent_text or "คืน" in intent_text:
        action_items.append("⚠️ ส่งต่อทีม Retention")
    if final_qa < 6.0:
        action_items.append("📋 แจ้ง Supervisor ตรวจสอบคุณภาพ")
    if not action_items:
        action_items.append("✅ ปิดเคสได้")

    processing_time = (datetime.now() - start_time).total_seconds()

    return {
        "model":                 TYPHOON_LLM_MODEL,
        "status":                "completed",
        "file_id":               file_id,
        "corrected_transcript":  result.get("corrected_transcript", transcript),
        "summary_text":          result.get("summary_text", ""),
        "summary_points":        result.get("summary_points", []),
        "sentiment":             sentiment,
        "sentiment_score":       sentiment_score,
        "sentiment_confidence":  sentiment_score,
        "intent":                result.get("intent", "สอบถามทั่วไป"),
        "brand_name":            _parse_brand_names(result)[0] if _parse_brand_names(result) else "Unknown",
        "brand_names":           _parse_brand_names(result),
        "product_category":      result.get("product_category", "Unknown"),
        "sale_channel":          result.get("sale_channel", "Unknown"),
        "qa_scoring": {
            "final_score":        final_qa,
            "max_score":          10.0,
            "grade":              grade,
            "criteria_breakdown": qa_scores,
        },
        "csat_predicted":        csat,
        "keywords":              result.get("keywords", []),
        "key_insights":          result.get("key_insights", ""),
        "action_items":          action_items,
        "processing_time_seconds": round(processing_time, 2),
        "completed_at":          datetime.now().isoformat(),
    }


# =============================================================================
# STEP 3: Full Pipeline — STT → LLM (Fix + Analyze)
# =============================================================================

async def run_typhoon_analysis_pipeline(
    file_id: str,
    audio_file_path: str,
    on_step_complete=None,
) -> dict:
    """
    Full AI Pipeline (2 Steps):
    1. Typhoon Audio — ถอดเสียงเป็นข้อความ
    2. Typhoon v2    — แก้ transcript + วิเคราะห์ + สรุป (รวมใน call เดียว)

    Args:
        file_id:           ID ของไฟล์
        audio_file_path:   path ไปยังไฟล์เสียง
        on_step_complete:  callback (optional)
    """
    pipeline_start = datetime.now()

    # --- Step 1: Typhoon Audio STT ---
    print(f"🚀 Pipeline START: {file_id}")
    print(f"  Step 1/2: Typhoon Audio (Speech-to-Text)...")

    whisper_result = await typhoon_stt_transcribe(
        file_id=file_id,
        audio_file_path=audio_file_path,
    )
    print(f"  ✅ Step 1 done: {whisper_result['word_count']} words, "
          f"{whisper_result['audio_duration_seconds']}s audio")

    if on_step_complete:
        await on_step_complete("whisper", whisper_result)

    # --- Step 2: Typhoon v2 LLM Analyze ---
    await asyncio.sleep(DELAY_BETWEEN_STEPS)
    print(f"  Step 2/2: Typhoon v2 (แก้ Transcript + วิเคราะห์)...")

    llama_result = await typhoon_llm_analyze(
        file_id=file_id,
        transcript=whisper_result["transcript"],
        segments=whisper_result.get("segments", []),
    )

    corrected_transcript = llama_result.get("corrected_transcript", whisper_result["transcript"])
    whisper_result["transcript_original"]  = whisper_result["transcript"]
    whisper_result["transcript"]           = corrected_transcript
    whisper_result["transcript_corrected"] = True

    print(f"  ✅ Step 2 done: sentiment={llama_result['sentiment']}, "
          f"QA={llama_result['qa_scoring']['final_score']}, "
          f"brand={llama_result['brand_name']}")

    if on_step_complete:
        await on_step_complete("llama", llama_result)

    pipeline_duration = (datetime.now() - pipeline_start).total_seconds()
    print(f"🏁 Pipeline DONE: {pipeline_duration:.1f}s total")

    return {
        "file_id":                  file_id,
        "pipeline_status":          "completed",
        "pipeline_duration_seconds": round(pipeline_duration, 2),
        "completed_at":             datetime.now().isoformat(),
        "summary": {
            "transcript":           corrected_transcript,
            "language":             whisper_result["language_detected"],
            "sentiment":            llama_result["sentiment"],
            "sentiment_confidence": llama_result["sentiment_confidence"],
            "intent":               llama_result["intent"],
            "qa_score":             llama_result["qa_scoring"]["final_score"],
            "qa_grade":             llama_result["qa_scoring"]["grade"],
            "csat_predicted":       llama_result["csat_predicted"],
            "summary_text":         llama_result["summary_text"],
            "summary_points":       llama_result["summary_points"],
            "action_items":         llama_result["action_items"],
            "brand_name":           llama_result["brand_name"],
            "brand_names":          llama_result.get("brand_names", []),
            "product_category":     llama_result["product_category"],
            "sale_channel":         llama_result["sale_channel"],
        },
        "model_results": {
            "whisper": whisper_result,
            "llama":   llama_result,
        },
    }


# =============================================================================
# Backward-compat alias (ใช้สลับกับ groq_ai_service ได้โดยแก้แค่ import)
# =============================================================================
run_groq_analysis_pipeline = run_typhoon_analysis_pipeline


# =============================================================================
# Helpers
# =============================================================================

def _parse_brand_names(result: dict) -> list:
    names = result.get("brand_names")
    if isinstance(names, list) and names:
        return [n.strip() for n in names if n.strip() and n.strip() != "Unknown"]
    name = result.get("brand_name", "")
    if not name or name.strip() == "Unknown":
        return []
    if "," in name:
        return [n.strip() for n in name.split(",") if n.strip() and n.strip() != "Unknown"]
    return [name.strip()]


def _score_to_grade(s):
    if s >= 9.0: return "A+ (ยอดเยี่ยม)"
    if s >= 8.0: return "A  (ดีมาก)"
    if s >= 7.0: return "B  (ดี)"
    if s >= 6.0: return "C  (พอใช้)"
    if s >= 5.0: return "D  (ต้องปรับปรุง)"
    return           "F  (ต่ำกว่ามาตรฐาน)"