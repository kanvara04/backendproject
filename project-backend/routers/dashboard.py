# =============================================================================
# routers/dashboard.py — v0.6.0
# Dashboard Router — Brand / Product / Sale Channel Filtering
#
# === UPDATE v0.6.0 ===
# Endpoints:
#   GET /filters  — ดึง dropdown options (brands, products, channels)
#   GET /summary  — KPIs + 3 Query Param Filters (?brand=&product=&channel=)
#   GET /overview — ภาพรวม KPIs + distribution ของ brand/product/channel
#   GET /trends   — แนวโน้มรายวัน
#   GET /intent-analysis — วิเคราะห์ประเภทปัญหา
#   GET /recommendations — คำแนะนำ AI
#   GET /export   — Export CSV/XLSX (รองรับ brand/product/channel columns)
#
# === วิธีใช้ Query Parameters ===
# GET /summary                                         → ทั้งหมด
# GET /summary?brand=Omazz                             → เฉพาะ Omazz
# GET /summary?product=Mattress                        → เฉพาะ Mattress
# GET /summary?channel=Online                          → เฉพาะ Online
# GET /summary?brand=Lotus&product=Pillow&channel=Department Store → กรอง 3 เงื่อนไข
# =============================================================================

import io
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from database.mock_db import (
    MOCK_ANALYSIS_RESULTS,
    MOCK_CUSTOMERS,
    get_filtered_analysis,
    get_available_brands,
    get_available_products,
    get_available_channels,
)

router = APIRouter()
EXPORT_DIR = Path(__file__).resolve().parent.parent / "storage" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Helpers
# =============================================================================

def _get_all_results() -> list[dict]:
    return list(MOCK_ANALYSIS_RESULTS.values())

def _safe_avg(values: list) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0

def _get_grade(score: float) -> str:
    if score >= 9.0: return "A+"
    if score >= 8.0: return "A"
    if score >= 7.0: return "B"
    if score >= 6.0: return "C"
    if score >= 5.0: return "D"
    return "F"

def _enrich_results(results: list[dict]) -> list[dict]:
    enriched = []
    for r in results:
        row = dict(r)
        customer = MOCK_CUSTOMERS.get(r.get("customer_id", ""), {})
        row["customer_name"] = customer.get("full_name", "ไม่ระบุ")
        row["customer_account"] = customer.get("account_type", "ไม่ระบุ")
        enriched.append(row)
    return enriched


# =============================================================================
# GET /filters — ดึง dropdown options ทั้งหมด
# =============================================================================
# ใช้ให้ Frontend สร้าง Dropdown Filter ก่อนเรียก /summary
# =============================================================================

@router.get(
    "/filters",
    summary="🏷️ ดึง Filter Options (Brand / Product / Channel)",
    description="""
ดึง list ทั้งหมดของ แบรนด์, หมวดสินค้า, ช่องทางซื้อ ที่มีในระบบ

**ใช้สำหรับ**: Frontend สร้าง Dropdown Filter
    """,
)
async def get_filter_options():
    """
    วิธีทำงาน:
    1. get_available_brands()    → ดึง list แบรนด์จาก DB (ไม่รวม Unknown)
    2. get_available_products()  → ดึง list product category
    3. get_available_channels()  → ดึง list sale channel
    """
    return {
        "brands": get_available_brands(),
        "products": get_available_products(),
        "channels": get_available_channels(),
    }


# =============================================================================
# GET /summary — KPIs + 3-Way Filter (⭐ หัวใจ v0.6.0)
# =============================================================================
# Query Parameters:
#   ?brand=Omazz           → กรองเฉพาะ Omazz
#   ?product=Mattress      → กรองเฉพาะ Mattress
#   ?channel=Online        → กรองเฉพาะ Online
#   รวมกันได้: ?brand=Lotus&product=Pillow&channel=Department Store
#
# FastAPI อ่าน Query String จาก URL อัตโนมัติ:
#   /summary?brand=Omazz → brand="Omazz", product=None, channel=None
#   /summary             → brand=None, product=None, channel=None (ดึงทั้งหมด)
# =============================================================================

@router.get(
    "/summary",
    summary="📊 KPIs Summary + Brand/Product/Channel Filter",
    description="""
สรุป KPIs (CSAT, QA Score, Sentiment) พร้อม filter 3 มิติ

**Query Parameters:**
- `brand` (optional): แบรนด์ เช่น Omazz, Lotus, Dunlopillo
- `product` (optional): หมวดสินค้า เช่น Mattress, Pillow, Bedding, Topper, Bed Frame, Protector
- `channel` (optional): ช่องทางซื้อ เช่น Online, Official Store, Department Store, Dealer
    """,
)
async def get_summary(
    brand: Optional[str] = Query(default=None, description="กรองตามแบรนด์ เช่น Omazz, Lotus, Dunlopillo"),
    product: Optional[str] = Query(default=None, description="กรองตามสินค้า เช่น Mattress, Pillow, Bedding"),
    channel: Optional[str] = Query(default=None, description="กรองตามช่องทาง เช่น Online, Official Store, Department Store, Dealer"),
):
    """
    ขั้นตอน:
    1. รับ Query Params → brand, product, channel (None = ไม่กรอง)
    2. เรียก get_filtered_analysis(brand, product, channel) จาก mock_db
    3. คำนวณสถิติจากข้อมูลที่กรองแล้ว
    4. ส่ง JSON กลับพร้อมระบุ filter ที่ใช้
    """
    results = get_filtered_analysis(brand=brand, product=product, channel=channel)

    if not results:
        return {
            "message": "ไม่พบข้อมูลตาม filter ที่ระบุ",
            "applied_filters": {"brand": brand, "product": product, "channel": channel},
            "total_calls": 0,
        }

    csat_scores = [r["csat_score"] for r in results if "csat_score" in r]
    qa_scores   = [r["qa_score"]   for r in results if "qa_score"   in r]
    sentiments  = [r["sentiment"]  for r in results if "sentiment"  in r]
    durations   = [r.get("call_duration_seconds", 0) for r in results]
    escalated   = [r for r in results if r.get("is_escalated")]

    total = len(results)
    sent_counts = Counter(sentiments)
    avg_csat = _safe_avg(csat_scores)
    avg_qa = _safe_avg(qa_scores)

    return {
        "generated_at": datetime.now().isoformat(),
        "applied_filters": {"brand": brand, "product": product, "channel": channel},
        "total_calls": total,

        "csat": {
            "average": avg_csat,
            "max_possible": 5,
            "percentage": round((avg_csat / 5) * 100, 1),
            "distribution": {f"{i}_stars": csat_scores.count(i) for i in range(5, 0, -1)},
        },

        "qa_score": {
            "average": avg_qa,
            "grade": _get_grade(avg_qa),
            "max_possible": 10.0,
            "calls_below_threshold": sum(1 for s in qa_scores if s < 6.0),
        },

        "sentiment": {
            "positive_count": sent_counts.get("positive", 0),
            "neutral_count":  sent_counts.get("neutral", 0),
            "negative_count": sent_counts.get("negative", 0),
            "positive_rate_%": round(sent_counts.get("positive", 0) / total * 100, 1),
            "negative_rate_%": round(sent_counts.get("negative", 0) / total * 100, 1),
        },

        "operations": {
            "avg_duration_seconds": round(_safe_avg(durations), 1),
            "avg_duration_minutes": round(_safe_avg(durations) / 60, 2),
            "total_escalated": len(escalated),
            "escalation_rate_%": round(len(escalated) / total * 100, 1),
        },
    }


# =============================================================================
# GET /overview — ภาพรวม KPIs + Distribution
# =============================================================================

@router.get("/overview", summary="📊 ภาพรวม KPIs ทั้งหมด")
async def get_overview():
    results = _get_all_results()
    if not results:
        return {"message": "ยังไม่มีข้อมูล", "total_calls": 0}

    csat_scores = [r["csat_score"] for r in results if "csat_score" in r]
    qa_scores   = [r["qa_score"]   for r in results if "qa_score"   in r]
    sentiments  = [r["sentiment"]  for r in results if "sentiment"  in r]
    durations   = [r.get("call_duration_seconds", 0) for r in results]
    escalated   = [r for r in results if r.get("is_escalated")]

    total = len(results)
    sent_counts = Counter(sentiments)
    avg_csat = _safe_avg(csat_scores)
    avg_qa = _safe_avg(qa_scores)

    return {
        "generated_at": datetime.now().isoformat(),
        "total_calls": total,
        "csat": {"average": avg_csat, "max_possible": 5, "percentage": round((avg_csat / 5) * 100, 1),
                 "distribution": {f"{i}_stars": csat_scores.count(i) for i in range(5, 0, -1)}},
        "qa_score": {"average": avg_qa, "grade": _get_grade(avg_qa), "max_possible": 10.0,
                     "calls_below_threshold": sum(1 for s in qa_scores if s < 6.0)},
        "sentiment": {
            "positive_count": sent_counts.get("positive", 0), "neutral_count": sent_counts.get("neutral", 0),
            "negative_count": sent_counts.get("negative", 0),
            "positive_rate_%": round(sent_counts.get("positive", 0) / total * 100, 1),
            "negative_rate_%": round(sent_counts.get("negative", 0) / total * 100, 1),
        },
        "operations": {"avg_duration_seconds": round(_safe_avg(durations), 1), "total_escalated": len(escalated),
                       "escalation_rate_%": round(len(escalated) / total * 100, 1)},
        # Distribution breakdowns
        "brand_distribution": dict(Counter(r.get("brand_name", "Unknown") for r in results).most_common()),
        "product_distribution": dict(Counter(r.get("product_category", "Unknown") for r in results).most_common()),
        "channel_distribution": dict(Counter(r.get("sale_channel", "Unknown") for r in results).most_common()),
    }


# =============================================================================
# GET /trends
# =============================================================================

@router.get("/trends", summary="📈 แนวโน้มตามช่วงเวลา")
async def get_trends(days: int = Query(default=7, ge=1, le=90)):
    results = _get_all_results()
    cutoff = datetime.now() - timedelta(days=days)
    daily: dict[str, list] = defaultdict(list)

    for r in results:
        try:
            dt = datetime.fromisoformat(r.get("call_timestamp", ""))
            if dt >= cutoff:
                daily[dt.strftime("%Y-%m-%d")].append(r)
        except (ValueError, TypeError):
            continue

    if len(daily) < 2:
        import random
        for i in range(days):
            dk = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if dk not in daily:
                daily[dk] = [{"csat_score": random.randint(3, 5), "qa_score": round(random.uniform(6.0, 9.5), 1),
                              "sentiment": random.choice(["positive", "positive", "neutral", "negative"]), "is_escalated": random.random() < 0.1}
                             for _ in range(random.randint(5, 20))]

    trend_points = []
    for ds in sorted(daily.keys()):
        dr = daily[ds]
        sc = Counter(r.get("sentiment", "") for r in dr)
        n = len(dr)
        trend_points.append({
            "date": ds, "total_calls": n,
            "avg_csat": _safe_avg([r.get("csat_score", 0) for r in dr if r.get("csat_score")]),
            "avg_qa_score": _safe_avg([r.get("qa_score", 0) for r in dr if r.get("qa_score")]),
            "positive_calls": sc.get("positive", 0), "negative_calls": sc.get("negative", 0),
            "positive_rate_%": round(sc.get("positive", 0) / n * 100, 1) if n else 0,
        })

    return {"period_days": days, "data_points": len(trend_points), "trends": trend_points}


# =============================================================================
# GET /intent-analysis
# =============================================================================

@router.get("/intent-analysis", summary="🎯 วิเคราะห์ประเภทปัญหา")
async def get_intent_analysis():
    results = _get_all_results()
    groups: dict[str, list] = defaultdict(list)
    for r in results:
        groups[r.get("intent", "ไม่ระบุ")].append(r)

    summary = []
    for intent, grp in groups.items():
        sc = Counter(r.get("sentiment", "") for r in grp)
        summary.append({
            "intent": intent, "call_count": len(grp),
            "avg_csat": _safe_avg([r.get("csat_score", 0) for r in grp if r.get("csat_score")]),
            "avg_qa_score": _safe_avg([r.get("qa_score", 0) for r in grp if r.get("qa_score")]),
            "escalation_count": sum(1 for r in grp if r.get("is_escalated")),
            "dominant_sentiment": sc.most_common(1)[0][0] if sc else "neutral",
            "negative_rate_%": round(sc.get("negative", 0) / len(grp) * 100, 1),
        })
    summary.sort(key=lambda x: x["call_count"], reverse=True)

    return {"total_intents": len(summary), "intent_breakdown": summary,
            "critical_intents": sorted([i for i in summary if i["avg_csat"] > 0], key=lambda x: x["avg_csat"])[:3]}


# =============================================================================
# GET /recommendations
# =============================================================================

@router.get("/recommendations", summary="💡 คำแนะนำ AI")
async def get_recommendations():
    results = _get_all_results()
    recs = []
    prio = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    csat_scores = [r.get("csat_score", 0) for r in results if r.get("csat_score")]
    avg_csat = _safe_avg(csat_scores) if csat_scores else 3.5

    if avg_csat < 3.0:
        recs.append({"priority": "critical", "icon": "🔴", "title": f"CSAT วิกฤต ({avg_csat}/5)", "action": "จัด Emergency review ทันที"})
    elif avg_csat < 4.0:
        recs.append({"priority": "high", "icon": "🟠", "title": f"CSAT ควรปรับปรุง ({avg_csat}/5)", "action": "จัด Empathy Training"})

    qa_scores = [r.get("qa_score", 0) for r in results if r.get("qa_score")]
    low_qa = sum(1 for s in qa_scores if s < 6.0)
    if low_qa > len(qa_scores) * 0.3:
        recs.append({"priority": "high", "icon": "🟠", "title": f"{low_qa} สายมี QA < 6.0", "action": "ทบทวน Script"})

    esc_rate = len([r for r in results if r.get("is_escalated")]) / len(results) * 100 if results else 0
    if esc_rate > 15:
        recs.append({"priority": "critical", "icon": "🔴", "title": f"Escalation สูง ({esc_rate:.1f}%)", "action": "เพิ่ม First-Call Resolution"})

    if not recs:
        recs.append({"priority": "low", "icon": "✅", "title": "ระบบทำงานดี", "action": "รักษามาตรฐาน"})

    recs.sort(key=lambda r: prio.get(r["priority"], 99))
    return {"generated_at": datetime.now().isoformat(), "recommendations": recs, "data_based_on": f"{len(results)} สาย"}


# =============================================================================
# GET /export — CSV/XLSX (รองรับ brand/product/channel columns)
# =============================================================================

@router.get("/export", summary="📥 Export CSV/XLSX")
async def export_data(
    format: Literal["csv", "xlsx"] = Query(default="xlsx"),
    include_raw: bool = Query(default=False, description="รวม raw model results"),
):
    results = _enrich_results(_get_all_results())
    if not results:
        return {"message": "ไม่มีข้อมูลสำหรับ export"}

    cols = [
        "analysis_id", "call_id", "call_timestamp",
        "customer_id", "customer_name", "customer_account",
        "agent_id", "phone_number_used", "call_duration_seconds",
        "brand_name", "product_category", "sale_channel",
        "csat_score", "qa_score", "sentiment", "sentiment_score",
        "intent", "summary", "is_escalated", "created_at",
    ]
    df = pd.DataFrame(results).reindex(columns=cols)

    rename = {
        "analysis_id": "รหัสการวิเคราะห์", "call_id": "รหัสการโทร", "call_timestamp": "วันเวลาที่โทร",
        "customer_id": "รหัสลูกค้า", "customer_name": "ชื่อลูกค้า", "customer_account": "ประเภทบัญชี",
        "agent_id": "เจ้าหน้าที่", "phone_number_used": "เบอร์โทร", "call_duration_seconds": "ระยะเวลา (วินาที)",
        "brand_name": "แบรนด์", "product_category": "หมวดสินค้า", "sale_channel": "ช่องทางซื้อ",
        "csat_score": "CSAT (1-5)", "qa_score": "QA (0-10)", "sentiment": "ความรู้สึก",
        "sentiment_score": "ค่าความมั่นใจ", "intent": "ประเภทปัญหา", "summary": "สรุปสนทนา",
        "is_escalated": "Escalated", "created_at": "วันที่วิเคราะห์",
    }
    df = df.rename(columns=rename)

    if "Escalated" in df.columns:
        df["Escalated"] = df["Escalated"].map({True: "ใช่", False: "ไม่ใช่"})
    if "ความรู้สึก" in df.columns:
        df["ความรู้สึก"] = df["ความรู้สึก"].map({"positive": "เชิงบวก", "neutral": "เป็นกลาง", "negative": "เชิงลบ"}).fillna(df["ความรู้สึก"])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8-sig",
                                 headers={"Content-Disposition": f"attachment; filename=export_{ts}.csv"})
    else:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, sheet_name="ผลการวิเคราะห์", index=False)

            num_cols = ["CSAT (1-5)", "QA (0-10)", "ระยะเวลา (วินาที)"]
            existing = [c for c in num_cols if c in df.columns]
            if existing:
                sm = df[existing].agg(["mean", "min", "max", "std"]).round(2)
                sm.index = ["เฉลี่ย", "ต่ำสุด", "สูงสุด", "SD"]
                sm.to_excel(w, sheet_name="สรุปสถิติ")

            # Brand Summary
            if "แบรนด์" in df.columns and "CSAT (1-5)" in df.columns:
                bg = df.groupby("แบรนด์").agg({"CSAT (1-5)": "mean", "QA (0-10)": "mean"}).round(2).reset_index()
                bc = df["แบรนด์"].value_counts().reset_index()
                bc.columns = ["แบรนด์", "จำนวนสาย"]
                bm = bg.merge(bc, on="แบรนด์")
                bm.to_excel(w, sheet_name="Brand Summary", index=False)

            # Channel Summary
            if "ช่องทางซื้อ" in df.columns:
                cc = df["ช่องทางซื้อ"].value_counts().reset_index()
                cc.columns = ["ช่องทางซื้อ", "จำนวน"]
                cc.to_excel(w, sheet_name="Channel Summary", index=False)

            for sn in w.sheets:
                ws = w.sheets[sn]
                for col in ws.columns:
                    mx = max((len(str(c.value)) for c in col if c.value), default=10)
                    ws.column_dimensions[col[0].column_letter].width = min(mx + 4, 50)

        buf.seek(0)
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f"attachment; filename=export_{ts}.xlsx"})
