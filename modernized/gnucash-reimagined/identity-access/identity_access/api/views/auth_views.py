"""
Authentication Views

API views for authentication operations.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from ..domain.services.authentication_service import AuthenticationService
from ..domain.models import User
from .serializers import UserSerializer, UserRegistrationSerializer


class RegisterView(APIView):
    """
    User registration endpoint.

    POST /api/v1/auth/register/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new user."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', '')
        )

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    """
    User login endpoint.

    POST /api/v1/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Login with email and password."""
        email = request.data.get('email')
        password = request.data.get('password')

        user = AuthenticationService.authenticate_user(email, password)

        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Check MFA if enabled
        if user.mfa_enabled:
            mfa_code = request.data.get('mfa_code')
            if not mfa_code:
                return Response(
                    {'error': 'MFA code required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not AuthenticationService.verify_mfa(user, mfa_code):
                return Response(
                    {'error': 'Invalid MFA code'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # Generate tokens
        access_token = AuthenticationService.generate_access_token(user)
        refresh_token = AuthenticationService.generate_refresh_token(user)

        # Record login
        ip_address = self.get_client_ip(request)
        AuthenticationService.record_login(user, ip_address)

        return Response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': UserSerializer(user).data
        })

    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class RefreshTokenView(APIView):
    """
    Refresh access token endpoint.

    POST /api/v1/auth/refresh/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """Refresh access token."""
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token = AuthenticationService.refresh_access_token(refresh_token)

        if not access_token:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response({
            'access_token': access_token
        })


class MeView(APIView):
    """
    Current user endpoint.

    GET /api/v1/auth/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user information."""
        return Response(UserSerializer(request.user).data)
