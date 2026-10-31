"""Configurações privadas locais; variáveis da hospedagem têm prioridade."""
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_environment(path=None):
    return load_dotenv(path or ROOT / ".env", override=False)
