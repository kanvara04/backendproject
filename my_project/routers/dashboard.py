# =============================================================================
# routers/dashboard.py
# Dashboard Router — ข้อมูลสรุป, แนวโน้ม, AI Recommendations และ Export
#
# อธิบาย: Router นี้ดึงข้อมูลจาก Mock DB มาประมวลผลเชิงสถิติ
# แล้วส่งให้ Frontend แสดงใน Dashboard และ Export เป็นไฟล์
#
# Endpoints:
#   GET /overview        — ภาพรวม KPIs (CSAT, QA, Sentiment)
#   GET /trends          — แนวโน้มรายวัน/รายสัปดาห์
#   GET /intent-analysis — วิเคราะห์ประเภทปัญหาที่พบบ่อย
#   GET /recommendations — คำแนะนำจาก AI
#   GET /agent-ranking   — จัดอันดับเจ้าหน้าที่
#   GET /export          — Export เป็น CSV หรือ XLSX
# =============================================================================

import io
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from database.mock_db import MOCK_ANALYSIS_RESULTS, MOCK_CUSTOMERS

# =============================================================================
# STEP 1: สร้าง Router
# =============================================================================

router = APIRouter()

# โฟลเดอร์สำหรับเก็บไฟล์ export ชั่วคราว
EXPORT_DIR = Path(__file__).resolve().parent.parent / "storage" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# STEP 2: Helper Functions — ฟังก์ชันช่วยคำนวณสถิติ
# =============================================================================

def _get_all_results() -> list[dict]:
    """ดึงผลการวิเคราะห์ทั้งหมดจาก Mock DB เป็น list"""
    return list(MOCK_ANALYSIS_RESULTS.values())


def _safe_avg(values: list) -> float:
    """คำนวณค่าเฉลี่ย — คืน 0.0 ถ้า list ว่างเปล่า (ป้องกัน ZeroDivisionError)"""
    return round(sum(values) / len(values), 2) if values else 0.0


def _get_grade(score: float) -> str:
    """แปลง QA Score เป็น Grade เหมือน ai_mock_service"""
    if score >= 9.0: return "A+"
    if score >= 8.0: return "A"
    if score >= 7.0: return "B"
    if score >= 6.0: return "C"
    if score >= 5.0: return "D"
    return "F"


def _enrich_results(results: list[dict]) -> list[dict]:
    """
    เติมข้อมูลลูกค้าลงในผลการวิเคราะห์ (JOIN จำลอง)
    คล้ายกับ SQL: SELECT * FROM analysis LEFT JOIN customers USING (customer_id)
    """
    enriched = []
    for r in results:
        row = dict(r)  # copy ไม่แก้ของเดิม
        customer = MOCK_CUSTOMERS.get(r.get("customer_id", ""), {})
        row["customer_name"]    = customer.get("full_name", "ไม่ระบุ")
        row["customer_account"] = customer.get("account_type", "ไม่ระบุ")
        enriched.append(row)
    return enriched


# =============================================================================
# ENDPOINT 1: GET /overview
# =============================================================================
# ภาพรวม KPIs หลัก — ใช้แสดงใน "Summary Cards" บน Dashboard
# URL เต็ม: GET /api/v1/dashboard/overview
# =============================================================================

@router.get(
    "/overview",
    summary="📊 ภาพรวม KPIs ทั้งหมด",
    description="ดึงค่าสถิติรวม เช่น เฉลี่ย CSAT, QA Score, สัดส่วน Sentiment",
)
async def get_overview():
    """
    คำนวณ KPIs หลักจากข้อมูลทั้งหมดใน Mock DB
    
    ขั้นตอน:
    1. ดึงข้อมูลทั้งหมด
    2. แยก list ของค่าแต่ละ metric
    3. คำนวณสถิติ (avg, count, %)
    4. ส่งกลับเป็น structured dict
    """
    results = _get_all_results()

    if not results:
        return {"message": "ยังไม่มีข้อมูล", "total_calls": 0}

    # --- ขั้นที่ 1: แยก values ออกมาเป็น list ก่อน ---
    csat_scores = [r["csat_score"] for r in results if "csat_score" in r]
    qa_scores   = [r["qa_score"]   for r in results if "qa_score"   in r]
    sentiments  = [r["sentiment"]  for r in results if "sentiment"  in r]
    durations   = [r.get("call_duration_seconds", 0) for r in results]
    escalated   = [r for r in results if r.get("is_escalated", False)]

    # --- ขั้นที่ 2: นับ Sentiment Distribution ---
    sentiment_counts = Counter(sentiments)
    total = len(results)

    # --- ขั้นที่ 3: คำนวณสถิติ CSAT (1-5) ---
    avg_csat = _safe_avg(csat_scores)
    csat_distribution = Counter(csat_scores)

    # --- ขั้นที่ 4: คำนวณสถิติ QA Score (0-10) ---
    avg_qa = _safe_avg(qa_scores)

    return {
        "generated_at": datetime.now().isoformat(),
        "total_calls": total,

        # CSAT Summary
        "csat": {
            "average": avg_csat,
            "max_possible": 5,
            "percentage": round((avg_csat / 5) * 100, 1),
            "distribution": {
                "5_stars": csat_distribution.get(5, 0),
                "4_stars": csat_distribution.get(4, 0),
                "3_stars": csat_distribution.get(3, 0),
                "2_stars": csat_distribution.get(2, 0),
                "1_star":  csat_distribution.get(1, 0),
            },
        },

        # QA Score Summary
        "qa_score": {
            "average": avg_qa,
            "grade": _get_grade(avg_qa),
            "max_possible": 10.0,
            "calls_below_threshold": sum(1 for s in qa_scores if s < 6.0),
        },

        # Sentiment Summary
        "sentiment": {
            "positive_count":  sentiment_counts.get("positive", 0),
            "neutral_count":   sentiment_counts.get("neutral",  0),
            "negative_count":  sentiment_counts.get("negative", 0),
            "positive_rate_%": round(sentiment_counts.get("positive", 0) / total * 100, 1),
            "negative_rate_%": round(sentiment_counts.get("negative", 0) / total * 100, 1),
        },

        # Call Operations
        "operations": {
            "avg_duration_seconds": round(_safe_avg(durations), 1),
            "avg_duration_minutes": round(_safe_avg(durations) / 60, 2),
            "total_escalated":      len(escalated),
            "escalation_rate_%":    round(len(escalated) / total * 100, 1),
        },
    }


# =============================================================================
# ENDPOINT 2: GET /trends
# =============================================================================
# ข้อมูลแนวโน้มตามเวลา — ใช้แสดงเป็น Line Chart บน Dashboard
# URL เต็ม: GET /api/v1/dashboard/trends?days=7
# =============================================================================

@router.get(
    "/trends",
    summary="📈 แนวโน้มตามช่วงเวลา",
    description="ข้อมูล CSAT และ QA Score แบบรายวัน สำหรับแสดงเป็น Line Chart",
)
async def get_trends(
    days: int = Query(default=7, ge=1, le=90, description="จำนวนวันย้อนหลัง (1-90)"),
):
    """
    จัดกลุ่มข้อมูลตามวัน แล้วคำนวณค่าเฉลี่ยแต่ละวัน
    
    เทคนิค: ใช้ defaultdict(list) สร้าง "กลุ่มวัน" อัตโนมัติ
    ไม่ต้อง check ว่า key มีอยู่แล้วหรือเปล่า
    """
    results = _get_all_results()
    cutoff = datetime.now() - timedelta(days=days)

    # จัดกลุ่มข้อมูลตามวัน
    # key = "YYYY-MM-DD", value = list ของผลการวิเคราะห์วันนั้น
    daily_data: dict[str, list] = defaultdict(list)

    for r in results:
        try:
            call_dt = datetime.fromisoformat(r.get("call_timestamp", ""))
            if call_dt >= cutoff:
                date_key = call_dt.strftime("%Y-%m-%d")
                daily_data[date_key].append(r)
        except (ValueError, TypeError):
            continue  # ข้ามถ้า timestamp ผิดรูปแบบ

    # ถ้าข้อมูลน้อย ให้สร้าง mock trend ให้ดูสมจริง
    if len(daily_data) < 2:
        import random
        base_date = datetime.now()
        for i in range(days):
            d = base_date - timedelta(days=i)
            dk = d.strftime("%Y-%m-%d")
            if dk not in daily_data:
                # สร้าง mock entries สำหรับวันนี้
                mock_entries = [
                    {
                        "csat_score": random.randint(3, 5),
                        "qa_score":   round(random.uniform(6.0, 9.5), 1),
                        "sentiment":  random.choice(["positive", "positive", "neutral", "negative"]),
                        "is_escalated": random.random() < 0.1,
                    }
                    for _ in range(random.randint(5, 20))
                ]
                daily_data[dk] = mock_entries

    # สร้าง trend data แต่ละวัน
    trend_points = []
    for date_str in sorted(daily_data.keys()):
        day_results = daily_data[date_str]
        day_csat = [r.get("csat_score", 0) for r in day_results if r.get("csat_score")]
        day_qa   = [r.get("qa_score", 0)   for r in day_results if r.get("qa_score")]
        day_sent = [r.get("sentiment", "") for r in day_results]

        sent_counts = Counter(day_sent)
        n = len(day_results)

        trend_points.append({
            "date":              date_str,
            "total_calls":       n,
            "avg_csat":          _safe_avg(day_csat),
            "avg_qa_score":      _safe_avg(day_qa),
            "positive_calls":    sent_counts.get("positive", 0),
            "negative_calls":    sent_counts.get("negative", 0),
            "neutral_calls":     sent_counts.get("neutral",  0),
            "positive_rate_%":   round(sent_counts.get("positive", 0) / n * 100, 1) if n else 0,
            "escalated_calls":   sum(1 for r in day_results if r.get("is_escalated")),
        })

    return {
        "period_days":   days,
        "data_points":   len(trend_points),
        "trends":        trend_points,
    }


# =============================================================================
# ENDPOINT 3: GET /intent-analysis
# =============================================================================
# วิเคราะห์ประเภทปัญหาที่ลูกค้าโทรเข้ามาบ่อยที่สุด
# URL เต็ม: GET /api/v1/dashboard/intent-analysis
# =============================================================================

@router.get(
    "/intent-analysis",
    summary="🎯 วิเคราะห์ประเภทปัญหา (Topic Trends)",
    description="สรุปว่าลูกค้าโทรมาเรื่องอะไรบ่อยที่สุด พร้อม CSAT เฉลี่ยของแต่ละประเภท",
)
async def get_intent_analysis():
    """
    จัดกลุ่มผลการวิเคราะห์ตาม intent
    แล้วหาว่า intent ไหนมี CSAT ต่ำสุด (ปัญหาที่ต้องแก้ด่วน)
    """
    results = _get_all_results()

    # จัดกลุ่มตาม intent
    intent_groups: dict[str, list] = defaultdict(list)
    for r in results:
        intent = r.get("intent", "ไม่ระบุ")
        intent_groups[intent].append(r)

    # ถ้าข้อมูลน้อย เพิ่ม mock intents
    if len(intent_groups) < 3:
        mock_intents = {
            "สอบถามค่าบริการรายเดือน": [
                {"csat_score": 4, "qa_score": 8.0, "sentiment": "positive", "is_escalated": False},
                {"csat_score": 3, "qa_score": 7.5, "sentiment": "neutral",  "is_escalated": False},
                {"csat_score": 4, "qa_score": 8.5, "sentiment": "positive", "is_escalated": False},
            ],
            "แจ้งสินค้าชำรุด": [
                {"csat_score": 2, "qa_score": 5.5, "sentiment": "negative", "is_escalated": True},
                {"csat_score": 1, "qa_score": 4.0, "sentiment": "negative", "is_escalated": True},
            ],
            "ขอยกเลิกบริการ": [
                {"csat_score": 2, "qa_score": 6.0, "sentiment": "negative", "is_escalated": False},
                {"csat_score": 3, "qa_score": 7.0, "sentiment": "neutral",  "is_escalated": False},
            ],
            "แจ้งปัญหาด้านเทคนิค": [
                {"csat_score": 3, "qa_score": 7.2, "sentiment": "neutral",  "is_escalated": False},
                {"csat_score": 4, "qa_score": 8.1, "sentiment": "positive", "is_escalated": False},
                {"csat_score": 3, "qa_score": 6.8, "sentiment": "neutral",  "is_escalated": True},
            ],
            "ชมเชยเจ้าหน้าที่": [
                {"csat_score": 5, "qa_score": 9.8, "sentiment": "positive", "is_escalated": False},
            ],
        }
        for k, v in mock_intents.items():
            if k not in intent_groups:
                intent_groups[k] = v

    # สร้าง summary ของแต่ละ intent
    intent_summary = []
    for intent, group in intent_groups.items():
        csat_vals = [r.get("csat_score", 0) for r in group if r.get("csat_score")]
        qa_vals   = [r.get("qa_score", 0)   for r in group if r.get("qa_score")]
        sents     = [r.get("sentiment", "")  for r in group]
        sent_cnt  = Counter(sents)

        intent_summary.append({
            "intent":            intent,
            "call_count":        len(group),
            "avg_csat":          _safe_avg(csat_vals),
            "avg_qa_score":      _safe_avg(qa_vals),
            "escalation_count":  sum(1 for r in group if r.get("is_escalated")),
            "dominant_sentiment": sent_cnt.most_common(1)[0][0] if sent_cnt else "neutral",
            "negative_rate_%":   round(sent_cnt.get("negative", 0) / len(group) * 100, 1),
        })

    # เรียงตามจำนวนโทรมากไปน้อย
    intent_summary.sort(key=lambda x: x["call_count"], reverse=True)

    # หา intent ที่มี CSAT ต่ำสุด → ต้องให้ความสนใจ
    critical_intents = sorted(
        [i for i in intent_summary if i["avg_csat"] > 0],
        key=lambda x: x["avg_csat"]
    )[:3]

    return {
        "total_intents":     len(intent_summary),
        "intent_breakdown":  intent_summary,
        "critical_intents":  critical_intents,
        "top_intent":        intent_summary[0]["intent"] if intent_summary else None,
    }


# =============================================================================
# ENDPOINT 4: GET /recommendations
# =============================================================================
# คำแนะนำจาก AI — Rule-based ที่มาจากการวิเคราะห์ข้อมูล
# URL เต็ม: GET /api/v1/dashboard/recommendations
# =============================================================================

@router.get(
    "/recommendations",
    summary="💡 คำแนะนำ AI สำหรับการปรับปรุง",
    description="วิเคราะห์จุดอ่อนจากข้อมูลและสร้างคำแนะนำเชิงปฏิบัติ",
)
async def get_recommendations():
    """
    สร้างคำแนะนำโดยวิเคราะห์ pattern จากข้อมูล:
    - CSAT ต่ำ → แนะนำให้เพิ่มการ Training
    - Escalation สูง → แนะนำให้ปรับ Script
    - QA Score ต่ำ → แนะนำ Coaching เฉพาะบุคคล
    """
    results = _get_all_results()

    recommendations = []
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    # ---- วิเคราะห์ CSAT ----
    csat_scores = [r.get("csat_score", 0) for r in results if r.get("csat_score")]
    avg_csat = _safe_avg(csat_scores) if csat_scores else 3.5

    if avg_csat < 3.0:
        recommendations.append({
            "priority": "critical",
            "category": "Customer Satisfaction",
            "icon": "🔴",
            "title": "CSAT ต่ำกว่าเกณฑ์วิกฤต",
            "detail": f"ค่าเฉลี่ย CSAT อยู่ที่ {avg_csat}/5 ต่ำกว่า benchmark (3.5) อย่างมีนัยสำคัญ",
            "action": "จัดประชุม Emergency review ทันที และทบทวน Script การสนทนา",
            "expected_impact": "เพิ่ม CSAT ได้ 0.5-1.0 ภายใน 2 สัปดาห์",
        })
    elif avg_csat < 4.0:
        recommendations.append({
            "priority": "high",
            "category": "Customer Satisfaction",
            "icon": "🟠",
            "title": "CSAT ควรปรับปรุง",
            "detail": f"ค่าเฉลี่ย CSAT อยู่ที่ {avg_csat}/5 ยังต่ำกว่าเป้าหมาย (4.0)",
            "action": "จัด Training เรื่องการรับฟังและเห็นอกเห็นใจลูกค้า (Empathy Training)",
            "expected_impact": "เพิ่ม CSAT ได้ 0.3-0.5 ภายใน 1 เดือน",
        })

    # ---- วิเคราะห์ QA Score ----
    qa_scores = [r.get("qa_score", 0) for r in results if r.get("qa_score")]
    low_qa_calls = [s for s in qa_scores if s < 6.0]

    if len(low_qa_calls) > len(qa_scores) * 0.3:
        recommendations.append({
            "priority": "high",
            "category": "Quality Assurance",
            "icon": "🟠",
            "title": f"{len(low_qa_calls)} สายมี QA Score ต่ำกว่า 6.0",
            "detail": f"คิดเป็น {round(len(low_qa_calls)/len(qa_scores)*100, 1)}% ของสายทั้งหมด",
            "action": "จัด Coaching Session รายบุคคลกับเจ้าหน้าที่ที่มี QA ต่ำ",
            "expected_impact": "ลด Low-QA calls ได้ 40-60% ภายใน 3 สัปดาห์",
        })

    # ---- วิเคราะห์ Escalation ----
    escalated = [r for r in results if r.get("is_escalated", False)]
    escalation_rate = len(escalated) / len(results) * 100 if results else 0

    if escalation_rate > 20:
        recommendations.append({
            "priority": "critical",
            "category": "Operations",
            "icon": "🔴",
            "title": f"Escalation Rate สูงผิดปกติ ({escalation_rate:.1f}%)",
            "detail": "มากกว่า 20% ของสายถูก Escalate ไปยัง Supervisor",
            "action": "ทบทวน First-Call Resolution process และเพิ่ม Empowerment ให้เจ้าหน้าที่",
            "expected_impact": "ลด Escalation Rate ลง 50% ภายใน 1 เดือน",
        })
    elif escalation_rate > 10:
        recommendations.append({
            "priority": "medium",
            "category": "Operations",
            "icon": "🟡",
            "title": f"Escalation Rate ควรติดตาม ({escalation_rate:.1f}%)",
            "detail": "แนะนำให้รักษาระดับไว้ต่ำกว่า 10%",
            "action": "เพิ่ม Knowledge Base และ Decision Tree สำหรับเจ้าหน้าที่",
            "expected_impact": "ลด Escalation Rate ลง 20-30% ภายใน 6 สัปดาห์",
        })

    # ---- วิเคราะห์ Negative Sentiment ----
    sentiments = [r.get("sentiment", "") for r in results]
    neg_rate = sentiments.count("negative") / len(sentiments) * 100 if sentiments else 0

    if neg_rate > 40:
        recommendations.append({
            "priority": "high",
            "category": "Customer Experience",
            "icon": "🟠",
            "title": f"Negative Sentiment สูง ({neg_rate:.1f}%)",
            "detail": "ลูกค้ามากกว่า 40% มีความรู้สึกเชิงลบระหว่างการสนทนา",
            "action": "วิเคราะห์ Root Cause และปรับปรุง Product/Service ที่ก่อให้เกิดความไม่พอใจ",
            "expected_impact": "ลด Negative Sentiment ลง 15-25% ภายใน 2 เดือน",
        })

    # ถ้าทุกอย่างดี ส่งคำแนะนำเชิงบวก
    if not recommendations:
        recommendations.append({
            "priority": "low",
            "category": "General",
            "icon": "✅",
            "title": "ระบบทำงานได้ดีในมาตรฐานที่กำหนด",
            "detail": f"CSAT: {avg_csat}/5, QA เฉลี่ย: {_safe_avg(qa_scores)}/10",
            "action": "รักษามาตรฐานการบริการและพิจารณา benchmarking กับอุตสาหกรรม",
            "expected_impact": "รักษา Customer Retention ในระดับสูง",
        })

    # เรียงตาม priority
    recommendations.sort(key=lambda r: priority_order.get(r["priority"], 99))

    return {
        "generated_at":       datetime.now().isoformat(),
        "total_recommendations": len(recommendations),
        "recommendations":    recommendations,
        "data_based_on":      f"{len(results)} การโทร",
    }


# =============================================================================
# ENDPOINT 5: GET /agent-ranking
# =============================================================================
# จัดอันดับเจ้าหน้าที่ตาม QA Score และ CSAT
# URL เต็ม: GET /api/v1/dashboard/agent-ranking
# =============================================================================

@router.get(
    "/agent-ranking",
    summary="🏆 จัดอันดับเจ้าหน้าที่",
    description="เรียงลำดับเจ้าหน้าที่ตาม QA Score และ CSAT เฉลี่ย",
)
async def get_agent_ranking():
    """จัดกลุ่มผลการวิเคราะห์ตาม agent_id แล้วคำนวณค่าเฉลี่ยแต่ละคน"""
    results = _get_all_results()

    # เพิ่ม mock agent data ถ้าข้อมูลน้อย
    if len(results) < 3:
        import random
        mock_agents = ["AGENT-001", "AGENT-002", "AGENT-003", "AGENT-004", "AGENT-005"]
        for i in range(10):
            results.append({
                "agent_id":     random.choice(mock_agents),
                "csat_score":   random.randint(2, 5),
                "qa_score":     round(random.uniform(4.0, 9.8), 1),
                "sentiment":    random.choice(["positive", "neutral", "negative"]),
                "is_escalated": random.random() < 0.15,
                "call_duration_seconds": random.randint(60, 480),
            })

    # จัดกลุ่มตาม agent_id
    agent_groups: dict[str, list] = defaultdict(list)
    for r in results:
        agent_id = r.get("agent_id", "UNKNOWN")
        agent_groups[agent_id].append(r)

    # สร้าง stats ของแต่ละ agent
    agent_stats = []
    for agent_id, calls in agent_groups.items():
        csat_vals  = [c.get("csat_score", 0) for c in calls if c.get("csat_score")]
        qa_vals    = [c.get("qa_score",   0) for c in calls if c.get("qa_score")]
        avg_csat   = _safe_avg(csat_vals)
        avg_qa     = _safe_avg(qa_vals)

        agent_stats.append({
            "agent_id":         agent_id,
            "total_calls":      len(calls),
            "avg_csat":         avg_csat,
            "avg_qa_score":     avg_qa,
            "grade":            _get_grade(avg_qa),
            "escalation_count": sum(1 for c in calls if c.get("is_escalated")),
            "positive_calls":   sum(1 for c in calls if c.get("sentiment") == "positive"),
            "needs_coaching":   avg_qa < 6.0 or avg_csat < 3.0,
        })

    # เรียงตาม QA Score (สูงไปต่ำ) → ได้ Ranking
    agent_stats.sort(key=lambda a: a["avg_qa_score"], reverse=True)

    # ใส่ Rank
    for idx, agent in enumerate(agent_stats, start=1):
        agent["rank"] = idx

    return {
        "total_agents":   len(agent_stats),
        "agents_needing_coaching": sum(1 for a in agent_stats if a["needs_coaching"]),
        "ranking":        agent_stats,
    }


# =============================================================================
# ENDPOINT 6: GET /export
# =============================================================================
# Export ข้อมูลผลการวิเคราะห์เป็น CSV หรือ XLSX
#
# URL เต็ม: GET /api/v1/dashboard/export?format=xlsx
#
# อธิบายการทำงาน:
#   1. ดึงข้อมูลจาก Mock DB
#   2. แปลงเป็น pandas DataFrame
#   3. สร้างไฟล์ CSV หรือ XLSX ใน memory (BytesIO)
#   4. ส่งกลับเป็น StreamingResponse (ไม่บันทึกไฟล์ลงดิสก์จริง)
# =============================================================================

@router.get(
    "/export",
    summary="📥 Export ข้อมูลเป็น CSV หรือ XLSX",
    description="""
Export ผลการวิเคราะห์เสียงทั้งหมดเป็นไฟล์

**?format=csv** — Comma-Separated Values (เปิดได้ทุก tool)  
**?format=xlsx** — Excel Workbook พร้อม 3 sheets (Summary, Raw Data, Agent Stats)
    """,
)
async def export_data(
    format: Literal["csv", "xlsx"] = Query(
        default="xlsx",
        description="รูปแบบไฟล์ที่ต้องการ: csv หรือ xlsx"
    ),
    include_raw_model_results: bool = Query(
        default=False,
        description="รวม raw results จากแต่ละ AI model ด้วยหรือไม่ (ทำให้ไฟล์ใหญ่ขึ้น)"
    ),
):
    """
    ขั้นตอนการทำงาน Export:
    
    1. ดึงข้อมูลจาก MOCK_ANALYSIS_RESULTS
    2. Enrich ด้วยข้อมูลลูกค้า (JOIN จำลอง)
    3. สร้าง pandas DataFrame
    4. แปลงเป็น CSV หรือ XLSX ใน RAM (BytesIO)
    5. ส่งกลับเป็น StreamingResponse พร้อม Content-Disposition header
       → Browser จะ download ไฟล์ทันทีโดยไม่แสดงในหน้าต่าง
    """

    # --- ขั้นที่ 1: เตรียมข้อมูล ---
    results = _enrich_results(_get_all_results())

    # ถ้าไม่มีข้อมูลเลย สร้าง mock เพื่อให้ทดสอบได้
    if not results:
        import random
        from datetime import datetime, timedelta
        mock_intents = ["สอบถามค่าบริการ", "แจ้งสินค้าชำรุด", "ขอยกเลิกบริการ", "แจ้งปัญหาเทคนิค"]
        agents = ["AGENT-001", "AGENT-002", "AGENT-003", "AGENT-004", "AGENT-005"]
        customers = list(MOCK_CUSTOMERS.values())[:4]
        for i in range(20):
            cust = random.choice(customers) if customers else {}
            results.append({
                "analysis_id":            f"ANALYSIS-{i+1:03d}",
                "call_id":                f"CALL-2024{random.randint(100,999)}-{i:03d}",
                "customer_id":            cust.get("customer_id", "CUST-001"),
                "customer_name":          cust.get("full_name", "ทดสอบ"),
                "customer_account":       cust.get("account_type", "Standard"),
                "agent_id":               random.choice(agents),
                "phone_number_used":      cust.get("primary_phone", "0800000000"),
                "call_duration_seconds":  random.randint(60, 480),
                "call_timestamp":         (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                "csat_score":             random.randint(1, 5),
                "intent":                 random.choice(mock_intents),
                "qa_score":               round(random.uniform(4.0, 9.8), 1),
                "sentiment":              random.choice(["positive", "neutral", "negative"]),
                "sentiment_score":        round(random.uniform(0.6, 0.95), 3),
                "summary":                f"สรุปการสนทนาครั้งที่ {i+1}",
                "is_escalated":           random.random() < 0.15,
                "created_at":             datetime.now().isoformat(),
            })

    # --- ขั้นที่ 2: เลือก Columns ที่จะ Export ---
    export_columns = [
        "analysis_id", "call_id", "call_timestamp",
        "customer_id", "customer_name", "customer_account",
        "agent_id", "phone_number_used",
        "call_duration_seconds",
        "csat_score", "qa_score", "sentiment", "sentiment_score",
        "intent", "summary", "is_escalated", "created_at",
    ]

    if include_raw_model_results and results and "model_results" in results[0]:
        export_columns.append("model_results")

    # --- ขั้นที่ 3: สร้าง DataFrame ---
    # pandas DataFrame คือตารางข้อมูลที่จัดการได้ง่าย
    # ใช้ reindex() เพื่อเลือกเฉพาะ columns ที่ต้องการ (ไม่ error ถ้าบางคอลัมน์ไม่มี)
    df = pd.DataFrame(results).reindex(columns=export_columns)

    # ปรับ column headers ให้อ่านง่าย (ภาษาไทย)
    column_rename = {
        "analysis_id":            "รหัสการวิเคราะห์",
        "call_id":                "รหัสการโทร",
        "call_timestamp":         "วันเวลาที่โทร",
        "customer_id":            "รหัสลูกค้า",
        "customer_name":          "ชื่อลูกค้า",
        "customer_account":       "ประเภทบัญชี",
        "agent_id":               "รหัสเจ้าหน้าที่",
        "phone_number_used":      "เบอร์โทรที่ใช้",
        "call_duration_seconds":  "ระยะเวลาการโทร (วินาที)",
        "csat_score":             "CSAT Score (1-5)",
        "qa_score":               "QA Score (0-10)",
        "sentiment":              "ความรู้สึก",
        "sentiment_score":        "ค่าความมั่นใจ Sentiment",
        "intent":                 "ประเภทปัญหา",
        "summary":                "สรุปการสนทนา",
        "is_escalated":           "มีการ Escalate",
        "created_at":             "วันที่วิเคราะห์",
    }
    df = df.rename(columns=column_rename)

    # แปลง True/False เป็นภาษาไทย
    if "มีการ Escalate" in df.columns:
        df["มีการ Escalate"] = df["มีการ Escalate"].map({True: "ใช่", False: "ไม่ใช่"})

    # แปลง sentiment เป็นภาษาไทย
    if "ความรู้สึก" in df.columns:
        df["ความรู้สึก"] = df["ความรู้สึก"].map({
            "positive": "เชิงบวก",
            "neutral":  "เป็นกลาง",
            "negative": "เชิงลบ",
        }).fillna(df["ความรู้สึก"])

    # --- ขั้นที่ 4: สร้างไฟล์ตามรูปแบบที่เลือก ---

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        # =========================================================
        # CSV Export
        # =========================================================
        # io.StringIO() = "ไฟล์ใน RAM" แบบ text
        # ไม่ต้องเขียนลงดิสก์จริง → เร็ว, ประหยัด disk I/O
        # =========================================================
        buffer = io.StringIO()
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        # utf-8-sig: เพิ่ม BOM character ให้ Excel อ่าน UTF-8 ได้ถูกต้อง (ป้องกันภาษาไทยเพี้ยน)
        buffer.seek(0)  # กลับไปต้น buffer ก่อนส่ง

        filename = f"ai_analysis_export_{timestamp}.csv"
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv; charset=utf-8-sig",
            headers={
                # Content-Disposition: attachment = บังคับให้ download (ไม่แสดงใน browser)
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Total-Records": str(len(df)),
            }
        )

    else:  # xlsx
        # =========================================================
        # XLSX Export — Multi-Sheet Excel
        # =========================================================
        # io.BytesIO() = "ไฟล์ใน RAM" แบบ binary
        # pandas ใช้ openpyxl เขียนลง BytesIO โดยตรง
        # =========================================================
        buffer = io.BytesIO()

        # ExcelWriter ช่วยให้เขียนหลาย Sheet ในไฟล์เดียว
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:

            # --- Sheet 1: ข้อมูลหลักทั้งหมด ---
            df.to_excel(writer, sheet_name="ผลการวิเคราะห์", index=False)

            # --- Sheet 2: สรุปสถิติ (Summary Stats) ---
            numeric_cols = ["CSAT Score (1-5)", "QA Score (0-10)", "ระยะเวลาการโทร (วินาที)"]
            existing_numeric = [c for c in numeric_cols if c in df.columns]

            if existing_numeric:
                summary_df = df[existing_numeric].agg(["mean", "min", "max", "std"]).round(2)
                summary_df.index = ["ค่าเฉลี่ย", "ค่าต่ำสุด", "ค่าสูงสุด", "ค่าเบี่ยงเบนมาตรฐาน"]
                summary_df.to_excel(writer, sheet_name="สรุปสถิติ")

            # --- Sheet 3: จำนวนแต่ละ Sentiment ---
            if "ความรู้สึก" in df.columns:
                sentiment_count = df["ความรู้สึก"].value_counts().reset_index()
                sentiment_count.columns = ["ความรู้สึก", "จำนวน"]
                sentiment_count.to_excel(writer, sheet_name="Sentiment Summary", index=False)

            # --- ปรับ column width อัตโนมัติ ---
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for col in worksheet.columns:
                    max_len = max(
                        (len(str(cell.value)) for cell in col if cell.value),
                        default=10
                    )
                    # จำกัดความกว้างไม่เกิน 50 ตัวอักษร
                    worksheet.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

        buffer.seek(0)
        filename = f"ai_analysis_export_{timestamp}.xlsx"

        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Total-Records": str(len(df)),
                "X-Sheets": "3",
            }
        )
