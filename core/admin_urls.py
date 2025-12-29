from django.urls import path
from . import admin_views

app_name = "superadmin"

urlpatterns = [
    path("dashboard/", admin_views.AdminDashboardView.as_view(), name="dashboard"),
    path(
        "provider-verification/",
        admin_views.ProviderVerificationView.as_view(),
        name="provider_verification",
    ),
    path(
        "provider/<uuid:provider_id>/",
        admin_views.ProviderDetailView.as_view(),
        name="provider_detail",
    ),
    path(
        "provider/<uuid:provider_id>/approve/",
        admin_views.ApproveProviderView.as_view(),
        name="approve_provider",
    ),
    path(
        "provider/<uuid:provider_id>/reject/",
        admin_views.RejectProviderView.as_view(),
        name="reject_provider",
    ),
    path(
        "refunds/", admin_views.RefundManagementView.as_view(), name="refund_management"
    ),
    path(
        "refunds/<uuid:refund_id>/",
        admin_views.RefundDetailView.as_view(),
        name="refund_detail",
    ),
    path(
        "refunds/<uuid:refund_id>/approve/",
        admin_views.ApproveRefundView.as_view(),
        name="approve_refund",
    ),
    path(
        "refunds/<uuid:refund_id>/reject/",
        admin_views.RejectRefundView.as_view(),
        name="reject_refund",
    ),
    path("analytics/", admin_views.AnalyticsDashboardView.as_view(), name="analytics"),
    path("users/", admin_views.UserManagementView.as_view(), name="user_management"),
    path(
        "users/<uuid:user_id>/",
        admin_views.UserDetailView.as_view(),
        name="user_detail",
    ),
    path(
        "users/<uuid:user_id>/toggle-status/",
        admin_views.ToggleUserStatusView.as_view(),
        name="toggle_user_status",
    ),
    path("audit-logs/", admin_views.AuditLogsView.as_view(), name="audit_logs"),
    path(
        "financials/",
        admin_views.FinancialDashboardView.as_view(),
        name="financial_dashboard",
    ),
    path("admins/", admin_views.AdminManagementView.as_view(), name="admin_management"),
    path("admins/create/", admin_views.CreateAdminView.as_view(), name="create_admin"),
    path(
        "admins/<uuid:admin_id>/",
        admin_views.AdminDetailView.as_view(),
        name="admin_detail",
    ),
    path(
        "admins/<uuid:admin_id>/permissions/",
        admin_views.UpdateAdminPermissionsView.as_view(),
        name="update_admin_permissions",
    ),
    path(
        "users/<uuid:user_id>/promote/",
        admin_views.PromoteToAdminView.as_view(),
        name="promote_to_admin",
    ),
    path(
        "admins/<uuid:admin_id>/revoke/",
        admin_views.RevokeAdminView.as_view(),
        name="revoke_admin",
    ),
]
