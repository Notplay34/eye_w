from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(editable=False, unique=True)),
                (
                    "financial_status",
                    models.CharField(
                        choices=[
                            ("UNPAID", "Unpaid"),
                            ("PARTIALLY_PAID", "Partially paid"),
                            ("FULLY_PAID", "Fully paid"),
                            ("OVERPAID", "Overpaid"),
                        ],
                        default="UNPAID",
                        max_length=32,
                    ),
                ),
                (
                    "operational_status",
                    models.CharField(
                        choices=[
                            ("CREATED", "Created"),
                            ("READY_FOR_PAYMENT", "Ready for payment"),
                            ("IN_PROGRESS", "In progress"),
                            ("SENT_TO_PRODUCTION", "Sent to production"),
                            ("IN_PRODUCTION", "In production"),
                            ("PRODUCED", "Produced"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                            ("PROBLEM", "Problem"),
                        ],
                        default="CREATED",
                        max_length=32,
                    ),
                ),
                ("total_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("state_duty_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("income_pavilion1", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("income_pavilion2", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("client_fio", models.CharField(blank=True, max_length=255, null=True)),
                ("client_phone", models.CharField(blank=True, max_length=64, null=True)),
                ("vin", models.CharField(blank=True, max_length=64, null=True)),
                ("plate_number", models.CharField(blank=True, max_length=32, null=True)),
                ("need_plate", models.BooleanField(default=False)),
                ("service_type", models.CharField(blank=True, max_length=64, null=True)),
                ("form_data", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "django_documents",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("STATE_DUTY", "State duty"),
                            ("INCOME_PAVILION1", "Income pavilion 1"),
                            ("INCOME_PAVILION2", "Income pavilion 2"),
                        ],
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "db_table": "django_payments",
            },
        ),
        migrations.CreateModel(
            name="DocumentItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("template", models.CharField(max_length=128)),
                ("label", models.CharField(blank=True, max_length=255, null=True)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="documents.document",
                    ),
                ),
            ],
            options={
                "db_table": "django_document_items",
            },
        ),
    ]

