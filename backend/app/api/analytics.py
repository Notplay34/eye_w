from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import RequireAnalyticsAccess, UserInfo
from app.core.database import get_db
from app.models import Order, Payment, PaymentType
from app.schemas.analytics import (
    TodayAnalytics,
    MonthAnalytics,
    EmployeesAnalytics,
    EmployeeStat,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _start_end_today(date_from: Optional[str] = None, date_to: Optional[str] = None):
    d_from = _parse_date(date_from)
    d_to = _parse_date(date_to)
    if d_from and d_to:
        start = datetime.combine(d_from, datetime.min.time())
        end = datetime.combine(d_to, datetime.min.time()) + timedelta(days=1)
        return start, end
    if d_from:
        start = datetime.combine(d_from, datetime.min.time())
        return start, start + timedelta(days=1)
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)
    return start, end


def _start_end_month(date_from: Optional[str] = None, date_to: Optional[str] = None):
    d_from = _parse_date(date_from)
    d_to = _parse_date(date_to)
    if d_from and d_to:
        start = datetime.combine(d_from, datetime.min.time())
        end = datetime.combine(d_to, datetime.min.time()) + timedelta(days=1)
        return start, end
    if d_from:
        start = datetime.combine(d_from, datetime.min.time())
        if d_from.month == 12:
            end = datetime(d_from.year + 1, 1, 1)
        else:
            end = datetime(d_from.year, d_from.month + 1, 1)
        return start, end
    today = date.today()
    start = datetime(today.year, today.month, 1)
    if today.month == 12:
        end = datetime(today.year + 1, 1, 1)
    else:
        end = datetime(today.year, today.month + 1, 1)
    return start, end


@router.get("/today", response_model=TodayAnalytics)
async def analytics_today(
    date_from: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    start, end = _start_end_today(date_from, date_to)
    # Считаем по платежам за сегодня
    q = (
        select(
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
            func.count(func.distinct(Payment.order_id)).label("cnt"),
        )
        .where(Payment.created_at >= start, Payment.created_at < end)
    )
    total_row = (await db.execute(q)).one()
    total_revenue = total_row.total or Decimal("0")
    orders_count = total_row.cnt or 0

    q_duty = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.STATE_DUTY,
        )
    )
    duty = (await db.execute(q_duty)).scalar_one() or Decimal("0")

    q_p1 = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.INCOME_PAVILION1,
        )
    )
    p1 = (await db.execute(q_p1)).scalar_one() or Decimal("0")

    q_p2 = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.INCOME_PAVILION2,
        )
    )
    p2 = (await db.execute(q_p2)).scalar_one() or Decimal("0")

    avg = (total_revenue / orders_count) if orders_count else Decimal("0")
    return TodayAnalytics(
        total_revenue=total_revenue,
        state_duty_total=duty,
        income_pavilion1=p1,
        income_pavilion2=p2,
        orders_count=orders_count,
        average_cheque=avg,
    )


@router.get("/month", response_model=MonthAnalytics)
async def analytics_month(
    date_from: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    start, end = _start_end_month(date_from, date_to)
    q = (
        select(
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
            func.count(func.distinct(Payment.order_id)).label("cnt"),
        )
        .where(Payment.created_at >= start, Payment.created_at < end)
    )
    total_row = (await db.execute(q)).one()
    total_revenue = total_row.total or Decimal("0")
    orders_count = total_row.cnt or 0

    q_duty = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.STATE_DUTY,
        )
    )
    duty = (await db.execute(q_duty)).scalar_one() or Decimal("0")

    q_p1 = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.INCOME_PAVILION1,
        )
    )
    p1 = (await db.execute(q_p1)).scalar_one() or Decimal("0")

    q_p2 = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.INCOME_PAVILION2,
        )
    )
    p2 = (await db.execute(q_p2)).scalar_one() or Decimal("0")

    avg = (total_revenue / orders_count) if orders_count else Decimal("0")
    return MonthAnalytics(
        total_revenue=total_revenue,
        state_duty_total=duty,
        income_pavilion1=p1,
        income_pavilion2=p2,
        orders_count=orders_count,
        average_cheque=avg,
    )


@router.get("/employees", response_model=EmployeesAnalytics)
async def analytics_employees(
    period: str = Query("day", description="day | month"),
    date_from: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    if period == "month":
        start, end = _start_end_month(date_from, date_to)
    else:
        start, end = _start_end_today(date_from, date_to)

    from app.models import Employee

    q = (
        select(
            Payment.employee_id,
            func.count(func.distinct(Payment.order_id)).label("cnt"),
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
        )
        .where(Payment.created_at >= start, Payment.created_at < end)
        .group_by(Payment.employee_id)
    )
    result = await db.execute(q)
    rows = result.all()

    stats = []
    for row in rows:
        emp_id = row.employee_id
        if emp_id is None:
            name = "—"
        else:
            emp = (await db.execute(select(Employee).where(Employee.id == emp_id))).scalar_one_or_none()
            name = emp.name if emp else str(emp_id)
        stats.append(
            EmployeeStat(
                employee_id=emp_id or 0,
                employee_name=name,
                orders_count=row.cnt or 0,
                total_amount=row.total or Decimal("0"),
            )
        )
    return EmployeesAnalytics(period=period, employees=stats)


@router.get("/export")
async def analytics_export(
    format: str = Query("csv", description="csv"),
    period: str = Query("day", description="day | month | employees"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    """Экспорт аналитики в CSV."""
    from app.models import Employee
    if period == "month":
        start, end = _start_end_month(date_from, date_to)
    elif period == "employees":
        start, end = _start_end_today(date_from, date_to)
    else:
        start, end = _start_end_today(date_from, date_to)

    def _row(*cells):
        return ",".join('"' + str(c).replace('"', '""') + '"' for c in cells) + "\r\n"

    async def _stream():
        if period == "employees":
            q = (
                select(
                    Payment.employee_id,
                    func.count(func.distinct(Payment.order_id)).label("cnt"),
                    func.coalesce(func.sum(Payment.amount), 0).label("total"),
                )
                .where(Payment.created_at >= start, Payment.created_at < end)
                .group_by(Payment.employee_id)
            )
            result = await db.execute(q)
            rows = result.all()
            lines = [_row("Сотрудник", "Заказов", "Сумма, ₽")]
            for r in rows:
                emp_id = r.employee_id
                if emp_id is None:
                    name = "—"
                else:
                    emp = (await db.execute(select(Employee).where(Employee.id == emp_id))).scalar_one_or_none()
                    name = emp.name if emp else str(emp_id)
                lines.append(_row(name, r.cnt or 0, float(r.total or 0)))
            return "".join(lines)
        else:
            total_row = (await db.execute(
                select(
                    func.coalesce(func.sum(Payment.amount), 0).label("total"),
                    func.count(func.distinct(Payment.order_id)).label("cnt"),
                ).where(Payment.created_at >= start, Payment.created_at < end)
            )).one()
            duty = (await db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(
                    Payment.created_at >= start,
                    Payment.created_at < end,
                    Payment.type == PaymentType.STATE_DUTY,
                )
            )).scalar_one() or Decimal("0")
            p1 = (await db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(
                    Payment.created_at >= start,
                    Payment.created_at < end,
                    Payment.type == PaymentType.INCOME_PAVILION1,
                )
            )).scalar_one() or Decimal("0")
            p2 = (await db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(
                    Payment.created_at >= start,
                    Payment.created_at < end,
                    Payment.type == PaymentType.INCOME_PAVILION2,
                )
            )).scalar_one() or Decimal("0")
            total = total_row.total or Decimal("0")
            cnt = total_row.cnt or 0
            avg = (total / cnt) if cnt else Decimal("0")
            lines = [
                _row("Показатель", "Значение"),
                _row("Период", f"{start.date()} — {end.date()}"),
                _row("", ""),
                _row("Выручка всего", float(total)),
                _row("Оплаченных заказов", cnt),
                _row("Средний чек", float(avg)),
                _row("Госпошлина", float(duty)),
                _row("Доход павильон 1", float(p1)),
                _row("Доход павильон 2", float(p2)),
            ]
            return "".join(lines)

    content = await _stream()
    content = "\ufeff" + content  # BOM for Excel UTF-8
    filename = f"analytics_{period}_{start.date()}_{end.date()}.csv"
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
