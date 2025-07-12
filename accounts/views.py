from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, CustomerProfile, StaffProfile, PhoneVerification, PasswordReset
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
                    'code': openapi.Schema(type=openapi.TYPE_STRING, description="Verification code (only included in development)"),
                    'phone': openapi.Schema(type=openapi.TYPE_STRING, description="Phone number")
                }
            )
        ),
        400: 'Invalid phone number',
    },
    operation_description="Send a verification code to the provided phone number. Only requires phone number in request."
)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """
    Send a verification code to the provided phone number
    
    This endpoint generates a 6-digit verification code and sends it to the user's phone.
    In a production environment, this would integrate with an SMS service.
    """
    serializer = PhoneVerificationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    
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
@csrf_exempt
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
@csrf_exempt
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
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'success': 'User registered successfully',
        'access': str(refresh.access_token),
        'refresh': str(refresh),
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
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
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
    
    Ends the user's current session.
    """
    logout(request)
    return Response({'success': 'Logout successful'}, status=status.HTTP_200_OK)


@swagger_auto_schema(
    method='post',
    request_body=ForgotPasswordSerializer,
    responses={
        200: 'Password reset code sent successfully',
        404: 'User not found',
    },
    operation_description="Send a password reset code to the user's phone"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    Send a password reset code to the user's phone
    
    This endpoint generates a 6-digit reset code and sends it to the user's phone.
    In a production environment, this would integrate with an SMS service.
    """
    serializer = ForgotPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    phone = serializer.validated_data['phone']
    
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
