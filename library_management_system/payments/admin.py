from django.contrib import admin

from .models import Payment, PaymentAllocation


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):

    list_display = (
        "payment_id",
        "student",
        "subscription",
        "amount",
        "payment_date",
        "payment_method",
        "status",
    )

    list_filter = (
        "status",
        "payment_method",
        "payment_date",
    )

    search_fields = (
        "student__full_name",
        "student__email",
        "transaction_id",
    )

    readonly_fields = (
        "payment_id",
        "payment_date",
    )


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):

    list_display = (
        "allocation_id",
        "payment",
        "subscription",
        "amount_allocated",
    )

    search_fields = (
        "payment__student__full_name",
        "payment__student__email",
    )

    readonly_fields = (
        "allocation_id",
    )