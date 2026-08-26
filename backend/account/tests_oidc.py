from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings

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

    def test_second_subject_cannot_claim_an_already_linked_account_id(self):
        user = oidc.provision_or_get(self.claims())

        with self.assertRaisesRegex(oidc.OIDCError, "account_claim_conflict"):
            oidc.provision_or_get(self.claims(sub="different-subject"))

        self.assertEqual(ExternalIdentity.objects.filter(user=user).count(), 1)

    def test_display_username_collision_uses_subject_suffix(self):
        first = oidc.provision_or_get(self.claims())
        second = oidc.provision_or_get(
            self.claims(
                sub="another-subject",
                email="another@example.test",
                icthub_account_id="87654321",
            )
        )

        self.assertEqual(first.username, "studio-user")
        self.assertNotEqual(first.username, second.username)
        self.assertTrue(second.username.startswith("studio-user-"))


@override_settings(AUTHENTIK_OIDC_ISSUER="https://auth.icthub.top/application/o/xju-oj/")
class OIDCProvisioningConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def claims(self):
        return {
            "sub": "concurrent-subject",
            "preferred_username": "concurrent-user",
            "email": "concurrent@example.test",
            "email_verified": True,
            "icthub_account_id": "23456789",
        }

    def provision(self):
        close_old_connections()
        try:
            return oidc.provision_or_get(self.claims())
        finally:
            close_old_connections()

    def test_same_subject_concurrent_callbacks_provision_once(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            users = list(pool.map(lambda _item: self.provision(), range(2)))

        self.assertEqual(users[0].pk, users[1].pk)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(ExternalIdentity.objects.count(), 1)
