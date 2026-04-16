from __future__ import annotations

from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from tenants.models import Tenant, TenantMembership
from tenants.permissions import IsTenantAdmin
from tenants.serializers import TenantMembershipSerializer, TenantSerializer, UserRegistrationSerializer


class TenantViewSet(viewsets.ModelViewSet):
    serializer_class = TenantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Tenant.objects.filter(memberships__user=self.request.user)


class TenantMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = TenantMembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsTenantAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return TenantMembership.objects.filter(tenant__memberships__user=self.request.user)


class RegistrationView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'id': user.id, 'email': user.email},
            status=status.HTTP_201_CREATED,
        )
