import json
from datetime import timedelta
from pathlib import PureWindowsPath

import pytest

from crm import automation
from crm.db import Config
from crm.desktop import child_commands, instance_lock, powershell_registration
from crm.domain import set_config
from test_crm import AT, setup_campaign


def configure(sessions, **changes):
    with sessions.begin() as s:
        set_config(s, 'automation', {'capture_enabled': True, 'city': 'Campinas', 'niche': 'Oficinas', 'limit': 25, **changes})


def test_parent_uses_streamlit_on_separate_port_and_independent_worker(tmp_path):
    commands = child_commands(tmp_path, 'python')
    assert commands['automacao'] == ['python', '-m', 'crm.local_runner']
    assert 'streamlit' in commands['painel'] and '8502' in commands['painel']
    assert str(tmp_path / 'streamlit_app.py') in commands['painel']
    assert set(child_commands(tmp_path, 'python', panel=False)) == {'automacao'}


def test_single_instance_lock_prevents_duplicate_local_processes(tmp_path):
    path = tmp_path / 'data' / 'runtime.lock'
    with instance_lock(path) as first:
        assert first
        with instance_lock(path) as second:
            assert not second
    with instance_lock(path) as later:
        assert later


def test_windows_task_script_preserves_main_crm_and_handles_spaced_paths():
    root = PureWindowsPath(r"C:\Users\carlo\Downloads\hello main")
    script = powershell_registration(root, PureWindowsPath(r'C:\Python 312\python.exe'))
    assert '-Daily' in script and "'08:50'" in script and '-AtLogOn' in script
    assert '-MultipleInstances IgnoreNew' in script and '-StartWhenAvailable' in script
    assert '-WakeToRun' in script and '-RunLevel Limited' in script
    assert 'Vertice CRM2 Brasil' in script and 'Description -ne $marker' in script
    assert 'Remove-ScheduledTask' not in script and 'Unregister-ScheduledTask' not in script
    assert str(root) in script and 'iniciar.py' in script


def test_cycle_caps_capture_once_and_shares_three_send_slots_across_runners(app, monkeypatch):
    setup_campaign(app.state.sessions)
    configure(app.state.sessions)
    calls = []
    def start(sessions, city, niche, limit):
        calls.append(('capture', city, niche, limit))
        from crm.service import save_capture
        data = {'run_id': 'daily-run-1', 'status': 'SUCCEEDED', 'imported': True, 'created_at': AT.isoformat(), 'city': city, 'niche': niche}
        with sessions.begin() as s:
            save_capture(s, data)
        return data
    def send(sessions, **kwargs):
        assert kwargs['scheduled'] and kwargs['batch'] == 20
        calls.append(('send', kwargs['clock']))
        return {'sent': 2}
    monkeypatch.setattr(automation, 'start_capture', start)
    monkeypatch.setattr(automation, 'execute', send)
    assert automation.cycle(app.state.sessions, clock=AT)['sent'] == 2
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=5))['sent'] == 0
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=20))['sent'] == 2
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=40))['sent'] == 2
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=45))['sent'] == 0
    assert len([x for x in calls if x[0] == 'capture']) == 1
    assert len([x for x in calls if x[0] == 'send']) == 3


def test_no_auto_send_or_capture_outside_window_or_paused_campaign(app, monkeypatch):
    setup_campaign(app.state.sessions, enabled=False, approved=False)
    configure(app.state.sessions)
    def forbidden(*args, **kwargs): raise AssertionError('Operação real não deveria iniciar')
    monkeypatch.setattr(automation, 'start_capture', forbidden)
    monkeypatch.setattr(automation, 'execute', forbidden)
    assert automation.cycle(app.state.sessions, clock=AT)['state'] == 'paused'
    assert automation.cycle(app.state.sessions, clock=AT-timedelta(minutes=10))['state'] == 'preparing'
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(hours=1))['sent'] == 0


def test_uncertain_capture_is_not_created_again_and_manual_run_is_adopted(app, monkeypatch):
    setup_campaign(app.state.sessions)
    configure(app.state.sessions)
    calls = []
    def failed(*args):
        calls.append('create')
        raise RuntimeError('unknown outcome')
    monkeypatch.setattr(automation, 'start_capture', failed)
    monkeypatch.setattr(automation, 'execute', lambda *args, **kwargs: {'sent': 0})
    automation.cycle(app.state.sessions, clock=AT)
    result = automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=5))
    assert calls == ['create'] and any('incerta' in x for x in result['warnings'])


def test_manual_capture_of_same_day_does_not_charge_another_search(app, monkeypatch):
    setup_campaign(app.state.sessions)
    with app.state.sessions.begin() as s:
        set_config(s, 'capture', {'run_id': 'manual-run-today', 'status': 'SUCCEEDED', 'added': 1, 'created_at': AT.isoformat(), 'city': 'Campinas', 'niche': 'Oficinas'})
    def forbidden(*args): raise AssertionError('Não criar nova busca')
    monkeypatch.setattr(automation, 'start_capture', forbidden)
    monkeypatch.setattr(automation, 'execute', lambda *args, **kwargs: {'sent': 0})
    automation.cycle(app.state.sessions, clock=AT)
    with app.state.sessions() as s:
        record = json.loads(s.get(Config, 'auto:2026-11-02:capture').value)
    assert record['state'] == 'adopted' and record['run_id'] == 'manual-run-today'


def test_busy_slot_retries_but_completed_slot_does_not(app, monkeypatch):
    from crm.service import Busy
    setup_campaign(app.state.sessions)
    configure(app.state.sessions, capture_enabled=False)
    calls = []
    def send(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1: raise Busy('occupied before sending')
        return {'sent': 1}
    monkeypatch.setattr(automation, 'execute', send)
    assert automation.cycle(app.state.sessions, clock=AT)['sent'] == 0
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=1))['sent'] == 1
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=2))['sent'] == 0
    assert len(calls) == 2


def test_empty_batch_waits_for_pending_capture_without_losing_slot(app, monkeypatch):
    setup_campaign(app.state.sessions)
    configure(app.state.sessions, capture_enabled=False)
    state = {'status': 'RUNNING'}
    monkeypatch.setattr(automation, 'get_capture', lambda sessions: state.copy())
    monkeypatch.setattr(automation, 'poll_capture', lambda sessions: state.copy())
    monkeypatch.setattr(automation, 'execute', lambda *args, **kwargs: {'sent': 0 if state['status'] == 'RUNNING' else 1})
    assert automation.cycle(app.state.sessions, clock=AT)['sent'] == 0
    state['status'] = 'SUCCEEDED'
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=5))['sent'] == 1
    assert automation.cycle(app.state.sessions, clock=AT+timedelta(minutes=6))['sent'] == 0
