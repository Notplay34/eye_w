from __future__ import annotations

from decimal import Decimal

from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from django.db.models import Sum

from .models import Document, Payment, PaymentType
from .services import DocumentService, OrderCreateData, PaymentService


def _json(request: HttpRequest) -> dict:
    import json

    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return {}


@csrf_exempt
@require_POST
def create_document_view(request: HttpRequest):
    """
    POST /django/documents/

    Принимает тело как текущий OrderCreate (JSON), создаёт Document через DocumentService.
    """
    payload = _json(request)
    data = OrderCreateData.from_raw_payload(payload)
    doc = DocumentService.create_document(data)
    return JsonResponse(
        {
            "id": doc.id,
            "total_amount": str(doc.total_amount),
            "financial_status": doc.financial_status,
            "operational_status": doc.operational_status,
        }
    )


@csrf_exempt
@require_POST
def add_payment_view(request: HttpRequest, document_id: int):
    """
    POST /django/documents/{id}/payments/

    Принимает:
    - amount
    - type (строка из PaymentType)
    """
    payload = _json(request)
    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return JsonResponse({"detail": "Document not found"}, status=404)

    try:
        amount = Decimal(str(payload.get("amount")))
    except Exception:
        return JsonResponse({"detail": "Invalid amount"}, status=400)

    type_str = payload.get("type")
    if type_str not in PaymentType.values:
        return JsonResponse({"detail": "Invalid payment type"}, status=400)

    payment_type = PaymentType(type_str)
    PaymentService.add_single_payment(doc, amount, payment_type)

    agg = Payment.objects.filter(document=doc).aggregate(total_paid=Sum("amount"))
    total_paid = agg["total_paid"] or Decimal("0.00")
    debt = doc.total_amount - total_paid

    return JsonResponse(
        {
            "financial_status": Document.objects.get(pk=document_id).financial_status,
            "total_paid": str(total_paid),
            "debt": str(debt),
        }
    )


@require_GET
def document_detail_view(request: HttpRequest, document_id: int):
    """
    GET /django/documents/{id}/

    Возвращает сводку документа + список платежей + остаток долга.
    """
    try:
        doc = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return JsonResponse({"detail": "Document not found"}, status=404)

    payments_qs = Payment.objects.filter(document=doc).order_by("created_at")

    agg = payments_qs.aggregate(total_paid=Sum("amount"))
    total_paid = agg["total_paid"] or Decimal("0.00")
    debt = doc.total_amount - total_paid

    summary = {
        "id": doc.id,
        "public_id": str(doc.public_id),
        "total_amount": str(doc.total_amount),
        "financial_status": doc.financial_status,
        "operational_status": doc.operational_status,
        "need_plate": doc.need_plate,
        "service_type": doc.service_type,
        "client_fio": doc.client_fio,
        "client_phone": doc.client_phone,
        "created_at": doc.created_at.isoformat(),
    }

    payments = [
        {
            "id": p.id,
            "amount": str(p.amount),
            "type": p.type,
            "created_at": p.created_at.isoformat(),
        }
        for p in payments_qs
    ]

    return JsonResponse(
        {
            "summary": summary,
            "payments": payments,
            "total_paid": str(total_paid),
            "debt": str(debt),
        }
    )

