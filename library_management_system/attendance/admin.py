from django.contrib import admin
from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "attendance_id",
        "student",
        "seat",
        "date",
        "check_in",
        "check_out",
        "status",
    )

    list_filter = (
        "status",
        "date",
    )

    search_fields = (
        "student__full_name",
        "seat__seat_number",
    )