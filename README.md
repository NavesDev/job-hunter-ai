# job-hunter-ai

🤖 Base para automatizar aplicação em vagas de emprego, integrável a agentes de IA (locais ou externos).

Scripts CLI **puros e desacoplados de IA**: qualquer agente (Claude Code, outro LLM, ou humano) orquestra por fora — decide se aplica e com quais dados — e chama os scripts via flag/argumento. Trabalho mecânico (enviar email, preencher formulário conhecido) fica em código determinístico.

Documentação completa: [Arquitetura](docs/ARCHITECTURE.md) · [Features e planejamento](docs/FEATURES.md) · [Design MVP (spec)](docs/superpowers/specs/2026-09-03-mvp-architecture-design.md)

## Status

🚧 Em desenvolvimento (fase 1 — documentação/design concluída, implementação não iniciada).

## Instalação

```bash
git clone <repo>
cd job-hunter-ai
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp config/config.example.yaml config/local/config.yaml
cp config/templates/email-body.example.html config/local/email-body.html
# edite config/local/config.yaml com seus dados (SMTP, currículo, nome)
# personalize config/local/email-body.html (HTML livre, com seu estilo)
# coloque seu currículo em config/local/resume.pdf (ou aponte outro caminho no config.yaml)
```

`config/local/` é gitignored — cada usuário configura suas próprias credenciais, nunca versionadas.

## Uso

### Listar vagas

```bash
list-jobs --source manual --file vagas.json --max-length 100
```

| Flag | Obrigatória | Descrição |
|---|---|---|
| `--source` | sim | Fonte de vagas registrada (`manual` na fase 1) |
| `--file` | depende da fonte | Caminho do JSON/CSV de entrada (fonte `manual`) |
| `--max-length` | não (default 50) | Máximo de vagas retornadas |

Saída: JSON no stdout, uma lista de vagas normalizadas (`id`, `title`, `company`, `description`, `url`, `raw`). Cada execução salva/deduplica no SQLite local.

### Aplicar numa vaga

```bash
apply-job --job-id abc123 --method email --email vaga@empresa.com --subject "Vaga Backend - Seu Nome"
apply-job --job-id abc123 --method form
apply-job --all-ready --method email
```

| Flag | Obrigatória | Descrição |
|---|---|---|
| `--job-id` | sim (ou `--all-ready`) | Id da vaga retornado por `list-jobs` |
| `--method` | sim | `email` ou `form` |
| `--email` | se `method=email` e vaga não tiver email associado | Endereço de destino |
| `--subject` | não | Assunto do email; sem isso usa o default configurado |
| `--all-ready` | não | Aplica em lote nas vagas já processadas |

Corpo do email (`config/local/email-body.html`, ou `config/templates/email-body.example.html` se o local não existir) e PDF do currículo (`config/local/resume.pdf`) são sempre fixos — só o método, o email e o assunto variam por chamada. `--method form` exige um applier registrado pra plataforma da vaga; sem isso, retorna `status=skipped` sem travar o restante do fluxo.

### Saída e erros

Todo comando imprime JSON estruturado. Sucesso vai pro stdout; erro vai pro stderr com exit code != 0:

```json
{"error": "smtp connection refused", "code": "SMTP_ERROR"}
```

Isso permite que um agente externo (IA ou humano) parseie o resultado sem depender de stack trace.

## Arquitetura (resumo)

```
cli/  →  application/  →  domain/
                              ↑
                           infra/ (implementa domain/ports)
```

Cada fonte de vaga (`JobSource`) e cada meio de aplicação (`JobApplier`) é uma strategy plugável, resolvida por registry — nova plataforma entra em `infra/` sem tocar `application`/`domain`. Detalhe completo em [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest
```

Testes seguem padrão **AAA** (Arrange/Act/Assert, comentado no código). Todo código novo em `domain/`, `application/`, `infra/` precisa de teste antes de merge.

## Roadmap

Ver [docs/FEATURES.md](docs/FEATURES.md) — fase 1 (base fixa) e fase 2+ (novas plataformas, form appliers, camada de IA).

## Licença

[MIT](LICENSE)
