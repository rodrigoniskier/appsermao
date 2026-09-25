# ExposiBot

### Workspace de pesquisa e preparação de conteúdo com IA

O **ExposiBot** é uma aplicação web em Flask criada para organizar um fluxo de trabalho que combina pesquisa, coleta de material, análise assistida por IA, estruturação e produção de documentos.

O projeto nasceu de uma necessidade concreta: evitar que pesquisa, notas, sugestões de IA e estrutura final fiquem espalhadas entre diferentes ferramentas. A aplicação reúne essas etapas em um único ambiente de trabalho.

## O que o projeto demonstra

- aplicação Flask estruturada em pacote;
- autenticação e persistência com SQLAlchemy;
- migrações de banco de dados;
- integração com diferentes provedores de IA;
- pesquisa externa com Tavily;
- geração de documentos DOCX;
- validação de dados;
- sanitização de conteúdo;
- rate limiting;
- configuração por variáveis de ambiente;
- testes automatizados;
- interface responsiva com design system próprio.

## Stack

- **Backend:** Python, Flask
- **Persistência:** Flask-SQLAlchemy, Flask-Migrate
- **Autenticação:** Flask-Login
- **IA:** Google Gemini e Groq
- **Pesquisa:** Tavily
- **Documentos:** python-docx
- **Validação:** Pydantic
- **Segurança:** Flask-Limiter, nh3
- **Testes:** pytest

## Arquitetura do produto

A interface foi pensada como um workspace, e não como um simples chat.

O fluxo separa visualmente:

1. **fontes e ferramentas**;
2. **resultado da análise**;
3. **material coletado e organizado**;
4. **estrutura final do trabalho**.

O design segue um sistema próprio documentado em [DESIGN.md](DESIGN.md), com atenção a hierarquia visual, responsividade, contraste e consistência.

## Configuração local

Requer Python 3.11+.

```bash
git clone https://github.com/rodrigoniskier/appsermao.git
cd appsermao

python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt
cp .env.example .env
```

Configure no arquivo `.env` os serviços que deseja utilizar. As chaves de API **não devem ser versionadas**.

Depois:

```bash
python app.py
```

## Variáveis de ambiente

O arquivo [.env.example](.env.example) documenta as configurações disponíveis, incluindo:

- `SECRET_KEY`;
- `DATABASE_URL`;
- `GROQ_API_KEY`;
- `GEMINI_API_KEY`;
- `TAVILY_API_KEY`;
- configuração de rate limiting.

SQLite pode ser utilizado para desenvolvimento local; a aplicação também aceita banco configurado por `DATABASE_URL`.

## Qualidade e manutenção

O repositório inclui:

- suíte de testes;
- scripts auxiliares;
- migrações;
- documentação de deploy;
- design system;
- separação entre configuração e credenciais.

Para desenvolvimento:

```bash
pip install -r requirements-dev.txt
pytest
```

## Por que este projeto faz parte do meu portfólio

O ExposiBot representa bem o tipo de problema que gosto de resolver: **transformar um processo intelectual complexo em um fluxo digital organizado**, combinando software tradicional, IA e experiência de usuário.

---

Desenvolvido por [Rodrigo Niskier](https://github.com/rodrigoniskier).
