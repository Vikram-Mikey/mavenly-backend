
# Function-based, CSRF-exempt logout endpoint for /logout/ and /api/logout/
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['POST', 'GET'])
@authentication_classes([BasicAuthentication])  # Remove SessionAuthentication to avoid CSRF
@permission_classes([AllowAny])
def logout_view(request):
    if request.method == 'GET':
        return Response({'status': 'logout endpoint is live'}, status=200)
    try:
        django_logout(request)
    except Exception:
        pass
    return Response({'success': 'Logged out successfully.'}, status=status.HTTP_200_OK)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from django.contrib.auth import logout as django_logout

# Add a logout API view
from .models import User, ProgramReview
from uuid import uuid4
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from .serializers import SignupSerializer, UserSerializer, ProgramReviewSerializer
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
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import random
import logging

from django.core.mail import send_mail
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.contrib.auth.hashers import make_password

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import User
from .serializers import UserSerializer
from rest_framework.permissions import AllowAny

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
# In-memory store for verification codes (for demo; use a DB or cache in production)
verification_codes = {}

@method_decorator(csrf_exempt, name='dispatch')
class RemoveProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)
        user.photo_url = ''
        user.save()
        return Response({'success': 'Profile photo removed.'})


@method_decorator(csrf_exempt, name='dispatch')
class SignupView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            raw_password = serializer.validated_data['password']
            hashed_password = make_password(raw_password)
            logging.debug(f"Signup: raw_password='{raw_password}', hashed_password='{hashed_password}'")
            user = serializer.save(password=hashed_password)
            logging.debug(f"Signup: user.id={user.id}, user.username={user.username}, user.password={user.password}")
            return Response(UserSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Invalid input.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def payment_info_view(request):
    return Response({
        'upi_number': settings.UPI_NUMBER,
        'qr_image_url': settings.QR_IMAGE_URL,
    })

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        identifier = request.data.get('username', '').strip()
        password = request.data.get('password')
        user = None
        logging.debug(f"Login request data: username={identifier}, password={password}")
        # Try username first
        try:
            user = User.objects.get(username=identifier)
            logging.debug(f"User found by username: id={user.id}, username={user.username}, email={user.email}, hash={user.password}")
        except User.DoesNotExist:
            # Try email next
            try:
                user = User.objects.get(email__iexact=identifier)
                logging.debug(f"User found by email: id={user.id}, username={user.username}, email={user.email}, hash={user.password}")
            except User.DoesNotExist:
                logging.warning(f"Login failed: identifier '{identifier}' not found.")
                return Response({'error': 'Username or email not found.'}, status=status.HTTP_400_BAD_REQUEST)
        # User found, check password
        password_matches = check_password(password, user.password)
        logging.debug(f"Login: entered_password='{password}', stored_hash='{user.password}', match={password_matches}")
        if password_matches:
            logging.info(f"Login successful for user '{identifier}' (id={user.id})")
            login(request, user)  # Django session login
            return Response(UserSerializer(user, context={'request': request}).data)
        else:
            logging.warning(f"Login failed: incorrect password for identifier '{identifier}' (id={user.id})")
            return Response({'error': 'Incorrect password.'}, status=status.HTTP_400_BAD_REQUEST)


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
                    price = item.get('price') or item.get('plan_amount') or item.get('amount') or '-'
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
Thank you for using Mavenly!
Please process the payment/order accordingly.
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
            fail_silently=False,
        )
        return Response({'success': 'Checkout email sent to host.'})

from rest_framework.permissions import AllowAny

class ProgramReviewView(APIView):
    permission_classes = [AllowAny]
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
        serializer = ProgramReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        ADMIN_EMAIL = getattr(settings, 'HOST_EMAIL', 'r.vikram.s321@gmail.com')
        user_email = request.COOKIES.get('user_email') or request.headers.get('X-User-Email')
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
        name = request.data.get('name')
        email = request.data.get('email')
        cart = request.data.get('cart', [])
        total = request.data.get('total')
        original_amount = request.data.get('original_amount')
        discount_amount = request.data.get('discount_amount')
        if not all([name, email]) or not cart or total is None:
            return Response({'error': 'Name, email, cart, and total are required.'}, status=status.HTTP_400_BAD_REQUEST)
        subject = '🧾 Invoice & Payment Confirmation - Mavenly'

        cart_items_str = ''
        if cart:
            cart_items_str = '\nItems Paid for:'
            cart_items_str += '\n-------------------------------\n'
            cart_items_str += f"{'No.':<4} {'Item':<30} {'Plan':<15} {'Price':<10}\n"
            cart_items_str += '-'*65 + '\n'
            for idx, item in enumerate(cart, 1):
                if isinstance(item, dict):
                    program = item.get('program', '-')
                    plan = item.get('plan', '-')
                    price = item.get('price') or item.get('plan_amount') or item.get('amount') or '-'
                    cart_items_str += f"{idx:<4} {program:<30} {plan:<15} {price:<10}\n"
                else:
                    cart_items_str += f"{idx:<4} {str(item):<30} {'-':<15} {'-':<10}\n"
            cart_items_str += '-------------------------------\n'
        else:
            cart_items_str = '\n(No items in cart)\n'

        amount_str = ''
        if original_amount is not None and discount_amount is not None and total is not None:
            try:
                original_amount = float(original_amount)
                discount_amount = float(discount_amount)
                total = float(total)
                amount_str = f"\nOriginal Amount: ₹{original_amount:,.2f}\nDiscount: -₹{discount_amount:,.2f}\nTotal Paid: ₹{total:,.2f}\n"
            except:
                pass

        message = f"""
==============================
Mavenly Payment Confirmation
==============================

Customer Details:
Name   : {name}
Email  : {email}

{cart_items_str}
{amount_str}

Thank you for your payment!
"""
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return Response({'success': 'Payment confirmation email sent.'})

# You can add other views below as needed...



# Simple in-memory store for verification codes (for demo only)
verification_codes = {}

class InvoiceEmailView(APIView):
    def post(self, request):
        # Extract data from request
        name = request.data.get('name')
        email = request.data.get('email')
        cart = request.data.get('cart', [])
        total = request.data.get('total')
        original_amount = request.data.get('original_amount')
        discount_amount = request.data.get('discount_amount')

        if not all([name, email, total]):
            return Response({'error': 'Name, email, and total are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate total, original_amount, discount_amount as floats
        try:
            total = float(total)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid total value.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            original_amount = float(original_amount)
        except (TypeError, ValueError):
            original_amount = None

        try:
            discount_amount = float(discount_amount)
        except (TypeError, ValueError):
            discount_amount = None

        # Build invoice rows HTML
        invoice_rows = ''
        if cart:
            for idx, item in enumerate(cart, 1):
                if isinstance(item, dict):
                    program = item.get('program', '-')
                    plan = item.get('plan', '-')
                    price = item.get('price') or item.get('plan_amount') or item.get('amount') or '-'
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

        # Add original, discount summary rows
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

        # Compose full HTML message
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

Best regards,
Mavenly Team
"""
        try:
            send_mail(
                'Mavenly Payment Confirmation',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=html_message,
            )
        except Exception as e:
            logging.exception("Failed to send invoice email")
            return Response({'error': f'Failed to send confirmation email: {str(e)}'}, status=500)

        return Response({'success': 'Confirmation email sent to user.'})

# Other API views follow similar pattern

class ContactEnquiryEmailView(APIView):
    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        message_text = request.data.get('message')
        phone = request.data.get('phone')
        company = request.data.get('company') or ''
        subject_text = request.data.get('subject') or ''

        if not all([name, email, message_text]):
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
{message_text}

Please respond to the enquiry as soon as possible.
"""
        try:
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
                fail_silently=False,
            )
        except Exception as e:
            logging.exception("Failed to send enquiry email")
            return Response({'error': f'Failed to send enquiry email: {str(e)}'}, status=500)
        return Response({'success': 'Enquiry email sent to host.'})

class ProgramDevEnquiryEmailView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        name = request.data.get('name')
        email = request.data.get('email')
        phone = request.data.get('phone')
        company = request.data.get('company', '-')
        program = request.data.get('program', '-')

        if not all([name, email, phone, company]):
            return Response({'error': 'Name, email, phone, and company are required.'}, status=status.HTTP_400_BAD_REQUEST)

        subject = '📩 New Program Enquiry - Mavenly'
        message_body = f"""
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
        try:
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
                fail_silently=False,
            )
        except Exception as e:
            logging.exception("Failed to send program enquiry email")
            return Response({'error': f'Failed to send program enquiry email: {str(e)}'}, status=500)
        return Response({'success': 'Program enquiry email sent to host.'})

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
        message_body = f"""
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
        try:
            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [getattr(settings, 'HOST_EMAIL', settings.DEFAULT_FROM_EMAIL)],
                fail_silently=False,
            )
        except Exception as e:
            logging.exception("Failed to send freelancing program enquiry email")
            return Response({'error': f'Failed to send freelancing program enquiry email: {str(e)}'}, status=500)
        return Response({'success': 'Freelancing program enquiry email sent to host.'})



@method_decorator(csrf_exempt, name='dispatch')
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class PublicProfileView(APIView):
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = UserSerializer(user, context={'request': request})
            return Response(serializer.data)
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
            <p style="font-size:18px;color:#374151;margin-bottom:12px;">Your verification code is:</p>
            <p style="font-weight:bold;font-size:26px;color:#2563eb;letter-spacing:6px;margin:0;">{code}</p>
          </div>
          <div style="font-size:14px;color:#64748b;text-align:center;">If you did not request this, please ignore this email.</div>
        </div>
        '''
        try:
            send_mail(
                'Mavenly Email Verification Code',
                f'Your verification code is: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=html_message,
            )
        except Exception as e:
            logging.exception("Failed to send verification code email")
            return Response({'error': f'Failed to send verification code: {str(e)}'}, status=500)
        return Response({'success': 'Verification code sent.'})

@method_decorator(csrf_exempt, name='dispatch')
class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'User not authenticated.'}, status=status.HTTP_401_UNAUTHORIZED)

        data = request.data
        verification_code = data.get('verification_code')
        email = data.get('email')

        # Verify code
        if not (email and verification_code and verification_codes.get(email) == verification_code):
            return Response({'error': 'Invalid or missing verification code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Update fields if provided
        if 'name' in data:
            user.name = data['name']

        if 'email' in data:
            user.email = data['email']

        if 'password' in data:
            user.password = make_password(data['password'])

        if 'phone' in data:
            user.phone = data['phone']

        if 'bio' in data:
            user.bio = data['bio']

        # Handle profile photo upload if exists
        photo_file = request.FILES.get('profile_photo')
        if photo_file:
            filename = f"profile_{user.id}.jpg"
            try:
                path = default_storage.save(filename, ContentFile(photo_file.read()))
                user.profile_photo = path
            except Exception as e:
                logging.exception("Failed to save profile photo")
                return Response({'error': 'Failed to save profile photo.'}, status=500)

        user.save()
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data)

