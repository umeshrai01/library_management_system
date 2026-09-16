from django.urls import path
from . import views


app_name = "management"


def owner_path(route, view, name):
    return path(route, views.owner_required(view), name=name)


urlpatterns = [

    # Dashboard
    owner_path("", views.dashboard, name="dashboard"),

    # Students
    owner_path("students/", views.students, name="students"),

    owner_path("students/add/", views.add_student, name="add_student"),

    owner_path("students/<int:student_id>/", views.student_detail, name="student_detail"),

    owner_path("students/<int:student_id>/approve/", views.approve_student, name="approve_student"),

    owner_path("students/<int:student_id>/reject/", views.reject_student, name="reject_student"),

    owner_path(
    "students/<int:student_id>/unregister/",
    views.unregister_student,
    name="unregister_student",
),

    owner_path("students/<int:student_id>/edit/", views.edit_student, name="edit_student"),


    # Owners
    owner_path("owners/", views.owners, name="owners"),

    # Attendance
    owner_path("attendance/", views.attendance, name="attendance"),

    # Fees
    owner_path("fees/", views.fee_management, name="fee_management"),
    owner_path("fees/collect/",views.collect_payment,name="collect_payment",),

    # Seats
    owner_path("seats/", views.seat_management, name="seat_management"),

    owner_path("seats/<int:allocation_id>/release/",views.release_seat,name="release_seat"),

    owner_path("seats/<int:allocation_id>/change/",views.change_seat,name="change_seat",),

    owner_path("seats/<int:allocation_id>/change/",views.change_seat,name="change_seat",),

    # Subscriptions
    owner_path("subscriptions/", views.subscriptions, name="subscriptions"),

    # Reports
    owner_path("reports/", views.reports, name="reports"),

    # Settings
    owner_path("settings/", views.settings, name="settings"),
]
