import json
import unittest
from unittest.mock import patch

from exposibot import create_app
from exposibot.extensions import db
from exposibot.models import Sermon, User


class ExposibotTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def _csrf(self, path="/login"):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def _register(self, email="user@example.com", password="password123"):
        token = self._csrf("/register")
        return self.client.post(
            "/register",
            data={
                "name": "Usuário Teste",
                "email": email,
                "password": password,
                "csrf_token": token,
            },
            follow_redirects=False,
        )

    def _logout(self):
        token = self._csrf("/dashboard")
        return self.client.post("/logout", data={"csrf_token": token})

    def test_post_without_csrf_is_rejected(self):
        response = self.client.post(
            "/register",
            data={"name": "Teste", "email": "csrf@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 400)

    def test_registration_hashes_password_and_authenticates(self):
        response = self._register()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))

        with self.app.app_context():
            user = User.query.filter_by(email="user@example.com").one()
            self.assertNotEqual(user.password_hash, "password123")
            self.assertTrue(user.check_password("password123"))

        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)

    def test_logout_requires_post_and_csrf(self):
        self._register()
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.post("/logout").status_code, 400)

        token = self._csrf("/dashboard")
        response = self.client.post("/logout", data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_sermon_isolation_between_users(self):
        self._register("one@example.com")
        token = self._csrf("/dashboard")
        response = self.client.post("/sermon/new", data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            sermon_id = Sermon.query.one().id

        self._logout()
        self._register("two@example.com")
        self.assertEqual(self.client.get(f"/sermon/{sermon_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/sermon/{sermon_id}/download.md").status_code, 404)

    def test_ai_markdown_html_is_escaped(self):
        self._register()
        with patch("exposibot.routes_api.ai_providers.perform_grounded_search", return_value="contexto"), patch(
            "exposibot.routes_api.ai_providers.generate_research",
            return_value=("<script>alert('x')</script>\n\n**seguro**", "mock"),
        ):
            response = self.client.post(
                "/api/analyze",
                json={"texto": "João 3.16", "tipo": "Contexto Canônico"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("<script>", payload["html"])
        self.assertIn("&lt;script&gt;", payload["html"])
        self.assertIn("<strong>seguro</strong>", payload["html"])

    def test_sermon_generation_accepts_extended_homiletic_schema(self):
        self._register()
        generated = {
            "ict": "Ideia central",
            "tese": "Tese",
            "fcd": "Condição caída",
            "proposito_redentivo": "Mostrar a graça de Deus em Cristo",
            "proposito_basico": "Doutrinário",
            "proposito_especifico": "Conduzir à fé e obediência",
            "intro": "Introdução",
            "topicos": [
                {
                    "titulo": "Ponto 1",
                    "texto_base": "v. 1",
                    "explicacao": "Elucidação",
                    "ilustracao": "Ilustração",
                    "aplicacao": "Aplicação",
                    "transicao": "Transição",
                }
            ],
            "conexao_cristocentrica": "Conexão legítima com Cristo",
            "conclusao": "Conclusão",
        }
        with patch(
            "exposibot.routes_api.ai_providers.generate_sermon_json",
            return_value=(json.dumps(generated), "mock"),
        ):
            response = self.client.post(
                "/api/suggest_sermon",
                json={"reference": "Romanos 8.1-4", "notes": "Notas de pesquisa"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["fcd"], "Condição caída")
        self.assertEqual(payload["topicos"][0]["transicao"], "Transição")
        self.assertEqual(payload["_provider"], "mock")

    def test_homiletic_prompt_contains_required_guardrails(self):
        from exposibot.ai_providers import HOMILETICS_SYSTEM_PROMPT, MASTER_SYSTEM_PROMPT

        combined = f"{MASTER_SYSTEM_PROMPT}\n{HOMILETICS_SYSTEM_PROMPT}".lower()
        for required in (
            "histórico-gramatical",
            "fcd",
            "moralismo",
            "explicação",
            "ilustração",
            "aplicação",
            "graça",
            "cristo",
        ):
            self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
