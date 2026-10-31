"""Configurações privadas locais; variáveis da hospedagem têm prioridade."""
from pathlib import Path
from dotenv import load_dotenv
import os
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def load_environment(path=None):
    return load_dotenv(path or ROOT / ".env", override=False)


def load_local_configuration(root=ROOT):
    """Secrets locais primeiro; .env como fallback; variáveis injetadas preservadas."""
    from .secrets_config import apply_secrets
    local = root / '.streamlit' / 'secrets.toml'
    if local.is_file():
        try:
            with local.open('rb') as f:
                apply_secrets(tomllib.load(f))
        except tomllib.TOMLDecodeError:
            raise ValueError('O arquivo .streamlit/secrets.toml não está em TOML válido; revise aspas e quebras de linha.') from None
    load_dotenv(root / '.env', override=False)
