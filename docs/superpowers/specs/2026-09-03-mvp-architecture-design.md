# JobHunterAi — Design MVP (Fase 1)

Data: 2026-09-03
Status: Aprovado

## Propósito

Base para automatizar aplicação em vagas de emprego, integrável a agentes de IA (locais ou externos). O projeto fornece scripts CLI independentes de IA — qualquer agente (Claude Code, outro LLM, ou humano) pode orquestrar a decisão de aplicar e chamar os scripts passando os dados via flags/argumentos.

## Princípio central

Scripts são **puros e determinísticos**. Nenhuma IA embutida no MVP. A decisão "aplicar ou não" e a extração de dados não-estruturados (email, assunto) são responsabilidade de quem chama os scripts — um agente de IA externo, orquestrando via CLI. Isso economiza tokens do agente: trabalho mecânico (enviar email, preencher formulário conhecido) fica em código determinístico; a IA só decide e extrai o que não é estruturado.

## User story guia

> Sou um agente de IA:
> - Quero receber uma lista de vagas de uma fonte sem abrir o site manualmente.
> - Quero aplicar numa vaga que decidi que combina com o perfil, de forma automatizada e estruturada, passando flags/argumentos com os dados da minha decisão (caso email). Em caso de formulário fixo/conhecido, quero que um script preencha para mim.
> - Assim economizo tokens usando trabalho automatizado.

## Stack

- **Python** — libs maduras de email (stdlib), CLI (Typer), validação (Pydantic), testes (pytest), scraping/form-fill futuro (Playwright).
- **SQLite** — estado/histórico (vagas coletadas, resultados de aplicação). Evita duplicata e re-aplicação.
- **Config local não versionada** — cada usuário configura credenciais e dados pessoais por fora do git.

## Arquitetura em camadas

```
job-hunter-ai/
├── src/
│   ├── domain/
│   │   ├── entities/
│   │   │   ├── job.py              # Job
│   │   │   ├── result.py           # ApplicationResult
│   │   │   └── candidate.py        # CandidateProfile, SmtpConfig
│   │   └── ports/
│   │       ├── job_source.py       # JobSource
│   │       ├── job_applier.py      # JobApplier
│   │       └── job_repository.py   # JobRepository
│   ├── application/
│   │   ├── list_jobs.py            # ListJobsUseCase
│   │   └── apply_job.py            # ApplyJobUseCase
│   ├── infra/
│   │   ├── sources/
│   │   │   └── manual_json_source.py   # ManualJsonJobSource (fase 1)
│   │   ├── appliers/
│   │   │   └── email_applier.py        # EmailApplier (fase 1, genérico)
│   │   └── repository/
│   │       └── sqlite_repository.py    # SqliteJobRepository
│   ├── config/
│   │   ├── loader.py
│   │   └── templates/
│   │       └── email.template.html
│   └── cli/
│       └── main.py                 # Typer app: list-jobs, apply-job
├── config/
│   ├── templates/
│   │   └── email.template.html     # versionado
│   ├── config.example.yaml         # versionado
│   └── local/                      # gitignored
│       ├── config.yaml
│       ├── resume.pdf
│       └── sources/
│           └── <plataforma>.yaml   # config específica por source, quando houver
├── tests/
│   ├── unit/
│   ├── integration/
│   └── cli/
└── docs/
```

**Regra de dependência**: `cli` → `application` → `domain`. `infra` implementa `domain/ports`, injetado no `application` via construtor. `domain` não depende de nada. Cada strategy (source/applier) é um `Protocol`, plugável via registry — cobre SOLID (Dependency Inversion, Open/Closed).

## Entidades (domain)

```python
# domain/entities/job.py
class Job:
    id: str                                       # hash estável (source + external_id/url)
    source: str                                    # "manual", "linkedin", "gupy", ...
    title: str
    company: str
    description: str
    url: str | None
    raw: dict                                       # payload original da fonte, auditoria
    collected_at: datetime

# domain/entities/result.py
class ApplicationResult:
    job_id: str
    method: Literal["email", "form"]
    status: Literal["sent", "failed", "skipped"]
    applier: str                                     # "email", "linkedin-form", ...
    detail: str
    applied_at: datetime

# domain/entities/candidate.py
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool

class CandidateProfile:
    name: str
    resume_pdf_path: Path
    smtp: SmtpConfig
    default_subject_template: str
    extra_fields: dict[str, str]     # telefone, linkedin_url, portfolio_url... reusável por form appliers
```

## Ports (domain)

```python
# domain/ports/job_source.py
class JobSource(Protocol):
    def fetch(self, max_length: int, **filters) -> list[Job]: ...

# domain/ports/job_applier.py
class JobApplier(Protocol):
    def apply(self, job: Job, candidate: CandidateProfile, **method_args) -> ApplicationResult: ...

# domain/ports/job_repository.py
class JobRepository(Protocol):
    def save_jobs(self, jobs: list[Job]) -> None: ...
    def save_result(self, result: ApplicationResult) -> None: ...
    def get_job(self, job_id: str) -> Job | None: ...
    def list_results(self, job_id: str | None = None) -> list[ApplicationResult]: ...
```

## Registries (resolução de strategy)

- `JobSource`: por `source` (`"manual"` → `ManualJsonJobSource`).
- `JobApplier`: por `(method, source)`. `"email"` tem fallback genérico `"*"` (mesmo SMTP, qualquer origem). `"form"` exige applier específico da plataforma — sem um registrado, `apply-job` retorna `status="skipped", detail="no form applier for source=X"`.

## CLI (MVP)

```bash
list-jobs  --source manual --file vagas.json --max-length 100
# stdout: JSON com lista de Job

apply-job  --job-id abc123 --method email --email vaga@empresa.com --subject "Vaga Backend - David Naves"
# corpo do email e PDF sempre fixos (template + config local)

apply-job  --job-id abc123 --method form
# resolve JobApplier específico da plataforma via registry (source do Job)

apply-job  --all-ready --method email ...
```

Cada comando imprime JSON no stdout (sucesso) ou stderr (erro estruturado, `{"error": ..., "code": ...}`) com exit code != 0 — permite uso por agente externo sem parsing de stack trace.

## Estáticos (email)

- **Body**: `config/templates/email.template.html`, versionado no git. HTML com placeholders (`{{job.title}}`, `{{company}}`, `{{candidate.name}}`...), resolvido via engine simples (Jinja2). `EmailApplier` envia multipart (`text/html` + fallback texto).
- **PDF**: `config/local/resume.pdf` (caminho configurável via `config.yaml` → `resume_pdf_path`), gitignored — dado pessoal.
- **Assunto**: vem via flag `--subject` de quem chama `apply-job` (fase 1); se omitido, usa `default_subject_template` da config local.

## Config por source

- `config/local/config.yaml`: geral, vira `CandidateProfile` — reusável por qualquer applier.
- `config/local/sources/<nome>.yaml`: schema próprio por plataforma (login, cookies, mapeamento de campo), carregado só pelo `infra/appliers/<nome>_form_applier.py` correspondente — domain fica agnóstico de plataforma.
- `config/config.example.yaml`: versionado, template de config sem dado real.

## Erros

Use cases nunca deixam exceção crua vazar pro CLI. `infra` lança exceções tipadas (`SmtpError`, `SourceNotFoundError`, `ApplierNotFoundError`); `application`/`cli` capturam e convertem em JSON de erro estruturado + exit code != 0.

## Testes

- Padrão AAA (Arrange/Act/Assert) em todo teste, `pytest`.
- `tests/unit/`: use cases com ports mockados (fake `JobSource`/`JobApplier`), entidades puras.
- `tests/integration/`: `SqliteJobRepository` real (banco temp), `EmailApplier` com SMTP fake (`aiosmtpd` local).
- `tests/cli/`: comandos Typer via `CliRunner`, valida JSON de saída e exit code.
- Todo código novo em `application/`, `domain/`, `infra/` exige teste antes de merge.

## Fora do escopo do MVP (fase 2+)

- `enrich-job`/`decide-job` como scripts próprios, ou camada `ai/` formal — decisão e extração de dado não-estruturado ficam por conta do agente orquestrador externo por enquanto.
- `ApplyInfo`/`ApplicationDecision` como entidades de domain — reavaliar se/quando a camada de IA for formalizada dentro do projeto.
- Fontes automatizadas (scraper de LinkedIn, Gupy, etc.) — fase 1 só tem `ManualJsonJobSource`.
- `JobApplier` de formulário por plataforma — implementado conforme cada plataforma for suportada.
- Múltiplos currículos selecionáveis por vaga — fase 1 usa 1 currículo fixo.
