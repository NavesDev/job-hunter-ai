# Features e Planejamento

## Base fixa (Fase 1 — MVP)

Estrutural, não muda por plataforma. Detalhes em [ARCHITECTURE.md](ARCHITECTURE.md).

- [ ] `list-jobs` — lista vagas de uma fonte (`--source`, `--max-length`, filtros), grava no SQLite, imprime JSON.
- [ ] `apply-job` — aplica numa vaga já listada, via `--method email` (flags `--email`, `--subject`) ou `--method form` (quando houver applier da plataforma). Corpo do email e PDF de currículo sempre fixos.
- [ ] `ManualJsonJobSource` — fonte de entrada manual (JSON/CSV colado/importado), única fonte da fase 1.
- [ ] `EmailApplier` genérico — SMTP configurável, template HTML versionado + currículo PDF fixo (local, gitignored).
- [ ] `SqliteJobRepository` — estado/histórico: vagas coletadas (dedup) e resultados de aplicação.
- [ ] Config local não versionada (`config/local/`), com template de exemplo versionado (`config.example.yaml`).
- [ ] Suíte de testes AAA (`pytest`) cobrindo `domain/`, `application/`, `infra/`, CLI.
- [ ] README com instalação, flags de cada comando e exemplos de uso por agente externo.

## Planejado (Fase 2+)

Cada item é incremental — não bloqueia a fase 1, entra plugando na mesma estrutura de ports/registry.

### Novas fontes de vaga (`JobSource`)
- Scraper por plataforma (ex.: LinkedIn, Gupy, Indeed) — cada um novo em `infra/sources/`, registrado por nome.
- Diferentes formatos de entrada de dados por site (cada plataforma lista/exporta vaga do seu jeito).

### Novos meios de aplicação (`JobApplier`)
- Form applier por plataforma (`infra/appliers/<plataforma>_form_applier.py`) — obrigatório para toda plataforma que só aceita formulário. Usa `config/local/sources/<plataforma>.yaml` (credenciais/config própria) + `CandidateProfile.extra_fields` (telefone, LinkedIn, portfólio) pra preencher campos.

### Camada de decisão/extração de IA (avaliar se formaliza no projeto)
- Hoje: agente externo decide "aplica ou não" e extrai dado não-estruturado (email/assunto da descrição) por fora, chamando os scripts com o resultado via flag.
- Possível evolução: formalizar como camada própria (`ai/`) com `enrich-job` (extrai `apply_email`/`apply_methods`/`email_subject` da descrição) e `decide-job` (compara vaga x currículo, gera score/motivo) — reavaliar quando/se fizer sentido internalizar.

### Outros
- Múltiplos currículos selecionáveis por vaga (perfil backend vs frontend, etc.) — fase 1 usa 1 currículo fixo.
- Cobertura mínima de teste obrigatória em CI (definir número/gate).
