from datetime import time,date, timedelta, datetime
from accounts.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models, transaction
from accounts.models import User
from attendance.models import Attendance
from library.models import (Library, Seat,SeatAllocation,Subscription,TimeSlot,SubscriptionPlan)
from payments.models import Payment
from students.models import StudentProfile
from django.utils import timezone
from decimal import Decimal
from payments.models import Payment, PaymentAllocation



@login_required
def dashboard(request):

    today = date.today()

    total_students = StudentProfile.objects.exclude(
        status="UNREGISTERED"
    ).count()

    active_students = StudentProfile.objects.filter(
        status="APPROVED"
    ).count()

    expired_students = Subscription.objects.filter(
        end_date__lt=today,
        status="ACTIVE"
    ).values(
        "student"
    ).distinct().count()

    total_owners = User.objects.filter(
        role="OWNER"
    ).count()

    present_today = Attendance.objects.filter(
        date=today,
        status="PRESENT"
    ).count()

    today_collection = Payment.objects.filter(
        payment_date__date=today,
        status="PAID"
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    expiry_limit = today + timedelta(days=7)

    expiring_subscriptions = Subscription.objects.filter(
        status="ACTIVE",
        end_date__gte=today,
        end_date__lte=expiry_limit
    ).select_related(
        "student",
        "plan",
        "time_slot"
    ).order_by(
        "end_date"
    )

    context = {
        "total_students": total_students,
        "active_students": active_students,
        "expired_students": expired_students,
        "total_owners": total_owners,
        "present_today": present_today,
        "today_collection": today_collection,
        "expiring_subscriptions": expiring_subscriptions,
    }

    return render(
        request,
        "management/dashboard.html",
        context
    )




@login_required
def student_detail(request, student_id):

    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "preferred_plan",
            "preferred_time_slot",
            "approved_by",
        ).prefetch_related(
            "subscriptions__plan",
            "subscriptions__time_slot",
            "seat_allocations__seat",
            "seat_allocations__subscription__plan",
            "seat_allocations__subscription__time_slot",
        ),
        student_id=student_id,
    )

    current_subscription = student.subscriptions.filter(
        status="ACTIVE"
    ).select_related(
        "plan",
        "time_slot",
    ).first()

    current_allocation = student.seat_allocations.filter(
        status="ACTIVE"
    ).select_related(
        "seat",
        "subscription__plan",
        "subscription__time_slot",
    ).first()

    subscription_history = student.subscriptions.all().order_by(
        "-start_date"
    )

    seat_history = student.seat_allocations.select_related(
        "seat",
        "subscription",
    ).order_by(
        "-start_date"
    )

    available_seats = Seat.objects.filter(
        status="AVAILABLE"
    ).order_by("seat_id")

    # Active subscription plans for approval
    plans = SubscriptionPlan.objects.filter(
        is_active=True
    ).order_by("hours_per_day")

    # Active time slots for approval
    time_slots = TimeSlot.objects.filter(
        is_active=True
    ).order_by("start_time")

    # Today's date for the start-date field
    today = timezone.localdate()

    return render(
        request,
        "management/student_detail.html",
        {
            "student": student,
            "current_subscription": current_subscription,
            "current_allocation": current_allocation,
            "subscription_history": subscription_history,
            "seat_history": seat_history,
            "available_seats": available_seats,

            # Required by approval form
            "plans": plans,
            "time_slots": time_slots,
            "today": today,
        },
    )

@login_required
def approve_student(request, student_id):

    if request.method != "POST":
        return redirect(
            "management:student_detail",
            student_id=student_id,
        )

    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "preferred_plan",
            "preferred_time_slot",
        ),
        student_id=student_id,
    )

    # -----------------------------------------
    # ONLY PENDING STUDENTS CAN BE APPROVED
    # -----------------------------------------

    if student.status != "PENDING":

        messages.warning(
            request,
            "Only pending students can be approved."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    # -----------------------------------------
    # FORM VALUES
    # -----------------------------------------

    plan_id = request.POST.get("plan")

    time_slot_id = request.POST.get("time_slot")

    seat_id = request.POST.get("seat")

    start_date_value = request.POST.get(
        "start_date"
    )

    amount_received_value = request.POST.get(
        "amount_received",
        "0",
    ).strip()

    payment_method = request.POST.get(
        "payment_method",
        "CASH",
    )

    transaction_id = request.POST.get(
        "transaction_id",
        "",
    ).strip()

    remarks = request.POST.get(
        "remarks",
        "",
    ).strip()

    # -----------------------------------------
    # REQUIRED VALIDATION
    # -----------------------------------------

    if not plan_id:

        messages.error(
            request,
            "Please select a subscription plan."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    if not time_slot_id:

        messages.error(
            request,
            "Please select a time slot."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    if not seat_id:

        messages.error(
            request,
            "Please select a seat."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    if not start_date_value:

        messages.error(
            request,
            "Please select a start date."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    # -----------------------------------------
    # GET PLAN
    # -----------------------------------------

    plan = get_object_or_404(
        SubscriptionPlan,
        plan_id=plan_id,
        is_active=True,
    )

    # -----------------------------------------
    # GET TIME SLOT
    # -----------------------------------------

    time_slot = get_object_or_404(
        TimeSlot,
        slot_id=time_slot_id,
        is_active=True,
    )

    if time_slot.start_time < time(6, 0):
        messages.error(
            request,
            "Library start time is 6:00 AM. Please select a valid start time.",
        )
        return redirect(
            "management:student_detail",
            student_id=student_id,
        )

    # -----------------------------------------
    # GET SEAT
    # -----------------------------------------

    try:

        seat_id = int(seat_id)

    except (TypeError, ValueError):

        messages.error(
            request,
            "Invalid seat selection."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    # -----------------------------------------
    # START DATE
    # -----------------------------------------

    try:

        start_date = datetime.strptime(
            start_date_value,
            "%Y-%m-%d",
        ).date()

    except ValueError:

        messages.error(
            request,
            "Invalid start date."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    # -----------------------------------------
    # PAYMENT AMOUNT
    # -----------------------------------------

    try:

        amount_received = Decimal(
            amount_received_value or "0"
        )

    except Exception:

        messages.error(
            request,
            "Invalid payment amount."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    if amount_received < 0:

        messages.error(
            request,
            "Payment amount cannot be negative."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    if amount_received > plan.fee:

        messages.error(
            request,
            "Amount received cannot be greater than "
            "the plan fee."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    # -----------------------------------------
    # SUBSCRIPTION END DATE
    # -----------------------------------------

    end_date = (
        start_date
        + timedelta(
            days=plan.duration_days - 1
        )
    )

    # -----------------------------------------
    # APPROVAL TRANSACTION
    # -----------------------------------------

    try:

        with transaction.atomic():

            # Lock selected seat so two users cannot
            # assign the same seat simultaneously.

            seat = (
                Seat.objects
                .select_for_update()
                .filter(
                    seat_id=seat_id,
                    status="AVAILABLE",
                )
                .first()
            )

            if not seat:

                raise ValueError(
                    "The selected seat is no longer available."
                )

            # -------------------------------------
            # CHECK ACTIVE SUBSCRIPTION
            # -------------------------------------

            existing_subscription = (
                Subscription.objects
                .filter(
                    student=student,
                    status="ACTIVE",
                )
                .exists()
            )

            if existing_subscription:

                raise ValueError(
                    "This student already has an active "
                    "subscription."
                )

            # -------------------------------------
            # CREATE SUBSCRIPTION
            # -------------------------------------

            subscription = Subscription.objects.create(
                student=student,
                plan=plan,
                time_slot=time_slot,
                start_date=start_date,
                end_date=end_date,
                status="ACTIVE",
            )

            # -------------------------------------
            # CREATE SEAT ALLOCATION
            # -------------------------------------
            start_datetime = datetime.combine(
                start_date,
                time_slot.start_time,
            )

            end_datetime = (
                start_datetime
                + timedelta(hours=plan.hours_per_day)
            )

            calculated_end_time = end_datetime.time()



            SeatAllocation.objects.create(
            student=student,
            seat=seat,
            subscription=subscription,
            start_date=start_date,
            end_date=end_date,
            start_time=time_slot.start_time,
            end_time=calculated_end_time,
            status="ACTIVE",
            )

            # -------------------------------------
            # MARK SEAT OCCUPIED
            # -------------------------------------

            seat.status = "OCCUPIED"

            seat.save(
                update_fields=["status"]
            )

            # -------------------------------------
            # FIRST INSTALLMENT
            # -------------------------------------

            if amount_received > 0:

                payment = Payment.objects.create(
                    student=student,
                    subscription=subscription,
                    amount=amount_received,
                    payment_method=payment_method,
                    transaction_id=(
                        transaction_id
                        if transaction_id
                        else None
                    ),
                    status="PAID",
                    remarks=remarks,
                )

                # IMPORTANT:
                # PaymentAllocation now stores only the
                # actual amount allocated.
                #
                # No days_covered.
                # No from_date.
                # No to_date.

                PaymentAllocation.objects.create(
                    payment=payment,
                    subscription=subscription,
                    amount_allocated=amount_received,
                    remarks=remarks,
                )

            # -------------------------------------
            # APPROVE STUDENT
            # -------------------------------------

            student.status = "APPROVED"

            student.approved_by = request.user

            student.approved_at = timezone.now()

            student.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                ]
            )

        # -----------------------------------------
        # SUCCESS
        # -----------------------------------------

        remaining_amount = (
            plan.fee
            - amount_received
        )

        messages.success(
            request,
            f"{student.full_name} has been approved successfully. "
            f"Seat {seat.seat_number} has been assigned. "
            f"₹{amount_received} received. "
            f"Remaining fee: ₹{remaining_amount}."
        )

    except ValueError as error:

        messages.error(
            request,
            str(error)
        )

    except Exception as error:

        messages.error(
            request,
            "Unable to approve student. Please try again."
        )

    return redirect(
        "management:student_detail",
        student_id=student.student_id,
    )


@login_required
def reject_student(request, student_id):

    if request.method != "POST":
        return redirect(
            "management:student_detail",
            student_id=student_id
        )

    student = get_object_or_404(
        StudentProfile,
        student_id=student_id
    )

    reason = request.POST.get(
        "rejection_reason",
        ""
    ).strip()

    student.status = "REJECTED"
    student.rejection_reason = reason

    student.save(
        update_fields=[
            "status",
            "rejection_reason",
        ]
    )

    messages.success(
        request,
        f"{student.full_name} has been rejected."
    )

    return redirect(
        "management:students"
    )


@login_required
def owners(request):

    owners = User.objects.filter(
        role="OWNER"
    ).order_by(
        "-date_joined"
    )

    return render(
        request,
        "management/owners.html",
        {
            "owners": owners
        }
    )

@login_required
def unregister_student(request, student_id):

    if request.method != "POST":
        return redirect("management:student_detail", student_id=student_id)

    student = get_object_or_404(
        StudentProfile.objects.select_related("user"),
        student_id=student_id,
    )

    # Already unregistered
    if student.status == "UNREGISTERED":
        messages.warning(
            request,
            f"{student.full_name} is already unregistered."
        )
        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    try:
        with transaction.atomic():

            # Find active seat allocation
            active_allocation = (
                SeatAllocation.objects
                .select_for_update()
                .select_related("seat", "subscription")
                .filter(
                    student=student,
                    status="ACTIVE",
                )
                .first()
            )

            # Release seat and end allocation
            if active_allocation:

                seat = Seat.objects.select_for_update().get(
                    seat_id=active_allocation.seat.seat_id
                )

                active_allocation.status = "ENDED"
                active_allocation.save(
                    update_fields=["status"]
                )

                seat.status = "AVAILABLE"
                seat.save(
                    update_fields=["status"]
                )

                # Cancel associated subscription
                subscription = active_allocation.subscription

                if subscription.status == "ACTIVE":
                    subscription.status = "CANCELLED"
                    subscription.save(
                        update_fields=["status"]
                    )

            # Cancel any other active subscriptions
            Subscription.objects.filter(
                student=student,
                status="ACTIVE",
            ).update(
                status="CANCELLED"
            )

            # Change student status
            student.status = "UNREGISTERED"
            student.save(
                update_fields=["status"]
            )

        messages.success(
            request,
            f"{student.full_name} has been unregistered successfully."
        )

    except Exception:
        messages.error(
            request,
            "Unable to unregister the student. Please try again."
        )

    return redirect(
        "management:student_detail",
        student_id=student.student_id,
    )

@login_required
def edit_student(request, student_id):

    student = get_object_or_404(
        StudentProfile.objects.select_related(
            "user",
            "preferred_plan",
            "preferred_time_slot",
        ),
        student_id=student_id,
    )

    plans = SubscriptionPlan.objects.filter(
        is_active=True
    ).order_by("hours_per_day")

    time_slots = TimeSlot.objects.filter(
        is_active=True
    ).order_by("start_time")

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        date_of_birth = request.POST.get("date_of_birth", "").strip()

        preferred_plan_id = request.POST.get(
            "preferred_plan"
        )

        preferred_time_slot_id = request.POST.get(
            "preferred_time_slot"
        )

        # =========================
        # Basic Validation
        # =========================

        if not full_name or not email or not phone:
            messages.error(
                request,
                "Name, email and phone are required."
            )

            return redirect(
                "management:edit_student",
                student_id=student.student_id,
            )

        # =========================
        # Check Email
        # =========================

        email_exists = StudentProfile.objects.filter(
            email=email
        ).exclude(
            student_id=student.student_id
        ).exists()

        if email_exists:
            messages.error(
                request,
                "Another student is already using this email address."
            )

            return redirect(
                "management:edit_student",
                student_id=student.student_id,
            )

        # =========================
        # Get Plan
        # =========================

        preferred_plan = None

        if preferred_plan_id:

            preferred_plan = get_object_or_404(
                SubscriptionPlan,
                plan_id=preferred_plan_id,
                is_active=True,
            )

        # =========================
        # Get Time Slot
        # =========================

        preferred_time_slot = None

        if preferred_time_slot_id:

            preferred_time_slot = get_object_or_404(
                TimeSlot,
                slot_id=preferred_time_slot_id,
                is_active=True,
            )

        # =========================
        # Update Student
        # =========================

        student.full_name = full_name
        student.email = email
        student.phone = phone
        student.address = address

        if date_of_birth:
            try:
                student.date_of_birth = datetime.strptime(
                    date_of_birth,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                messages.error(
                    request,
                    "Invalid date of birth."
                )

                return redirect(
                    "management:edit_student",
                    student_id=student.student_id,
                )

        else:
            student.date_of_birth = None

            student.preferred_plan = preferred_plan
            student.preferred_time_slot = preferred_time_slot

        # =========================
        # Photo
        # =========================

        if request.FILES.get("photo"):
            student.photo = request.FILES["photo"]

        # =========================
        # Aadhaar
        # =========================

        if request.FILES.get("aadhaar_document"):
            student.aadhaar_document = request.FILES[
                "aadhaar_document"
            ]

        student.save()

        # Keep User account email synchronized
        user = student.user

        user.email = email
        user.save(update_fields=["email"])

        messages.success(
            request,
            f"{student.full_name}'s information was updated successfully."
        )

        return redirect(
            "management:student_detail",
            student_id=student.student_id,
        )

    return render(
        request,
        "management/edit_student.html",
        {
            "student": student,
            "plans": plans,
            "time_slots": time_slots,
        },
    )



@login_required
def attendance(request):

    # -----------------------------
    # SELECTED DATE
    # -----------------------------
    selected_date = request.GET.get("date")

    if selected_date:
        try:
            selected_date = datetime.strptime(
                selected_date,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    # -----------------------------
    # SEARCH
    # -----------------------------
    search = request.GET.get("search", "").strip()

    # -----------------------------
    # STATUS FILTER
    # -----------------------------
    status_filter = request.GET.get("status", "").strip().upper()

    # -----------------------------
    # APPROVED / ACTIVE STUDENTS
    # -----------------------------
    active_students = StudentProfile.objects.filter(
        status="APPROVED"
    ).count()

    # -----------------------------
    # ATTENDANCE FOR SELECTED DATE
    # -----------------------------
    attendances = Attendance.objects.filter(
        date=selected_date
    ).select_related(
        "student",
        "seat"
    ).order_by(
        "-check_in"
    )

    # -----------------------------
    # SEARCH BY STUDENT NAME
    # -----------------------------
    if search:
        attendances = attendances.filter(
            student__full_name__icontains=search
        )

    # -----------------------------
    # STATUS FILTER
    # -----------------------------
    if status_filter in ["PRESENT", "ABSENT"]:
        attendances = attendances.filter(
            status=status_filter
        )

    # -----------------------------
    # SUMMARY COUNTS
    # -----------------------------
    date_attendances = Attendance.objects.filter(
        date=selected_date
    )

    present_today = date_attendances.filter(
        status="PRESENT"
    ).count()

    absent_today = date_attendances.filter(
        status="ABSENT"
    ).count()

    currently_inside = date_attendances.filter(
        status="PRESENT",
        check_in__isnull=False,
        check_out__isnull=True
    ).count()

    # -----------------------------
    # CALCULATE TOTAL HOURS
    # -----------------------------
    attendance_rows = []

    for attendance_record in attendances:

        total_hours = None

        if (
            attendance_record.check_in
            and attendance_record.check_out
        ):
            check_in_datetime = datetime.combine(
                attendance_record.date,
                attendance_record.check_in
            )

            check_out_datetime = datetime.combine(
                attendance_record.date,
                attendance_record.check_out
            )

            # Handles an overnight checkout
            if check_out_datetime < check_in_datetime:
                check_out_datetime += timedelta(days=1)

            duration = check_out_datetime - check_in_datetime

            total_seconds = duration.total_seconds()

            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)

            total_hours = f"{hours}h {minutes}m"

        elif attendance_record.check_in:
            total_hours = "Inside"

        attendance_rows.append({
            "attendance": attendance_record,
            "total_hours": total_hours,
        })

    return render(
        request,
        "management/attendance.html",
        {
            "active_students": active_students,
            "present_today": present_today,
            "absent_today": absent_today,
            "currently_inside": currently_inside,
            "attendances": attendance_rows,
            "selected_date": selected_date,
            "search": search,
            "status_filter": status_filter,
        }
    )


@login_required
def fee_management(request):

    today = timezone.localdate()

    # -----------------------------------------
    # PAYMENT HISTORY
    # -----------------------------------------

    payments = (
        Payment.objects
        .select_related(
            "student",
            "subscription",
            "subscription__plan",
            "subscription__time_slot",
        )
        .order_by(
            "-payment_date"
        )
    )

    # -----------------------------------------
    # TODAY'S COLLECTION
    # -----------------------------------------

    today_collection = (
        Payment.objects
        .filter(
            payment_date__date=today,
            status="PAID",
        )
        .aggregate(
            total=models.Sum("amount")
        )["total"]
        or Decimal("0")
    )

    # -----------------------------------------
    # MONTHLY COLLECTION
    # -----------------------------------------

    monthly_collection = (
        Payment.objects
        .filter(
            payment_date__year=today.year,
            payment_date__month=today.month,
            status="PAID",
        )
        .aggregate(
            total=models.Sum("amount")
        )["total"]
        or Decimal("0")
    )

    # -----------------------------------------
    # ACTIVE SUBSCRIPTIONS
    # -----------------------------------------

    active_subscriptions = (
        Subscription.objects
        .filter(
            status="ACTIVE",
        )
        .select_related(
            "student",
            "plan",
            "time_slot",
        )
        .order_by(
            "student__full_name"
        )
    )

    # -----------------------------------------
    # STUDENT FEE BALANCES
    # -----------------------------------------

    fee_balances = []

    pending_amount = Decimal("0")

    for subscription in active_subscriptions:

        total_paid = (
            Payment.objects
            .filter(
                subscription=subscription,
                status="PAID",
            )
            .aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0")
        )

        remaining_amount = (
            subscription.plan.fee
            - total_paid
        )

        if remaining_amount < 0:
            remaining_amount = Decimal("0")

        pending_amount += remaining_amount

        fee_balances.append(
            {
                "subscription": subscription,
                "total_paid": total_paid,
                "remaining_amount": remaining_amount,
            }
        )

    # -----------------------------------------
    # INSTALLMENT COUNT
    # -----------------------------------------

    installments = Payment.objects.filter(
        status="PAID"
    ).count()

    # -----------------------------------------
    # RENDER
    # -----------------------------------------

    return render(
        request,
        "management/fee_management.html",
        {
            "payments": payments,
            "today_collection": today_collection,
            "monthly_collection": monthly_collection,
            "pending_amount": pending_amount,
            "installments": installments,
            "fee_balances": fee_balances,
        },
    )


@login_required
def collect_payment(request):

    # ==========================================
    # POST
    # ==========================================

    if request.method == "POST":

        student_id = request.POST.get(
            "student"
        )

        subscription_id = request.POST.get(
            "subscription"
        )

        amount_value = request.POST.get(
            "amount",
            "0",
        ).strip()

        payment_method = request.POST.get(
            "payment_method",
            "CASH",
        )

        transaction_id = request.POST.get(
            "transaction_id",
            "",
        ).strip()

        remarks = request.POST.get(
            "remarks",
            "",
        ).strip()

        # ======================================
        # REQUIRED FIELDS
        # ======================================

        if not student_id:

            messages.error(
                request,
                "Please select a student."
            )

            return redirect(
                "management:collect_payment"
            )

        if not subscription_id:

            messages.error(
                request,
                "Please select a subscription."
            )

            return redirect(
                "management:collect_payment"
            )

        # ======================================
        # GET SUBSCRIPTION
        # ======================================

        subscription = get_object_or_404(
            Subscription.objects.select_related(
                "student",
                "plan",
            ),
            subscription_id=subscription_id,
            status="ACTIVE",
        )

        # ======================================
        # VERIFY STUDENT
        # ======================================

        if str(subscription.student.student_id) != str(student_id):

            messages.error(
                request,
                "Invalid student and subscription selection."
            )

            return redirect(
                "management:collect_payment"
            )

        # ======================================
        # PAYMENT AMOUNT
        # ======================================

        try:

            amount = Decimal(
                amount_value or "0"
            )

        except Exception:

            messages.error(
                request,
                "Invalid payment amount."
            )

            return redirect(
                "management:collect_payment"
            )

        if amount <= 0:

            messages.error(
                request,
                "Payment amount must be greater than zero."
            )

            return redirect(
                "management:collect_payment"
            )

        # ======================================
        # CALCULATE ALREADY PAID
        # ======================================

        already_paid = (
            Payment.objects
            .filter(
                subscription=subscription,
                status="PAID",
            )
            .aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0")
        )

        remaining_amount = (
            subscription.plan.fee
            - already_paid
        )

        # ======================================
        # DON'T OVERPAY
        # ======================================

        if amount > remaining_amount:

            messages.error(
                request,
                f"Maximum remaining amount is ₹{remaining_amount}."
            )

            return redirect(
                "management:collect_payment"
            )

        # ======================================
        # CREATE PAYMENT
        # ======================================

        try:

            with transaction.atomic():

                payment = Payment.objects.create(
                    student=subscription.student,
                    subscription=subscription,
                    amount=amount,
                    payment_method=payment_method,
                    transaction_id=(
                        transaction_id
                        if transaction_id
                        else None
                    ),
                    status="PAID",
                    remarks=remarks,
                )

                PaymentAllocation.objects.create(
                    payment=payment,
                    subscription=subscription,
                    amount_allocated=amount,
                    remarks=remarks,
                )

            new_total_paid = (
                already_paid + amount
            )

            new_remaining = (
                subscription.plan.fee
                - new_total_paid
            )

            messages.success(
                request,
                f"Payment of ₹{amount} recorded successfully. "
                f"Remaining fee: ₹{new_remaining}."
            )

            return redirect(
                "management:fee_management"
            )

        except Exception:

            messages.error(
                request,
                "Unable to record payment. Please try again."
            )

            return redirect(
                "management:collect_payment"
            )

    # ==========================================
    # GET
    # ==========================================

    active_subscriptions = (
        Subscription.objects
        .filter(
            status="ACTIVE",
        )
        .select_related(
            "student",
            "plan",
            "time_slot",
        )
        .order_by(
            "student__full_name"
        )
    )

    # ==========================================
    # CALCULATE BALANCE FOR EACH SUBSCRIPTION
    # ==========================================

    subscription_data = []

    for subscription in active_subscriptions:

        total_paid = (
            Payment.objects
            .filter(
                subscription=subscription,
                status="PAID",
            )
            .aggregate(
                total=models.Sum("amount")
            )["total"]
            or Decimal("0")
        )

        remaining = (
            subscription.plan.fee
            - total_paid
        )

        subscription.total_paid = total_paid
        subscription.remaining_amount = max(
            remaining,
            Decimal("0")
        )

        subscription_data.append(
            subscription
        )

    return render(
        request,
        "management/collect_payment.html",
        {
            "active_subscriptions": subscription_data,
        },
    )


@login_required
def seat_management(request):

    if request.method == "POST":

        # ==========================================
        # GET FORM DATA
        # ==========================================

        student_id = request.POST.get("student")
        seat_id = request.POST.get("seat")
        plan_id = request.POST.get("plan")
        time_slot_id = request.POST.get("time_slot")
        start_date_value = request.POST.get("start_date")

        amount_received_value = request.POST.get(
            "amount_received",
            "0",
        ).strip()

        payment_method = request.POST.get(
            "payment_method",
            "CASH",
        )

        transaction_id = request.POST.get(
            "transaction_id",
            "",
        ).strip()

        remarks = request.POST.get(
            "remarks",
            "",
        ).strip()

        # ==========================================
        # REQUIRED FIELD VALIDATION
        # ==========================================

        if not student_id:
            messages.error(
                request,
                "Please select a student."
            )
            return redirect("management:seat_management")

        if not seat_id:
            messages.error(
                request,
                "Please select a seat."
            )
            return redirect("management:seat_management")

        if not plan_id:
            messages.error(
                request,
                "Please select a subscription plan."
            )
            return redirect("management:seat_management")

        if not time_slot_id:
            messages.error(
                request,
                "Please select a time slot."
            )
            return redirect("management:seat_management")

        if not start_date_value:
            messages.error(
                request,
                "Please select a start date."
            )
            return redirect("management:seat_management")

        # ==========================================
        # GET STUDENT
        # ==========================================

        student = get_object_or_404(
            StudentProfile,
            student_id=student_id,
        )

        if student.status != "APPROVED":
            messages.error(
                request,
                "Only approved students can be assigned a seat."
            )
            return redirect("management:seat_management")

        # ==========================================
        # GET PLAN
        # ==========================================

        plan = get_object_or_404(
            SubscriptionPlan,
            plan_id=plan_id,
            is_active=True,
        )

        # ==========================================
        # GET TIME SLOT
        # ==========================================

        time_slot = get_object_or_404(
            TimeSlot,
            slot_id=time_slot_id,
            is_active=True,
        )


        if time_slot.start_time < time(6, 0):
            messages.error(
                request,
                "Library start time is 6:00 AM. Please select a valid start time.",
            )
            return redirect("management:seat_management")


        # ==========================================
        # PARSE START DATE
        # ==========================================

        try:

            start_date = datetime.strptime(
                start_date_value,
                "%Y-%m-%d",
            ).date()

        except ValueError:

            messages.error(
                request,
                "Invalid start date."
            )

            return redirect(
                "management:seat_management"
            )

        # ==========================================
        # PARSE PAYMENT AMOUNT
        # ==========================================

        try:

            amount_received = Decimal(
                amount_received_value or "0"
            )

        except Exception:

            messages.error(
                request,
                "Invalid payment amount."
            )

            return redirect(
                "management:seat_management"
            )

        # ==========================================
        # PAYMENT VALIDATION
        # ==========================================

        if amount_received < 0:

            messages.error(
                request,
                "Payment amount cannot be negative."
            )

            return redirect(
                "management:seat_management"
            )

        if amount_received > plan.fee:

            messages.error(
                request,
                "Payment cannot be greater than the plan fee."
            )

            return redirect(
                "management:seat_management"
            )

        # ==========================================
        # CHECK EXISTING PAYMENT
        # ==========================================
        #
        # If the student already has an active
        # subscription, we don't allow another one
        # to be created from Seat Management.
        #
        # Future installments will be handled from
        # Fee Management.
        # ==========================================

        existing_subscription = (
            Subscription.objects
            .filter(
                student=student,
                status="ACTIVE",
            )
            .first()
        )

        if existing_subscription:

            messages.error(
                request,
                "This student already has an active subscription. "
                "Use Fee Management to record another installment."
            )

            return redirect(
                "management:seat_management"
            )

        # ==========================================
        # CALCULATE SUBSCRIPTION END DATE
        # ==========================================

        end_date = (
            start_date
            + timedelta(
                days=plan.duration_days - 1
            )
        )

        # ==========================================
        # CREATE SUBSCRIPTION + SEAT + PAYMENT
        # ==========================================

        try:

            with transaction.atomic():

                # ----------------------------------
                # LOCK THE SEAT
                # ----------------------------------

                seat = (
                    Seat.objects
                    .select_for_update()
                    .filter(
                        seat_id=seat_id,
                        status="AVAILABLE",
                    )
                    .first()
                )

                if not seat:

                    raise ValueError(
                        "The selected seat is no longer available."
                    )

                # ----------------------------------
                # CREATE SUBSCRIPTION
                # ----------------------------------

                subscription = Subscription.objects.create(

                    student=student,

                    plan=plan,

                    time_slot=time_slot,

                    start_date=start_date,

                    end_date=end_date,

                    status="ACTIVE",
                )

                # ----------------------------------
                # CREATE SEAT ALLOCATION
                # ----------------------------------

                SeatAllocation.objects.create(

                    student=student,

                    seat=seat,

                    subscription=subscription,

                    start_date=start_date,

                    end_date=end_date,

                    start_time=time_slot.start_time,

                    end_time=time_slot.end_time,

                    status="ACTIVE",
                )

                # ----------------------------------
                # MARK SEAT OCCUPIED
                # ----------------------------------

                seat.status = "OCCUPIED"

                seat.save(
                    update_fields=["status"]
                )

                # ----------------------------------
                # CREATE PAYMENT
                # ----------------------------------

                if amount_received > 0:

                    payment = Payment.objects.create(

                        student=student,

                        subscription=subscription,

                        amount=amount_received,

                        payment_method=payment_method,

                        transaction_id=(
                            transaction_id
                            if transaction_id
                            else None
                        ),

                        status="PAID",

                        remarks=remarks,
                    )

                    # ----------------------------------
                    # CREATE PAYMENT ALLOCATION
                    # ----------------------------------

                    PaymentAllocation.objects.create(

                        payment=payment,

                        subscription=subscription,

                        amount_allocated=amount_received,

                        remarks=remarks,
                    )

            # ======================================
            # SUCCESS MESSAGE
            # ======================================

            remaining_amount = (
                plan.fee - amount_received
            )

            messages.success(
                request,
                f"Seat {seat.seat_number} assigned successfully "
                f"to {student.full_name}. "
                f"₹{amount_received} received. "
                f"Remaining fee: ₹{remaining_amount}."
            )

        except ValueError as error:

            messages.error(
                request,
                str(error)
            )

        except Exception as error:

            messages.error(
                request,
                "Unable to assign the seat. Please try again."
            )

        return redirect(
            "management:seat_management"
        )

    # ==================================================
    # GET REQUEST
    # ==================================================

    seats = (
        Seat.objects
        .select_related("library")
        .order_by("seat_id")
    )

    # ------------------------------------------
    # SEAT STATUS
    # ------------------------------------------

    available_seats = seats.filter(
        status="AVAILABLE"
    )

    occupied_seats = seats.filter(
        status="OCCUPIED"
    )

    maintenance_seats = seats.filter(
        status="MAINTENANCE"
    )

    # ------------------------------------------
    # APPROVED STUDENTS WITHOUT ACTIVE
    # SUBSCRIPTION
    # ------------------------------------------

    active_students = (
        StudentProfile.objects
        .filter(
            status="APPROVED"
        )
        .exclude(
            subscriptions__status="ACTIVE"
        )
        .select_related(
            "preferred_plan",
            "preferred_time_slot",
        )
        .distinct()
        .order_by(
            "full_name"
        )
    )

    # ------------------------------------------
    # ACTIVE PLANS
    # ------------------------------------------

    plans = (
        SubscriptionPlan.objects
        .filter(
            is_active=True
        )
        .order_by(
            "hours_per_day"
        )
    )

    # ------------------------------------------
    # ACTIVE TIME SLOTS
    # ------------------------------------------

    time_slots = (
        TimeSlot.objects
        .filter(
            is_active=True
        )
        .order_by(
            "start_time"
        )
    )

    # ------------------------------------------
    # CURRENT ACTIVE ALLOCATIONS
    # ------------------------------------------

    active_allocations = (
        SeatAllocation.objects
        .filter(
            status="ACTIVE"
        )
        .select_related(
            "student",
            "seat",
            "subscription",
            "subscription__plan",
            "subscription__time_slot",
        )
        .order_by(
            "seat__seat_id"
        )
    )

    # ==========================================
    # RENDER PAGE
    # ==========================================

    return render(
        request,
        "management/seat_management.html",
        {
            "seats": seats,

            "available_seats": available_seats,

            "occupied_seats": occupied_seats,

            "maintenance_seats": maintenance_seats,

            "active_students": active_students,

            "plans": plans,

            "time_slots": time_slots,

            "active_allocations": active_allocations,
        },
    )


@login_required
def reports(request):

    return render(
        request,
        "management/reports.html"
    )


@login_required
def settings(request):

    return render(
        request,
        "management/settings.html"
    )


@login_required
def subscriptions(request):

    today = timezone.now().date()

    active_subscriptions = Subscription.objects.filter(
        status="ACTIVE",
        end_date__gte=today,
    ).select_related(
        "student",
        "plan",
        "time_slot",
    ).prefetch_related(
        "seat_allocations__seat",
    ).order_by("end_date")

    expiring = Subscription.objects.filter(
        status="ACTIVE",
        end_date__gte=today,
        end_date__lte=today + timedelta(days=7),
    ).select_related(
        "student",
        "plan",
        "time_slot",
    ).prefetch_related(
        "seat_allocations__seat",
    ).order_by("end_date")

    expired = Subscription.objects.filter(
        end_date__lt=today,
    ).select_related(
        "student",
        "plan",
        "time_slot",
    ).prefetch_related(
        "seat_allocations__seat",
    ).order_by("-end_date")

    installment_count = 0

    return render(
        request,
        "management/subscriptions.html",
        {
            "active_subscriptions": active_subscriptions,
            "expiring": expiring,
            "expired": expired,
            "installment_count": installment_count,
        },
    )


@login_required
def release_seat(request, allocation_id):

    if request.method != "POST":
        return redirect("management:seat_management")

    allocation = get_object_or_404(
        SeatAllocation.objects.select_related(
            "seat",
            "student",
            "subscription",
        ),
        allocation_id=allocation_id,
        status="ACTIVE",
    )

    try:
        with transaction.atomic():

            # Lock the seat
            seat = Seat.objects.select_for_update().get(
                seat_id=allocation.seat.seat_id
            )

            # End seat allocation
            allocation.status = "ENDED"
            allocation.save(update_fields=["status"])

            # Make seat available again
            seat.status = "AVAILABLE"
            seat.save(update_fields=["status"])

            # End the related subscription
            subscription = allocation.subscription

            if subscription.status == "ACTIVE":
                subscription.status = "CANCELLED"
                subscription.save(
                    update_fields=["status"]
                )

        messages.success(
            request,
            f"Seat {seat.seat_number} has been released successfully."
        )

    except Exception:
        messages.error(
            request,
            "Unable to release the seat. Please try again."
        )

    return redirect("management:seat_management")

@login_required
def change_seat(request, allocation_id):
    """
    Change only the seat assigned to an active allocation.

    This does NOT:
    - create a new subscription
    - create a payment
    - change the subscription fee
    - affect today's collection
    - change the student's plan
    - change the student's time slot
    """

    allocation = get_object_or_404(
        SeatAllocation.objects.select_related(
            "student",
            "seat",
            "subscription",
            "subscription__plan",
            "subscription__time_slot",
        ),
        allocation_id=allocation_id,
        status="ACTIVE",
    )

    if request.method != "POST":
        return redirect("management:seat_management")

    new_seat_id = request.POST.get("new_seat")

    if not new_seat_id:
        messages.error(request, "Please select a new seat.")
        return redirect("management:seat_management")

    with transaction.atomic():

        # Lock the current allocation.
        allocation = (
            SeatAllocation.objects
            .select_for_update()
            .select_related(
                "student",
                "seat",
                "subscription",
                "subscription__plan",
                "subscription__time_slot",
            )
            .get(
                allocation_id=allocation_id,
                status="ACTIVE",
            )
        )

        # Lock the requested new seat.
        new_seat = (
            Seat.objects
            .select_for_update()
            .filter(
                seat_id=new_seat_id,
                status="AVAILABLE",
            )
            .first()
        )

        if not new_seat:
            messages.error(
                request,
                "The selected seat is no longer available.",
            )
            return redirect("management:seat_management")

        # Prevent selecting the same seat.
        if new_seat.seat_id == allocation.seat.seat_id:
            messages.error(
                request,
                "The student is already assigned to this seat.",
            )
            return redirect("management:seat_management")

        old_seat = Seat.objects.select_for_update().get(
            seat_id=allocation.seat.seat_id
        )

        # Free the old seat.
        old_seat.status = "AVAILABLE"
        old_seat.save(update_fields=["status"])

        # Occupy the new seat.
        new_seat.status = "OCCUPIED"
        new_seat.save(update_fields=["status"])

        # Update only the seat on the existing allocation.
        allocation.seat = new_seat
        allocation.save(update_fields=["seat"])

    messages.success(
        request,
        f"Seat changed successfully from "
        f"Seat {old_seat.seat_number} to "
        f"Seat {new_seat.seat_number}.",
    )

    return redirect("management:seat_management")


@login_required
def students(request):

    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("search", "").strip()

    students_queryset = StudentProfile.objects.select_related(
        "user",
        "preferred_plan",
        "preferred_time_slot",
    ).prefetch_related(
        "subscriptions__plan",
        "subscriptions__time_slot",
        "seat_allocations__seat",
    ).order_by("-registration_date")

    # Search
    if search_query:
        students_queryset = students_queryset.filter(
            models.Q(full_name__icontains=search_query)
            | models.Q(email__icontains=search_query)
            | models.Q(phone__icontains=search_query)
        )

    # Status filter
    if status_filter:
        students_queryset = students_queryset.filter(
            status=status_filter
        )

    return render(
        request,
        "management/students.html",
        {
            "students": students_queryset,
            "status_filter": status_filter,
            "search_query": search_query,
        },
    )

@login_required
def add_student(request):

    plans = SubscriptionPlan.objects.filter(
        is_active=True
    ).order_by("hours_per_day")

    time_slots = TimeSlot.objects.filter(
        is_active=True
    ).order_by("start_time")

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()

        full_name = request.POST.get("full_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        date_of_birth = request.POST.get("date_of_birth", "").strip()

        preferred_plan_id = request.POST.get(
            "preferred_plan"
        )

        preferred_time_slot_id = request.POST.get(
            "preferred_time_slot"
        )

        # -------------------------
        # REQUIRED FIELD VALIDATION
        # -------------------------

        if not email:
            messages.error(
                request,
                "Email is required."
            )
            return redirect(
                "management:add_student"
            )

        if not password:
            messages.error(
                request,
                "Password is required."
            )
            return redirect(
                "management:add_student"
            )

        if not full_name:
            messages.error(
                request,
                "Full name is required."
            )
            return redirect(
                "management:add_student"
            )

        if not phone:
            messages.error(
                request,
                "Phone number is required."
            )
            return redirect(
                "management:add_student"
            )

        # -------------------------
        # USERNAME = EMAIL
        # -------------------------

        if User.objects.filter(
            username=email
        ).exists():

            messages.error(
                request,
                "A student account with this email already exists."
            )

            return redirect(
                "management:add_student"
            )

        # -------------------------
        # STUDENT EMAIL CHECK
        # -------------------------

        if StudentProfile.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "A student with this email already exists."
            )

            return redirect(
                "management:add_student"
            )

        # -------------------------
        # PLAN
        # -------------------------

        preferred_plan = None

        if preferred_plan_id:

            preferred_plan = get_object_or_404(
                SubscriptionPlan,
                plan_id=preferred_plan_id,
                is_active=True,
            )

        # -------------------------
        # TIME SLOT
        # -------------------------

        preferred_time_slot = None

        if preferred_time_slot_id:

            preferred_time_slot = get_object_or_404(
                TimeSlot,
                slot_id=preferred_time_slot_id,
                is_active=True,
            )

        # -------------------------
        # DATE OF BIRTH
        # -------------------------

        parsed_date_of_birth = None

        if date_of_birth:

            try:

                parsed_date_of_birth = datetime.strptime(
                    date_of_birth,
                    "%Y-%m-%d",
                ).date()

            except ValueError:

                messages.error(
                    request,
                    "Invalid date of birth."
                )

                return redirect(
                    "management:add_student"
                )

        # -------------------------
        # CREATE USER + STUDENT
        # -------------------------

        try:

            with transaction.atomic():

                user = User.objects.create_user(
                    username=email,
                    password=password,
                    email=email,
                )

                user.role = "STUDENT"

                user.save(
                    update_fields=["role"]
                )

                student = StudentProfile.objects.create(
                    user=user,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    date_of_birth=parsed_date_of_birth,
                    preferred_plan=preferred_plan,
                    preferred_time_slot=preferred_time_slot,
                    status="PENDING",
                )

                # -------------------------
                # PHOTO
                # -------------------------

                if request.FILES.get("photo"):

                    student.photo = request.FILES[
                        "photo"
                    ]

                # -------------------------
                # AADHAAR
                # -------------------------

                if request.FILES.get(
                    "aadhaar_document"
                ):

                    student.aadhaar_document = (
                        request.FILES[
                            "aadhaar_document"
                        ]
                    )

                student.save()

            messages.success(
                request,
                f"{student.full_name} has been added successfully "
                f"and is waiting for approval."
            )

            return redirect(
                "management:student_detail",
                student_id=student.student_id,
            )

        except Exception as error:

            messages.error(
                request,
                "Unable to add student. Please try again."
            )

            return redirect(
                "management:add_student"
            )

    return render(
        request,
        "management/add_student.html",
        {
            "plans": plans,
            "time_slots": time_slots,
        },
    )