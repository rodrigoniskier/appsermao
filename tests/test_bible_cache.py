import unittest
from unittest.mock import patch

from exposibot import create_app
from exposibot.extensions import db
from exposibot.models import Sermon, User


class BibleApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "RATELIMIT_ENABLED": False,
                "SESSION_COOKIE_SECURE": False,
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            user = User(name="Teste", email="bible@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

        token = self._csrf("/login")
        self.client.post(
            "/login",
            data={
                "email": "bible@example.com",
                "password": "password123",
                "csrf_token": token,
            },
        )
        token = self._csrf("/dashboard")
        response = self.client.post("/sermon/new", data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.sermon_id = Sermon.query.one().id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _csrf(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def test_catalog_exposes_book_and_chapter_metadata(self):
        response = self.client.get("/api/bible/catalog")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        romans = next(book for book in payload["books"] if book["abbr"] == "rm")
        self.assertEqual(romans["name"], "Romanos")
        self.assertEqual(romans["chapters"], 16)

    def test_passage_is_cached_per_sermon(self):
        result = {"version": "NVI", "text": "1. Portanto, agora já não há condenação..."}
        with patch("exposibot.routes_api.bible.fetch_passage", return_value=result) as fetch_passage:
            url = f"/api/passage?ref=Romanos%208:1&sermon_id={self.sermon_id}"
            first = self.client.get(url)
            second = self.client.get(url)

        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.get_json()["cached"])
        self.assertTrue(second.get_json()["cached"])
        fetch_passage.assert_called_once_with("Romanos 8:1")

        with self.app.app_context():
            cache = db.session.get(Sermon, self.sermon_id).passage_cache
            self.assertEqual(cache["reference"], "Romanos 8:1")
            self.assertEqual(cache["version"], "NVI")

    def test_reference_change_invalidates_passage_cache(self):
        with self.app.app_context():
            sermon = db.session.get(Sermon, self.sermon_id)
            sermon.reference = "Romanos 8:1"
            sermon.passage_cache = {
                "reference": "Romanos 8:1",
                "version": "NVI",
                "text": "texto",
            }
            db.session.commit()

        token = self._csrf(f"/sermon/{self.sermon_id}")
        response = self.client.patch(
            f"/api/sermons/{self.sermon_id}",
            json={"reference": "Romanos 8:2"},
            headers={"X-CSRFToken": token},
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            sermon = db.session.get(Sermon, self.sermon_id)
            self.assertIsNone(sermon.passage_cache)


if __name__ == "__main__":
    unittest.main()
