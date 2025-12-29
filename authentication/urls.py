from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "authentication"

router = DefaultRouter()

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("accept-terms/", views.accept_terms, name="accept_terms"),
    path("decline-terms/", views.decline_terms, name="decline_terms"),
    path("verify-email/", views.verify_email_page, name="verify_email_page"),
    path("verify-email/code/", views.verify_email_with_code, name="verify_email_code"),
    path(
        "verify-email/<str:uidb64>/<str:token>/",
        views.verify_email_with_link,
        name="verify_email_link",
    ),
    path(
        "resend-verification/",
        views.resend_verification_email,
        name="resend_verification",
    ),
    path("change-password/", views.change_password_view, name="change_password"),
    path("forgot-password/", views.password_reset_request_view, name="password_reset_request"),
    path(
        "reset-password/<str:uidb64>/<str:token>/",
        views.password_reset_confirm_view,
        name="password_reset_confirm",
    ),
    path("", include(router.urls)),
]
