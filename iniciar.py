"""Inicia o Streamlit e o agendador local independente do CRM principal."""
import argparse
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def create_environment(root=ROOT):
    target = root / ".env"
    if target.exists():
        return False
    content = (root / ".env.example").read_text(encoding="utf-8")
    for name in ("CRM_ADMIN_PASSWORD", "CRM_SESSION_SECRET", "CRM_WORKER_TOKEN"):
        content = content.replace(name + "=\n", name + "=" + secrets.token_urlsafe(36) + "\n")
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def fill_access_values(root=ROOT):
    """Preenche apenas campos privados ausentes/vazios, sem rotacionar valores."""
    from dotenv import dotenv_values, set_key
    create_environment(root)
    target = root / '.env'
    values = dotenv_values(target, interpolate=False)
    filled = []
    for name in ('CRM_ADMIN_PASSWORD', 'CRM_SESSION_SECRET', 'CRM_WORKER_TOKEN'):
        if not (values.get(name) or '').strip():
            set_key(target, name, secrets.token_urlsafe(36), quote_mode='always')
            filled.append(name)
    return filled


def verify():
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.engine import make_url
    from crm.db import Base
    from crm.tls import postgres_connect_options

    ready = True
    url = os.getenv("CRM_DATABASE_URL", "sqlite:///data/crm2.db")
    try:
        parsed = make_url(url)
        if parsed.drivername in {"postgres", "postgresql"}:
            parsed = parsed.set(drivername="postgresql+psycopg")
        if parsed.get_backend_name() != "postgresql":
            print("PENDENTE: Supabase não conectado; o CRM está usando o banco local.")
            ready = False
        elif parsed.query.get("sslmode") != "verify-full":
            print("PENDENTE: acrescente sslmode=verify-full à conexão do Supabase.")
            ready = False
        else:
            engine = create_engine(parsed, connect_args=postgres_connect_options())
            try:
                with engine.connect() as c:
                    c.execute(text("SELECT 1"))
                    inspector = inspect(c)
                    available = set(inspector.get_table_names(schema="public"))
                    missing = set(Base.metadata.tables) - available
                    incompatible = []
                    for name, table in Base.metadata.tables.items():
                        if name in available:
                            actual = {column["name"] for column in inspector.get_columns(name, schema="public")}
                            if set(table.columns.keys()) - actual:
                                incompatible.append(name)
                    if missing or incompatible:
                        print("PENDENTE: execute supabase/schema.sql; a estrutura do banco está incompleta.")
                        ready = False
                    else:
                        print("OK: Supabase e tabelas do CRM verificados (somente leitura).")
            finally:
                engine.dispose()
    except Exception:
        print("PENDENTE: não foi possível verificar o Supabase. Confira URI, senha, SSL e rede.")
        ready = False
    groups = {
        "Apify": ["CRM_APIFY_TOKEN"],
        "Gmail OAuth": ["CRM_GMAIL_CLIENT_ID", "CRM_GMAIL_CLIENT_SECRET", "CRM_GMAIL_REFRESH_TOKEN"],
        "Acesso ao painel": ["CRM_ADMIN_PASSWORD", "CRM_SESSION_SECRET", "CRM_WORKER_TOKEN"],
    }
    for label, names in groups.items():
        missing = [name for name in names if not os.getenv(name)]
        if missing:
            print(f"PENDENTE: {label}: preencha " + ", ".join(missing) + " no .env.")
            ready = False
        else:
            print(f"DEFINIDO: {label}. Valores não são exibidos.")
    print("Credenciais presentes não comprovam acesso às APIs. Nenhum email foi enviado.")
    return ready


def main():
    parser = argparse.ArgumentParser(description="Iniciar ou verificar o CRM Brasil")
    parser.add_argument("--verificar", action="store_true")
    parser.add_argument("--gerar-acesso", action="store_true", help="Preenche senha/tokens vazios no .env sem mostrar valores nem iniciar o servidor")
    parser.add_argument('--instalar-inicio', action='store_true', help='Instala e inicia tarefa diária/logon no Windows, sem alterar o CRM principal')
    parser.add_argument('--sem-painel', action='store_true', help='Inicia somente a automação local')
    parser.add_argument("--port", type=int, default=8502)
    args = parser.parse_args()
    local_python = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if local_python.is_file() and Path(sys.prefix).resolve() != (ROOT / '.venv').resolve():
        os.execv(str(local_python), [str(local_python), str(ROOT / 'iniciar.py'), *sys.argv[1:]])
    if sys.version_info < (3, 11):
        raise SystemExit('O CRM 2 exige Python 3.11 ou mais recente; use preferencialmente Python 3.12.')
    os.chdir(ROOT)
    if create_environment(ROOT):
        print("Arquivo .env criado. Abra-o para preencher conexões e consultar a senha do painel.")
    try:
        from crm.environment import load_local_configuration
        import streamlit
    except ImportError:
        raise SystemExit("Instale as dependências: python -m pip install -r requirements.txt")
    filled = fill_access_values(ROOT)
    if filled:
        print('Campos de acesso preenchidos no .env: ' + ', '.join(filled) + '. Valores não são exibidos.')
    if args.gerar_acesso:
        print('Abra o .env e copie os três valores de acesso para Secrets do Streamlit, entre aspas. Os valores existentes foram preservados. Nenhum servidor foi iniciado ou email enviado.')
        return
    try:
        load_local_configuration(ROOT)
    except ValueError:
        raise SystemExit('Revise o formato TOML de .streamlit/secrets.toml. Nenhuma credencial será exibida.')
    if args.verificar:
        raise SystemExit(0 if verify() else 2)
    from crm.desktop import install_windows, supervise
    if args.instalar_inicio:
        install_windows(ROOT)
        return
    supervise(ROOT, port=args.port, panel=not args.sem_painel)


if __name__ == "__main__":
    main()
