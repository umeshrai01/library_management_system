from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from students.models import StudentProfile
from library.models import SeatAllocation

from .models import Attendance


@login_required
def attendance_page(request):
    student = get_object_or_404(
        StudentProfile,
        user=request.user,
    )

    today = timezone.localdate()

    # Today's attendance
    today_attendance = (
        Attendance.objects
        .filter(
            student=student,
            date=today,
        )
        .select_related("seat")
        .first()
    )

    # Current active seat allocation
    current_allocation = (
        SeatAllocation.objects
        .filter(
            student=student,
            status="ACTIVE",
        )
        .select_related(
            "seat",
            "subscription",
            "subscription__plan",
        )
        .order_by("-start_date")
        .first()
    )

    # Previous attendance records
    attendance_history = (
        Attendance.objects
        .filter(student=student)
        .select_related("seat")
        .order_by("-date")[:30]
    )

    return render(
        request,
        "attendance/attendance.html",
        {
            "student": student,
            "today": today,
            "today_attendance": today_attendance,
            "current_allocation": current_allocation,
            "attendance_history": attendance_history,
        },
    )


@login_required
def check_in(request):
    if request.method != "POST":
        return redirect("attendance:page")

    student = get_object_or_404(
        StudentProfile,
        user=request.user,
    )

    # Student must be approved
    if student.status != "APPROVED":
        messages.error(
            request,
            "You cannot mark attendance because your registration is not approved.",
        )
        return redirect("attendance:page")

    # Student must have an active seat
    current_allocation = (
        SeatAllocation.objects
        .filter(
            student=student,
            status="ACTIVE",
        )
        .select_related("seat")
        .first()
    )

    if not current_allocation:
        messages.error(
            request,
            "You do not have an active seat allocation.",
        )
        return redirect("attendance:page")

    today = timezone.localdate()

    # Check whether attendance already exists
    attendance = (
        Attendance.objects
        .filter(
            student=student,
            date=today,
        )
        .first()
    )

    if attendance:
        if attendance.check_in:
            messages.warning(
                request,
                "You have already checked in today.",
            )
            return redirect("attendance:page")

        attendance.seat = current_allocation.seat
        attendance.check_in = timezone.localtime().time()
        attendance.status = "PRESENT"

        attendance.save(
            update_fields=[
                "seat",
                "check_in",
                "status",
            ]
        )

        messages.success(
            request,
            "Attendance marked successfully.",
        )

        return redirect("attendance:page")

    # Create today's attendance
    Attendance.objects.create(
        student=student,
        seat=current_allocation.seat,
        date=today,
        check_in=timezone.localtime().time(),
        status="PRESENT",
    )

    messages.success(
        request,
        "Attendance marked successfully.",
    )

    return redirect("attendance:page")


@login_required
def check_out(request):
    if request.method != "POST":
        return redirect("attendance:page")

    student = get_object_or_404(
        StudentProfile,
        user=request.user,
    )

    # Student must be approved
    if student.status != "APPROVED":
        messages.error(
            request,
            "You cannot mark attendance because your registration is not approved.",
        )
        return redirect("attendance:page")

    today = timezone.localdate()

    attendance = (
        Attendance.objects
        .filter(
            student=student,
            date=today,
        )
        .first()
    )

    if not attendance:
        messages.error(
            request,
            "You have not checked in today.",
        )
        return redirect("attendance:page")

    if not attendance.check_in:
        messages.error(
            request,
            "You have not checked in today.",
        )
        return redirect("attendance:page")

    if attendance.check_out:
        messages.warning(
            request,
            "You have already checked out today.",
        )
        return redirect("attendance:page")

    attendance.check_out = timezone.localtime().time()

    attendance.save(
        update_fields=[
            "check_out",
        ]
    )

    messages.success(
        request,
        "You have successfully checked out.",
    )

    return redirect("attendance:page")