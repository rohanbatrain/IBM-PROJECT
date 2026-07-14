import unittest

from app import app


class PasswordAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Password Strength", response.data)

    def test_static_css_is_served(self):
        response = self.client.get("/static/style.css")
        self.assertEqual(response.status_code, 200)

    def test_analyze_route_returns_json(self):
        response = self.client.post(
            "/analyze",
            json={"password": "StrongPass123!"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("strength", data)
        self.assertIn("score", data)


if __name__ == "__main__":
    unittest.main()
