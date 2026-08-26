from django.test import TestCase, override_settings

from . import oidc
from .models import ExternalIdentity, User, UserProfile


@override_settings(AUTHENTIK_OIDC_ISSUER="https://auth.icthub.top/application/o/xju-oj/")
class OIDCProvisioningTests(TestCase):
    def claims(self, **overrides):
        value = {
            "sub": "stable-subject",
            "preferred_username": "studio-user",
            "name": "Studio User",
            "email": "user@example.test",
            "email_verified": True,
            "icthub_account_id": "12345678",
        }
        value.update(overrides)
        return value

    def test_first_login_creates_one_user_profile_and_identity(self):
        user = oidc.provision_or_get(self.claims())
        repeated = oidc.provision_or_get(self.claims())

        self.assertEqual(user.pk, repeated.pk)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(ExternalIdentity.objects.count(), 1)
        self.assertEqual(user.studio_account_id, "12345678")
        self.assertFalse(user.userprofile.oj_onboarding_completed)

    def test_existing_email_requires_explicit_link(self):
        existing = User.objects.create(username="legacy", email="user@example.test")
        UserProfile.objects.create(user=existing)

        with self.assertRaisesRegex(oidc.OIDCError, "account_link_required"):
            oidc.provision_or_get(self.claims())

    def test_explicit_link_sets_account_id_and_identity(self):
        existing = User.objects.create(username="legacy", email="user@example.test")
        UserProfile.objects.create(user=existing)

        linked = oidc.provision_or_get(self.claims(), mode="link", linked_user_id=existing.pk)

        self.assertEqual(linked.pk, existing.pk)
        self.assertEqual(linked.studio_account_id, "12345678")
        self.assertEqual(ExternalIdentity.objects.get(user=existing).subject, "stable-subject")

    def test_invalid_or_changed_account_id_is_rejected(self):
        with self.assertRaisesRegex(oidc.OIDCError, "account_claim_invalid"):
            oidc.provision_or_get(self.claims(icthub_account_id="01234567"))

        user = oidc.provision_or_get(self.claims())
        with self.assertRaisesRegex(oidc.OIDCError, "account_claim_mismatch"):
            oidc.provision_or_get(self.claims(icthub_account_id="87654321"))
        self.assertEqual(user.studio_account_id, "12345678")
