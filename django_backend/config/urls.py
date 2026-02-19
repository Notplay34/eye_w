from django.urls import path

from documents.views import (
    add_payment_view,
    create_document_view,
    document_detail_view,
)

urlpatterns = [
    path("django/documents/", create_document_view, name="django-create-document"),
    path("django/documents/<int:document_id>/payments/", add_payment_view, name="django-add-payment"),
    path("django/documents/<int:document_id>/", document_detail_view, name="django-document-detail"),
]
