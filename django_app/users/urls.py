from django.urls import path
from . import views

urlpatterns = [
    path("",          views.dashboard_view, name="dashboard"),
    path("register/", views.register_view,  name="register"),
    path("login/",    views.login_view,     name="login"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("logout/",   views.logout_view,    name="logout"),
]
