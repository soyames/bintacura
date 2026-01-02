from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_new
from . import universal_payment_views
from . import payment_request_views
from .invoice_views import MarkOnsitePaymentPaidView, VerifyInvoiceQRView, InitiateInvoicePaymentView

app_name = "payments"

router = DefaultRouter()
router.register(r"fees", views.FeeLedgerViewSet, basename="feeledger")
router.register(
    r"payment-requests", views.PaymentRequestViewSet, basename="paymentrequest"
)
router.register(r"linked-vendors", views.LinkedVendorViewSet, basename="linkedvendor")
router.register(
    r"financial-chats", views.FinancialChatViewSet, basename="financialchat"
)
router.register(
    r"fedapay-transactions", views.FedaPayTransactionViewSet, basename="fedapaytransaction"
)

router.register(r"phones", views_new.ParticipantPhoneViewSet, basename="participantphone")
router.register(r"service-catalog", views_new.ServiceCatalogViewSet, basename="servicecatalog")
router.register(r"gateway-accounts", views_new.ParticipantGatewayAccountViewSet, basename="gatewayaccount")
router.register(r"service-transactions", views_new.ServiceTransactionViewSet, basename="servicetransaction")
router.register(r"payouts", views_new.PayoutScheduleViewSet, basename="payoutschedule")
router.register(r"receipts", views_new.PaymentReceiptViewSet, basename="receipt")

urlpatterns = [
    path("", include(router.urls)),
    path("service/pay/", views_new.ServicePaymentView.as_view(), name="service-payment"),
    path("fees/calculate/", views_new.FeeCalculationView.as_view(), name="fee-calculation"),
    path("fedapay/webhook/", views.fedapay_webhook, name="fedapay-webhook"),
    path("webhooks/fedapay/", views.fedapay_webhook, name="fedapay-webhook-alt"),
    path("transactions/<uuid:transaction_id>/download-receipt/", views.download_transaction_receipt, name="download-transaction-receipt"),
    path("receipts/<uuid:pk>/", views_new.PaymentReceiptViewSet.as_view({'get': 'retrieve'}), name="receipt-detail"),
    path("receipts/<uuid:pk>/download/", views_new.PaymentReceiptViewSet.as_view({'get': 'download'}), name="download-receipt"),
    path("mark-onsite-paid/", MarkOnsitePaymentPaidView.as_view(), name="mark-onsite-paid"),
    path("verify-invoice-qr/", VerifyInvoiceQRView.as_view(), name="verify-invoice-qr"),
    path("initiate-invoice-payment/", InitiateInvoicePaymentView.as_view(), name="initiate-invoice-payment"),
    
    # New payment workflow endpoints
    path("request-cash-payment/", payment_request_views.create_cash_payment_request, name="request-cash-payment"),
    path("pending-payment-requests/", payment_request_views.get_pending_payment_requests, name="pending-payment-requests"),
    path("process-cash-payment/<uuid:payment_request_id>/", payment_request_views.process_cash_payment, name="process-cash-payment"),
    
    # Web views for providers
    path("provider/requests/", payment_request_views.ProviderPaymentRequestsView.as_view(), name="provider-payment-requests"),
    path("provider/requests/<uuid:request_id>/process/", payment_request_views.ProcessPaymentRequestView.as_view(), name="process-payment-request"),

    # Universal payment endpoints (works for all service types: appointment, pharmacy_order, lab_test, etc.)
    path("verify/<str:service_type>/<uuid:service_id>/", universal_payment_views.verify_payment_qr, name="verify-payment-qr"),
    path("pay/<str:service_type>/<uuid:service_id>/", universal_payment_views.pay_service, name="pay-service"),
    path("scan/", universal_payment_views.scan_service_qr, name="scan-service-qr"),
    path("callback/<str:service_type>/<uuid:service_id>/", universal_payment_views.payment_callback, name="payment-callback"),
]
