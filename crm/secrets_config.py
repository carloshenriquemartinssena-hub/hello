"""Configuração comum ao Streamlit e ao worker. Nunca registra valores."""
import os
import tomllib

NAMES = {"CRM_ENV", "CRM_DATABASE_URL", "CRM_ADMIN_PASSWORD", "CRM_SESSION_SECRET",
         "CRM_WORKER_TOKEN", "CRM_APIFY_TOKEN", "CRM_GMAIL_CLIENT_ID",
         "CRM_GMAIL_CLIENT_SECRET", "CRM_GMAIL_REFRESH_TOKEN", "CRM_PUBLIC_URL"}


def apply_secrets(settings):
    for name in NAMES:
        value = settings.get(name)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError("Os valores de Secrets precisam ser textos entre aspas.")
            os.environ.setdefault(name, value)


def load_worker_secrets():
    raw = os.getenv("CRM2_SECRETS_TOML", "")
    if not raw:
        raise ValueError("Configure o secret CRM2_SECRETS_TOML no GitHub Actions.")
    try:
        settings = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        raise ValueError("CRM2_SECRETS_TOML precisa ter o mesmo formato TOML de Secrets do Streamlit.") from None
    apply_secrets(settings)


def validate_panel_security():
    if any(os.getenv(name, '').startswith('SUBSTITUA_') for name in ['CRM_ADMIN_PASSWORD', 'CRM_SESSION_SECRET', 'CRM_WORKER_TOKEN']):
        raise ValueError('Substitua os exemplos de senha e tokens pelos valores privados do seu CRM 2.')
    if len(os.getenv("CRM_ADMIN_PASSWORD", "")) < 16:
        raise ValueError("Defina CRM_ADMIN_PASSWORD com pelo menos 16 caracteres em Secrets.")
    if len(os.getenv("CRM_SESSION_SECRET", "")) < 32 or len(os.getenv("CRM_WORKER_TOKEN", "")) < 32:
        raise ValueError("Defina CRM_SESSION_SECRET e CRM_WORKER_TOKEN com pelo menos 32 caracteres em Secrets.")
