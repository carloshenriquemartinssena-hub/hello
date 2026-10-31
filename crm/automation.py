"""Ciclo compartilhado pelo terminal e GitHub; decisões persistidas no Supabase."""
import json
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .db import Config, utcnow
from .domain import TZ, campaign, set_config
from .providers import ProviderError
from .service import Busy, CAPTURE_ACTIVE, execute, get_capture, now, poll_capture, start_capture


class AutomationSettings(BaseModel):
    capture_enabled: bool = True
    city: str = Field(default='', max_length=120)
    niche: str = Field(default='', max_length=120)
    limit: int = Field(default=25, ge=1, le=100)


def settings(s):
    row = s.get(Config, 'automation')
    data = json.loads(row.value) if row else {}
    previous = s.get(Config, 'capture')
    source = json.loads(previous.value) if previous else {}
    data['city'] = data.get('city') or source.get('city') or ''
    data['niche'] = data.get('niche') or source.get('niche') or ''
    return AutomationSettings.model_validate(data)


def claim(sessions, key):
    owner = str(uuid.uuid4())
    try:
        with sessions.begin() as s:
            s.add(Config(key=key, value=json.dumps({'owner': owner, 'state': 'claimed', 'created_at': utcnow()})))
            s.flush()
    except IntegrityError as exc:
        if getattr(exc.orig, 'sqlstate', None) == '23505' or 'unique constraint' in str(exc.orig).lower():
            return None
        raise
    return owner


def finish(sessions, key, owner, **values):
    with sessions.begin() as s:
        row = s.get(Config, key)
        if row:
            data = json.loads(row.value)
            if data.get('owner') == owner:
                data.update(values)
                set_config(s, key, data)


def release_unstarted(sessions, key, owner):
    # Busy ocorre antes de iniciar o ator/enviar. Uma falha incerta nunca é liberada.
    with sessions.begin() as s:
        row = s.get(Config, key)
        if row and json.loads(row.value).get('owner') == owner:
            s.delete(row)


def _same_day(capture, day):
    try:
        return datetime.fromisoformat(capture['created_at']).astimezone(TZ).date().isoformat() == day
    except (KeyError, ValueError, TypeError):
        return False


def cycle(sessions, clock=None, should_stop=None):
    at = clock or now()
    local = at.astimezone(TZ)
    day = local.date().isoformat()
    result = {'day': day, 'sent': 0, 'capture': None, 'warnings': [], 'state': 'waiting'}
    if should_stop and should_stop():
        result['state'] = 'stopped'
        return result
    with sessions() as s:
        c, cfg = campaign(s), settings(s)
    valid = bool(c.enabled and c.approved and c.start_date <= day <= c.end_date)

    # Importar uma execução já iniciada não cria outra busca nem envia emails.
    current = get_capture(sessions)
    if current.get('status') in CAPTURE_ACTIVE:
        try:
            current = poll_capture(sessions)
            result['capture'] = {k: current[k] for k in ('status', 'added', 'duplicates', 'rejected') if k in current}
        except (ProviderError, Busy) as exc:
            result['warnings'].append(str(exc))

    if local.hour != 9:
        if local.hour == 8 and local.minute >= 50:
            result['state'] = 'preparing'
        result['reason'] = 'Aguardando 09h–10h de Brasília. Preparação às 08h50. Nenhum envio fora da janela.'
        return result
    if not valid:
        result.update(state='paused', reason='Campanha pausada, não aprovada ou fora da validade; captação automática e envios não iniciados.')
        return result
    if should_stop and should_stop():
        result['state'] = 'stopped'
        return result

    if cfg.capture_enabled:
        if not cfg.city.strip() or not cfg.niche.strip():
            result['warnings'].append('Defina cidade e nicho em Configurações → Automação, ou faça uma busca manual para registrar o alvo.')
        else:
            key = 'auto:' + day + ':capture'
            owner = claim(sessions, key)
            if owner:
                try:
                    # Busca manual do mesmo dia/em andamento é reaproveitada, sem nova cobrança.
                    current = get_capture(sessions)
                    if current.get('run_id') and (_same_day(current, day) or current.get('status') in CAPTURE_ACTIVE):
                        finish(sessions, key, owner, state='adopted', run_id=current['run_id'])
                    else:
                        current = start_capture(sessions, cfg.city.strip(), cfg.niche.strip(), cfg.limit)
                        finish(sessions, key, owner, state='started', run_id=current['run_id'])
                    result['capture'] = {'status': current['status'], 'run_id': current.get('run_id')}
                except Busy as exc:
                    release_unstarted(sessions, key, owner)
                    result['warnings'].append(str(exc))
                except Exception:
                    finish(sessions, key, owner, state='uncertain')
                    result['warnings'].append('A busca diária não foi confirmada. Confira Runs no Apify e recupere pelo Run ID; não haverá outra criação automática hoje.')
            else:
                with sessions() as s:
                    row = s.get(Config, key)
                    existing = json.loads(row.value) if row else {}
                if existing.get('state') == 'uncertain':
                    result['warnings'].append('Captação diária incerta: recupere a execução existente no painel. Nenhuma nova busca será criada automaticamente hoje.')

    # Cada lote é reservado uma vez no banco, inclusive entre Windows e GitHub.
    for minute in (0, 20, 40):
        if local.minute < minute or (should_stop and should_stop()):
            break
        key = f'auto:{day}:send09{minute:02d}'
        owner = claim(sessions, key)
        if not owner:
            continue
        try:
            outcome = execute(sessions, scheduled=True, batch=20, clock=clock, should_stop=should_stop)
            if outcome['sent'] == 0 and get_capture(sessions).get('status') in CAPTURE_ACTIVE:
                # A fonte pode terminar após o horário do lote. Sem envio efetuado,
                # mantenha o lote disponível para os resultados dentro da janela.
                release_unstarted(sessions, key, owner)
            else:
                finish(sessions, key, owner, state='done', sent=outcome['sent'])
            result['sent'] += outcome['sent']
        except Busy as exc:
            release_unstarted(sessions, key, owner)
            result['warnings'].append(str(exc))
        except Exception:
            finish(sessions, key, owner, state='uncertain')
            result['warnings'].append('O lote teve uma falha ou resultado incerto. A reserva foi mantida; confira Atividades antes de qualquer reenvio.')
            break
    result.update(state='processed', reason='Ciclo concluído. Cotas, respostas e reservas continuam controladas pelo banco.')
    return result
