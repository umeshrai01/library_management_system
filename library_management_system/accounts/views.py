from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.shortcuts import redirect, render

from .models import User
from students.models import StudentProfile
from library.models import SubscriptionPlan, TimeSlot


def login(request):

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None

        if user is None:

            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Invalid email or password."
                }
            )

        user = authenticate(
            request,
            username=user.username,
            password=password
        )

        if user is None:

            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Invalid email or password."
                }
            )

        if not user.is_active:

            return render(
                request,
                "accounts/login.html",
                {
                    "error": "This account is inactive."
                }
            )

        auth_login(request, user)

        # ADMIN / OWNER
        if user.role in ["ADMIN", "OWNER"]:
            return redirect("management:dashboard")

        # STUDENT
        if user.role == "STUDENT":

            try:
                student = user.student_profile

            except StudentProfile.DoesNotExist:

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "error": "Student profile not found."
                    }
                )

            if student.status == "UNREGISTERED":

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "error": "Your library account has been unregistered."
                    }
                )

            return redirect("students_dashboard")

        return render(
            request,
            "accounts/login.html",
            {
                "error": "Invalid account role."
            }
        )

    return render(
        request,
        "accounts/login.html"
    )


def logout_view(request):

    logout(request)

    return redirect("login")


def signup(request):

    subscription_plans = SubscriptionPlan.objects.filter(
        is_active=True
    ).order_by(
        "hours_per_day"
    )

    time_slots = TimeSlot.objects.filter(
        is_active=True
    ).order_by(
        "start_time"
    )

    if request.method == "POST":

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        preferred_plan_id = request.POST.get(
            "preferred_plan",
            ""
        )

        preferred_time_slot_id = request.POST.get(
            "preferred_time_slot",
            ""
        )

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )


        # -------------------------
        # REQUIRED FIELDS
        # -------------------------

        if (
            not full_name
            or not email
            or not phone
            or not address
            or not preferred_plan_id
            or not preferred_time_slot_id
            or not password
            or not confirm_password
        ):

            messages.error(
                request,
                "Please fill in all required fields."
            )

            return render(
                request,
                "accounts/signup.html",
                {
                    "subscription_plans": subscription_plans,
                    "time_slots": time_slots,
                }
            )


        # -------------------------
        # PASSWORD
        # -------------------------

        if password != confirm_password:

            messages.error(
                request,
                "Passwords do not match."
            )

            return render(
                request,
                "accounts/signup.html",
                {
                    "subscription_plans": subscription_plans,
                    "time_slots": time_slots,
                }
            )


        # -------------------------
        # DUPLICATE EMAIL
        # -------------------------

        if User.objects.filter(
            username=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return render(
                request,
                "accounts/signup.html",
                {
                    "subscription_plans": subscription_plans,
                    "time_slots": time_slots,
                }
            )


        if User.objects.filter(
            email=email
        ).exists():

            messages.error(
                request,
                "An account with this email already exists."
            )

            return render(
                request,
                "accounts/signup.html",
                {
                    "subscription_plans": subscription_plans,
                    "time_slots": time_slots,
                }
            )


        # -------------------------
        # GET SELECTED PLAN
        # -------------------------

        try:

            preferred_plan = SubscriptionPlan.objects.get(
                plan_id=preferred_plan_id,
                is_active=True
            )

        except SubscriptionPlan.DoesNotExist:

            messages.error(
                request,
                "Selected subscription plan is invalid."
            )

            return render(
                request,
                "accounts/signup.html",
                {
                    "subscription_plans": subscription_plans,
                    "time_slots": time_slots,
                }
            )


        # -------------------------
        # GET SELECTED TIME SLOT
        # -------------------------

        try:

            preferred_time_slot = TimeSlot.objects.get(
                slot_id=preferred_time_slot_id,
                is_active=True
            )

        except TimeSlot.DoesNotExist:

            messages.error(
                request,
                "Selected time slot is invalid."
            )

            return render(
                request,
                "accounts/signup.html",
                {
                    "subscription_plans": subscription_plans,
                    "time_slots": time_slots,
                }
            )


        # -------------------------
        # CREATE USER
        # -------------------------

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            role="STUDENT"
        )


        # -------------------------
        # CREATE STUDENT PROFILE
        # -------------------------

        StudentProfile.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            phone=phone,
            address=address,
            preferred_plan=preferred_plan,
            preferred_time_slot=preferred_time_slot,
            status="PENDING"
        )


        # -------------------------
        # SUCCESS
        # -------------------------

        messages.success(
            request,
            "Registration successful. Your account is waiting for admin approval."
        )

        return redirect("login")


    # -------------------------
    # GET REQUEST
    # -------------------------

    return render(
        request,
        "accounts/signup.html",
        {
            "subscription_plans": subscription_plans,
            "time_slots": time_slots,
        }
    )