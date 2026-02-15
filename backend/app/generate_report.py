from io import BytesIO
from datetime import datetime
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


def _fmt_dt(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _draw_wrapped(c, text: str, x: float, y: float, max_width: float, leading: float) -> float:
    lines = simpleSplit(text or "", c._fontname, c._fontsize, max_width)
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    return y


def generate_competency_report(
    candidate_profile,
    session,
    seasons,
    competencies: list[dict],
    recommendations: list[str],
) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left = 20 * mm
    right = width - 20 * mm
    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, "Business Cats — Отчёт компетенций кандидата")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Данные кандидата")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    profile_lines = [
        f"ФИО: {getattr(candidate_profile, 'full_name', '')}",
        f"Город: {getattr(candidate_profile, 'city', '')}",
        f"Университет: {getattr(candidate_profile, 'university', '')}",
        f"Программа: {getattr(candidate_profile, 'program', '')}",
        f"Курс: {getattr(candidate_profile, 'study_year', '')}",
    ]
    for line in profile_lines:
        c.drawString(left, y, line)
        y -= 5 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Сводка по сессии")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    session_lines = [
        f"Session ID: {session.id}",
        f"Роль: {session.assigned_role}",
        f"Старт: {_fmt_dt(session.started_at)}",
        f"Финиш: {_fmt_dt(session.finished_at)}",
        f"Итог игрока: {session.result_coins_player}, бот: {session.result_coins_bot}",
    ]
    for line in session_lines:
        c.drawString(left, y, line)
        y -= 5 * mm

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Компетенции")
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Название")
    c.drawString(left + 110 * mm, y, "Score")
    c.drawString(left + 130 * mm, y, "Explanation")
    y -= 5 * mm
    c.setFont("Helvetica", 9)

    for item in competencies:
        name = item.get("name", "")
        score = str(item.get("score", ""))
        explanation = item.get("explanation", "")
        c.drawString(left, y, name[:48])
        c.drawString(left + 110 * mm, y, score)
        y = _draw_wrapped(c, explanation, left + 130 * mm, y, right - (left + 130 * mm), 4 * mm)
        y -= 3 * mm
        if y < 25 * mm:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 20 * mm

    y -= 2 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Recommendations")
    y -= 6 * mm
    c.setFont("Helvetica", 10)
    for rec in recommendations:
        y = _draw_wrapped(c, f"• {rec}", left, y, right - left, 5 * mm)
        y -= 2 * mm
        if y < 25 * mm:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - 20 * mm

    y -= 2 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "История по сезонам")
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Season")
    c.drawString(left + 25 * mm, y, "Profit")
    c.drawString(left + 45 * mm, y, "DebtEnd")
    c.drawString(left + 70 * mm, y, "FinishEarly")
    y -= 5 * mm
    c.setFont("Helvetica", 9)

    for s in seasons:
        meta = {}
        try:
            meta = json.loads(s.meta_json or "{}")
        except Exception:
            meta = {}
        debt_end = meta.get("debtEnd", 0)
        finish_early = bool(meta.get("finishEarly", False))
        c.drawString(left, y, str(s.season_number))
        c.drawString(left + 25 * mm, y, str(s.profit))
        c.drawString(left + 45 * mm, y, str(debt_end))
        c.drawString(left + 70 * mm, y, "yes" if finish_early else "no")
        y -= 4 * mm
        if y < 25 * mm:
            c.showPage()
            c.setFont("Helvetica", 9)
            y = height - 20 * mm

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
