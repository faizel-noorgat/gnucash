"""
API Authentication Classes

Custom authentication classes for JWT and API token authentication.
"""
from rest_framework import authentication, exceptions
from django.utils import timezone
from ..domain.services.authentication_service import AuthenticationService
from ..domain.models import ApiToken


class JWTAuthentication(authentication.BaseAuthentication):
    """
    JWT token authentication.

    Expects Authorization header: Bearer <token>
    """

    keyword = 'Bearer'

    def authenticate(self, request):
        """
        Authenticate request with JWT token.

        Args:
            request: HTTP request

        Returns:
            (user, token) tuple if authenticated, None otherwise
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith(f'{self.keyword} '):
            return None

        token = auth_header[len(self.keyword) + 1:]

        user = AuthenticationService.validate_token(token, token_type='access')

        if not user:
            raise exceptions.AuthenticationFailed('Invalid or expired token')

        return (user, token)

    def authenticate_header(self, request):
        """
        Return WWW-Authenticate header value for 401 responses.
        """
        return self.keyword


class APITokenAuthentication(authentication.BaseAuthentication):
    """
    API token authentication.

    Expects Authorization header: Token <token>
    """

    keyword = 'Token'

    def authenticate(self, request):
        """
        Authenticate request with API token.

        Args:
            request: HTTP request

        Returns:
            (user, token) tuple if authenticated, None otherwise
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith(f'{self.keyword} '):
            return None

        token_key = auth_header[len(self.keyword) + 1:]

        try:
            api_token = ApiToken.objects.select_related('user').get(token=token_key)
        except ApiToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if not api_token.is_valid:
            if api_token.is_expired:
                raise exceptions.AuthenticationFailed('Token has expired')
            raise exceptions.AuthenticationFailed('Token has been revoked')

        # Record token usage
        ip_address = self.get_client_ip(request)
        api_token.record_usage(ip_address)

        return (api_token.user, api_token)

    def get_client_ip(self, request):
        """
        Get client IP address from request.

        Args:
            request: HTTP request

        Returns:
            IP address string
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def authenticate_header(self, request):
        """
        Return WWW-Authenticate header value for 401 responses.
        """
        return self.keyword
