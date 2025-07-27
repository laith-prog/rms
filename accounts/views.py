from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from datetime import datetime
from django.urls import reverse
from django.contrib.auth import login as auth_login

from .models import User, CustomerProfile, StaffProfile, PhoneVerification, PasswordReset, StaffShift
from .serializers import (
    PhoneVerificationSerializer, VerifyPhoneSerializer, UserRegistrationSerializer, 
    UserLoginSerializer, ForgotPasswordSerializer, VerifyResetCodeSerializer,
    ResetPasswordSerializer, CustomerProfileSerializer, ProfileImageSerializer,
    CustomTokenObtainPairSerializer
)
from .permissions import IsCustomer, IsStaffMember


@swagger_auto_schema(
    method='post',
    request_body=PhoneVerificationSerializer,
    responses={
        200: openapi.Response(
            description="Verification code sent successfully",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_STRING, description="Success message"),
                    'code': openapi.Schema(type=openapi.TYPE_STRING, description="4-digit verification code (only included in development)"),
                    'phone': openapi.Schema(type=openapi.TYPE_STRING, description="Phone number")
                }
            )
        ),
        400: 'Invalid phone number or phone already registered',
    },
    operation_description="Send a verification code to the provided phone number for new user registration. Only requires phone number in request."
)
@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """
    Send a verification code to the provided phone number for new user registration
    
    This endpoint generates a 4-digit verification code and sends it to the user's phone.
    In a production environment, this would integrate with an SMS service.
    The phone number must not already be registered with an existing account.
    """
    serializer = PhoneVerificationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    
    # Check if user already exists - for registration, the phone should NOT exist
    if User.objects.filter(phone=phone).exists():
        return Response({'error': 'Phone number is already registered'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate and send verification code
    verification = PhoneVerification.generate_code(phone)
    
    # In a real application, you would send an SMS here
    # For development, we'll just return the code in the response
    # In production, remove the 'code' from the response
    return Response({
        'success': 'Verification code sent',
        'code': verification.code,  # Remove this in production
        'phone': phone
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=VerifyPhoneSerializer,
    responses={
        200: 'Phone number verified successfully',
        400: 'Invalid code or phone number',
    },
    operation_description="Verify a phone number using the provided verification code"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_phone(request):
    """
    Verify a phone number using the provided verification code
    
    This endpoint checks if the verification code is valid for the given phone number.
    """
    serializer = VerifyPhoneSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    code = serializer.validated_data['code']
    
    # Verify the code
    if PhoneVerification.verify_code(phone, code):
        # If the user already exists, mark their phone as verified
        try:
            user = User.objects.get(phone=phone)
            user.is_phone_verified = True
            user.save()
        except User.DoesNotExist:
            pass
        
        return Response({'success': 'Phone number verified successfully'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid or expired verification code'}, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    request_body=UserRegistrationSerializer,
    responses={
        201: 'User registered successfully',
        400: 'Invalid input or phone number already exists or not verified',
    },
    operation_description="Register a new user (customer) with a verified phone number"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user (customer) with a verified phone number
    
    Creates a new user account with phone number, password, and name details.
    The phone number must have been verified before registration.
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user = serializer.save()
    
    # Generate JWT tokens using custom serializer
    from .serializers import CustomTokenObtainPairSerializer
    refresh = CustomTokenObtainPairSerializer.get_token(user)
    
    return Response({
        'success': 'User registered successfully',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
        'access_token_lifetime': settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() // 60,
        'user': {
            'id': user.id,
            'phone': user.phone,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_customer': user.is_customer,
        }
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method='post',
    request_body=UserLoginSerializer,
    responses={
        200: 'Login successful',
        401: 'Invalid credentials',
    },
    operation_description="Login a user"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    Login a user
    
    Authenticates a user with phone number and password.
    """
    serializer = UserLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    password = serializer.validated_data['password']
    
    user = authenticate(request, phone=phone, password=password)
    if user:
        # Generate JWT tokens using custom serializer
        from .serializers import CustomTokenObtainPairSerializer
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        
        # Get profile data
        profile_data = {}
        if user.is_customer:
            try:
                profile = user.customer_profile
                profile_image = None
                if profile.profile_image:
                    profile_image = request.build_absolute_uri(profile.profile_image.url)
                
                profile_data = {
                    'profile_image': profile_image,
                    'allergies': profile.allergies,
                    'dietary_preferences': profile.dietary_preferences,
                    'default_address': profile.default_address,
                }
            except CustomerProfile.DoesNotExist:
                pass
        
        return Response({
            'success': 'Login successful',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'access_token_lifetime': settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() // 60,
            'user': {
                'id': user.id,
                'phone': user.phone,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_customer': user.is_customer,
                'is_staff_member': user.is_staff_member,
                'profile': profile_data
            }
        }, status=status.HTTP_200_OK)
    
    return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@swagger_auto_schema(
    method='post',
    responses={
        200: 'Logout successful',
    },
    operation_description="Logout a user"
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    Logout a user
    
    Ends the user's current session and invalidates only the current JWT token.
    """
    # Get the token from the authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        
        try:
            # Create a token object
            from rest_framework_simplejwt.tokens import AccessToken, TokenError
            
            # Blacklist the token
            from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
            
            # Get token data
            token_obj = AccessToken(token)
            
            # Convert exp timestamp to datetime
            from datetime import datetime
            import pytz
            expires_at = datetime.fromtimestamp(token_obj['exp'], tz=pytz.UTC)
            
            # Find or create the outstanding token
            outstanding_token, created = OutstandingToken.objects.get_or_create(
                jti=token_obj['jti'],
                defaults={
                    'token': token,
                    'user': request.user,
                    'expires_at': expires_at
                }
            )
            
            # Check if the token is already blacklisted
            if BlacklistedToken.objects.filter(token=outstanding_token).exists():
                # Token is already blacklisted, so it's been used after logout
                logout(request)
                return Response({'error': 'Token already invalidated. Please login again.'}, status=status.HTTP_401_UNAUTHORIZED)
            
            # Blacklist the token
            BlacklistedToken.objects.create(token=outstanding_token)
            
            # Also perform Django session logout
            logout(request)
            
            return Response({'success': 'Logout successful. Your token has been invalidated.'}, status=status.HTTP_200_OK)
        except Exception as e:
            # If there's an error, still log out the session
            logout(request)
            return Response({'success': 'Logged out of session, but token could not be invalidated.', 'error': str(e)}, status=status.HTTP_200_OK)
    else:
        # If no token is provided, just log out the session
        logout(request)
        return Response({'success': 'Logged out of session.'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=ForgotPasswordSerializer,
    responses={
        200: 'Password reset code sent successfully',
        404: 'User not found',
    },
    operation_description="Send a password reset code to an existing user's phone"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Send a password reset code to an existing user's phone
    
    This endpoint generates a 4-digit reset code and sends it to the user's phone.
    In a production environment, this would integrate with an SMS service.
    The user must exist in the system to receive a reset code.
    """
    serializer = ForgotPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    
    # Check if user exists
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({'error': 'No account found with this phone number'}, status=status.HTTP_404_NOT_FOUND)
    
    # Generate and send reset code
    reset = PasswordReset.generate_code(phone)
    
    # In a real application, you would send an SMS here
    # For development, we'll just return the code in the response
    # In production, remove the 'code' from the response
    return Response({
        'success': 'Password reset code sent',
        'code': reset.code,  # Remove this in production
        'phone': phone
    }, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=VerifyResetCodeSerializer,
    responses={
        200: 'Reset code verified successfully',
        400: 'Invalid code or phone number',
    },
    operation_description="Verify a password reset code"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_reset_code(request):
    """
    Verify a password reset code
    
    This endpoint checks if the reset code is valid for the given phone number.
    """
    serializer = VerifyResetCodeSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'success': 'Reset code verified successfully'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=ResetPasswordSerializer,
    responses={
        200: 'Password reset successfully',
        400: 'Invalid phone number or password',
        404: 'User not found',
    },
    operation_description="Reset user password after verification"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset user password after verification
    
    This endpoint resets the user's password after verifying the reset code.
    """
    serializer = ResetPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']
    
    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Mark reset code as used
    try:
        reset = PasswordReset.objects.get(phone=phone, code=code, is_used=False)
        reset.is_used = True
        reset.save()
    except PasswordReset.DoesNotExist:
        return Response({'error': 'Invalid reset code'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Reset password
    user.set_password(new_password)
    user.save()
    
    return Response({'success': 'Password reset successfully'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='get',
    responses={
        200: CustomerProfileSerializer,
        404: 'Profile not found',
    },
    operation_description="Get user profile information"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get user profile information
    
    Returns the authenticated user's profile information.
    """
    user = request.user
    
    if user.is_customer:
        try:
            profile = user.customer_profile
            serializer = CustomerProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomerProfile.DoesNotExist:
            return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
    elif user.is_staff_member:
        try:
            profile = user.staff_profile
            return Response({
                'id': profile.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'role': profile.role,
                'restaurant': {
                    'id': profile.restaurant.id,
                    'name': profile.restaurant.name,
                }
            }, status=status.HTTP_200_OK)
        except StaffProfile.DoesNotExist:
            return Response({'error': 'Staff profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({'error': 'User has no profile'}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='put',
    request_body=CustomerProfileSerializer,
    responses={
        200: CustomerProfileSerializer,
        403: 'Forbidden - staff profiles can only be updated by admin',
        404: 'Profile not found',
    },
    operation_description="Update user profile information"
)
@api_view(['PUT'])
@permission_classes([IsCustomer])
def update_profile(request):
    """
    Update user profile information
    
    Updates the authenticated user's profile information.
    """
    user = request.user
    
    try:
        profile = user.customer_profile
        serializer = CustomerProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except CustomerProfile.DoesNotExist:
        return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)


@swagger_auto_schema(
    method='post',
    manual_parameters=[
        openapi.Parameter(
            name='profile_image',
            in_=openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description='Profile image file'
        ),
    ],
    responses={
        200: ProfileImageSerializer,
        400: 'Invalid image file',
        404: 'Profile not found',
    },
    operation_description="Upload or update user profile image"
)
@api_view(['POST'])
@permission_classes([IsCustomer])
@parser_classes([MultiPartParser, FormParser])
def upload_profile_image(request):
    """
    Upload or update user profile image
    
    Allows users to upload or update their profile image.
    """
    user = request.user
    
    try:
        profile = user.customer_profile
    except CustomerProfile.DoesNotExist:
        return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ProfileImageSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        
        # Return the URL of the uploaded image
        profile_image = None
        if profile.profile_image:
            profile_image = request.build_absolute_uri(profile.profile_image.url)
        
        return Response({
            'success': 'Profile image uploaded successfully',
            'profile_image': profile_image
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_staff_member(request):
    """Create a new staff member (manager only)"""
    user = request.user
    
    # Verify that the user is a manager
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access this endpoint'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        if staff_profile.role != 'manager':
            return Response({'error': 'Only managers can create staff members'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get staff details from request
    phone = request.data.get('phone')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    role = request.data.get('role')
    
    # Validate required fields
    if not phone or not password or not first_name or not last_name or not role:
        return Response({'error': 'Phone, password, first name, last name, and role are required'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Validate role
    valid_roles = [r[0] for r in StaffProfile.ROLE_CHOICES]
    if role not in valid_roles:
        return Response({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Managers can only create waiters, chefs, and employees (not other managers)
    if role == 'manager':
        return Response({'error': 'Managers cannot create other managers. Only superusers can create managers.'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    # Check if user with this phone already exists
    if User.objects.filter(phone=phone).exists():
        return Response({'error': 'User with this phone number already exists'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Create the user
    new_user = User.objects.create_user(
        phone=phone,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_staff_member=True,
        is_phone_verified=True  # Auto-verify staff phone numbers
    )
    
    # Create staff profile
    staff_profile = StaffProfile.objects.create(
        user=new_user,
        role=role,
        restaurant=restaurant
    )
    
    return Response({
        'success': f'{role.capitalize()} created successfully',
        'staff_id': staff_profile.id,
        'user_id': new_user.id
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_staff_shift(request):
    """Create a new shift for a staff member (manager only)"""
    user = request.user
    
    # Verify that the user is a manager
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access this endpoint'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        if staff_profile.role != 'manager':
            return Response({'error': 'Only managers can create staff shifts'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get shift details from request
    staff_id = request.data.get('staff_id')
    start_time = request.data.get('start_time')
    end_time = request.data.get('end_time')
    
    # Validate required fields
    if not staff_id or not start_time or not end_time:
        return Response({'error': 'Staff ID, start time, and end time are required'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Get the staff member
    try:
        staff_member = StaffProfile.objects.get(id=staff_id, restaurant=restaurant)
    except StaffProfile.DoesNotExist:
        return Response({'error': 'Staff member not found or not part of your restaurant'}, 
                         status=status.HTTP_404_NOT_FOUND)
    
    # Parse datetime strings
    try:
        start_datetime = datetime.strptime(start_time, '%Y-%m-%d %H:%M')
        end_datetime = datetime.strptime(end_time, '%Y-%m-%d %H:%M')
    except ValueError:
        return Response({'error': 'Invalid datetime format. Use YYYY-MM-DD HH:MM'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Validate start time is before end time
    if start_datetime >= end_datetime:
        return Response({'error': 'Start time must be before end time'}, 
                         status=status.HTTP_400_BAD_REQUEST)
    
    # Create the shift
    shift = StaffShift.objects.create(
        staff=staff_member,
        start_time=start_datetime,
        end_time=end_datetime,
        created_by=user
    )
    
    return Response({
        'success': 'Shift created successfully',
        'shift_id': shift.id,
        'staff': f"{staff_member.user.first_name} {staff_member.user.last_name}",
        'start_time': shift.start_time,
        'end_time': shift.end_time
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def staff_list(request):
    """Get all staff members for a restaurant (manager only)"""
    user = request.user
    
    # Verify that the user is a manager
    if not user.is_staff_member:
        return Response({'error': 'Only staff members can access this endpoint'}, 
                         status=status.HTTP_403_FORBIDDEN)
    
    try:
        staff_profile = user.staff_profile
        if staff_profile.role != 'manager':
            return Response({'error': 'Only managers can view all staff members'}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        restaurant = staff_profile.restaurant
    except:
        return Response({'error': 'Staff profile not found'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get all staff for this restaurant
    staff_members = StaffProfile.objects.filter(restaurant=restaurant)
    
    # Filter by role if provided
    role = request.GET.get('role')
    if role:
        staff_members = staff_members.filter(role=role)
    
    # Filter by on-shift status if provided
    on_shift = request.GET.get('on_shift')
    if on_shift is not None:
        is_on_shift = on_shift.lower() == 'true'
        staff_members = staff_members.filter(is_on_shift=is_on_shift)
    
    data = []
    for staff in staff_members:
        data.append({
            'id': staff.id,
            'user_id': staff.user.id,
            'name': f"{staff.user.first_name} {staff.user.last_name}",
            'phone': staff.user.phone,
            'role': staff.get_role_display(),
            'is_on_shift': staff.is_on_shift,
            'profile_image': request.build_absolute_uri(staff.profile_image.url) if staff.profile_image else None,
        })
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def direct_admin_login(request):
    """
    Direct login for admin - use only for troubleshooting
    """
    import os
    admin_phone = os.environ.get('DJANGO_ADMIN_PHONE', '0953241659')
    admin_password = 'admin123'
    
    user = authenticate(request, phone=admin_phone, password=admin_password)
    if user and user.is_superuser:
        login(request, user)
        return HttpResponse(f"Admin login successful! User: {user.phone}, Superuser: {user.is_superuser}, Staff: {user.is_staff}")
    else:
        return HttpResponse(f"Admin login failed. User exists: {User.objects.filter(phone=admin_phone).exists()}")


class RoleBasedAdminLoginView(LoginView):
    template_name = 'admin/login.html'
    
    def form_valid(self, form):
        """Security check complete. Log the user in and redirect based on role."""
        # Call the parent method to authenticate the user
        auth_login(self.request, form.get_user())
        
        user = self.request.user
        
        # Automatically determine where to redirect based on user role
        if user.is_superuser:
            redirect_to = '/superadmin/'
        elif user.is_staff_member:
            try:
                role = user.staff_profile.role
                if role == 'manager':
                    redirect_to = '/manager/'
                elif role in ['waiter', 'chef']:
                    redirect_to = '/staff/'
                else:
                    # Unknown staff role
                    self.request.session['login_error'] = f'Unknown staff role: {role}'
                    return HttpResponseRedirect(reverse('admin:login'))
            except:
                self.request.session['login_error'] = 'Staff profile not found.'
                return HttpResponseRedirect(reverse('admin:login'))
        else:
            # User doesn't have admin privileges
            self.request.session['login_error'] = 'You do not have admin privileges.'
            return HttpResponseRedirect(reverse('admin:login'))
        
        # Redirect to the appropriate admin site
        return HttpResponseRedirect(redirect_to)


@api_view(['GET'])
@permission_classes([AllowAny])
def fix_manager_permissions(request):
    """
    Direct fix for manager permissions - use only for troubleshooting
    """
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType
    from restaurants.models import MenuItem, Category, Table, Reservation, Review, Restaurant, RestaurantImage, ReservationStatusUpdate
    from orders.models import Order, OrderItem, OrderStatusUpdate
    
    # Find all manager users
    managers = User.objects.filter(is_staff_member=True, staff_profile__role='manager')
    fixed_count = 0
    
    for user in managers:
        # Ensure user is marked as staff in Django's system
        if not user.is_staff:
            user.is_staff = True
            user.save()
        
        # Grant all permissions for relevant models
        all_models = [
            MenuItem, Category, Table, Reservation, Order, Review, 
            RestaurantImage, ReservationStatusUpdate, OrderItem, OrderStatusUpdate
        ]
        
        # Add view-only permission for Restaurant model
        restaurant_content_type = ContentType.objects.get_for_model(Restaurant)
        view_perm = Permission.objects.get(content_type=restaurant_content_type, codename='view_restaurant')
        user.user_permissions.add(view_perm)
        
        # Add all permissions for other models
        for model_class in all_models:
            content_type = ContentType.objects.get_for_model(model_class)
            for action in ['view', 'change', 'add', 'delete']:
                perm_codename = f'{action}_{model_class._meta.model_name}'
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=perm_codename)
                    user.user_permissions.add(perm)
                except Permission.DoesNotExist:
                    continue
        
        fixed_count += 1
    
    return HttpResponse(f"Fixed permissions for {fixed_count} manager(s). Please try logging in again.")
