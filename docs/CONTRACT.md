# Contrato de CLI

Contrato de entrada/saída que todo script (`list-jobs`, `apply-job`, e qualquer novo comando) deve respeitar. É o que permite um agente externo (IA ou humano) consumir os scripts sem conhecer a implementação interna.

## Regras gerais

1. **Stdout** só recebe JSON de sucesso. Nada de log, print de debug ou texto solto — quem consome espera `json.loads(stdout)` direto.
2. **Stderr** recebe erro estruturado (ver formato abaixo) e logs/diagnóstico.
3. **Exit code** `0` = sucesso. Qualquer valor `!= 0` = falha; o motivo está no JSON de erro do stderr.
4. Todo campo de data/hora é ISO 8601 UTC (`2026-09-03T14:00:00Z`).
5. Nenhum comando lê stdin interativamente — tudo vem de flag/argumento/arquivo apontado por flag. Scripts precisam rodar não-interativos (agente externo não responde prompt).

## `list-jobs`

**Entrada** (flags):

| Flag | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `--source` | string | sim | Nome da fonte registrada (`manual`) |
| `--file` | path | depende da fonte | Arquivo de entrada (fonte `manual`) |
| `--max-length` | int | não (default 50) | Máximo de vagas retornadas |

**Saída** (stdout), lista de `Job`:

```json
[
  {
    "id": "manual:a1b2c3",
    "source": "manual",
    "title": "Backend Engineer",
    "company": "Acme",
    "description": "...",
    "url": "https://...",
    "raw": {},
    "collected_at": "2026-09-03T14:00:00Z"
  }
]
```

## `apply-job`

**Entrada** (flags):

| Flag | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `--job-id` | string | sim (ou `--all-ready`) | Id retornado por `list-jobs` |
| `--method` | `email` \| `form` | sim | Meio de aplicação |
| `--email` | string | se `method=email` e vaga não trouxer email | Destinatário |
| `--subject` | string | não | Assunto; default vem da config local |
| `--all-ready` | flag | não | Aplica em lote |

**Saída** (stdout), `ApplicationResult`:

```json
{
  "job_id": "manual:a1b2c3",
  "method": "email",
  "status": "sent",
  "applier": "email",
  "detail": "",
  "applied_at": "2026-09-03T14:05:00Z"
}
```

`status` é sempre um de `sent` / `failed` / `skipped`. `skipped` nunca é erro de exit code — é resultado válido (ex.: sem applier de formulário pra aquela plataforma).

## Erro (qualquer comando)

Stderr, JSON único:

```json
{"error": "smtp connection refused", "code": "SMTP_ERROR"}
```

Códigos usados na fase 1: `SOURCE_NOT_FOUND`, `APPLIER_NOT_FOUND`, `JOB_NOT_FOUND`, `SMTP_ERROR`, `INVALID_INPUT`. Novo código = documentar aqui antes de usar.

## Compatibilidade

Mudança que **quebra** o contrato (remover campo, mudar tipo, renomear) exige nova major version do pacote e entrada no [CHANGELOG](../CHANGELOG.md) em `BREAKING`. Adicionar campo novo em resposta é sempre compatível (consumidor deve ignorar campo desconhecido).
