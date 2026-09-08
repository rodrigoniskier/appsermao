# Atualização no PythonAnywhere

## Pré-requisitos

O arquivo `~/mysite/.env` deve permanecer fora do Git e conter, no mínimo:

```env
APP_ENV=production
SECRET_KEY=<chave longa e aleatória>
GEMINI_API_KEY=<se usada>
GROQ_API_KEY=<se usada>
TAVILY_API_KEY=<se usada>
GEMINI_MODEL=gemini-3.8-flash
RATELIMIT_STORAGE_URI=memory://
```

`DATABASE_URL` pode ficar ausente enquanto o projeto usar o SQLite existente em `instance/exposibot.db`.

## Atualização normal

No Bash Console do PythonAnywhere:

```bash
cd ~/mysite
git status
git pull origin main
source venv/bin/activate  # use apenas se este for o nome do virtualenv atual
bash scripts/deploy_pythonanywhere.sh
```

O script:

1. cria backup do SQLite quando ele existir;
2. atualiza dependências;
3. compila o código;
4. executa toda a suíte de testes;
5. executa as migrações Alembic/Flask-Migrate;
6. verifica `/healthz` e `/readyz`.

Depois, abra a aba **Web** do PythonAnywhere e clique em **Reload**.

## Primeira atualização desta versão

Esta versão substitui `db.create_all()` por migrações versionadas. A migração-base é idempotente: se `users` e `sermons` já existirem, ela preserva os dados e registra o estado atual do esquema.

Não apague `instance/exposibot.db` e não copie o `.env.example` sobre o `.env` de produção.

## Verificação após o Reload

Confirme:

```bash
curl -fsS https://niskierrodrigo.pythonanywhere.com/healthz
curl -fsS https://niskierrodrigo.pythonanywhere.com/readyz
```

As respostas esperadas são `{"status":"ok"}` e `{"status":"ready"}`.
