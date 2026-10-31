"""Agendador local permanente. Não depende de o navegador permanecer aberto."""
import json
import logging
import os
import signal
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .environment import ROOT, load_local_configuration


def main():
    os.chdir(ROOT)
    load_local_configuration()
    from .automation import cycle
    from .db import connect
    from .diagnostics import database_diagnostic
    from .secrets_config import validate_database_settings
    stop = threading.Event()
    for name in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: stop.set())
    Path('data').mkdir(exist_ok=True)
    logger = logging.getLogger('crm2.local')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(message)s')
    for handler in [logging.StreamHandler(), RotatingFileHandler('data/automation.log', maxBytes=1000000, backupCount=3, encoding='utf-8')]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    engine = sessions = None
    previous = None
    logger.info('CRM 2: automação local iniciada. Janela 09h–10h de Brasília; limites compartilhados no Supabase.')
    try:
        while not stop.is_set():
            try:
                if sessions is None:
                    if os.getenv('CRM_ENV') != 'production':
                        from .secrets_config import ConfigurationError
                        raise ConfigurationError('A automação exige CRM_ENV=production e o Supabase do CRM 2; banco temporário não será usado.')
                    validate_database_settings()
                    engine, sessions = connect()
                outcome = cycle(sessions, should_stop=stop.is_set)
                message = json.dumps(outcome, ensure_ascii=False, sort_keys=True)
                if message != previous:
                    logger.info(message)
                    previous = message
            except Exception as exc:
                from .secrets_config import ConfigurationError
                if isinstance(exc, ConfigurationError):
                    message = str(exc)
                elif isinstance(exc, ValueError) and not hasattr(exc, 'statement'):
                    message = 'CONFIGURACAO: confira CRM_ENV, a URI PostgreSQL e os arquivos locais de Secrets. Nenhum valor de credencial é registrado.'
                else:
                    code, detail = database_diagnostic(exc)
                    message = f'[{code}] {detail}'
                if message != previous:
                    logger.error(message)
                    previous = message
            stop.wait(30)
    finally:
        if engine is not None:
            engine.dispose()
        logger.info('CRM 2: automação encerrada.')


if __name__ == '__main__':
    main()
