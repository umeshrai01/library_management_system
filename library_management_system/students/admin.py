from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "full_name",
        "phone",
        "status",
        "registration_date",
    )

    list_filter = (
        "status",
        "registration_date",
    )

    search_fields = (
        "full_name",
        "phone",
        "user__username",
        "user__email",
    )