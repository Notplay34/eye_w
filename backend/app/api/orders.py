from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.api.auth import RequireFormAccess, RequireAnalyticsAccess, RequireOrdersListAccess, RequirePlateAccess, UserInfo

logger = get_logger(__name__)
from app.models import Order, OrderStatus, Payment, PaymentType, Employee, CashShift, ShiftStatus
from pydantic import BaseModel

from app.schemas.order import OrderCreate, OrderResponse, OrderDetailResponse
from app.schemas.payment import PayOrderResponse
from app.services.order_service import create_order
from app.services.order_status import can_transition

router = APIRouter(prefix="/orders", tags=["orders"])


async def _get_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def _current_shift_id(db: AsyncSession, pavilion: int) -> Optional[int]:
    """Текущая открытая смена по павильону (1 или 2). Возвращает id смены или None."""
    q = (
        select(CashShift.id)
        .where(CashShift.pavilion == pavilion, CashShift.status == ShiftStatus.OPEN)
        .order_by(CashShift.opened_at.desc())
        .limit(1)
    )
    r = await db.execute(q)
    return r.scalar_one_or_none()


@router.post("", response_model=OrderResponse)
async def post_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireFormAccess),
):
    order = await create_order(db, data)
    logger.info("Создан заказ id=%s public_id=%s", order.id, order.public_id)
    return OrderResponse(
        id=order.id,
        public_id=order.public_id,
        status=order.status.value,
        total_amount=order.total_amount,
        state_duty_amount=order.state_duty_amount,
        income_pavilion1=order.income_pavilion1,
        income_pavilion2=order.income_pavilion2,
        need_plate=order.need_plate,
        service_type=order.service_type,
        created_at=order.created_at.isoformat() if order.created_at else "",
    )


@router.post("/{order_id}/pay", response_model=PayOrderResponse)
async def pay_order(
    order_id: int,
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user: UserInfo = Depends(RequireFormAccess),
):
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if not can_transition(order.status, OrderStatus.PAID):
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя принять оплату для заказа со статусом {order.status.value}",
        )
    emp_id = employee_id if employee_id is not None else user.id
    shift_1 = await _current_shift_id(db, 1)
    shift_2 = await _current_shift_id(db, 2)
    if order.state_duty_amount > 0:
        db.add(
            Payment(
                order_id=order.id,
                amount=order.state_duty_amount,
                type=PaymentType.STATE_DUTY,
                employee_id=emp_id,
                shift_id=shift_1,
            )
        )
    if order.income_pavilion1 > 0:
        db.add(
            Payment(
                order_id=order.id,
                amount=order.income_pavilion1,
                type=PaymentType.INCOME_PAVILION1,
                employee_id=emp_id,
                shift_id=shift_1,
            )
        )
    if order.income_pavilion2 > 0:
        db.add(
            Payment(
                order_id=order.id,
                amount=order.income_pavilion2,
                type=PaymentType.INCOME_PAVILION2,
                employee_id=emp_id,
                shift_id=shift_2,
            )
        )
    order.status = OrderStatus.PAID
    db.add(order)
    await db.flush()
    logger.info("Оплата принята по заказу id=%s", order.id)
    return PayOrderResponse(
        order_id=order.id,
        public_id=order.public_id,
        status=OrderStatus.PAID.value,
    )


@router.get("/plate-list")
async def list_orders_for_plate(
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequirePlateAccess),
):
    """Список заказов с номерами для павильона 2: клиент, сумма, оплачено, долг."""
    from sqlalchemy import func

    q = (
        select(Order, func.coalesce(func.sum(Payment.amount), 0).label("total_paid"))
        .outerjoin(Payment, Payment.order_id == Order.id)
        .where(Order.need_plate == True)
        .where(Order.status.in_([OrderStatus.PAID, OrderStatus.PLATE_IN_PROGRESS, OrderStatus.PLATE_READY, OrderStatus.PROBLEM]))
        .group_by(Order.id)
        .order_by(Order.created_at.desc())
        .limit(100)
    )
    result = await db.execute(q)
    rows = result.all()
    out = []
    for order, total_paid in rows:
        total_paid = float(total_paid or 0)
        fd = order.form_data or {}
        client = fd.get("client_fio") or fd.get("client_legal_name") or "—"
        out.append({
            "id": order.id,
            "public_id": order.public_id,
            "status": order.status.value,
            "total_amount": float(order.total_amount),
            "income_pavilion2": float(order.income_pavilion2),
            "client": client,
            "total_paid": total_paid,
            "debt": float(order.total_amount) - total_paid,
            "created_at": order.created_at.isoformat() if order.created_at else "",
        })
    return out


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status: Optional[OrderStatus] = None,
    need_plate: Optional[bool] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireOrdersListAccess),
):
    q = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status is not None:
        q = q.where(Order.status == status)
    if need_plate is not None:
        q = q.where(Order.need_plate == need_plate)
    result = await db.execute(q)
    orders = result.scalars().all()
    return [
        OrderResponse(
            id=o.id,
            public_id=o.public_id,
            status=o.status.value,
            total_amount=o.total_amount,
            state_duty_amount=o.state_duty_amount,
            income_pavilion1=o.income_pavilion1,
            income_pavilion2=o.income_pavilion2,
            need_plate=o.need_plate,
            service_type=o.service_type,
            created_at=o.created_at.isoformat() if o.created_at else "",
        )
        for o in orders
    ]


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireOrdersListAccess),
):
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return OrderResponse(
        id=order.id,
        public_id=order.public_id,
        status=order.status.value,
        total_amount=order.total_amount,
        state_duty_amount=order.state_duty_amount,
        income_pavilion1=order.income_pavilion1,
        income_pavilion2=order.income_pavilion2,
        need_plate=order.need_plate,
        service_type=order.service_type,
        created_at=order.created_at.isoformat() if order.created_at else "",
    )


@router.get("/{order_id}/detail", response_model=OrderDetailResponse)
async def get_order_detail(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireAnalyticsAccess),
):
    """Детали заказа для админки: form_data и кто оформил."""
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    created_by_name = None
    if order.employee_id:
        r = await db.execute(select(Employee.name).where(Employee.id == order.employee_id))
        created_by_name = r.scalar_one_or_none()
    return OrderDetailResponse(
        id=order.id,
        public_id=order.public_id,
        status=order.status.value,
        total_amount=order.total_amount,
        state_duty_amount=order.state_duty_amount,
        income_pavilion1=order.income_pavilion1,
        income_pavilion2=order.income_pavilion2,
        need_plate=order.need_plate,
        service_type=order.service_type,
        created_at=order.created_at.isoformat() if order.created_at else "",
        form_data=order.form_data,
        created_by_name=created_by_name,
    )


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class PayExtraBody(BaseModel):
    amount: float


@router.get("/{order_id}/payments")
async def get_order_payments(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireOrdersListAccess),
):
    """Список платежей по заказу (для расчёта total_paid и долга)."""
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    r = await db.execute(select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at))
    payments = r.scalars().all()
    total_paid = sum(float(p.amount) for p in payments)
    return {
        "payments": [{"amount": float(p.amount), "type": p.type.value, "created_at": p.created_at.isoformat() if p.created_at else ""} for p in payments],
        "total_paid": total_paid,
        "debt": float(order.total_amount) - total_paid,
    }


@router.post("/{order_id}/pay-extra")
async def pay_extra(
    order_id: int,
    body: PayExtraBody,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequirePlateAccess),
):
    """Доплата за номера (INCOME_PAVILION2)."""
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть больше нуля")
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if not order.need_plate:
        raise HTTPException(status_code=400, detail="У заказа нет номера для доплаты")
    shift_2 = await _current_shift_id(db, 2)
    db.add(
        Payment(
            order_id=order.id,
            amount=body.amount,
            type=PaymentType.INCOME_PAVILION2,
            employee_id=_user.id,
            shift_id=shift_2,
        )
    )
    await db.flush()
    logger.info("Доплата за номера id=%s сумма=%s", order.id, body.amount)
    return {"order_id": order.id, "amount": body.amount, "type": "INCOME_PAVILION2"}


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequirePlateAccess),
):
    new_status = body.status
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if not can_transition(order.status, new_status):
        raise HTTPException(
            status_code=400,
            detail=f"Переход из {order.status.value} в {new_status.value} невозможен",
        )
    order.status = new_status
    db.add(order)
    return {"order_id": order.id, "public_id": order.public_id, "status": new_status.value}
