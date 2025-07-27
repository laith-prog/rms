from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from .models import TokenVersion

class VersionedJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that validates token version against user's current version.
    This ensures that tokens issued before logout are no longer valid.
    """
    
    def get_user(self, validated_token):
        """
        Attempt to find and return a user using the given validated token.
        Also check if the token version matches the user's current version.
        """
        # First get the user using the parent method
        user = super().get_user(validated_token)
        
        # Check token version
        if user is not None:
            # Check if token is blacklisted
            jti = validated_token.get('jti', None)
            if jti:
                try:
                    # Check if this token is in the blacklist
                    outstanding_token = OutstandingToken.objects.get(jti=jti)
                    if BlacklistedToken.objects.filter(token=outstanding_token).exists():
                        raise AuthenticationFailed('Token is blacklisted. Please login again.')
                except OutstandingToken.DoesNotExist:
                    pass  # Token not in database, continue with other checks
            
            # Get token version from the token
            token_version = validated_token.get('token_version', None)
            
            # If token has no version, it's an old token format - reject it
            if token_version is None:
                raise InvalidToken('Token has no version claim')
            
            # Get user's current token version
            current_version = TokenVersion.get_version(user)
            
            # If versions don't match, token was issued before logout - reject it
            if token_version != current_version:
                raise AuthenticationFailed('Token version mismatch. Please login again.')
        
        return user 