"""
The two non-request paths that must establish the same context as a request:
background tasks, and advisor (practice) access to a client tenant.

Layering note, because it governs what these tests can honestly assert:

* **RLS enforces the tenant boundary.** Once ``app.current_tenant_id`` is set,
  no query - ORM or raw - can read or write outside that tenant. That is
  ``test_tenant_isolation.py``.
* **``AuthorizationService.can_access_tenant()`` decides which tenant a caller
  may assume in the first place.** RLS cannot make this decision on its own
  without duplicating the practice/engagement/grant chain in SQL, and two
  implementations of one authorization rule is precisely the failure mode that
  let ``Role.get_permissions()`` rot.

So the advisor assertions here pin the chain at the authorization layer, and pin
RLS as the backstop behind it once the context has been assumed.
"""

import pytest
from django.test import override_settings

from apps.accounting.models import Account
from apps.identity.models import (
    AdvisorAccessGrant,
    ClientEngagement,
    Practice,
    PracticeMembership,
    Role,
    User,
)
from apps.identity.services.authorization import AuthorizationService
from common.rls.tasks import TenantScopedTask
from config.celery import app as celery_app
from tests.rls.conftest import app_role, rls_session

pytestmark = pytest.mark.django_db(transaction=True)


@celery_app.task(base=TenantScopedTask, bind=True, name="tests.rls.count_accounts")
def count_accounts_task(self, *, tenant_id, user_id=None, entity_id=None):
    """Minimal tenant-scoped task: how many accounts can this worker see?"""
    return Account.objects.count()


# --------------------------------------------------------------------------
# Celery
# --------------------------------------------------------------------------


@override_settings(RLS_ENABLED=True)
def test_tenant_scoped_task_establishes_the_same_context_as_a_request(two_tenants):
    """A task body sees its own tenant's rows and nothing else.

    Without the base class the task would run with no context and read zero rows
    - the failure would look like missing data, not a missing context.
    """
    tenant_a = two_tenants["tenant_a"]

    with app_role():
        # The runtime role on its own grants nothing: with no context set,
        # app_user reads no rows at all. Everything below is the task's doing.
        assert Account.objects.count() == 0

        assert count_accounts_task(tenant_id=str(tenant_a.guid)) == 2
        assert count_accounts_task(tenant_id=str(two_tenants["tenant_b"].guid)) == 1


@override_settings(RLS_ENABLED=True)
def test_tenant_scoped_task_entity_context_narrows_the_task(two_tenants):
    """A task may be scoped to one legal entity, same as a request."""
    tenant_a = two_tenants["tenant_a"]

    with app_role():
        assert (
            count_accounts_task(
                tenant_id=str(tenant_a.guid),
                entity_id=str(two_tenants["entity_a1"].guid),
            )
            == 1
        )


@override_settings(RLS_ENABLED=True)
def test_tenant_scoped_task_refuses_to_run_without_a_tenant(two_tenants):
    """A tenant-scoped task with no tenant is a bug, not an empty result."""
    with pytest.raises(ValueError) as exc:
        count_accounts_task()

    assert "tenant-scoped" in str(exc.value)


@override_settings(RLS_ENABLED=True)
def test_task_context_does_not_leak_back_to_the_caller(two_tenants):
    """The task's transaction-local context ends with the task."""
    tenant_a = two_tenants["tenant_a"]
    count_accounts_task(tenant_id=str(tenant_a.guid))

    # Back on the caller's connection with no context: the unrestricted owner
    # sees everything, and app_user sees nothing. Neither inherits tenant A.
    with rls_session():
        assert Account.objects.count() == 0


# --------------------------------------------------------------------------
# Advisor / practice access
# --------------------------------------------------------------------------


@pytest.fixture
def practice_setup(two_tenants):
    """A practice with one advisor, engaged to tenant A, granted and not granted."""
    practice = Practice.objects.create(name="Test Practice", slug="test-practice")
    engagement = ClientEngagement.objects.create(
        practice=practice, tenant=two_tenants["tenant_a"], status="active"
    )

    advisor = User.objects.create_user(email="advisor@example.com", password="testpass")
    PracticeMembership.objects.create(
        practice=practice, user=advisor, role="staff", status="active"
    )

    # A second practice member on the same engagement, with no grant naming
    # them: membership of the practice is not access to the client.
    ungranted = User.objects.create_user(
        email="ungranted@example.com", password="testpass"
    )
    PracticeMembership.objects.create(
        practice=practice, user=ungranted, role="staff", status="active"
    )

    role = Role.objects.create(name="Client Accountant")
    grant = AdvisorAccessGrant.objects.create(
        engagement=engagement, practice_user=advisor, tenant_role=role
    )
    return {
        "practice": practice,
        "engagement": engagement,
        "advisor": advisor,
        "ungranted": ungranted,
        "grant": grant,
    }


def test_practice_membership_alone_is_not_access(two_tenants, practice_setup):
    """Being in the practice, on a live engagement, is still not enough."""
    assert (
        AuthorizationService.can_access_tenant(
            practice_setup["ungranted"], two_tenants["tenant_a"]
        )
        is False
    )


def test_practice_user_can_only_assume_granted_client_tenants(
    two_tenants, practice_setup
):
    """The granted client tenant is reachable; any other tenant is not."""
    advisor = practice_setup["advisor"]

    assert (
        AuthorizationService.can_access_tenant(advisor, two_tenants["tenant_a"]) is True
    )
    assert (
        AuthorizationService.can_access_tenant(advisor, two_tenants["tenant_b"]) is False
    )


def test_granted_context_is_then_confined_by_rls(two_tenants, practice_setup):
    """Once the granted context is assumed, RLS confines what the advisor reads.

    The advisor has no Membership row in the client tenant - the data is
    reachable only through the grant plus a tenant context. Being in context for
    tenant A means tenant B's rows are unreachable, which is the property that
    matters when a practice user switches between client engagements.
    """
    advisor = practice_setup["advisor"]

    with rls_session(tenant=two_tenants["tenant_a"].guid, user=advisor.pk):
        assert Account.objects.count() == 2
        assert Account.objects.filter(pk=two_tenants["account_b1"].pk).count() == 0

    # Stated plainly, because it is the reason can_access_tenant() has to exist:
    # RLS is a boundary around whatever tenant is in context, not an
    # authorization rule about which tenant a caller may put in context. Set the
    # context to tenant B and tenant B's rows are visible, grant or no grant.
    with rls_session(tenant=two_tenants["tenant_b"].guid, user=advisor.pk):
        assert Account.objects.count() == 1
        assert Account.objects.filter(pk=two_tenants["account_a1"].pk).count() == 0


def test_revoked_practice_grant_immediately_removes_access(
    two_tenants, practice_setup
):
    """Revocation is effective on the next check - there is no cached grant."""
    advisor = practice_setup["advisor"]
    tenant_a = two_tenants["tenant_a"]

    assert AuthorizationService.can_access_tenant(advisor, tenant_a) is True

    practice_setup["grant"].revoke(revoked_by=advisor, reason="Engagement ended")

    assert AuthorizationService.can_access_tenant(advisor, tenant_a) is False
