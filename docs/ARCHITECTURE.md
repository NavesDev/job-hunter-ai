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
│   └── templates/   email.template.html
└── cli/
    └── main.py       list-jobs, apply-job

config/
├── templates/email.template.html   versionado
├── config.example.yaml             versionado
└── local/                          gitignored: config.yaml, resume.pdf, sources/<plataforma>.yaml

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
