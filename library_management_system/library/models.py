from django.db import models

from students.models import StudentProfile


class Library(models.Model):
    library_id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=150)

    address = models.TextField()

    total_seats = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Seat(models.Model):

    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("OCCUPIED", "Occupied"),
        ("MAINTENANCE", "Maintenance"),
    ]

    seat_id = models.AutoField(primary_key=True)

    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        related_name="seats"
    )

    seat_number = models.CharField(max_length=20)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["library", "seat_number"],
                name="unique_seat_per_library"
            )
        ]

    def __str__(self):
        return self.seat_number


class SubscriptionPlan(models.Model):

    plan_id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=100)

    hours_per_day = models.PositiveIntegerField()

    duration_days = models.PositiveIntegerField()

    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class TimeSlot(models.Model):

    slot_id = models.AutoField(primary_key=True)

    name = models.CharField(max_length=100)

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return (
            self.name
        )


class Subscription(models.Model):

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    subscription_id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    time_slot = models.ForeignKey(
        TimeSlot,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subscriptions"
    )

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.plan.name}"


class SeatAllocation(models.Model):

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("ENDED", "Ended"),
    ]

    allocation_id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="seat_allocations"
    )

    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name="allocations"
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="seat_allocations"
    )

    start_date = models.DateField()

    end_date = models.DateField()

    start_time = models.TimeField(
        null=True,
        blank=True
    )

    end_time = models.TimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    def __str__(self):
        return (
            f"{self.student.full_name} - "
            f"Seat {self.seat.seat_number}"
        )