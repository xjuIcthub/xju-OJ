import json

from django.test import TestCase, Client


class HttpContractTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_website_envelope_and_keys(self):
        response = self.client.get("/api/website/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json;charset=UTF-8")
        self.assertEqual(set(response.json()), {"error", "data"})
        self.assertIsNone(response.json()["error"])
        self.assertEqual(
            set(response.json()["data"]),
            {
                "website_base_url",
                "website_name",
                "website_name_shortcut",
                "website_footer",
                "allow_register",
                "submission_list_show_all",
            },
        )

    def test_profile_get_is_public_and_sets_csrf_cookie(self):
        response = self.client.get("/api/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"error": None, "data": None})
        self.assertIn("csrftoken", response.cookies)

    def test_missing_csrf_is_rejected(self):
        response = self.client.post(
            "/api/login/",
            data=json.dumps({"username": "fixture-user", "password": "fixture-password"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_login_keeps_error_data_envelope(self):
        csrf_response = self.client.get("/api/profile/")
        csrf_token = csrf_response.cookies["csrftoken"].value
        response = self.client.post(
            "/api/login/",
            data=json.dumps({"username": "fixture-user", "password": "fixture-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"error": "error", "data": "Invalid username or password"},
        )

    def test_pagination_contract(self):
        response = self.client.get("/api/contests/?limit=0&offset=-1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"error", "data"})
        self.assertIsNone(response.json()["error"])
        self.assertEqual(set(response.json()["data"]), {"results", "total"})
