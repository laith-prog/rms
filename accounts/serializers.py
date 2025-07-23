from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomerProfile, PhoneVerification, PasswordReset
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['phone'] = user.phone
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['is_customer'] = user.is_customer
        token['is_staff_member'] = user.is_staff_member
        
        return token
        
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra responses
        user = self.user
        data['user'] = {
            'id': user.id,
            'phone': user.phone,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_customer': user.is_customer,
            'is_staff_member': user.is_staff_member,
        }
        
        # Add access token expiration time in minutes
        data['access_token_lifetime'] = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() // 60
        
        return data

class PhoneVerificationSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=15)
    
    class Meta:
        model = PhoneVerification
        fields = ['phone']  # Remove 'code' from fields
    
    def validate_phone(self, value):
        # Basic phone validation - can be enhanced with regex
        if not value or len(value) < 10:
            raise serializers.ValidationError("Please enter a valid phone number")
        return value

class VerifyPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=4)

class UserRegistrationSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['phone', 'first_name', 'last_name', 'password', 'confirm_password']
    
    def validate(self, data):
        # Check if passwords match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        # Check if phone is verified
        phone = data['phone']
        try:
            # In the PhoneVerification model, a used code means the phone has been verified
            verification = PhoneVerification.objects.get(phone=phone, is_used=True)
        except PhoneVerification.DoesNotExist:
            raise serializers.ValidationError({"phone": "Phone number is not verified"})
        
        return data
    
    def create(self, validated_data):
        # Remove confirm_password from validated_data
        validated_data.pop('confirm_password', None)
        
        # Create user
        user = User.objects.create_user(
            phone=validated_data['phone'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_customer=True,
            is_phone_verified=True
        )
        
        # Create customer profile
        CustomerProfile.objects.create(user=user)
        
        return user

class UserLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(style={'input_type': 'password'})

class ForgotPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    
    def validate_phone(self, value):
        try:
            User.objects.get(phone=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this phone number")
        return value

class VerifyResetCodeSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=4)
    
    def validate(self, data):
        try:
            reset = PasswordReset.objects.get(
                phone=data['phone'],
                code=data['code'],
                is_used=False
            )
            # Check if the reset code is expired (10 minutes)
            if (timezone.now() - reset.created_at).total_seconds() > 600:
                raise serializers.ValidationError({"code": "Reset code has expired"})
        except PasswordReset.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid reset code"})
        return data

class ResetPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=4)
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, data):
        # Check if passwords match
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        
        # Verify reset code
        try:
            reset = PasswordReset.objects.get(
                phone=data['phone'],
                code=data['code'],
                is_used=False
            )
            # Check if the reset code is expired (10 minutes)
            if (timezone.now() - reset.created_at).total_seconds() > 600:
                raise serializers.ValidationError({"code": "Reset code has expired"})
        except PasswordReset.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid reset code"})
        
        return data

class CustomerProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone = serializers.CharField(source='user.phone', read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = ['id', 'first_name', 'last_name', 'phone', 'profile_image']
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        
        # Update user fields
        user = instance.user
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        user.save()
        
        # Update profile fields
        return super().update(instance, validated_data)

class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['profile_image'] 