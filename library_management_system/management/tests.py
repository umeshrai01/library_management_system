from datetime import time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from library.models import (
    Library,
    Seat,
    SeatAllocation,
    Subscription,
    SubscriptionPlan,
    TimeSlot,
)
from payments.models import Payment
from students.models import StudentProfile

from .views import calculate_end_time


class ManagementAccessAndRenewalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="owner-password",
            role="OWNER",
        )
        self.student_user = User.objects.create_user(
            username="student@example.com",
            email="student@example.com",
            password="student-password",
            role="STUDENT",
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            full_name="Renewal Student",
            email="student@example.com",
            phone="9999999999",
            address="Bermo",
            status="APPROVED",
        )
        self.plan = SubscriptionPlan.objects.create(
            name="8 Hours",
            hours_per_day=8,
            duration_days=30,
            fee=Decimal("1000.00"),
        )
        self.time_slot = TimeSlot.objects.create(
            name="6:00 AM",
            start_time=time(6, 0),
        )
        self.library = Library.objects.create(
            name="Test Library",
            address="Bermo",
            total_seats=1,
        )
        self.seat = Seat.objects.create(
            library=self.library,
            seat_number="A-1",
            status="OCCUPIED",
        )

    def test_student_cannot_open_management_dashboard(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("management:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_owner_can_open_management_dashboard(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("management:dashboard"))

        self.assertEqual(response.status_code, 200)

    def test_end_time_uses_plan_duration(self):
        self.assertEqual(calculate_end_time(time(6, 0), 8), time(14, 0))

    def test_seat_assignment_stores_end_time_from_plan_duration(self):
        available_seat = Seat.objects.create(
            library=self.library,
            seat_number="A-2",
            status="AVAILABLE",
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            reverse("management:seat_management"),
            {
                "student": self.student.student_id,
                "seat": available_seat.seat_id,
                "plan": self.plan.plan_id,
                "time_slot": self.time_slot.slot_id,
                "start_date": timezone.localdate().isoformat(),
                "amount_received": "0",
                "payment_method": "CASH",
            },
        )

        self.assertRedirects(response, reverse("management:seat_management"))
        allocation = SeatAllocation.objects.get(student=self.student, status="ACTIVE")
        self.assertEqual(allocation.start_time, time(6, 0))
        self.assertEqual(allocation.end_time, time(14, 0))

    def test_payment_renews_an_expired_subscription_with_same_seat(self):
        today = timezone.localdate()
        expired_subscription = Subscription.objects.create(
            student=self.student,
            plan=self.plan,
            time_slot=self.time_slot,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=1),
            status="ACTIVE",
        )
        expired_allocation = SeatAllocation.objects.create(
            student=self.student,
            seat=self.seat,
            subscription=expired_subscription,
            start_date=expired_subscription.start_date,
            end_date=expired_subscription.end_date,
            start_time=time(6, 0),
            end_time=time(14, 0),
            status="ACTIVE",
        )
        self.client.force_login(self.owner)

        payment_page = self.client.get(reverse("management:collect_payment"))
        self.assertContains(payment_page, "Renewal due")

        response = self.client.post(
            reverse("management:collect_payment"),
            {
                "student": self.student.student_id,
                "subscription": expired_subscription.subscription_id,
                "amount": "1000.00",
                "payment_method": "CASH",
                "transaction_id": "renewal-1",
            },
        )

        self.assertRedirects(response, reverse("management:fee_management"))
        expired_subscription.refresh_from_db()
        expired_allocation.refresh_from_db()
        renewed_subscription = Subscription.objects.get(
            student=self.student,
            status="ACTIVE",
            end_date__gte=today,
        )
        renewed_allocation = SeatAllocation.objects.get(
            subscription=renewed_subscription,
            status="ACTIVE",
        )

        self.assertEqual(expired_subscription.status, "EXPIRED")
        self.assertEqual(expired_allocation.status, "ENDED")
        self.assertEqual(renewed_subscription.start_date, today)
        self.assertEqual(renewed_subscription.end_date, today + timedelta(days=29))
        self.assertEqual(renewed_allocation.seat, self.seat)
        self.assertEqual(renewed_allocation.end_time, time(14, 0))
        self.assertTrue(
            Payment.objects.filter(
                subscription=renewed_subscription,
                amount=Decimal("1000.00"),
            ).exists()
        )

    def test_pending_students_come_before_expiring_students(self):
        pending_user = User.objects.create_user(
            username="pending@example.com",
            email="pending@example.com",
            password="pending-password",
            role="STUDENT",
        )
        pending_student = StudentProfile.objects.create(
            user=pending_user,
            full_name="Pending Student",
            email="pending@example.com",
            phone="8888888888",
            address="Bermo",
            status="PENDING",
        )
        Subscription.objects.create(
            student=self.student,
            plan=self.plan,
            time_slot=self.time_slot,
            start_date=timezone.localdate() - timedelta(days=27),
            end_date=timezone.localdate() + timedelta(days=3),
            status="ACTIVE",
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse("management:students"))
        ordered_students = list(response.context["students"])

        self.assertEqual(ordered_students[0], pending_student)
        self.assertEqual(ordered_students[1], self.student)
