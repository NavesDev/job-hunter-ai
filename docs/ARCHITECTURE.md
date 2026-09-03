# Arquitetura

Referência viva da arquitetura do projeto. Decisões e histórico de discussão: [docs/superpowers/specs/2026-09-03-mvp-architecture-design.md](superpowers/specs/2026-09-03-mvp-architecture-design.md).

## Princípio central

Scripts são **puros e determinísticos, desacoplados de IA**. Qualquer agente (Claude Code, outro LLM, ou humano) orquestra por fora, chamando os scripts via CLI e passando dados de decisão por flag/argumento. Trabalho mecânico (enviar email, preencher formulário conhecido) fica em código; a IA só decide e extrai dado não-estruturado — economiza tokens do agente.

## Camadas

```
cli/  →  application/  →  domain/
                              ↑
                           infra/ (implementa domain/ports)
```

- **domain/**: entidades e contratos (`Protocol`), zero dependência externa.
- **application/**: use cases, orquestram domain via ports injetados no construtor. Sem I/O direto.
- **infra/**: implementações concretas (SQLite, SMTP, fontes de vaga). Implementa `domain/ports`.
- **cli/**: entrypoint (Typer). Resolve dependências concretas via registry, chama use case, imprime JSON.

Cada strategy plugável (fonte de vaga, meio de aplicação) é um `Protocol` em `domain/ports`, resolvido por um **registry** — nova plataforma = nova classe em `infra/`, sem tocar `application`/`domain` (Open/Closed, Dependency Inversion).

## Estrutura de pastas

```
src/
├── domain/
│   ├── entities/    Job, ApplicationResult, CandidateProfile, SmtpConfig
│   └── ports/       JobSource, JobApplier, JobRepository
├── application/     ListJobsUseCase, ApplyJobUseCase
├── infra/
│   ├── sources/     JobSource concretos (ManualJsonJobSource, ...)
│   ├── appliers/     JobApplier concretos (EmailApplier, form appliers por plataforma)
│   └── repository/  SqliteJobRepository
├── config/
│   ├── loader.py
│   └── templates/   email-body.example.html
└── cli/
    └── main.py       list-jobs, apply-job

config/
├── templates/email-body.example.html   versionado (exemplo)
├── config.example.yaml                 versionado (exemplo) — configuração não-sensível
└── local/                              gitignored: config.yaml, email-body.html, resume.pdf, sources/<plataforma>.yaml

.env.example                            versionado (exemplo) — credenciais/segredos
.env                                    gitignored — credenciais reais (SMTP, login por plataforma)

tests/
├── unit/         use cases com ports mockados
├── integration/  SQLite real, SMTP fake
└── cli/          Typer CliRunner
```

## Registries (strategy resolution)

| Port | Chave de resolução | Fase 1 | Extensão |
|---|---|---|---|
| `JobSource` | `source` | `"manual"` | novo source por plataforma |
| `JobApplier` | `(method, source)` | `"email" → "*"` (genérico) | `"form" → <plataforma>` obrigatório por site |

Sem applier registrado para `(method, source)`, `apply-job` retorna `status="skipped"` — nunca falha silenciosa nem trava o fluxo.

## Config vs credenciais

Duas coisas distintas, dois lugares distintos:

- **Configuração** (não-sensível: caminhos, template default, ordem de preferência de método): `config/local/config.yaml`, carregado por `config/loader.py`.
- **Credenciais** (segredo: usuário/senha SMTP, login/token por plataforma): `.env` na raiz, carregado via `python-dotenv`. Nunca versionado, nunca em YAML.

`config/loader.py` lê os dois e monta `CandidateProfile`/`SmtpConfig` combinando ambos. Credencial de plataforma específica usa prefixo por fonte (`LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD`) no mesmo `.env` — `config/local/sources/<plataforma>.yaml` fica só pra configuração não-sensível daquela plataforma (seletor, timeout), se precisar.

## Contratos principais

Ver detalhamento completo no [spec](superpowers/specs/2026-09-03-mvp-architecture-design.md#entidades-domain). Resumo:

- `Job` — vaga normalizada, independente da origem.
- `ApplicationResult` — resultado de uma tentativa de aplicação (`sent`/`failed`/`skipped`).
- `CandidateProfile` — perfil do candidato (config local), inclui `extra_fields` genérico reusável por form appliers de qualquer plataforma.

## Erros

`infra` lança exceções tipadas; `application`/`cli` capturam e convertem em JSON estruturado no stderr + exit code != 0. Nenhuma stack trace crua chega no agente que chamou o script.

## Testes

AAA (Arrange/Act/Assert) obrigatório. `pytest`. Todo código novo em `domain/`, `application/`, `infra/` exige teste antes de merge.

## Fora do escopo atual

Decisão "aplicar ou não" e extração de dado não-estruturado (email/assunto da descrição) não têm script/camada própria no momento — ficam por conta do agente orquestrador externo. Ver [Features e Planejamento](FEATURES.md) para status e evolução.
