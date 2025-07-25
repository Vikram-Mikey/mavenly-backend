from django.urls import path
from .views import SignupView, LoginView, ForgotPasswordView, ForgotPasswordOTPView, ForgotPasswordVerifyOTPView, CheckoutEmailView, PaymentConfirmationEmailView, ContactEnquiryEmailView, ProgramDevEnquiryEmailView, FreelancingProgramDevEnquiryEmailView, ProfileView, SendVerificationCodeView, UpdateProfileView, UploadProfilePhotoView, RemoveProfilePhotoView ,PublicProfileView, ProgramReviewView

from django.urls import re_path

from .views import SignupView, LoginView, ForgotPasswordView, ForgotPasswordOTPView, ForgotPasswordVerifyOTPView, CheckoutEmailView, PaymentConfirmationEmailView, ContactEnquiryEmailView, ProgramDevEnquiryEmailView, FreelancingProgramDevEnquiryEmailView, ProfileView, SendVerificationCodeView, UpdateProfileView, UploadProfilePhotoView, payment_info_view
urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('forgot-password-otp/', ForgotPasswordOTPView.as_view(), name='forgot-password-otp'),
    path('forgot-password-verify/', ForgotPasswordVerifyOTPView.as_view(), name='forgot-password-verify'),
    path('checkout-email/', CheckoutEmailView.as_view(), name='checkout-email'),
    path('payment-confirmation-email/', PaymentConfirmationEmailView.as_view(), name='payment-confirmation-email'),
    path('enquiry-email/', ContactEnquiryEmailView.as_view(), name='enquiry-email'),
    path('program-enquiry-email/', ProgramDevEnquiryEmailView.as_view(), name='program-enquiry-email'),
    path('freelancing-enquiry-email/', FreelancingProgramDevEnquiryEmailView.as_view(), name='freelancing-enquiry-email'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('send-verification-code/', SendVerificationCodeView.as_view(), name='send-verification-code'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
    path('upload-profile-photo/', UploadProfilePhotoView.as_view(), name='upload-profile-photo'),
    path('remove-profile-photo/', RemoveProfilePhotoView.as_view(), name='remove-profile-photo'),
    path('profile/<int:user_id>/', PublicProfileView.as_view(), name='public-profile'),
    path('program-reviews/', ProgramReviewView.as_view(), name='program-reviews'),
    re_path(r'^program-reviews/(?P<pk>[\w-]+)/$', ProgramReviewView.as_view(), name='program-review-detail'),
    path('payment-info/', payment_info_view, name='payment-info'),
]
