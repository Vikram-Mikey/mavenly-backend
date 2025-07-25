import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import User
from django.contrib.auth.hashers import make_password
from .serializers import SignupSerializer

OTP_STORE = {}

def validate_password(password):
    import re
    errors = []
    if password is not None:
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter.')
        if not re.search(r'\d', password):
            errors.append('Password must contain at least one number.')
        if not re.search(r'[^A-Za-z0-9]', password):
            errors.append('Password must contain at least one special character.')
    return errors

class ForgotPasswordOTPView(APIView):
    def post(self, request):
        username_or_email = request.data.get('username')
        if not username_or_email:
            return Response({'error': 'Username or email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Only allow sending OTP to the email of a registered username
        try:
            user = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Always send OTP to the email of the found user
        otp = str(random.randint(100000, 999999))
        OTP_STORE[user.username] = otp
        subject = 'Mavenly Password Reset OTP'
        text_message = f'Hello {user.username},\n\nYour One-Time Password (OTP) for resetting your Mavenly account password is: {otp}\n\nThis OTP is valid for 10 minutes. If you did not request a password reset, please ignore this email.\n\nThank you,\nMavenly Team'
        html_message = f'''<div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;border:1px solid #eee;padding:24px;">
            <h2 style="color:#007bff;">Mavenly Password Reset</h2>
            <p>Hello <b>{user.username}</b>,</p>
            <p>Your <b>One-Time Password (OTP)</b> for resetting your Mavenly account password is:</p>
            <div style="font-size:2rem;font-weight:bold;letter-spacing:2px;background:#f5f5f5;padding:12px 0;text-align:center;border-radius:6px;margin:16px 0;">{otp}</div>
            <p>This OTP is valid for <b>10 minutes</b>.<br>If you did not request a password reset, please ignore this email.</p>
            <p style="margin-top:32px;">Thank you,<br><span style="color:#007bff;font-weight:bold;">Mavenly Team</span></p>
        </div>'''
        send_mail(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
            html_message=html_message
        )
        return Response({'success': 'OTP sent to your email.'})

class ForgotPasswordVerifyOTPView(APIView):
    def post(self, request):
        username = request.data.get('username')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
        if not username or not otp or not new_password:
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
        if OTP_STORE.get(username) != otp:
            return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        # Only validate password, not username/email/phone uniqueness
        password_errors = validate_password(new_password)
        if password_errors:
            return Response({'error': {'password': password_errors}}, status=status.HTTP_400_BAD_REQUEST)
        user.password = make_password(new_password)
        user.save()
        OTP_STORE.pop(username, None)
        return Response({'success': 'Password changed successfully.'})
