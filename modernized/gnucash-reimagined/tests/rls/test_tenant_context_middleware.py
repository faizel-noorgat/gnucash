"""The request path: who is allowed to put a tenant into context.

RLS confines a session to whatever tenant is in context. It has no opinion
about whether that tenant was the right one, and it cannot have one - a session
pointing at tenant B reads tenant B's data exactly as instructed. So the only
thing standing between a caller-supplied tenant id and another tenant's books
is the decision made before the context is set.

Two failure modes are being ruled out here, and they are different:

* an unauthorised tenant being *accepted*, which is a leak;
* the context not surviving to the view at all, which is the silent no-op -
  the request succeeds, returns nothing, and looks like missing data.

The tests that assert what the *view* can see run inside ``app_role()``, i.e.
as ``app_user``. That matters: Django's own connection is the ``postgres``
superuser, and a superuser bypasses row-level security whatever the policies
say, so the propagation proof would be worthless without it.
"""

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

import pytest

from apps.accounting.models import Account
from apps.identity.models import AdvisorAccessGrant
from common.middleware.tenant import TenantContextMiddleware, get_current_tenant_id
from tests.rls.conftest import app_role, rls_session

pytestmark = pytest.mark.django_db(transaction=True)


def _request(tenant=None, user=None):
    """A request carrying ``user`` and, optionally, a client-supplied tenant id."""
    factory = RequestFactory()
    headers = {"HTTP_X_TENANT_ID": str(tenant.guid)} if tenant is not None else {}
    request = factory.get("/api/v1/anything/", **headers)
    request.user = user
    return request


class _RecordingView:
    """A view that records whether it ran, and what it could see."""

    def __init__(self):
        self.called = False
        self.accounts = None

    def __call__(self, request):
        self.called = True
        self.accounts = set(Account.objects.values_list("name", flat=True))
        return HttpResponse("ok")


# --------------------------------------------------------------------------
# The context survives into the view
# --------------------------------------------------------------------------


@override_settings(RLS_ENABLED=True)
def test_an_authorised_request_runs_with_the_tenant_actually_in_context(
    child_rows, two_tenants
):
    """The whole point: the decision is made, and then the context is real.

    Asserted by reading a tenant-scoped table *inside the view*, as
    ``app_user``. If the middleware's ``SET LOCAL`` were discarded - which is
    what happens to a ``SET LOCAL`` issued outside a transaction, and what the
    previous ``process_request`` implementation did - this returns nothing.
    """
    tenant_a = two_tenants["tenant_a"]
    view = _RecordingView()

    with app_role():
        response = TenantContextMiddleware(view)(
            _request(tenant=tenant_a, user=two_tenants["member_a"])
        )

    assert response.status_code == 200
    assert view.called
    assert view.accounts == {
        two_tenants["account_a1"].name,
        two_tenants["account_a2"].name,
    }


@override_settings(RLS_ENABLED=True)
def test_an_advisor_with_a_live_grant_is_let_in(child_rows, two_tenants):
    """The second route into a tenant, through the same middleware.

    The advisor holds no membership in tenant A at all; access comes only from
    the practice engagement and the active grant.
    """
    view = _RecordingView()

    with app_role():
        TenantContextMiddleware(view)(
            _request(tenant=two_tenants["tenant_a"], user=two_tenants["advisor_a"])
        )

    assert view.called
    assert view.accounts == {
        two_tenants["account_a1"].name,
        two_tenants["account_a2"].name,
    }


@override_settings(RLS_ENABLED=True)
def test_the_advisor_route_works_before_any_tenant_context_exists(
    child_rows, two_tenants
):
    """The decision is answerable with no tenant context set.

    ``can_access_tenant`` reads memberships, grants, engagements and the tenant
    row - all tables RLS confines. Without the pre-context read set those reads
    return nothing, the answer is ``False`` for everyone, and the middleware
    denies every request including legitimate ones. This asserts the advisor
    half of that set specifically, because it is the half whose chain crosses
    four tables.
    """
    from apps.identity.services.authorization import AuthorizationService

    # Only the *user* context is set, exactly as the middleware does before it
    # consults the service. Deliberately not a tenant context: the whole point
    # is that the decision must be answerable without one.
    with rls_session(user=two_tenants["advisor_a"].guid):
        assert (
            AuthorizationService.can_access_tenant(
                two_tenants["advisor_a"], two_tenants["tenant_a"]
            )
            is True
        )

    with rls_session(user=two_tenants["advisor_b"].guid):
        assert (
            AuthorizationService.can_access_tenant(
                two_tenants["advisor_b"], two_tenants["tenant_a"]
            )
            is False
        )


# --------------------------------------------------------------------------
# The context is not established when it should not be
# --------------------------------------------------------------------------


@override_settings(RLS_ENABLED=True)
def test_a_member_of_another_tenant_is_refused(child_rows, two_tenants):
    """A caller-supplied tenant id is a request, not a grant."""
    view = _RecordingView()

    with app_role(), pytest.raises(PermissionDenied) as exc:
        TenantContextMiddleware(view)(
            _request(tenant=two_tenants["tenant_a"], user=two_tenants["member_b"])
        )

    assert not view.called, "the view ran for a tenant the caller cannot access"
    assert "do not have access" in str(exc.value)


@override_settings(RLS_ENABLED=True)
def test_an_outsider_is_refused(child_rows, two_tenants):
    """No membership and no grant means no tenant, however valid the id."""
    view = _RecordingView()

    with app_role(), pytest.raises(PermissionDenied):
        TenantContextMiddleware(view)(
            _request(tenant=two_tenants["tenant_a"], user=two_tenants["outsider"])
        )

    assert not view.called


@override_settings(RLS_ENABLED=True)
def test_an_unauthenticated_caller_is_refused(child_rows, two_tenants):
    """The header used to be trusted before anyone had logged in at all."""
    view = _RecordingView()

    with app_role(), pytest.raises(PermissionDenied):
        TenantContextMiddleware(view)(
            _request(tenant=two_tenants["tenant_a"], user=AnonymousUser())
        )

    assert not view.called


@override_settings(RLS_ENABLED=True)
def test_a_revoked_grant_stops_the_advisor(child_rows, two_tenants):
    """Revoking advisor access takes effect on the next request.

    BR-PRACTICE-004 - the client can withdraw access at any time - holds on the
    request path only if the middleware consults the grant rather than trusting
    the engagement.

    The revocation itself is done as the unrestricted owner. Revoking is a
    write against a policed table and needs a tenant context of its own; giving
    this test one would confuse the thing under test, which is what happens on
    the *next* request.
    """
    grant = child_rows["advisor_grant_a"]
    grant.revoke(revoked_by=two_tenants["member_a"])
    assert AdvisorAccessGrant.objects.get(pk=grant.pk).revoked_at is not None

    view = _RecordingView()

    with app_role(), pytest.raises(PermissionDenied):
        TenantContextMiddleware(view)(
            _request(tenant=two_tenants["tenant_a"], user=two_tenants["advisor_a"])
        )

    assert not view.called


@override_settings(RLS_ENABLED=True)
def test_a_tenant_id_that_is_not_a_uuid_is_refused_not_crashed(
    child_rows, two_tenants
):
    """A malformed header is a denied request, not a 500.

    The id goes straight into a UUID primary-key lookup, so a junk value is
    caught by the same path that catches an unknown tenant rather than
    escaping as a validation error.
    """
    factory = RequestFactory()
    request = factory.get("/api/v1/anything/", HTTP_X_TENANT_ID="not-a-uuid")
    request.user = two_tenants["member_a"]
    view = _RecordingView()

    with app_role(), pytest.raises(PermissionDenied):
        TenantContextMiddleware(view)(request)

    assert not view.called


# --------------------------------------------------------------------------
# Requests that legitimately carry no tenant
# --------------------------------------------------------------------------


@override_settings(RLS_ENABLED=True)
def test_a_request_with_no_tenant_identifier_still_runs(child_rows, two_tenants):
    """Login, register and /me/ have no tenant yet, and must still work.

    They run with no tenant context, so they reach global tables and their own
    rows through the pre-context read set - and tenant-scoped data not at all.
    """
    seen = {}

    def view(request):
        seen["accounts"] = Account.objects.count()
        return HttpResponse("ok")

    with app_role():
        response = TenantContextMiddleware(view)(_request(user=two_tenants["member_a"]))

    assert response.status_code == 200
    assert seen["accounts"] == 0


@override_settings(RLS_ENABLED=True)
def test_the_tenant_list_is_answerable_with_no_tenant_context(child_rows, two_tenants):
    """A user can discover which tenants they belong to.

    This is the query the tenant picker is built on, and it is inherently
    cross-tenant, so no tenant context can be set while asking it. It works
    only because of the permissive ``own_membership_read`` /
    ``member_tenant_read`` policies; without them the endpoint returns an empty
    list and the product has no way in.
    """
    from apps.identity.services.authorization import AuthorizationService

    with rls_session(user=two_tenants["member_a"].guid):
        tenants = set(
            AuthorizationService.get_accessible_tenants(
                two_tenants["member_a"]
            ).values_list("guid", flat=True)
        )

    assert tenants == {two_tenants["tenant_a"].guid}


# --------------------------------------------------------------------------
# RLS being off must not turn the authorisation decision off
# --------------------------------------------------------------------------


@override_settings(RLS_ENABLED=False)
def test_the_authorisation_decision_does_not_depend_on_rls_being_on(
    child_rows, two_tenants
):
    """``RLS_ENABLED=False`` switches off the database mechanism, not the check.

    Development and the ordinary test suite both run with RLS off. If that also
    disabled the middleware's authorisation step, every such environment would
    accept any tenant id from any authenticated caller - and the environments
    where the check was skipped are exactly the ones where nobody would notice.
    """
    view = _RecordingView()

    with pytest.raises(PermissionDenied):
        TenantContextMiddleware(view)(
            _request(tenant=two_tenants["tenant_a"], user=two_tenants["member_b"])
        )

    assert not view.called


@override_settings(RLS_ENABLED=False)
def test_an_authorised_request_still_runs_when_rls_is_off(child_rows, two_tenants):
    """And a legitimate caller is not collateral damage."""
    view = _RecordingView()

    TenantContextMiddleware(view)(
        _request(tenant=two_tenants["tenant_a"], user=two_tenants["member_a"])
    )

    assert view.called


# --------------------------------------------------------------------------
# A refusal leaves nothing behind
# --------------------------------------------------------------------------


def test_no_tenant_context_is_set_when_the_request_is_refused(child_rows, two_tenants):
    """The refusal leaves nothing for a later query to inherit.

    Checked inside the same transaction the middleware would have used: after
    the raise the session variable is still unset, so code that caught the
    refusal and carried on would read zero rows rather than another tenant's.
    """
    with override_settings(RLS_ENABLED=True), app_role():
        with pytest.raises(PermissionDenied):
            TenantContextMiddleware(_RecordingView())(
                _request(tenant=two_tenants["tenant_a"], user=two_tenants["member_b"])
            )

        assert get_current_tenant_id() is None

    # ...and the session holds nothing afterwards either.
    with rls_session():
        assert Account.objects.count() == 0
