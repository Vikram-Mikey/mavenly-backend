from rest_framework.views import APIView
# Remove profile photo API
from rest_framework.permissions import IsAuthenticated

class RemoveProfilePhotoView(APIView):
    def post(self, request):
        user_id = request.COOKIES.get('user_id')
        if not user_id:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        user.photo_url = ''
        user.save()
        return Response({'success': 'Profile photo removed.'})
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import SignupSerializer, UserSerializer, ProgramReviewSerializer
from .models import User, ProgramReview
from django.contrib.auth.hashers import make_password, check_password
from .forgot_password_otp import ForgotPasswordOTPView, ForgotPasswordVerifyOTPView
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import random

# In-memory store for verification codes (for demo; use a DB or cache in production)
verification_codes = {}

class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(password=make_password(serializer.validated_data['password']))
            response = Response(UserSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)
            # Secure cookie settings from settings.py
            cookie_opts = {
                'path': '/',
                'secure': getattr(settings, 'USER_COOKIE_SECURE', True),
                'samesite': getattr(settings, 'USER_COOKIE_SAMESITE', 'Lax'),
                'httponly': getattr(settings, 'USER_COOKIE_HTTPONLY', False),
            }
            response.set_cookie('user_id', str(user.id), **cookie_opts)
            return response
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from django.conf import settings
# API endpoint to provide UPI number and QR image URL securely
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def payment_info_view(request):
    return Response({
        'upi_number': settings.UPI_NUMBER,
        'qr_image_url': settings.QR_IMAGE_URL,
    })

class LoginView(APIView):
    def post(self, request):
        identifier = request.data.get('username', '').strip()
        password = request.data.get('password')
        user = None
        # Try to find user by username (case-sensitive) or email (case-insensitive)
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email__iexact=identifier)
            except User.DoesNotExist:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        if user and check_password(password, user.password):
            response = Response(UserSerializer(user, context={'request': request}).data)
            cookie_opts = {
                'path': '/',
                'secure': getattr(settings, 'USER_COOKIE_SECURE', True),
                'samesite': getattr(settings, 'USER_COOKIE_SAMESITE', 'Lax'),
                'httponly': getattr(settings, 'USER_COOKIE_HTTPONLY', False),
            }
            response.set_cookie('user_id', str(user.id), **cookie_opts)
            response.set_cookie('user_email', user.email, **cookie_opts)
            return response
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    def post(self, request):
        username = request.data.get('username')
        new_password = request.data.get('new_password')
        if not username or not new_password:
            return Response({'error': 'Username and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)
        # Validate password using SignupSerializer logic
        serializer = SignupSerializer(data={'username': username, 'password': new_password, 'email': 'dummy@email.com', 'phone': '0000000000'})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'error': serializer.errors.get('password', ['Invalid password'])[0]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=username)
            user.password = make_password(new_password)
            user.save()
            return Response({'success': 'Password changed successfully.'})
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

class CheckoutEmailView(APIView):
    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        address = request.data.get('address')
        phone = request.data.get('phone')
        cart = request.data.get('cart', [])
        referral_code = request.data.get('referral_code')
        referral_name = request.data.get('referral_name')
        total = request.data.get('total')
        original_amount = request.data.get('original_amount')
        discount_amount = request.data.get('discount_amount')
        if not all([name, email, address, phone]):
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = '🛒 New Checkout Submission - Mavenly'
        cart_items_str = ''
        if cart:
            cart_items_str = '\nItems to be paid for:'
            cart_items_str += '\n-------------------------------\n'
            cart_items_str += f"{'No.':<4} {'Item':<30} {'Plan':<15} {'Price':<10}\n"
            cart_items_str += '-'*65 + '\n'
            for idx, item in enumerate(cart, 1):
                if isinstance(item, dict):
                    program = item.get('program', '-')
                    plan = item.get('plan', '-')
                    # Try to get price from multiple possible keys
                    price = item.get('price')
                    if price is None:
                        price = item.get('plan_amount')
                    if price is None:
                        price = item.get('amount')
                    if price is None:
                        price = '-'
                    cart_items_str += f"{idx:<4} {program:<30} {plan:<15} {price:<10}\n"
                else:
                    cart_items_str += f"{idx:<4} {str(item):<30} {'-':<15} {'-':<10}\n"
            cart_items_str += '-------------------------------\n'
        else:
            cart_items_str = '\n(No items in cart)\n'

        referral_str = ''
        if referral_code and referral_name:
            referral_str = f"\nReferral Code: {referral_code}\nReferral Name: {referral_name}\n"
        elif referral_code:
            referral_str = f"\nReferral Code: {referral_code}\n"
        elif referral_name:
            referral_str = f"\nReferral Name: {referral_name}\n"

        # Add total, original, and discount info
        amount_str = ''
        if original_amount is not None and discount_amount is not None and total is not None:
            try:
                original_amount = float(original_amount)
                discount_amount = float(discount_amount)
                total = float(total)
                amount_str = f"\nOriginal Amount: ₹{original_amount:,.2f}\nDiscount: -₹{discount_amount:,.2f}\nTotal Payable: ₹{total:,.2f}\n"
            except:
                pass

        message = f"""
==============================
Mavenly Checkout Submission
==============================

Customer Details:
Name   : {name}
Email  : {email}
Address: {address}
Phone  : {phone}
{referral_str}
{cart_items_str}
{amount_str}
Thank you for using Mavenly!\nPlease process the payment/order accordingly.
"""
        from django.conf import settings
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            fail_silently=False,
        )
        return Response({'success': 'Checkout email sent to host.'})

from rest_framework.response import Response
from rest_framework import status

class ProgramReviewView(APIView):
    def get(self, request):
        program = request.GET.get('program')
        if not program:
            return Response({'error': 'Program is required.'}, status=status.HTTP_400_BAD_REQUEST)
        reviews = ProgramReview.objects.filter(program=program).order_by('-created_at')
        serializer = ProgramReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data.copy()
        from datetime import datetime
        data['created_at'] = datetime.utcnow().isoformat()
        print("Incoming review POST data:", data)
        serializer = ProgramReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            print("Review saved successfully.")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        # Only allow host/admin to delete
        from django.conf import settings
        ADMIN_EMAIL = getattr(settings, 'HOST_EMAIL', None)
        if not ADMIN_EMAIL:
            ADMIN_EMAIL = 'r.vikram.s321@gmail.com'
        user_email = request.COOKIES.get('user_email') or request.headers.get('X-User-Email')
        print(f"DEBUG: user_email={user_email!r}, ADMIN_EMAIL={ADMIN_EMAIL!r}")
        if not user_email or user_email.strip().lower() != ADMIN_EMAIL.strip().lower():
            return Response({'error': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        review_id = pk or request.GET.get('id')
        if not review_id:
            return Response({'error': 'Review ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            review = ProgramReview.objects.get(pk=review_id)
            review.delete()
            return Response({'success': 'Review deleted.'}, status=status.HTTP_200_OK)
        except ProgramReview.DoesNotExist:
            return Response({'error': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
class PaymentConfirmationEmailView(APIView):
    def post(self, request):
        # The frontend must send the total value (including discounts) as calculated on the Addcart page.
        # Example frontend payload:
        # axios.post('/api/payment-confirmation/', { name, email, cart, total, ... })
        name = request.data.get('name')
        email = request.data.get('email')
        cart = request.data.get('cart', [])
        total = request.data.get('total')
        original_amount = request.data.get('original_amount')
        discount_amount = request.data.get('discount_amount')
        if not all([name, email]) or not cart or total is None:
            return Response({'error': 'Name, email, cart, and total are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = '🧾 Invoice & Payment Confirmation - Mavenly'
        try:
            total = float(total)
        except:
            return Response({'error': 'Invalid total value.'}, status=status.HTTP_400_BAD_REQUEST)
        # Parse original and discount amounts if present
        try:
            original_amount = float(original_amount)
        except:
            original_amount = None
        try:
            discount_amount = float(discount_amount)
        except:
            discount_amount = None
        invoice_rows = ''
        if cart:
            for idx, item in enumerate(cart, 1):
                if isinstance(item, dict):
                    program = item.get('program', '-')
                    plan = item.get('plan', '-')
                    price = item.get('price')
                    if price is None:
                        price = item.get('plan_amount')
                    if price is None:
                        price = item.get('amount')
                    if price is None:
                        price = '-'
                    invoice_rows += f"<tr style='background:#f9fafb;'>"
                    invoice_rows += f"<td style='padding:8px 6px;border:1px solid #e5e7eb;text-align:center;'>{idx}</td>"
                    invoice_rows += f"<td style='padding:8px 6px;border:1px solid #e5e7eb;'>{program}</td>"
                    invoice_rows += f"<td style='padding:8px 6px;border:1px solid #e5e7eb;text-align:center;'>{plan}</td>"
                    invoice_rows += f"<td style='padding:8px 6px;border:1px solid #e5e7eb;text-align:right;'>₹{price}</td>"
                    invoice_rows += "</tr>"
                else:
                    invoice_rows += f"<tr><td colspan='4' style='padding:8px 6px;border:1px solid #e5e7eb;text-align:center;'>{str(item)}</td></tr>"
        else:
            invoice_rows = "<tr><td colspan='4' style='padding:12px;text-align:center;color:#ef4444;'>No items in cart</td></tr>"

        # Add original, discount, and total info below the table
        summary_html = ''
        if original_amount is not None and discount_amount is not None:
            summary_html = f'''
              <tr style="background:#fff;">
                <td colspan="2" style="border:none;"></td>
                <td style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;">Original:</td>
                <td style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;">₹{original_amount:,.2f}</td>
              </tr>
              <tr style="background:#fff;">
                <td colspan="2" style="border:none;"></td>
                <td style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;">Discount:</td>
                <td style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;color:#ef4444;">-₹{discount_amount:,.2f}</td>
              </tr>
            '''

        html_message = f'''
        <div style="font-family:Arial,sans-serif;max-width:540px;margin:0 auto;background:#fff;border-radius:14px;padding:32px 28px 28px 28px;box-shadow:0 4px 24px #0001;border:1.5px solid #2563eb;">
          <div style="text-align:center;margin-bottom:18px;">
            <h1 style="color:#ff5757;margin:0 0 8px 0;font-size:2rem;letter-spacing:1px;">Mavenly</h1>
            <h2 style="color:#2563eb;margin:0 0 8px 0;font-size:1.7rem;letter-spacing:1px;">Payment Invoice</h2>
          </div>
          <div style="background:#f1f5f9;border-radius:8px;padding:18px 16px 10px 16px;margin-bottom:18px;border:1px solid #e0e7ef;">
            <div style="font-size:15px;color:#374151;margin-bottom:10px;">Hi <b>{name}</b>,<br>Thank you for your payment! Your order has been received and processed successfully.</div>
            <table style="width:100%;border-collapse:collapse;margin-top:10px;">
              <thead>
                <tr style="background:#2563eb;color:#fff;">
                  <th style="padding:8px 6px;border:1px solid #e5e7eb;">No.</th>
                  <th style="padding:8px 6px;border:1px solid #e5e7eb;">Program</th>
                  <th style="padding:8px 6px;border:1px solid #e5e7eb;">Plan</th>
                  <th style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;">Amount (₹)</th>
                </tr>
              </thead>
              <tbody>
                {invoice_rows}
                {summary_html}
                <tr style="background:#f3f4f6;font-weight:bold;">
                  <td colspan="2" style="border:none;"></td>
                  <td style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;">Total:</td>
                  <td style="padding:8px 6px;border:1px solid #e5e7eb;text-align:right;color:#2563eb;">₹{total:.2f}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div style="font-size:18px;color:#4998da;text-align:center;font-weight:bold;margin-top:24px;">Mavenly</div>
          <div style="font-size:14px;color:#64748b;text-align:center;">If you have any questions, please contact us.<br/><br/>Best regards,<br/>Mavenly Team</div>
        </div>
        '''
        message = f"""
==============================
Mavenly Invoice & Payment Confirmation
==============================

Dear {name},

Thank you for your payment! Your order has been received and processed successfully.

If you have any questions, please contact us.

Best regards,\nMavenly Team
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
            html_message=html_message
        )
        return Response({'success': 'Confirmation email sent to user.'})

class ContactEnquiryEmailView(APIView):
    def post(self, request):
        import logging
        name = request.data.get('name')
        email = request.data.get('email')
        message = request.data.get('message')
        phone = request.data.get('phone')
        company = request.data.get('company') or ''
        subject_text = request.data.get('subject') or ''
        if not all([name, email, message]):
            return Response({'error': 'Name, email, and message are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = '📩 New Enquiry Received - Mavenly'
        message_body = f"""
==============================
Mavenly Enquiry
==============================

Name   : {name}
Email  : {email}
Phone  : {phone or ''}
Company: {company}
Subject: {subject_text}

Message:
--------
{message}

Please respond to the enquiry as soon as possible.
"""
        from django.conf import settings
        try:
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
                fail_silently=False,
            )
            return Response({'success': 'Enquiry email sent to host.'})
        except Exception as e:
            logging.exception("Failed to send enquiry email")
            return Response({'error': f'Failed to send enquiry email: {str(e)}'}, status=500)

class ProgramDevEnquiryEmailView(APIView):
    def post(self, request):
        import logging
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        company = request.data.get('company', '-')
        program = request.data.get('program', '-')
        if not all([name, email, phone, company]):
            return Response({'error': 'Name, email, phone, and company are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = '📩 New Program Enquiry - Mavenly'
        message = f"""
==============================
Mavenly Program Enquiry
==============================

Name   : {name}
Email  : {email}
Phone  : {phone}
Company: {company}
Program: {program}

This is a program enquiry from the ProgramDevSection form.
"""
        from django.conf import settings
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
                fail_silently=False,
            )
            return Response({'success': 'Program enquiry email sent to host.'})
        except Exception as e:
            logging.exception("Failed to send program enquiry email")
            return Response({'error': f'Failed to send program enquiry email: {str(e)}'}, status=500)

class FreelancingProgramDevEnquiryEmailView(APIView):
    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        company = request.data.get('company', '')
        office_motive = request.data.get('officeMotive', '')
        preference = request.data.get('preference', '')
        program = request.data.get('program', '')
        if not all([name, email, phone]):
            return Response({'error': 'Name, email, and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = '📩 New Freelancing Program Enquiry - Mavenly'
        message = f"""
==============================
Mavenly Freelancing Program Enquiry
==============================

Name         : {name}
Email        : {email}
Phone        : {phone}
Company Name : {company}
Office Motive: {office_motive}
Preference   : {preference}
Program      : {program}

This is a freelancing program enquiry from the FreelancingProgramDevSection form.
"""
        from django.conf import settings
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            fail_silently=False,
        )
        return Response({'success': 'Freelancing program enquiry email sent to host.'})

class ProfileView(APIView):
    def get(self, request):
        user_id = request.COOKIES.get('user_id')
        if not user_id:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            user = User.objects.get(id=user_id)
            return Response(UserSerializer(user, context={'request': request}).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

@method_decorator(csrf_exempt, name='dispatch')


class PublicProfileView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            return Response(UserSerializer(user, context={'request': request}).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        
class SendVerificationCodeView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        code = str(random.randint(100000, 999999))
        verification_codes[email] = code
        html_message = f'''
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;background:#f8fafc;border-radius:12px;padding:32px 24px 24px 24px;box-shadow:0 4px 24px #0001;">
          <div style="text-align:center;margin-bottom:18px;">
            <img src="https://mavenly.in/mavenly%20logo.png" alt="Mavenly Logo" style="height:48px;margin-bottom:8px;"/>
            <h2 style="color:#2563eb;margin:0 0 8px 0;font-size:1.6rem;">Email Verification Code</h2>
          </div>
          <div style="background:#fff;border-radius:8px;padding:24px 18px;margin-bottom:18px;border:1px solid #e0e7ef;text-align:center;">
            <div style="font-size:15px;color:#374151;margin-bottom:10px;">Use the code below to verify your email address:</div>
            <div style="font-size:2.2rem;letter-spacing:0.2em;font-weight:700;color:#2563eb;background:#f1f5f9;padding:12px 0;border-radius:7px;display:inline-block;width:180px;">{code}</div>
          </div>
          <div style="font-size:14px;color:#64748b;text-align:center;">This code is valid for a short time. If you did not request this, you can ignore this email.<br/><br/>Thank you,<br/>Mavenly Team</div>
        </div>
        '''
        try:
            send_mail(
                'Your Verification Code',
                f'Your verification code is: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=html_message
            )
            return Response({'success': 'Verification code sent.'})
        except Exception as e:
            import logging
            logging.exception("Failed to send verification code email")
            return Response({'error': f'Failed to send verification code: {str(e)}'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UpdateProfileView(APIView):
    def post(self, request):
        user_id = request.COOKIES.get('user_id')
        if not user_id:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        field = request.data.get('field')
        value = request.data.get('value')
        code = request.data.get('verification_code')
        password = request.data.get('password')
        if not all([field, value, code]):
            return Response({'error': 'All fields and verification code are required.'}, status=status.HTTP_400_BAD_REQUEST)
        email = user.email if field != 'email' else value
        if verification_codes.get(email) != code:
            return Response({'error': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)
        if field == 'username':
            user.username = value
        elif field == 'email':
            user.email = value
        elif field == 'phone':
            user.phone = value
        elif field == 'password':
            if not password:
                return Response({'error': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)
            user.password = make_password(password)
        else:
            return Response({'error': 'Invalid field.'}, status=status.HTTP_400_BAD_REQUEST)
        user.save()
        verification_codes.pop(email, None)
        return Response({'success': 'Profile updated.'})

class UploadProfilePhotoView(APIView):
    def post(self, request):
        user_id = request.COOKIES.get('user_id')
        if not user_id:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'error': 'No photo uploaded.'}, status=status.HTTP_400_BAD_REQUEST)
        filename = f'user_{user.id}_profile.jpg'
        path = default_storage.save(f'profile_photos/{filename}', ContentFile(photo.read()))
        user.photo_url = default_storage.url(path)
        user.save()
        return Response({'photo_url': user.photo_url})
