"""Configuração comum ao Streamlit e ao worker. Nunca registra valores."""
import os
import tomllib

NAMES = {"CRM_ENV", "CRM_DATABASE_URL", "CRM_ADMIN_PASSWORD", "CRM_SESSION_SECRET",
         "CRM_WORKER_TOKEN", "CRM_APIFY_TOKEN", "CRM_GMAIL_CLIENT_ID",
         "CRM_GMAIL_CLIENT_SECRET", "CRM_GMAIL_REFRESH_TOKEN", "CRM_PUBLIC_URL", "CRM_REQUIRE_LOGIN", "CRM_DATABASE_CA_CERT"}


class ConfigurationError(ValueError):
    pass


def requires_login():
    return os.getenv('CRM_REQUIRE_LOGIN', 'true').strip().lower() not in {'false', '0', 'no'}


def validate_database_settings():
    if os.getenv('CRM_ENV') != 'production':
        return
    from sqlalchemy.engine import make_url
    try:
        url = make_url(os.getenv('CRM_DATABASE_URL', ''))
    except Exception:
        raise ConfigurationError('CRM_DATABASE_URL inválida: use a URI PostgreSQL de Supabase → Connect → Session pooler, entre aspas em Secrets.') from None
    if url.drivername not in {'postgres', 'postgresql', 'postgresql+psycopg'}:
        raise ConfigurationError('CRM_DATABASE_URL deve ser uma URI PostgreSQL, não a URL HTTPS da API Supabase.')
    if url.query.get('sslmode') != 'verify-full':
        raise ConfigurationError('Falta SSL na conexão: acrescente ?sslmode=verify-full&sslrootcert=system ao final da URI PostgreSQL. Se já houver ?, acrescente com &. Não desative TLS.')


def apply_secrets(settings):
    for name in NAMES:
        value = settings.get(name)
        if value is not None:
            if name == 'CRM_REQUIRE_LOGIN' and isinstance(value, bool):
                value = 'true' if value else 'false'
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
