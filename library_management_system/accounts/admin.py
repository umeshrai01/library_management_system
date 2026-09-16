from django.contrib import admin
from .models import User, AuditLog


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "date_joined",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "action",
        "model_name",
        "object_id",
        "created_at",
    )

    list_filter = (
        "action",
        "model_name",
    )

    search_fields = (
        "description",
        "model_name",
    )

    readonly_fields = (
        "created_at",
    )