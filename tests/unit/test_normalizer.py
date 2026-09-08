from job_hunter_ai.domain.matching.normalizer import canonical_text, mentions, normalize, tokens


def test_normalize_should_drop_accents_and_casing_when_the_text_is_portuguese():
    # Arrange
    text = "Experiência Profissional"

    # Act
    result = normalize(text)

    # Assert
    assert result == "experiencia profissional"


def test_tokens_should_resolve_an_alias_when_the_resume_uses_a_short_spelling():
    # Arrange
    text = "JS, Node.js e Postgres"

    # Act
    result = tokens(text)

    # Assert
    assert result == ("javascript", "nodejs", "e", "postgresql")


def test_tokens_should_keep_the_symbols_of_a_skill_name_when_they_carry_meaning():
    # Arrange
    text = "C# e .NET Core"

    # Act
    result = tokens(text)

    # Assert
    assert result == ("csharp", "e", "dotnet", "core")


def test_mentions_should_match_a_plural_spelling_when_the_posting_uses_the_singular():
    # Arrange
    haystack = canonical_text("Desenvolvi APIs REST em producao")

    # Act
    result = mentions(haystack, "API Rest")

    # Assert
    assert result is True


def test_mentions_should_refuse_a_partial_word_when_the_term_is_only_a_prefix():
    # Arrange
    haystack = canonical_text("Programacao reativa com RxJava")

    # Act
    result = mentions(haystack, "React")

    # Assert
    assert result is False


def test_mentions_should_require_every_word_when_the_term_is_a_phrase():
    # Arrange
    haystack = canonical_text("Escrevi casos de teste automatizados no projeto")

    # Act
    result = mentions(haystack, "Casos de Teste Automatizados")

    # Assert
    assert result is True
