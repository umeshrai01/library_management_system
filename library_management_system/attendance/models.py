from django.db import models
from students.models import StudentProfile
from library.models import Seat


class Attendance(models.Model):

    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
    ]

    attendance_id = models.AutoField(primary_key=True)

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="attendance_records"
    )

    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        related_name="attendance_records"
    )

    date = models.DateField()

    check_in = models.TimeField(
        null=True,
        blank=True
    )

    check_out = models.TimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PRESENT"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"],
                name="one_attendance_per_student_per_day"
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} - {self.date}"