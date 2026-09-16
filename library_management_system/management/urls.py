from django.urls import path
from . import views


app_name = "management"


urlpatterns = [

    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Students
    path("students/", views.students, name="students"),

    path("students/add/", views.add_student, name="add_student"),

    path("students/<int:student_id>/", views.student_detail, name="student_detail"),

    path("students/<int:student_id>/approve/", views.approve_student, name="approve_student"),

    path("students/<int:student_id>/reject/", views.reject_student, name="reject_student"),

    path(
    "students/<int:student_id>/unregister/",
    views.unregister_student,
    name="unregister_student",
),

    path("students/<int:student_id>/edit/", views.edit_student, name="edit_student"),


    # Owners
    path("owners/", views.owners, name="owners"),

    # Attendance
    path("attendance/", views.attendance, name="attendance"),

    # Fees
    path("fees/", views.fee_management, name="fee_management"),
    path("fees/collect/",views.collect_payment,name="collect_payment",),

    # Seats
    path("seats/", views.seat_management, name="seat_management"),

    path("seats/<int:allocation_id>/release/",views.release_seat,name="release_seat"),

    path("seats/<int:allocation_id>/change/",views.change_seat,name="change_seat",),

    path("seats/<int:allocation_id>/change/",views.change_seat,name="change_seat",),

    # Subscriptions
    path("subscriptions/", views.subscriptions, name="subscriptions"),

    # Reports
    path("reports/", views.reports, name="reports"),

    # Settings
    path("settings/", views.settings, name="settings"),
]