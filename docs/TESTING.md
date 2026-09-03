# Padrões de teste

## Framework

`pytest`. Sem framework de mock externo além do `unittest.mock` da stdlib, salvo necessidade real.

## Padrão AAA obrigatório

Todo teste comentado em 3 blocos, sempre nessa ordem, sempre esses comentários:

```python
def test_apply_job_returns_skipped_when_no_applier_registered():
    # Arrange
    job = build_job(source="unknown-platform")
    use_case = ApplyJobUseCase(appliers={}, repo=FakeJobRepository())

    # Act
    result = use_case.execute(job_id=job.id, method="form")

    # Assert
    assert result.status == "skipped"
```

Um `Arrange`/`Act`/`Assert` por teste. Teste que precisa de mais de um `Act` geralmente devia ser dois testes.

## Estrutura

```
tests/
├── unit/           domain/ e application/, ports mockados/fake, sem I/O real
├── integration/    infra/ com dependência real (SQLite em arquivo temp, SMTP fake local)
└── cli/            comandos via Typer CliRunner, valida stdout/stderr/exit code contra o CONTRACT.md
```

- **unit**: rápido, roda sempre. Usa fake/mock de `JobSource`, `JobApplier`, `JobRepository` (implementações simples em `tests/fakes/`, não `Mock()` genérico quando o comportamento importa).
- **integration**: valida que a implementação concreta (`SqliteJobRepository`, `EmailApplier`) cumpre o contrato do port. Usa banco/SMTP real, mas local/efêmero — nunca rede externa de verdade.
- **cli**: garante que o JSON de saída bate com o [contrato](CONTRACT.md) — campo, tipo, exit code.

## Regra de cobertura

Todo código novo em `domain/`, `application/`, `infra/` exige teste no mesmo PR — sem teste, sem merge. `cli/` (parsing puro) pode ter cobertura menor, mas o caminho feliz de cada comando precisa de ao menos um teste em `tests/cli/`.

## Nomeação

`test_<unidade>_<comportamento_esperado>_when_<condição>` — nome do teste é a especificação, deve dar pra entender o que quebrou só lendo o nome no CI, sem abrir o arquivo.

## Fakes vs Mocks

Prefira **fake** (implementação simples e real de um port, em memória) a **mock** (`Mock()`/`MagicMock`) quando o teste depende de comportamento, não só de "foi chamado com X". Mock é aceitável pra verificar interação (ex.: "SMTP foi chamado com esses parâmetros"), fake é melhor pra testar fluxo (ex.: "job aplicado duas vezes não duplica no repository").
