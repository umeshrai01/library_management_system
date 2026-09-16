from django.urls import path

from . import views

urlpatterns = [
path("dashboard/",views.dashboard,name="students_dashboard"),

path("profile/",views.profile,name="students_profile"),

path("documents/",views.upload_documents,name="students_documents"),

path("subscriptions/", views.subscriptions, name="students_subscriptions"),

path("seat/", views.my_seat, name="students_seat"),
]