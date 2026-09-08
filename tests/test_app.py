import json
import unittest
from unittest.mock import patch

from exposibot import create_app
from exposibot.extensions import db
from exposibot.models import Sermon, User
from exposibot.security import render_markdown


class ExposibotTestCase(unittest.TestCase):
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

    def _api_headers(self):
        with self.client.session_transaction() as session:
            token = session.get("_csrf_token")
        if not token:
            token = self._csrf("/login")
        return {"X-CSRFToken": token}

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

    def test_healthcheck_and_security_headers(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])

    def test_post_without_csrf_is_rejected(self):
        response = self.client.post(
            "/register",
            data={"name": "Teste", "email": "csrf@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, 400)

    def test_json_mutation_without_csrf_is_rejected(self):
        self._register()
        response = self.client.post(
            "/api/analyze",
            json={"texto": "João 3:16", "tipo": "Contexto Canônico"},
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

        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_logout_requires_post_and_csrf(self):
        self._register()
        self.assertEqual(self.client.get("/logout").status_code, 405)
        self.assertEqual(self.client.post("/logout").status_code, 400)
        token = self._csrf("/dashboard")
        response = self.client.post("/logout", data={"csrf_token": token})
        self.assertEqual(response.status_code, 302)

    def test_sermon_isolation_between_users(self):
        self._register("one@example.com")
        token = self._csrf("/dashboard")
        self.client.post("/sermon/new", data={"csrf_token": token})
        with self.app.app_context():
            sermon_id = Sermon.query.one().id
        self._logout()
        self._register("two@example.com")
        self.assertEqual(self.client.get(f"/sermon/{sermon_id}").status_code, 404)
        self.assertEqual(self.client.get(f"/sermon/{sermon_id}/download.md").status_code, 404)

    def test_markdown_sanitizer_blocks_script_and_javascript_urls(self):
        html = str(render_markdown("<script>alert(1)</script> [x](javascript:alert(1)) **ok**"))
        self.assertNotIn("<script", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("<strong>ok</strong>", html)

    def test_ai_markdown_html_is_sanitized(self):
        self._register()
        with patch(
            "exposibot.routes_api.ai_service.generate_research",
            return_value=("<script>alert('x')</script>\n\n**seguro**", "mock"),
        ):
            response = self.client.post(
                "/api/analyze",
                json={"texto": "João 3:16", "tipo": "Contexto Canônico"},
                headers=self._api_headers(),
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("<script>", payload["html"])
        self.assertIn("<strong>seguro</strong>", payload["html"])

    def test_sermon_generation_accepts_and_validates_full_schema(self):
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
            "exposibot.routes_api.ai_service.generate_sermon_json",
            return_value=(json.dumps(generated), "mock"),
        ):
            response = self.client.post(
                "/api/suggest_sermon",
                json={"reference": "Romanos 8:1-4", "notes": "Notas de pesquisa suficientes para o teste."},
                headers=self._api_headers(),
            )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["fcd"], "Condição caída")
        self.assertEqual(payload["topicos"][0]["texto_base"], "v. 1")
        self.assertEqual(payload["topicos"][0]["transicao"], "Transição")
        self.assertEqual(payload["_provider"], "mock")

    def test_full_outline_survives_autosave_cycle(self):
        self._register()
        token = self._csrf("/dashboard")
        self.client.post("/sermon/new", data={"csrf_token": token})
        with self.app.app_context():
            sermon_id = Sermon.query.one().id

        outline = {
            "ict": "ICT",
            "tese": "Tese",
            "fcd": "FCD",
            "proposito_redentivo": "Graça em Cristo",
            "proposito_basico": "Doutrinário",
            "proposito_especifico": "Responder pela fé",
            "intro": "Introdução",
            "topicos": [{
                "titulo": "Ponto",
                "texto_base": "Rm 8:1",
                "explicacao": "Explicação",
                "ilustracao": "Ilustração",
                "aplicacao": "Aplicação",
                "transicao": "Transição",
            }],
            "conexao_cristocentrica": "Cristo",
            "conclusao": "Conclusão",
        }
        response = self.client.patch(
            f"/api/sermons/{sermon_id}",
            json={"reference": "Romanos 8:1-4", "research_notes": [], "outline": outline},
            headers=self._api_headers(),
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            saved = db.session.get(Sermon, sermon_id).outline
            self.assertEqual(saved["fcd"], "FCD")
            self.assertEqual(saved["topicos"][0]["texto_base"], "Rm 8:1")
            self.assertEqual(saved["topicos"][0]["transicao"], "Transição")
            self.assertEqual(saved["conexao_cristocentrica"], "Cristo")

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
