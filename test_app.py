import unittest
from unittest.mock import patch

from app import app, calculate_strength, calculate_entropy, crack_time, has_sequence


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        patcher = patch("app.check_breach", return_value=(False, 0, True))
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Password Strength", response.data)

    def test_static_css_is_served(self):
        self.assertEqual(self.client.get("/static/style.css").status_code, 200)

    def test_analyze_returns_expected_fields(self):
        response = self.client.post("/analyze", json={"password": "Tr0ub4dor&3xK!"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        for key in ("score", "strength", "entropy", "crack_time", "breached", "suggestions"):
            self.assertIn(key, data)

    def test_missing_body_is_400_not_500(self):
        self.assertEqual(self.client.post("/analyze").status_code, 400)

    def test_wrong_type_is_400(self):
        self.assertEqual(self.client.post("/analyze", json={"password": 123}).status_code, 400)

    def test_empty_password_is_400(self):
        self.assertEqual(self.client.post("/analyze", json={"password": ""}).status_code, 400)

    def test_overlong_password_is_400(self):
        response = self.client.post("/analyze", json={"password": "a" * 500})
        self.assertEqual(response.status_code, 400)


class ScoringTests(unittest.TestCase):
    def test_common_password_scores_weak(self):
        score, strength, _ = calculate_strength("password")
        self.assertEqual(strength, "Weak")
        self.assertLess(score, 40)

    def test_random_password_scores_high(self):
        _, strength, _ = calculate_strength("x9#Qv!mZp2Lw@7Rt")
        self.assertIn(strength, ("Strong", "Very Strong"))

    def test_score_never_negative(self):
        score, _, _ = calculate_strength("qwerty123")
        self.assertGreaterEqual(score, 0)

    def test_sequence_detection(self):
        self.assertTrue(has_sequence("abcd"))
        self.assertTrue(has_sequence("4321"))
        self.assertFalse(has_sequence("abab"))
        self.assertFalse(has_sequence("azby"))

    def test_entropy_zero_for_empty(self):
        self.assertEqual(calculate_entropy(""), 0)

    def test_crack_time_does_not_overflow(self):
        self.assertIsInstance(crack_time(calculate_entropy("A1!a" * 60)), str)

    def test_crack_time_edges(self):
        self.assertEqual(crack_time(0), "instantly")
        self.assertIn("years", crack_time(60))
        self.assertIn("universe", crack_time(200))


class BreachTests(unittest.TestCase):
    def test_offline_reports_unavailable(self):
        import requests
        from app import check_breach

        with patch("app.requests.get", side_effect=requests.RequestException):
            self.assertEqual(check_breach("hunter2"), (False, 0, False))



class BreachOverrideTests(unittest.TestCase):
    def test_breached_password_is_forced_weak(self):
        client = app.test_client()
        with patch("app.check_breach", return_value=(True, 3614, True)):
            data = client.post("/analyze", json={"password": "Summer2024!"}).get_json()
        self.assertEqual(data["strength"], "Weak")
        self.assertLessEqual(data["score"], 20)
        self.assertIn("exposed in a breach", " ".join(data["suggestions"]))


if __name__ == "__main__":
    unittest.main()
