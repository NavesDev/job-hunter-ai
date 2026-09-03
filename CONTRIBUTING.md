# Contribuindo

## Antes de começar

Leia, nessa ordem:

1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — camadas, regra de dependência, strategy/registry.
2. [docs/CODE_STANDARDS.md](docs/CODE_STANDARDS.md) — estilo, SOLID, o que não fazer.
3. [docs/TESTING.md](docs/TESTING.md) — padrão AAA, estrutura de testes.
4. [docs/CONTRACT.md](docs/CONTRACT.md) — se a mudança toca CLI (flag, campo de saída, exit code).

## Fluxo

1. Branch a partir de `main`, nome descritivo (`feat/email-applier`, `fix/smtp-timeout`).
2. Implementa seguindo TDD quando fizer sentido: teste primeiro, AAA, depois código.
3. Roda local antes de abrir PR:
   ```bash
   ruff check . && ruff format --check .
   mypy src/
   pytest
   ```
4. Commit em [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
5. PR contra `main`, descrição explica o "porquê", não só o "o quê" (o diff já mostra o quê).
6. Toda mudança em `domain/`, `application/` ou `infra/` precisa de teste no mesmo PR.
7. Mudança que altera o [contrato de CLI](docs/CONTRACT.md) (flag, campo JSON, exit code, código de erro) precisa atualizar o `CONTRACT.md` no mesmo PR — nunca depois.

## Nova plataforma (fonte ou applier)

Não precisa tocar `application/`/`domain/` — só:

1. Nova classe em `infra/sources/<plataforma>.py` (implementa `JobSource`) ou `infra/appliers/<plataforma>_form_applier.py` (implementa `JobApplier`).
2. Registro no factory/registry correspondente.
3. Teste unit (fake/mock) + integration se envolver rede/formulário real.
4. Se precisar de config própria: `config/local/sources/<plataforma>.yaml` (não-sensível) + variáveis no `.env.example` (credencial).

## Changelog

Toda mudança visível pro usuário (nova flag, novo comando, mudança de contrato, bugfix relevante) entra em [CHANGELOG.md](CHANGELOG.md), seção `Unreleased`, no mesmo PR.

## Dúvida de design

Mudança pequena: discute no PR. Mudança de arquitetura (nova camada, port novo, contrato quebrando): abre uma spec em `docs/superpowers/specs/YYYY-MM-DD-<topico>-design.md` antes de implementar — mesmo processo usado no design inicial do projeto.
