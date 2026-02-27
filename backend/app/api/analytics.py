from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import RequireAnalyticsAccess, UserInfo
from app.core.database import get_db
from app.models import Order, Payment, PaymentType
from app.schemas.analytics import (
    TodayAnalytics,
    MonthAnalytics,
    EmployeesAnalytics,
    EmployeeStat,
    BaseAnalyticsBlock,
    SummaryAnalytics,
    DynamicsAnalytics,
    DynamicsPoint,
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


def _period_bounds(period: str, date_from: Optional[str], date_to: Optional[str]) -> Tuple[datetime, datetime]:
    """Границы периода для summary/dynamics."""
    if period == "month":
        return _start_end_month(date_from, date_to)
    # day или week считаем от _start_end_today, который может покрывать несколько дней
    start, end = _start_end_today(date_from, date_to)
    if period == "week":
        # Нормализуем к началу недели (понедельник) и 7 дням
        start_date = start.date()
        start_date = start_date - timedelta(days=start_date.weekday())
        start = datetime.combine(start_date, datetime.min.time())
        end = start + timedelta(days=7)
    return start, end


def _previous_period(start: datetime, end: datetime) -> Tuple[datetime, datetime]:
    """Предыдущий период такой же длины."""
    delta = end - start
    prev_end = start
    prev_start = prev_end - delta
    return prev_start, prev_end


async def _calc_block(db: AsyncSession, start: datetime, end: datetime) -> BaseAnalyticsBlock:
    q_total = (
        select(
            func.coalesce(func.sum(Payment.amount), 0).label("total"),
            func.count(func.distinct(Payment.order_id)).label("cnt"),
        )
        .where(Payment.created_at >= start, Payment.created_at < end)
    )
    total_row = (await db.execute(q_total)).one()
    total_revenue: Decimal = total_row.total or Decimal("0")
    orders_count: int = total_row.cnt or 0

    q_duty = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.STATE_DUTY,
        )
    )
    duty: Decimal = (await db.execute(q_duty)).scalar_one() or Decimal("0")

    q_p1 = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.INCOME_PAVILION1,
        )
    )
    p1: Decimal = (await db.execute(q_p1)).scalar_one() or Decimal("0")

    q_p2 = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(
            Payment.created_at >= start,
            Payment.created_at < end,
            Payment.type == PaymentType.INCOME_PAVILION2,
        )
    )
    p2: Decimal = (await db.execute(q_p2)).scalar_one() or Decimal("0")

    net_income = total_revenue - duty
    avg = (total_revenue / orders_count) if orders_count else Decimal("0")

    return BaseAnalyticsBlock(
        total_revenue=total_revenue,
        state_duty_total=duty,
        net_income=net_income,
        income_pavilion1=p1,
        income_pavilion2=p2,
        orders_count=orders_count,
        average_check=avg,
    )


@router.get("/today", response_model=TodayAnalytics)
async def analytics_today(
    date_from: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    start, end = _start_end_today(date_from, date_to)
    block = await _calc_block(db, start, end)
    # TodayAnalytics совместим по полям с BaseAnalyticsBlock
    return TodayAnalytics(**block.dict())


@router.get("/month", response_model=MonthAnalytics)
async def analytics_month(
    date_from: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    start, end = _start_end_month(date_from, date_to)
    block = await _calc_block(db, start, end)
    return MonthAnalytics(**block.dict())


@router.get("/employees", response_model=EmployeesAnalytics)
async def analytics_employees(
    period: str = Query("day", description="day | week | month"),
    date_from: Optional[str] = Query(None, description="Начало периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Конец периода (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    if period not in {"day", "week", "month"}:
        period = "day"
    start, end = _period_bounds(period, date_from, date_to)

    from app.models import Employee

    # Общая выручка за период для расчёта долей
    q_total = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.created_at >= start, Payment.created_at < end)
    )
    total_revenue: Decimal = (await db.execute(q_total)).scalar_one() or Decimal("0")

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

    stats: List[EmployeeStat] = []
    for row in rows:
        emp_id = row.employee_id
        if emp_id is None:
            name = "—"
        else:
            emp = (await db.execute(select(Employee).where(Employee.id == emp_id))).scalar_one_or_none()
            name = emp.name if emp else str(emp_id)
        total_amount: Decimal = row.total or Decimal("0")
        orders_count = row.cnt or 0
        average_check = (total_amount / orders_count) if orders_count else Decimal("0")
        share_percent = (
            (total_amount / total_revenue * Decimal("100")) if total_revenue else Decimal("0")
        )
        stats.append(
            EmployeeStat(
                employee_id=emp_id or 0,
                employee_name=name,
                orders_count=orders_count,
                total_amount=total_amount,
                average_check=average_check,
                share_percent=share_percent,
            )
        )
    return EmployeesAnalytics(period=period, total_revenue=total_revenue, employees=stats)


@router.get("/summary", response_model=SummaryAnalytics)
async def analytics_summary(
    period: str = Query("day", description="day | week | month"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    """Управленческая сводка: текущий и предыдущий периоды."""
    if period not in {"day", "week", "month"}:
        period = "day"

    start, end = _period_bounds(period, date_from, date_to)
    prev_start, prev_end = _previous_period(start, end)

    current_block = await _calc_block(db, start, end)
    previous_block = await _calc_block(db, prev_start, prev_end)

    return SummaryAnalytics(period=period, current=current_block, previous=previous_block)


@router.get("/dynamics", response_model=DynamicsAnalytics)
async def analytics_dynamics(
    group_by: str = Query("day", description="day | week | month"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    """Динамика показателей по дням/неделям/месяцам."""
    if group_by not in {"day", "week", "month"}:
        group_by = "day"

    start, end = _period_bounds(group_by, date_from, date_to)

    # date_trunc вернёт начало соответствующего периода (дня/недели/месяца)
    trunc_unit = "day" if group_by == "day" else "week" if group_by == "week" else "month"
    period_expr = func.date_trunc(trunc_unit, Payment.created_at).label("period_start")

    duty_sum = func.coalesce(
        func.sum(
            case(
                (Payment.type == PaymentType.STATE_DUTY, Payment.amount),
                else_=0,
            )
        ),
        0,
    ).label("state_duty_total")

    p1_sum = func.coalesce(
        func.sum(
            case(
                (Payment.type == PaymentType.INCOME_PAVILION1, Payment.amount),
                else_=0,
            )
        ),
        0,
    ).label("income_pavilion1")

    p2_sum = func.coalesce(
        func.sum(
            case(
                (Payment.type == PaymentType.INCOME_PAVILION2, Payment.amount),
                else_=0,
            )
        ),
        0,
    ).label("income_pavilion2")

    q = (
        select(
            period_expr,
            func.coalesce(func.sum(Payment.amount), 0).label("total_revenue"),
            duty_sum,
            p1_sum,
            p2_sum,
            func.count(func.distinct(Payment.order_id)).label("orders_count"),
        )
        .where(Payment.created_at >= start, Payment.created_at < end)
        .group_by(period_expr)
        .order_by(period_expr)
    )

    result = await db.execute(q)
    rows = result.all()

    points: List[DynamicsPoint] = []
    for row in rows:
        total_revenue: Decimal = row.total_revenue or Decimal("0")
        duty: Decimal = row.state_duty_total or Decimal("0")
        net_income: Decimal = total_revenue - duty
        p1: Decimal = row.income_pavilion1 or Decimal("0")
        p2: Decimal = row.income_pavilion2 or Decimal("0")
        orders_count: int = row.orders_count or 0

        # period_start приводим к ISO-дате
        period_start_dt: datetime = row.period_start
        period_start_str = period_start_dt.date().isoformat()

        points.append(
            DynamicsPoint(
                period_start=period_start_str,
                total_revenue=total_revenue,
                net_income=net_income,
                income_pavilion1=p1,
                income_pavilion2=p2,
                orders_count=orders_count,
            )
        )

    return DynamicsAnalytics(group_by=group_by, points=points)


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
