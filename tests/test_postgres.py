"""Persistência real no PostgreSQL local/CI; nunca usa a URI de produção."""
import os
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


@pytest.fixture
def postgres_app(monkeypatch):
    raw = os.getenv('CRM2_TEST_POSTGRES_URL')
    if not raw:
        pytest.skip('Defina CRM2_TEST_POSTGRES_URL para o PostgreSQL isolado de testes')
    url = make_url(raw)
    assert url.host in {'127.0.0.1', 'localhost'} and url.database == 'crm2qa', 'Este teste só pode recriar o banco local crm2qa'
    for key in ['CRM_ENV', 'CRM_ADMIN_PASSWORD', 'CRM_SESSION_SECRET', 'CRM_WORKER_TOKEN', 'CRM_DATABASE_CA_CERT']:
        monkeypatch.delenv(key, raising=False)
    engine = create_engine(url)
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        c.exec_driver_sql('DROP SCHEMA public CASCADE; CREATE SCHEMA public')
        c.exec_driver_sql("DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon NOLOGIN; END IF; IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF; END $$")
        schema = (Path(__file__).resolve().parents[1] / 'supabase/schema.sql').read_text()
        # Reproduz o contexto informado: varchar sem tamanho e sem UNIQUE(lead_id,stage).
        schema = re.sub(r'VARCHAR\(\d+\)', 'VARCHAR', schema).replace('\tUNIQUE (lead_id, stage),\n', '')
        c.exec_driver_sql(schema)
    from crm.main import create_app
    app = create_app(raw)
    yield app
    app.state.engine.dispose()
    engine.dispose()


def test_postgres_campaign_validation_and_save_survive_new_session(postgres_app):
    from crm.domain import Campaign
    with TestClient(postgres_app) as c:
        bad = Campaign().model_dump()
        bad.update(start_date='2026-11-01', end_date='2026-11-30')
        result = c.put('/api/campaign', json=bad)
        assert result.status_code == 422 and '7 dias' in result.json()['detail']
        good = Campaign().model_dump()
        good.update(name='Campanha PostgreSQL', start_date='2026-11-01', end_date='2026-11-07')
        assert c.put('/api/campaign', json=good).status_code == 200
        with postgres_app.state.sessions() as s:
            from crm.domain import campaign
            assert campaign(s).name == 'Campanha PostgreSQL'
        assert c.get('/api/campaign').json() == good


def test_postgres_recovers_external_run_imports_and_deduplicates(postgres_app, monkeypatch):
    class Source:
        def poll(self, run_id):
            base = {'title': 'Empresa PostgreSQL', 'country': 'Brasil', 'reviewsCount': 140,
                    'emails': ['contato@example.invalid'], 'phone': '+55 11 99999-0000', 'placeId': 'pg-place'}
            return 'SUCCEEDED', [base, base, {**base, 'emails': []}]
        def close(self): pass
    monkeypatch.setattr('crm.service.Apify', Source)
    with TestClient(postgres_app) as c:
        data = {'run_id': 'pg-run-external', 'city': 'Campinas', 'niche': 'Oficinas'}
        result = c.post('/api/capture/recover', json=data)
        assert result.status_code == 200, result.json()
        summary = result.json()
        assert (summary['added'], summary['duplicates'], summary['rejected']) == (1, 1, 1)
        assert summary['rejection_reasons']['Sem email válido fornecido pela fonte'] == 1
        assert c.post('/api/capture/recover', json=data).json() == summary
        assert c.get('/api/leads').json()['total'] == 1


def test_postgres_index_migration_is_non_destructive_and_repeatable(postgres_app):
    sql = (Path(__file__).resolve().parents[1] / 'supabase/002_runtime_indexes.sql').read_text()
    engine = postgres_app.state.engine
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        c.exec_driver_sql(sql)
        c.exec_driver_sql(sql)
    indexes = inspect(engine).get_indexes('crm2_dispatches')
    assert any(i['unique'] and i['column_names'] == ['lead_id', 'stage'] for i in indexes)


def test_manual_ids_produce_specific_sequence_error_then_migration_fixes_without_deletion(postgres_app):
    from crm.db import Lead
    with postgres_app.state.sessions.begin() as s:
        s.add_all([Lead(id=i, name=f'Importada {i}', email=f'manual{i}@example.invalid') for i in range(1, 4)])
    with TestClient(postgres_app) as c:
        response = c.post('/api/leads', json={'name': 'Nova empresa', 'email': 'new@example.invalid'})
        assert response.status_code == 503 and response.json()['code'] == 'DB_SEQUENCE'
        sql = (Path(__file__).resolve().parents[1] / 'supabase/002_runtime_indexes.sql').read_text()
        with postgres_app.state.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
            conn.exec_driver_sql(sql)
        assert c.post('/api/leads', json={'name': 'Nova empresa', 'email': 'new@example.invalid'}).status_code == 200
        assert c.get('/api/leads').json()['total'] == 4
