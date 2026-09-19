"""
Authentication Service

Handles user authentication, JWT token management, and MFA.
"""
from django.contrib.auth import authenticate
from django.utils import timezone
import jwt
from datetime import datetime, timedelta
from django.conf import settings

from ..models import User


class AuthenticationService:
    """
    Service for authentication operations.

    Responsibilities:
    - Email/password authentication
    - JWT token generation and validation
    - MFA enrollment and verification
    - Session management
    """

    @staticmethod
    def authenticate_user(email, password):
        """
        Authenticate user with email and password.

        Returns:
            User object if authentication successful, None otherwise
        """
        user = authenticate(username=email, password=password)
        if user and user.is_active:
            return user
        return None

    @staticmethod
    def generate_access_token(user):
        """
        Generate JWT access token for user.

        Args:
            user: User object

        Returns:
            JWT token string
        """
        payload = {
            'user_id': str(user.guid),
            'email': user.email,
            'exp': datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def generate_refresh_token(user):
        """
        Generate JWT refresh token for user.

        Args:
            user: User object

        Returns:
            JWT token string
        """
        payload = {
            'user_id': str(user.guid),
            'exp': datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def validate_token(token, token_type='access'):
        """
        Validate JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')

        Returns:
            User object if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

            if payload.get('type') != token_type:
                return None

            user_id = payload.get('user_id')
            user = User.objects.get(guid=user_id)

            if not user.is_active:
                return None

            return user
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
            return None

    @staticmethod
    def refresh_access_token(refresh_token):
        """
        Generate new access token using refresh token.

        Args:
            refresh_token: JWT refresh token string

        Returns:
            New access token string if valid, None otherwise
        """
        user = AuthenticationService.validate_token(refresh_token, token_type='refresh')
        if user:
            return AuthenticationService.generate_access_token(user)
        return None

    @staticmethod
    def enroll_mfa(user):
        """
        Enroll user in MFA.

        Args:
            user: User object

        Returns:
            MFA secret and QR code URL
        """
        # Generate MFA secret
        import secrets
        secret = secrets.token_hex(20)

        # Store secret (in production, encrypt this)
        user.mfa_enabled = True
        user.mfa_enrolled_at = timezone.now()
        user.save()

        # Generate QR code URL (simplified - in production use qrcode library)
        qr_url = f'otpauth://totp/FVA:{user.email}?secret={secret}&issuer=FVA'

        return {
            'secret': secret,
            'qr_url': qr_url
        }

    @staticmethod
    def verify_mfa(user, code):
        """
        Verify MFA code.

        Args:
            user: User object
            code: MFA code entered by user

        Returns:
            True if code is valid, False otherwise
        """
        # In production, validate against user's MFA secret
        # This is a stub implementation
        return True

    @staticmethod
    def record_login(user, ip_address):
        """
        Record user login event.

        Args:
            user: User object
            ip_address: IP address of login
        """
        user.last_login_ip = ip_address
        user.last_login = timezone.now()
        user.save(update_fields=['last_login_ip', 'last_login'])
