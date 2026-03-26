# =============================================================================
# test_local_ai.py — ทดสอบว่า Local AI ติดตั้งครบหรือยัง
# วางไว้ที่ project-backend/ แล้วรัน: python test_local_ai.py
# =============================================================================

import sys

print("=" * 60)
print("🔍 ตรวจสอบ Local AI Setup")
print("=" * 60)

errors = []

# --- 1. Check faster-whisper ---
print("\n[1/4] faster-whisper...", end=" ")
try:
    from faster_whisper import WhisperModel
    print("✅ ติดตั้งแล้ว")
except ImportError:
    print("❌ ยังไม่ได้ติดตั้ง")
    errors.append("pip install faster-whisper")

# --- 2. Check CUDA ---
print("[2/4] CUDA (GPU)...", end=" ")
try:
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram = torch.cuda.get_device_properties(0).total_mem / (1024**3)
        print(f"✅ {gpu_name} ({vram:.1f} GB VRAM)")
    else:
        print("⚠️ CUDA ไม่พร้อมใช้งาน (จะใช้ CPU แทน — ช้ากว่ามาก)")
        errors.append("ติดตั้ง CUDA toolkit: https://developer.nvidia.com/cuda-downloads")
except ImportError:
    print("⚠️ PyTorch ไม่ได้ติดตั้ง (faster-whisper จะใช้ CTranslate2 แทน)")

# --- 3. Check Ollama ---
print("[3/4] Ollama...", end=" ")
try:
    import requests
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    if r.status_code == 200:
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"✅ รันอยู่ — models: {models}")

        # ตรวจว่ามี llama3.1:8b หรือเปล่า
        has_llama = any("llama3.1" in m for m in models)
        if not has_llama:
            print("  ⚠️ ไม่พบ llama3.1:8b — ต้องรัน: ollama pull llama3.1:8b")
            errors.append("ollama pull llama3.1:8b")
    else:
        print(f"❌ Ollama ตอบ HTTP {r.status_code}")
        errors.append("ตรวจสอบ Ollama: ollama serve")
except requests.ConnectionError:
    print("❌ Ollama ไม่ได้รัน")
    errors.append("เปิด Ollama app หรือรัน: ollama serve")
except ImportError:
    print("❌ requests ไม่ได้ติดตั้ง")
    errors.append("pip install requests")

# --- 4. Check requests ---
print("[4/4] requests...", end=" ")
try:
    import requests
    print("✅ ติดตั้งแล้ว")
except ImportError:
    print("❌ ยังไม่ได้ติดตั้ง")
    errors.append("pip install requests")

# --- Summary ---
print("\n" + "=" * 60)
if not errors:
    print("🎉 ทุกอย่างพร้อมแล้ว! สามารถรัน backend ได้เลย:")
    print("   python -m uvicorn main:app --reload --port 8000")
else:
    print(f"⚠️ ยังต้องแก้ {len(errors)} ข้อ:")
    for i, err in enumerate(errors, 1):
        print(f"   {i}. {err}")
print("=" * 60)
