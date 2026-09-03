# Padrões de código

## Estilo

- **PEP 8**, aplicado via `ruff` (lint + format). Sem discussão de estilo em PR — se o linter aceita, tá aceito.
- **Type hints obrigatórios** em toda função/método público. `mypy` (ou `pyright`) roda no CI.
- Nome de arquivo/módulo: `snake_case`. Classe: `PascalCase`. Função/variável: `snake_case`. Constante: `UPPER_SNAKE_CASE`.
- Docstring só onde o nome da função não deixa óbvio o "porquê" (não descreva o "o quê" que o type hint já mostra).

## Arquitetura (regra de dependência)

```
cli/  →  application/  →  domain/
                              ↑
                           infra/
```

- `domain/` nunca importa de `application/`, `infra/` ou `cli/`. Zero dependência externa (nem Pydantic, se possível — `dataclass` puro).
- `application/` só depende de `domain/` (ports). Nunca importa classe concreta de `infra/` diretamente — sempre recebe via injeção no construtor.
- `infra/` implementa `domain/ports`. Pode depender de bibliotecas externas (SQLite, SMTP, Playwright).
- `cli/` é o único lugar que sabe montar o grafo de dependência concreta (registry/factory) e instanciar use cases.

Violação comum a evitar: use case importando `infra.appliers.email_applier` direto em vez de receber `JobApplier` no construtor — quebra testabilidade e Dependency Inversion.

## SOLID — checklist rápido ao abrir PR

- **S**: a classe faz uma coisa só? Se o nome tem "e"/"ou" (`SourceAndApplier`), provavelmente não.
- **O**: nova plataforma/fonte é extensão (nova classe + registro), não edição de código existente?
- **L**: toda implementação de `JobSource`/`JobApplier` pode substituir outra sem quebrar quem chama?
- **I**: port não força implementação a ter método que não faz sentido pra ela?
- **D**: `application/` depende de `Protocol`, nunca de classe concreta de `infra/`?

## Tamanho de arquivo/unidade

Arquivo crescendo demais (~200-300 linhas pra módulo comum) é sinal de responsabilidade misturada — quebrar antes de continuar empilhando. Prefira muitos arquivos pequenos e coesos a poucos grandes (mesmo princípio já usado em `domain/entities/` e `domain/ports/`, um arquivo por conceito).

## Commits

Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`). Corpo explica o "porquê" quando não for óbvio pelo diff.

## O que não fazer

- Sem `print()`/log solto em `stdout` de comando CLI — quebra o [contrato](CONTRACT.md).
- Sem exceção genérica (`except Exception`) engolindo erro sem log/re-raise tipado.
- Sem lógica de negócio em `cli/` — CLI só faz parse de flag, resolve dependência, chama use case, formata saída.
- Sem acesso a arquivo/rede direto em `domain/` ou `application/`.
