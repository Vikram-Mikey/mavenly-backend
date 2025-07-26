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
)

urlpatterns = [
    path('invoice-email/', InvoiceEmailView.as_view(), name='invoice-email'),
    path('contact-enquiry-email/', ContactEnquiryEmailView.as_view(), name='contact-enquiry-email'),
    path('program-dev-enquiry-email/', ProgramDevEnquiryEmailView.as_view(), name='program-dev-enquiry-email'),
    path('freelancing-program-dev-enquiry-email/', FreelancingProgramDevEnquiryEmailView.as_view(), name='freelancing-program-dev-enquiry-email'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('public-profile/<int:user_id>/', PublicProfileView.as_view(), name='public-profile'),
    path('send-verification-code/', SendVerificationCodeView.as_view(), name='send-verification-code'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),
]
