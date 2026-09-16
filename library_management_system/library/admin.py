from django.contrib import admin
from .models import (
    Library,
    Seat,
    SubscriptionPlan,
    Subscription,
    SeatAllocation,
)


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = (
        "library_id",
        "name",
        "total_seats",
        "created_at",
    )

    search_fields = (
        "name",
        "address",
    )


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = (
        "seat_id",
        "library",
        "seat_number",
        "status",
    )

    list_filter = (
        "library",
        "status",
    )

    search_fields = (
        "seat_number",
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "plan_id",
        "name",
        "hours_per_day",
        "duration_days",
        "fee",
        "is_active",
    )

    list_filter = (
        "hours_per_day",
        "is_active",
    )

    search_fields = (
        "name",
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "subscription_id",
        "student",
        "plan",
        "start_date",
        "end_date",
        "status",
    )

    list_filter = (
        "status",
        "plan",
    )

    search_fields = (
        "student__full_name",
        "student__user__username",
    )


@admin.register(SeatAllocation)
class SeatAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "allocation_id",
        "student",
        "seat",
        "subscription",
        "start_date",
        "end_date",
        "status",
    )

    list_filter = (
        "status",
        "seat",
    )

    search_fields = (
        "student__full_name",
        "seat__seat_number",
    )