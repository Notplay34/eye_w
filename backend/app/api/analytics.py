from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Order, Payment, PaymentType
from app.schemas.analytics import (
    TodayAnalytics,
    MonthAnalytics,
    EmployeesAnalytics,
    EmployeeStat,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _start_end_today():
    today = date.today()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)
    return start, end


def _start_end_month():
    today = date.today()
    start = datetime(today.year, today.month, 1)
    if today.month == 12:
        end = datetime(today.year + 1, 1, 1)
    else:
        end = datetime(today.year, today.month + 1, 1)
    return start, end


@router.get("/today", response_model=TodayAnalytics)
async def analytics_today(db: AsyncSession = Depends(get_db)):
    start, end = _start_end_today()
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
async def analytics_month(db: AsyncSession = Depends(get_db)):
    start, end = _start_end_month()
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
    db: AsyncSession = Depends(get_db),
):
    if period == "month":
        start, end = _start_end_month()
    else:
        start, end = _start_end_today()

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
