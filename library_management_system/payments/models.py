from django.db import models

from students.models import StudentProfile
from library.models import Subscription


class Payment(models.Model):

    STATUS_CHOICES = [
        ("PAID", "Paid"),
        ("PENDING", "Pending"),
        ("REFUNDED", "Refunded"),
    ]

    METHOD_CHOICES = [
        ("CASH", "Cash"),
        ("UPI", "UPI"),
        ("CARD", "Card"),
        ("BANK", "Bank Transfer"),
        ("OTHER", "Other"),
    ]

    payment_id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES
    )

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PAID"
    )

    remarks = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount}"


class PaymentAllocation(models.Model):

    allocation_id = models.AutoField(primary_key=True)

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="allocations"
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="payment_allocations"
    )

    amount_allocated = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    remarks = models.TextField(
        blank=True
    )

    def __str__(self):
        return (
            f"Payment {self.payment.payment_id} - "
            f"₹{self.amount_allocated}"
        )