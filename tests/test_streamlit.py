import importlib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from crm.streamlit_bridge import APIError, LocalAPI
from crm.secrets_config import apply_secrets, load_worker_secrets

PASSWORD = 'test-streamlit-password-123'


@pytest.fixture
def streamlit_app(tmp_path, monkeypatch):
    from crm.main import create_app
    from crm import streamlit_ui
    monkeypatch.setenv('CRM_ENV', 'development')
    monkeypatch.setenv('CRM_ADMIN_PASSWORD', PASSWORD)
    monkeypatch.setenv('CRM_SESSION_SECRET', 's' * 40)
    monkeypatch.setenv('CRM_WORKER_TOKEN', 'w' * 40)
    monkeypatch.delenv('CRM_PUBLIC_URL', raising=False)
    app = create_app('sqlite:///' + str(tmp_path / 'streamlit.db'))
    monkeypatch.setattr(streamlit_ui, 'application', lambda: app)
    yield app
    app.state.engine.dispose()


def test_internal_api_cookies_are_individual(streamlit_app):
    first, second = LocalAPI(streamlit_app), LocalAPI(streamlit_app)
    first.request('POST', '/auth/login', json={'password': PASSWORD})
    assert first.request('GET', '/api/dashboard')['total'] == 0
    with pytest.raises(APIError):
        second.request('GET', '/api/dashboard')
    first.request('POST', '/api/leads', json={'name': 'Empresa Streamlit'})
    assert first.request('GET', '/api/leads')['total'] == 1


def widget(items, label):
    return next(x for x in items if x.label == label)


def test_streamlit_login_crud_and_navigation(streamlit_app):
    path = Path(__file__).resolve().parents[1] / 'streamlit_app.py'
    at = AppTest.from_file(str(path), default_timeout=15).run()
    assert not at.exception
    widget(at.text_input, 'Senha do administrador').set_value(PASSWORD)
    widget(at.button, 'Entrar').click().run()
    assert not at.exception and not at.error
    widget(at.radio, 'Espaço de trabalho').set_value('Meus leads').run()
    assert not at.exception and not at.error
    widget(at.text_input, 'Nome da empresa').set_value('Clínica de Teste Streamlit')
    widget(at.text_input, 'Email comercial').set_value('teste@example.invalid')
    widget(at.button, 'Salvar lead').click().run()
    assert not at.exception and not at.error
    with streamlit_app.state.sessions() as s:
        from sqlalchemy import select
        from crm.db import Lead
        assert s.scalar(select(Lead)).name == 'Clínica de Teste Streamlit'
    for page in ['Encontrar empresas', 'Campanha & cadência', 'Atividades', 'Configurações', 'Visão geral']:
        widget(at.radio, 'Espaço de trabalho').set_value(page).run()
        assert not at.exception and not at.error, page
    widget(at.radio, 'Tema').set_value('Escuro').run()
    assert not at.exception and not at.error
    widget(at.button, 'Sair').click().run()
    assert widget(at.text_input, 'Senha do administrador')


def test_worker_toml_is_private_and_does_not_override_injected_values(monkeypatch):
    monkeypatch.delenv('CRM_APIFY_TOKEN', raising=False)
    monkeypatch.setenv('CRM_ENV', 'production')
    monkeypatch.setenv('CRM2_SECRETS_TOML', 'CRM_APIFY_TOKEN = "test-only"\nCRM_ENV = "development"\nUNRELATED = "ignored"')
    monkeypatch.delenv('UNRELATED', raising=False)
    load_worker_secrets()
    import os
    assert os.environ['CRM_APIFY_TOKEN'] == 'test-only'
    assert os.environ['CRM_ENV'] == 'production'
    assert 'UNRELATED' not in os.environ
    with pytest.raises(ValueError):
        apply_secrets({'CRM_DATABASE_URL': 123})


def test_worker_prepares_without_open_panel_or_sending(app, monkeypatch):
    module = importlib.import_module('crm.worker')
    monkeypatch.setattr(module, 'load_worker_secrets', lambda: None)
    monkeypatch.setenv('CRM_ENV', 'production')
    monkeypatch.setattr(module, 'connect', lambda: (app.state.engine, app.state.sessions))
    def forbidden(*args, **kwargs):
        raise AssertionError('Preparação não pode enviar')
    monkeypatch.setattr(module, 'execute', forbidden)
    assert module.run('prepare') == {'status': 'prepared', 'database': 'ok', 'emails_sent': 0, 'capture_started': False}
