from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.db.models import Sum

from .price_list import get_label_by_template
from .models import (
    Document,
    DocumentItem,
    FinancialStatus,
    OperationalStatus,
    Payment,
    PaymentType,
)


@dataclass
class OrderCreateData:
    """
    Минимальный DTO поверх текущего OrderCreate (FastAPI),
    чтобы не тащить внутрь Django весь Pydantic.
    Поля соответствуют backend/app/schemas/order.py::OrderCreate.
    """

    form_data: dict
    documents: list[dict]
    need_plate: bool
    service_type: str | None
    state_duty: Decimal
    income_pavilion1: Decimal
    income_pavilion2: Decimal

    @classmethod
    def from_raw_payload(cls, payload: dict) -> "OrderCreateData":
        """
        Построить данные так же, как это делает FastAPI-сервис create_order:
        - state_duty: payload.state_duty
        - income_pavilion1: сумма по documents либо extra_amount + plate_amount
        - need_plate, service_type: из документов или полей формы
        - income_pavilion2: пока всегда 0 (как в текущем коде)
        - form_data: аналог _form_data_from_create (с подстановкой label по шаблону)
        """
        state_duty = Decimal(str(payload.get("state_duty") or "0"))

        raw_documents = payload.get("documents") or []
        documents: list[dict] = []
        for d in raw_documents:
            template = d.get("template")
            if not template:
                continue
            price = Decimal(str(d.get("price") or "0"))
            label = d.get("label") or get_label_by_template(template)
            documents.append({"template": template, "label": label, "price": price})

        if documents:
            income_p1 = sum(Decimal(str(doc["price"])) for doc in documents)
            need_plate = any(doc["template"] == "number.docx" for doc in documents)
            service_type = documents[0]["template"]
        else:
            extra_amount = Decimal(str(payload.get("extra_amount") or "0"))
            plate_amount = Decimal(str(payload.get("plate_amount") or "0"))
            need_plate = bool(payload.get("need_plate"))
            income_p1 = extra_amount + (plate_amount if need_plate else Decimal("0"))
            service_type = payload.get("service_type")

        income_p2 = Decimal("0")

        form_data: dict = {
            "client_fio": payload.get("client_fio"),
            "client_passport": payload.get("client_passport"),
            "client_address": payload.get("client_address"),
            "client_phone": payload.get("client_phone"),
            "client_comment": payload.get("client_comment"),
            "client_is_legal": bool(payload.get("client_is_legal", False)),
            "client_legal_name": payload.get("client_legal_name"),
            "client_inn": payload.get("client_inn"),
            "client_ogrn": payload.get("client_ogrn"),
            "seller_fio": payload.get("seller_fio"),
            "seller_passport": payload.get("seller_passport"),
            "seller_address": payload.get("seller_address"),
            "trustee_fio": payload.get("trustee_fio"),
            "trustee_passport": payload.get("trustee_passport"),
            "trustee_basis": payload.get("trustee_basis"),
            "vin": payload.get("vin"),
            "brand_model": payload.get("brand_model"),
            "vehicle_type": payload.get("vehicle_type"),
            "year": payload.get("year"),
            "engine": payload.get("engine"),
            "chassis": payload.get("chassis"),
            "body": payload.get("body"),
            "color": payload.get("color"),
            "srts": payload.get("srts"),
            "plate_number": payload.get("plate_number"),
            "pts": payload.get("pts"),
            "dkp_date": payload.get("dkp_date"),
            "dkp_number": payload.get("dkp_number"),
            "dkp_summary": payload.get("dkp_summary"),
            "summa_dkp": str(payload.get("summa_dkp") or ""),
            "plate_quantity": payload.get("plate_quantity"),
        }
        if documents:
            form_data["documents"] = [
                {
                    "template": x["template"],
                    "label": x["label"],
                    "price": str(x["price"]),
                }
                for x in documents
            ]

        return cls(
            form_data=form_data,
            documents=documents,
            need_plate=need_plate,
            service_type=service_type,
            state_duty=state_duty,
            income_pavilion1=income_p1,
            income_pavilion2=income_p2,
        )


class DocumentService:
    """
    Сервис для создания документа и управления операционным статусом.
    Вся логика расчёта сумм и статусов — здесь, а не во view.
    """

    @staticmethod
    @transaction.atomic
    def create_document(data: OrderCreateData) -> Document:
        import uuid

        total_amount = data.state_duty + data.income_pavilion1 + data.income_pavilion2

        doc = Document.objects.create(
            public_id=uuid.uuid4(),
            financial_status=FinancialStatus.UNPAID,
            operational_status=OperationalStatus.CREATED,
            total_amount=total_amount,
            state_duty_amount=data.state_duty,
            income_pavilion1=data.income_pavilion1,
            income_pavilion2=data.income_pavilion2,
            need_plate=data.need_plate,
            service_type=data.service_type,
            form_data=data.form_data,
            client_fio=data.form_data.get("client_fio") or data.form_data.get("client_legal_name"),
            client_phone=data.form_data.get("client_phone"),
            vin=data.form_data.get("vin"),
            plate_number=data.form_data.get("plate_number"),
        )

        items = [
            DocumentItem(
                document=doc,
                template=item["template"],
                label=item.get("label") or item["template"],
                price=Decimal(str(item["price"])),
            )
            for item in data.documents
        ]
        if items:
            DocumentItem.objects.bulk_create(items)

        return doc

    @staticmethod
    def recompute_financial_status(document: Document) -> None:
        """
        Пересчитать financial_status по сумме платежей и total_amount.
        """
        # Предполагается, что документ уже заблокирован select_for_update()
        agg = document.payments.aggregate(s=Sum("amount"))
        total_paid = agg["s"] or Decimal("0.00")

        if total_paid == 0:
            new_status = FinancialStatus.UNPAID
        elif total_paid < document.total_amount:
            new_status = FinancialStatus.PARTIALLY_PAID
        elif total_paid == document.total_amount:
            new_status = FinancialStatus.FULLY_PAID
        else:
            new_status = FinancialStatus.OVERPAID

        if document.financial_status != new_status:
            document.financial_status = new_status
            document.save(update_fields=["financial_status"])


class PaymentService:
    """
    Приём частичных платежей по документу с атомарным обновлением финансового статуса.

    ВАЖНО: сервис НЕ распределяет сумму по типам сам.
    Варианты использования:
    - один платёж: передать type + amount;
    - несколько платежей: заранее посчитать суммы снаружи и передать список.
    """

    @staticmethod
    @transaction.atomic
    def add_single_payment(
        document: Document,
        amount: Decimal,
        payment_type: PaymentType,
    ) -> Payment:
        if amount <= 0:
            raise ValueError("Payment amount must be positive")

        payment = Payment.objects.create(
            document=document,
            amount=amount,
            type=payment_type,
        )
        # Обновляем financial_status с блокировкой документа
        locked_doc = Document.objects.select_for_update().get(pk=document.pk)
        DocumentService.recompute_financial_status(locked_doc)
        return payment

    @staticmethod
    @transaction.atomic
    def add_many_payments(
        document: Document,
        items: Iterable[tuple[Decimal, PaymentType]],
    ) -> list[Payment]:
        """
        Явное создание нескольких платежей. Распределение сумм выполняется
        вызывающим кодом, здесь нет дополнительной логики.
        """
        payments: list[Payment] = []
        for amount, payment_type in items:
            if amount <= 0:
                raise ValueError("Payment amount must be positive")
            payments.append(
                Payment.objects.create(
                    document=document,
                    amount=amount,
                    type=payment_type,
                )
            )
        locked_doc = Document.objects.select_for_update().get(pk=document.pk)
        DocumentService.recompute_financial_status(locked_doc)
        return payments

