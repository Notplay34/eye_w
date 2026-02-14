from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.api.auth import RequireFormAccess, RequireAnalyticsAccess, UserInfo

logger = get_logger(__name__)
from app.models import Order, OrderStatus, Payment, PaymentType, Employee
from pydantic import BaseModel

from app.schemas.order import OrderCreate, OrderResponse, OrderDetailResponse
from app.schemas.payment import PayOrderResponse
from app.services.order_service import create_order
from app.services.order_status import can_transition
from app.services.telegram_notify import notify_plate_operators_new_order

router = APIRouter(prefix="/orders", tags=["orders"])


async def _get_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


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
    _user: UserInfo = Depends(RequireFormAccess),
):
    order = await _get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if not can_transition(order.status, OrderStatus.PAID):
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя принять оплату для заказа со статусом {order.status.value}",
        )
    if order.state_duty_amount > 0:
        db.add(
            Payment(
                order_id=order.id,
                amount=order.state_duty_amount,
                type=PaymentType.STATE_DUTY,
                employee_id=employee_id,
            )
        )
    if order.income_pavilion1 > 0:
        db.add(
            Payment(
                order_id=order.id,
                amount=order.income_pavilion1,
                type=PaymentType.INCOME_PAVILION1,
                employee_id=employee_id,
            )
        )
    if order.income_pavilion2 > 0:
        db.add(
            Payment(
                order_id=order.id,
                amount=order.income_pavilion2,
                type=PaymentType.INCOME_PAVILION2,
                employee_id=employee_id,
            )
        )
    order.status = OrderStatus.PAID
    db.add(order)
    await db.flush()
    logger.info("Оплата принята по заказу id=%s", order.id)
    if order.need_plate:
        plate_qty = (order.form_data or {}).get("plate_quantity")
        plate_qty = int(plate_qty) if plate_qty is not None else 1
        await notify_plate_operators_new_order(db, order.id, order.public_id, order.total_amount, plate_qty)
    return PayOrderResponse(
        order_id=order.id,
        public_id=order.public_id,
        status=OrderStatus.PAID.value,
    )


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status: Optional[OrderStatus] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _user: UserInfo = Depends(RequireFormAccess),
):
    q = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status is not None:
        q = q.where(Order.status == status)
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
    _user: UserInfo = Depends(RequireFormAccess),
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


async def _is_plate_operator(db: AsyncSession, telegram_id: int) -> bool:
    from app.models import Employee
    from app.models.employee import EmployeeRole
    r = await db.execute(
        select(Employee.id).where(
            Employee.telegram_id == telegram_id,
            Employee.role == EmployeeRole.ROLE_PLATE_OPERATOR,
            Employee.is_active == True,
        )
    )
    return r.scalar_one_or_none() is not None


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    x_telegram_user_id: Optional[str] = Header(None, alias="X-Telegram-User-Id"),
):
    if x_telegram_user_id is not None:
        try:
            tid = int(x_telegram_user_id)
        except ValueError:
            raise HTTPException(status_code=403, detail="Неверный X-Telegram-User-Id")
        if not await _is_plate_operator(db, tid):
            raise HTTPException(status_code=403, detail="Доступ только для оператора павильона 2")
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
