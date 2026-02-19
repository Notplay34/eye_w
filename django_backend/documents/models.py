from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.db import models


class FinancialStatus(models.TextChoices):
    UNPAID = "UNPAID", "Unpaid"
    PARTIALLY_PAID = "PARTIALLY_PAID", "Partially paid"
    FULLY_PAID = "FULLY_PAID", "Fully paid"
    OVERPAID = "OVERPAID", "Overpaid"


class OperationalStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    READY_FOR_PAYMENT = "READY_FOR_PAYMENT", "Ready for payment"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    SENT_TO_PRODUCTION = "SENT_TO_PRODUCTION", "Sent to production"
    IN_PRODUCTION = "IN_PRODUCTION", "In production"
    PRODUCED = "PRODUCED", "Produced"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    PROBLEM = "PROBLEM", "Problem"


class Document(models.Model):
    """
    Новый агрегат заказа на Django:
    - хранит form_data (JSONB) с полями OrderCreate;
    - хранит агрегированные суммы и разделённые статусы.
    """

    public_id = models.UUIDField(unique=True, editable=False)

    financial_status = models.CharField(
        max_length=32,
        choices=FinancialStatus.choices,
        default=FinancialStatus.UNPAID,
    )
    operational_status = models.CharField(
        max_length=32,
        choices=OperationalStatus.choices,
        default=OperationalStatus.CREATED,
    )

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    state_duty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    income_pavilion1 = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    income_pavilion2 = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Дублируемые поля для индексации/поиска (основные ключи поиска)
    client_fio = models.CharField(max_length=255, null=True, blank=True)
    client_phone = models.CharField(max_length=64, null=True, blank=True)
    vin = models.CharField(max_length=64, null=True, blank=True)
    plate_number = models.CharField(max_length=32, null=True, blank=True)

    need_plate = models.BooleanField(default=False)
    service_type = models.CharField(max_length=64, null=True, blank=True)

    form_data = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # employee_id и другие связи с существующей схемой FastAPI можно добавить отдельной миграцией

    class Meta:
        db_table = "django_documents"
        ordering = ("-created_at",)


class DocumentItem(models.Model):
    """
    Позиция документа: ссылка на шаблон docx и цену из прайс-листа.
    """

    document = models.ForeignKey(Document, related_name="items", on_delete=models.CASCADE)
    template = models.CharField(max_length=128)
    label = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "django_document_items"


class PaymentType(models.TextChoices):
    STATE_DUTY = "STATE_DUTY", "State duty"
    INCOME_PAVILION1 = "INCOME_PAVILION1", "Income pavilion 1"
    INCOME_PAVILION2 = "INCOME_PAVILION2", "Income pavilion 2"


class Payment(models.Model):
    """
    Частичный платёж по документу. Несколько платежей на один документ.
    """

    document = models.ForeignKey(Document, related_name="payments", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=32, choices=PaymentType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    # привязка к сотруднику/кассе появится в следующих итерациях

    class Meta:
        db_table = "django_payments"

