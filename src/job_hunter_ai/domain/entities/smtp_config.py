from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SmtpConfig:
    """SMTP credentials. Always loaded from .env, never from versioned YAML."""

    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
