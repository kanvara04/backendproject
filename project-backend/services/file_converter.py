# =============================================================================
# services/file_converter.py
# บริการแปลงไฟล์เสียง/วิดีโอ → .wav (16kHz, Mono) สำหรับ AI Transcription
#
# อธิบาย: Whisper AI และ Speech-to-Text Models ส่วนใหญ่ทำงานได้ดีที่สุดกับ
# ไฟล์ .wav ที่ Sample Rate 16kHz และเป็น Mono (1 Channel)
# ไฟล์นี้จัดการการแปลงทั้งหมดก่อนส่งให้ AI ประมวลผล
# =============================================================================

import os
import uuid
import subprocess
import shutil
from pathlib import Path
from typing import Tuple

# =============================================================================
# STEP 1: กำหนดค่าคงที่ (Constants)
# =============================================================================
# Path ที่ใช้เก็บไฟล์ทั้งหมด
# BASE_DIR: ตำแหน่งของไฟล์ file_converter.py นี้
# UPLOAD_DIR: โฟลเดอร์สำหรับเก็บไฟล์ที่ upload เข้ามา (ก่อนแปลง)
# CONVERTED_DIR: โฟลเดอร์สำหรับเก็บไฟล์ .wav ที่แปลงแล้ว (พร้อมให้ AI ใช้)
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent  # ขึ้นไป 2 ระดับ → root project
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"      # storage/uploads/
CONVERTED_DIR = BASE_DIR / "storage" / "converted" # storage/converted/

# สร้างโฟลเดอร์ถ้ายังไม่มี (exist_ok=True = ไม่ error ถ้ามีอยู่แล้ว)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CONVERTED_DIR.mkdir(parents=True, exist_ok=True)

# นามสกุลไฟล์ที่รองรับ
# Audio formats: ไฟล์เสียงทั่วไป
# Video formats: บางครั้งลูกค้า record ผ่าน screen recording แล้วได้ไฟล์ .mp4
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma", ".opus"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".3gp"}
ALL_SUPPORTED_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

# ค่า Target สำหรับ Whisper AI
TARGET_SAMPLE_RATE = 16000  # 16kHz - มาตรฐานสำหรับ Speech Recognition
TARGET_CHANNELS = 1         # Mono - ลดความซับซ้อน, Whisper ไม่ต้องการ Stereo
TARGET_FORMAT = "wav"       # WAV - Lossless, ไม่มีการบีบอัดที่เสียคุณภาพ


# =============================================================================
# STEP 2: ตรวจสอบว่า ffmpeg ติดตั้งอยู่ในระบบหรือไม่
# =============================================================================
# ffmpeg คือโปรแกรม Command-line สำหรับจัดการไฟล์มัลติมีเดียที่ทรงพลังที่สุด
# ต้องติดตั้งแยกต่างหาก: https://ffmpeg.org/download.html
# Ubuntu/Debian: sudo apt install ffmpeg
# Mac:           brew install ffmpeg
# Windows:       choco install ffmpeg
# =============================================================================

def check_ffmpeg_available() -> bool:
    """
    ตรวจสอบว่า ffmpeg ติดตั้งอยู่ในระบบหรือเปล่า
    shutil.which() คล้ายกับคำสั่ง 'which ffmpeg' ใน Terminal
    คืนค่า path ของโปรแกรมถ้าเจอ, คืน None ถ้าไม่เจอ
    """
    return shutil.which("ffmpeg") is not None


# =============================================================================
# STEP 3: ฟังก์ชันหลัก - แปลงไฟล์เสียง/วิดีโอ → .wav
# =============================================================================
def convert_to_wav(input_path: Path) -> Tuple[Path, dict]:
    """
    แปลงไฟล์เสียงหรือวิดีโอใดๆ ให้เป็น .wav (16kHz, Mono)
    
    กระบวนการทำงาน (Pipeline):
    1. ตรวจสอบว่าไฟล์มีอยู่จริงและนามสกุลรองรับ
    2. ตรวจสอบว่า ffmpeg พร้อมใช้งาน
    3. ถ้าไฟล์เป็น .wav อยู่แล้ว → ตรวจสอบ spec แล้วแปลงถ้าจำเป็น
    4. ถ้าเป็นไฟล์อื่น → แปลงด้วย ffmpeg
    5. คืนค่า path ของไฟล์ที่แปลงแล้ว + metadata
    
    Args:
        input_path: Path ของไฟล์ต้นฉบับ
    
    Returns:
        Tuple[Path, dict]:
          - Path: ตำแหน่งของไฟล์ .wav ที่แปลงแล้ว
          - dict: metadata เช่น ขนาดไฟล์, ใช้เวลาแปลงนานแค่ไหน
    
    Raises:
        FileNotFoundError: ถ้าไม่พบไฟล์ต้นฉบับ
        ValueError: ถ้านามสกุลไฟล์ไม่รองรับ
        RuntimeError: ถ้า ffmpeg ทำงานผิดพลาด
    """
    import time
    start_time = time.time()

    # --- ขั้นที่ 1: Validate Input File ---
    if not input_path.exists():
        raise FileNotFoundError(f"ไม่พบไฟล์: {input_path}")

    file_extension = input_path.suffix.lower()  # .MP4 → .mp4

    if file_extension not in ALL_SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"นามสกุลไฟล์ '{file_extension}' ไม่รองรับ\n"
            f"รองรับ: {', '.join(sorted(ALL_SUPPORTED_EXTENSIONS))}"
        )

    # --- ขั้นที่ 2: ตรวจสอบ ffmpeg ---
    if not check_ffmpeg_available():
        raise RuntimeError(
            "ไม่พบ ffmpeg ในระบบ\n"
            "กรุณาติดตั้ง: sudo apt install ffmpeg (Ubuntu) หรือ brew install ffmpeg (Mac)"
        )

    # --- ขั้นที่ 3: กำหนดชื่อไฟล์ Output ---
    # ใช้ stem (ชื่อไฟล์ไม่รวมนามสกุล) + "_converted" + .wav
    # เช่น: "call_recording.mp4" → "call_recording_converted.wav"
    output_filename = f"{input_path.stem}_converted.wav"
    output_path = CONVERTED_DIR / output_filename

    # --- ขั้นที่ 4: สร้าง ffmpeg Command ---
    # อธิบายแต่ละ argument:
    #   -i {input}       : Input file (i = input)
    #   -ar 16000        : Audio Rate = 16,000 Hz (16kHz)
    #   -ac 1            : Audio Channels = 1 (Mono)
    #   -c:a pcm_s16le   : Audio Codec = PCM Signed 16-bit Little Endian
    #                      (มาตรฐานสำหรับ WAV, ไม่มีการ compress)
    #   -vn              : Video No = ไม่เอา video stream (สำหรับไฟล์ .mp4)
    #   -y               : Yes = overwrite ถ้าไฟล์ output มีอยู่แล้ว
    #   {output}         : Output file path
    ffmpeg_command = [
        "ffmpeg",
        "-i", str(input_path),   # Input: ไฟล์ต้นฉบับ
        "-ar", str(TARGET_SAMPLE_RATE),  # Sample Rate: 16000 Hz
        "-ac", str(TARGET_CHANNELS),     # Channels: 1 (Mono)
        "-c:a", "pcm_s16le",             # Codec: WAV มาตรฐาน
        "-vn",                           # ตัด Video stream ออก (ถ้ามี)
        "-y",                            # Overwrite output ถ้ามีอยู่แล้ว
        str(output_path),        # Output: ไฟล์ .wav ปลายทาง
    ]

    # --- ขั้นที่ 5: รัน ffmpeg Command ---
    # subprocess.run() = รันโปรแกรมภายนอกจาก Python
    # capture_output=True = เก็บ stdout และ stderr ไว้ใน result
    # text=True = แปลง bytes output เป็น string
    try:
        result = subprocess.run(
            ffmpeg_command,
            capture_output=True,  # เก็บ output ของ ffmpeg ไว้
            text=True,            # แปลงเป็น text (ไม่ใช่ bytes)
            timeout=300,          # Timeout 5 นาที (ป้องกันไฟล์ใหญ่มากค้างไว้)
        )

        # ตรวจสอบว่า ffmpeg ทำงานสำเร็จหรือไม่
        # returncode = 0 → สำเร็จ, returncode != 0 → มี error
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg แปลงไฟล์ล้มเหลว\n"
                f"Error: {result.stderr}"
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError("การแปลงไฟล์ใช้เวลานานเกิน 5 นาที กรุณาตรวจสอบขนาดไฟล์")

    # --- ขั้นที่ 6: เก็บ Metadata ของผลลัพธ์ ---
    conversion_time = round(time.time() - start_time, 2)
    output_size_mb = round(output_path.stat().st_size / (1024 * 1024), 2)
    input_size_mb = round(input_path.stat().st_size / (1024 * 1024), 2)

    metadata = {
        "original_filename": input_path.name,
        "original_format": file_extension,
        "original_size_mb": input_size_mb,
        "converted_filename": output_filename,
        "converted_format": ".wav",
        "converted_size_mb": output_size_mb,
        "sample_rate": TARGET_SAMPLE_RATE,
        "channels": TARGET_CHANNELS,
        "conversion_time_seconds": conversion_time,
        "ffmpeg_stderr": result.stderr[-500:] if result.stderr else "",  # เก็บแค่ 500 ตัวท้าย
    }

    return output_path, metadata


# =============================================================================
# STEP 4: ฟังก์ชัน Save Uploaded File
# =============================================================================
def save_uploaded_file(file_content: bytes, original_filename: str) -> Tuple[str, Path]:
    """
    บันทึกไฟล์ที่ upload มาลงดิสก์ พร้อมสร้าง Unique ID
    
    ทำไมต้องสร้าง UUID?
    - ป้องกัน filename collision (ไม่มีปัญหาถ้าลูกค้า 2 คน upload ไฟล์ชื่อเหมือนกัน)
    - ป้องกัน Path Traversal Attack (เช่น ส่งชื่อไฟล์ว่า "../../etc/passwd")
    - ทำให้ไฟล์มี ID ที่ unique สำหรับ tracking
    
    Args:
        file_content: เนื้อหาไฟล์ในรูปแบบ bytes
        original_filename: ชื่อไฟล์เดิม (เก็บไว้เพื่อดึงนามสกุล)
    
    Returns:
        Tuple[str, Path]:
          - str: file_id (UUID) สำหรับอ้างอิงในอนาคต
          - Path: ตำแหน่งที่บันทึกไฟล์
    """
    # สร้าง Unique ID สำหรับไฟล์นี้
    file_id = str(uuid.uuid4())  # เช่น "550e8400-e29b-41d4-a716-446655440000"

    # ดึงนามสกุลจากชื่อไฟล์เดิม เช่น "recording.mp4" → ".mp4"
    original_extension = Path(original_filename).suffix.lower()

    # ตรวจสอบนามสกุลก่อนบันทึก
    if original_extension not in ALL_SUPPORTED_EXTENSIONS:
        raise ValueError(f"นามสกุล '{original_extension}' ไม่รองรับ")

    # ชื่อไฟล์ที่จะบันทึก = UUID + นามสกุลเดิม
    # เช่น "550e8400-e29b-41d4-a716-446655440000.mp4"
    saved_filename = f"{file_id}{original_extension}"
    saved_path = UPLOAD_DIR / saved_filename

    # เขียนไฟล์ลงดิสก์
    # "wb" = write binary mode (สำหรับไฟล์ที่ไม่ใช่ text)
    with open(saved_path, "wb") as f:
        f.write(file_content)

    return file_id, saved_path


# =============================================================================
# STEP 5: ฟังก์ชันค้นหาและลบไฟล์
# =============================================================================
def find_converted_file(file_id: str) -> Path | None:
    """
    หาไฟล์ .wav ที่แปลงแล้วจาก file_id
    ค้นหาใน CONVERTED_DIR โดยดูไฟล์ที่ขึ้นต้นด้วย file_id
    """
    # ค้นหาไฟล์ที่ชื่อขึ้นต้นด้วย file_id ใน converted directory
    for file in CONVERTED_DIR.iterdir():
        if file.stem.startswith(file_id):
            return file
    return None


def find_uploaded_file(file_id: str) -> Path | None:
    """
    หาไฟล์ต้นฉบับที่ upload มาจาก file_id
    """
    for file in UPLOAD_DIR.iterdir():
        if file.stem == file_id:
            return file
    return None


def delete_files_by_id(file_id: str) -> dict:
    """
    ลบทั้งไฟล์ต้นฉบับและไฟล์ที่แปลงแล้วตาม file_id
    
    Returns:
        dict แสดงผลการลบแต่ละไฟล์
    """
    result = {
        "file_id": file_id,
        "uploaded_file_deleted": False,
        "converted_file_deleted": False,
        "errors": [],
    }

    # ลบไฟล์ต้นฉบับ
    uploaded = find_uploaded_file(file_id)
    if uploaded:
        try:
            uploaded.unlink()  # unlink() = ลบไฟล์ (คล้าย rm ใน Terminal)
            result["uploaded_file_deleted"] = True
        except OSError as e:
            result["errors"].append(f"ลบไฟล์ต้นฉบับไม่สำเร็จ: {e}")

    # ลบไฟล์ที่แปลงแล้ว
    converted = find_converted_file(file_id)
    if converted:
        try:
            converted.unlink()
            result["converted_file_deleted"] = True
        except OSError as e:
            result["errors"].append(f"ลบไฟล์ WAV ไม่สำเร็จ: {e}")

    return result
