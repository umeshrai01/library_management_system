from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import StudentProfile

from library.models import (
    Subscription,
    SeatAllocation,
)

from payments.models import Payment

from attendance.models import Attendance


@login_required
def dashboard(request):
    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "preferred_plan",
            "preferred_time_slot",
        ),
        user=request.user,
    )

    # ---------------------------------------------------------
    # CURRENT ACTIVE SUBSCRIPTION
    # ---------------------------------------------------------
    current_subscription = (
        Subscription.objects
        .filter(
            student=student,
            status="ACTIVE",
        )
        .select_related(
            "plan",
            "time_slot",
        )
        .order_by("-start_date")
        .first()
    )

    # ---------------------------------------------------------
    # CURRENT ACTIVE SEAT
    # ---------------------------------------------------------
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
            "subscription__time_slot",
        )
        .order_by("-start_date")
        .first()
    )

    # ---------------------------------------------------------
    # TODAY'S ATTENDANCE
    # ---------------------------------------------------------
    today = timezone.localdate()

    today_attendance = (
        Attendance.objects
        .filter(
            student=student,
            date=today,
        )
        .select_related("seat")
        .first()
    )

    # ---------------------------------------------------------
    # FEE INFORMATION
    # ---------------------------------------------------------
    total_paid = Decimal("0.00")
    remaining_fee = Decimal("0.00")

    if current_subscription:
        total_paid = (
            Payment.objects
            .filter(
                student=student,
                subscription=current_subscription,
                status="PAID",
            )
            .aggregate(total=models.Sum("amount"))["total"]
            or Decimal("0.00")
        )

        remaining_fee = (
            current_subscription.plan.fee - total_paid
        )

        if remaining_fee < Decimal("0.00"):
            remaining_fee = Decimal("0.00")

    # ---------------------------------------------------------
    # RECENT PAYMENTS
    # ---------------------------------------------------------
    recent_payments = (
        Payment.objects
        .filter(
            student=student,
            status="PAID",
        )
        .select_related(
            "subscription",
            "subscription__plan",
        )
        .order_by("-payment_date")[:5]
    )

    # ---------------------------------------------------------
    # SUBSCRIPTION HISTORY
    # ---------------------------------------------------------
    subscription_history = (
        Subscription.objects
        .filter(student=student)
        .select_related(
            "plan",
            "time_slot",
        )
        .order_by("-start_date")
    )

    # ---------------------------------------------------------
    # SEAT HISTORY
    # ---------------------------------------------------------
    seat_history = (
        SeatAllocation.objects
        .filter(student=student)
        .select_related(
            "seat",
            "subscription",
            "subscription__plan",
        )
        .order_by("-start_date")
    )

    return render(
        request,
        "students/dashboard.html",
        {
            "student": student,
            "current_subscription": current_subscription,
            "current_allocation": current_allocation,
            "today_attendance": today_attendance,
            "total_paid": total_paid,
            "remaining_fee": remaining_fee,
            "recent_payments": recent_payments,
            "subscription_history": subscription_history,
            "seat_history": seat_history,
            "today": today,
        },
    )


@login_required
def profile(request):
    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "preferred_plan",
            "preferred_time_slot",
        ),
        user=request.user,
    )

    return render(
        request,
        "students/profile.html",
        {
            "student": student,
        },
    )



@login_required
def upload_documents(request):
    student = get_object_or_404(
        StudentProfile,
        user=request.user,
    )

    if request.method == "POST":

        if "photo" in request.FILES:
            student.photo = request.FILES["photo"]

            student.save(update_fields=["photo"])

            messages.success(
                request,
                "Your photograph has been uploaded successfully.",
            )

        elif "aadhaar_document" in request.FILES:
            student.aadhaar_document = request.FILES["aadhaar_document"]

            student.save(update_fields=["aadhaar_document"])

            messages.success(
                request,
                "Your Aadhaar document has been uploaded successfully.",
            )

        else:
            messages.error(
                request,
                "Please select a document to upload.",
            )

        return redirect("students_documents")

    return render(
        request,
        "students/upload_documents.html",
        {
            "student": student,
        },
    )


@login_required
def subscriptions(request):
    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "preferred_plan",
            "preferred_time_slot",
        ),
        user=request.user,
    )

    # All subscriptions belonging to this student
    subscription_history = (
        Subscription.objects
        .filter(student=student)
        .select_related(
            "plan",
            "time_slot",
        )
        .order_by("-start_date")
    )

    # Current active subscription
    current_subscription = (
        Subscription.objects
        .filter(
            student=student,
            status="ACTIVE",
        )
        .select_related(
            "plan",
            "time_slot",
        )
        .order_by("-start_date")
        .first()
    )

    total_paid = Decimal("0.00")
    remaining_fee = Decimal("0.00")
    payment_history = Payment.objects.none()

    if current_subscription:

        payment_history = (
            Payment.objects
            .filter(
                student=student,
                subscription=current_subscription,
                status="PAID",
            )
            .order_by("-payment_date")
        )

        total_paid = (
            payment_history.aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        remaining_fee = (
            current_subscription.plan.fee - total_paid
        )

        if remaining_fee < Decimal("0.00"):
            remaining_fee = Decimal("0.00")

    return render(
        request,
        "students/subscriptions.html",
        {
            "student": student,
            "current_subscription": current_subscription,
            "subscription_history": subscription_history,
            "payment_history": payment_history,
            "total_paid": total_paid,
            "remaining_fee": remaining_fee,
        },
    )

@login_required
def my_seat(request):
    student = get_object_or_404(
        StudentProfile,
        user=request.user,
    )

    current_allocation = (
        SeatAllocation.objects
        .filter(
            student=student,
            status="ACTIVE",
        )
        .select_related(
            "seat",
            "seat__library",
            "subscription",
            "subscription__plan",
        )
        .order_by("-start_date")
        .first()
    )

    seat_history = (
        SeatAllocation.objects
        .filter(student=student)
        .select_related(
            "seat",
            "seat__library",
            "subscription",
            "subscription__plan",
        )
        .order_by("-start_date")
    )

    return render(
        request,
        "students/seat.html",
        {
            "student": student,
            "current_allocation": current_allocation,
            "seat_history": seat_history,
        },
    )
