from django.conf import settings
from django.db import models


class StudentProfile(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("UNREGISTERED", "Unregistered"),
    ]

    student_id = models.AutoField(primary_key=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    full_name = models.CharField(
        max_length=150
    )

    email = models.EmailField(
        unique=True,
    )

    phone = models.CharField(
        max_length=15
    )

    address = models.TextField(
        blank=True
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    photo = models.ImageField(
        upload_to="students/photos/",
        null=True,
        blank=True
    )

    aadhaar_document = models.FileField(
        upload_to="students/aadhaar/",
        null=True,
        blank=True
    )

    registration_date = models.DateField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    preferred_plan = models.ForeignKey(
    "library.SubscriptionPlan",
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="preferred_students"
    )

    preferred_time_slot = models.ForeignKey(
    "library.TimeSlot",
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name="preferred_students"
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_students"
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    rejection_reason = models.TextField(
        blank=True
    )

    def __str__(self):
        return self.full_name