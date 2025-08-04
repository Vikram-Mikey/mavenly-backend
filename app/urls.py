from django.urls import path
from .views import (
    InvoiceEmailView,
    ContactEnquiryEmailView,
    ProgramDevEnquiryEmailView,
    FreelancingProgramDevEnquiryEmailView,
    ProfileView,
    PublicProfileView,
    SendVerificationCodeView,
    UpdateProfileView,
    ProgramReviewView,
    RemoveProfilePhotoView,
    SignupView,
    LoginView,
    CheckoutEmailView,
    PaymentConfirmationEmailView,
    LogoutView,
)
from .forgot_password_otp import ForgotPasswordOTPView, ForgotPasswordVerifyOTPView

urlpatterns = [
    path('invoice-email/', InvoiceEmailView.as_view(), name='invoice-email'),
    path('contact-enquiry-email/', ContactEnquiryEmailView.as_view(), name='contact-enquiry-email'),
    path('program-dev-enquiry-email/', ProgramDevEnquiryEmailView.as_view(), name='program-dev-enquiry-email'),
    path('freelancing-program-dev-enquiry-email/', FreelancingProgramDevEnquiryEmailView.as_view(), name='freelancing-program-dev-enquiry-email'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('public-profile/<int:user_id>/', PublicProfileView.as_view(), name='public-profile'),
    path('send-verification-code/', SendVerificationCodeView.as_view(), name='send-verification-code'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    path('program-reviews/', ProgramReviewView.as_view(), name='program-reviews'),
    path('remove-profile-photo/', RemoveProfilePhotoView.as_view(), name='remove-profile-photo'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('checkout-email/', CheckoutEmailView.as_view(), name='checkout-email'),
    path('payment-confirmation-email/', PaymentConfirmationEmailView.as_view(), name='payment-confirmation-email'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordOTPView.as_view(), name='forgot-password'),
    path('forgot-password-verify/', ForgotPasswordVerifyOTPView.as_view(), name='forgot_password_verify'),
]
