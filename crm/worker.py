"""Rotina diária independente da disponibilidade do painel Streamlit."""
import argparse
import json
import os

from sqlalchemy import select

from .db import Lease, connect
from .domain import campaign
from .secrets_config import load_worker_secrets
from .service import Busy, execute
from .providers import ProviderError


def run(operation):
    if operation not in {"prepare", "run"}:
        raise ValueError("Operação inválida")
    load_worker_secrets()
    if os.getenv('CRM_ENV') != 'production':
        raise ValueError('Use CRM_ENV = "production" no secret CRM2_SECRETS_TOML para não executar com banco temporário.')
    engine, sessions = connect()
    try:
        if operation == "prepare":
            with sessions() as s:
                if not s.get(Lease, 1):
                    raise ValueError("Execute o SQL do CRM 2 no Supabase.")
                campaign(s)
            return {"status": "prepared", "database": "ok", "emails_sent": 0, "capture_started": False}
        return execute(sessions, scheduled=True, batch=20)
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", choices=["prepare", "run"], default="prepare")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.operation), ensure_ascii=False))
    except (ValueError, ProviderError, Busy) as exc:
        print(str(exc))
        raise SystemExit(1)
    except Exception:
        print("A rotina não foi concluída. Confira a conexão PostgreSQL, SSL, tabelas e credenciais do CRM 2. Nenhum reenvio automático será feito.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
