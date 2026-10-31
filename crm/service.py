import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update

from .db import Activity, Attachment, Config, Dispatch, Lead, Lease, Suppression, utcnow
from .domain import TZ, add_lead, campaign, set_config
from .providers import Apify, Gmail, ProviderError, map_place


class Busy(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc)


@contextmanager
def exclusive(sessions):
    owner = str(uuid.uuid4())
    with sessions.begin() as s:
        result = s.execute(update(Lease).where(Lease.id == 1, Lease.expires < utcnow()).values(owner=owner, expires=(now() + timedelta(minutes=10)).isoformat()))
        if not result.rowcount:
            raise Busy("Uma operação está em andamento. Aguarde e tente novamente.")
    try:
        yield owner
    finally:
        with sessions.begin() as s:
            s.execute(update(Lease).where(Lease.id == 1, Lease.owner == owner).values(owner="", expires=""))


def heartbeat(sessions, owner):
    with sessions.begin() as s:
        result = s.execute(update(Lease).where(Lease.id == 1, Lease.owner == owner, Lease.expires > utcnow()).values(expires=(now() + timedelta(minutes=10)).isoformat()))
        if not result.rowcount:
            raise Busy("Reserva de execução expirada; execução interrompida")


def daily_counts(s, day=None):
    day = day or now().astimezone(TZ).date().isoformat()
    rows = s.execute(select(Dispatch.stage, func.count()).where(Dispatch.day == day).group_by(Dispatch.stage)).all()
    initial = sum(n for stage, n in rows if stage == 0)
    followup = sum(n for stage, n in rows if stage > 0)
    return {"initial": initial, "followup": followup, "total": initial + followup}


def is_due(lead, c, at):
    if lead.deleted or not lead.email or lead.status not in {"novo", "em_cadencia"}:
        return False
    if lead.stage >= 3:
        return False
    if lead.stage == -1:
        return lead.status == "novo"
    return bool(lead.next_send and lead.next_send <= at.isoformat())


def stop_for_reply(s, lead):
    lead.status = "respondeu"
    lead.next_send = None
    if not s.get(Suppression, lead.email):
        s.add(Suppression(email=lead.email, reason="resposta"))
    s.add(Activity(kind="resposta", detail=f"{lead.name}: resposta recebida; sequência interrompida."))


def reply_history(s, lead):
    lead.history_threads = list(s.scalars(select(Dispatch.thread_id).where(Dispatch.lead_id == lead.id, Dispatch.thread_id.is_not(None))))
    return lead


def sync_inbox(sessions, gmail, owner):
    with sessions() as s:
        ids = list(s.scalars(select(Lead.id).where(Lead.first_sent.is_not(None), Lead.status.in_(["em_cadencia", "arquivado"]), Lead.deleted.is_(False))))
    count = 0
    for lead_id in ids:
        heartbeat(sessions, owner)
        with sessions.begin() as s:
            lead = reply_history(s, s.get(Lead, lead_id))
            if gmail.has_reply(lead):
                stop_for_reply(s, lead)
                count += 1
    with sessions.begin() as s:
        set_config(s, "last_inbox_sync", utcnow())
    return count


def execute(sessions, selected=None, scheduled=False, gmail_factory=Gmail, clock=None, batch=60):
    at = clock or now()
    local = at.astimezone(TZ)
    with sessions() as s:
        c = campaign(s)
    if scheduled and local.hour != 9:
        return {"sent": 0, "reason": "Fora da janela de 09:00–10:00 de Brasília"}
    if not c.enabled or not c.approved:
        return {"sent": 0, "reason": "Campanha pausada ou ainda não aprovada"}
    if not c.start_date <= local.date().isoformat() <= c.end_date:
        return {"sent": 0, "reason": "Campanha fora do período de validade; revise a oferta antes de reativar"}
    sent, replies = 0, 0
    with exclusive(sessions) as owner:
        gmail = gmail_factory()
        try:
            gmail.verify_sender(c.sender)
            replies = sync_inbox(sessions, gmail, owner)
            with sessions() as s:
                q = select(Lead.id).where(Lead.deleted.is_(False)).order_by(Lead.next_send.asc().nullslast(), Lead.created_at)
                if selected is not None:
                    q = q.where(Lead.id.in_(selected))
                ids = list(s.scalars(q))
            for lead_id in ids:
                if sent >= batch:
                    break
                # O relógio real prevalece quando a chamada atravessa o fim da janela.
                current = clock or now()
                current_local = current.astimezone(TZ)
                if scheduled and current_local.hour != 9:
                    break
                if not c.start_date <= current_local.date().isoformat() <= c.end_date:
                    break
                heartbeat(sessions, owner)
                with sessions.begin() as s:
                    lead = reply_history(s, s.get(Lead, lead_id))
                    if not is_due(lead, c, current) or s.get(Suppression, lead.email):
                        continue
                    stage = lead.stage + 1
                    if s.scalar(select(Dispatch.id).where(Dispatch.lead_id == lead.id, Dispatch.stage == stage)):
                        continue
                    if lead.first_sent and gmail.has_reply(lead):
                        stop_for_reply(s, lead)
                        replies += 1
                        continue
                    counts = daily_counts(s, current_local.date().isoformat())
                    if counts["total"] >= c.daily_total:
                        break
                    category, limit = ("initial", c.daily_initial) if stage == 0 else ("followup", c.daily_followup)
                    if counts[category] >= limit:
                        continue
                    attachments = list(s.scalars(select(Attachment)))
                    # Reserva persistida antes de acessar a API. Falha ambígua nunca libera cota ou reenvia.
                    dispatch = Dispatch(lead_id=lead.id, stage=stage, day=current_local.date().isoformat(), state="reservado")
                    s.add(dispatch)
                    s.flush()
                    dispatch_id = dispatch.id
                try:
                    result = gmail.send(c, lead, stage, attachments)
                    if not result.get("id") or not result.get("threadId"):
                        raise ProviderError("Resposta Gmail incompleta")
                except Exception:
                    with sessions.begin() as s:
                        s.get(Dispatch, dispatch_id).state = "incerto"
                        s.get(Lead, lead_id).status = "pausado"
                        s.add(Activity(kind="erro", detail=f"{lead.name}: envio incerto. Confira a pasta Enviados antes de qualquer ação; não haverá repetição automática."))
                    raise ProviderError("Envio não confirmado. Lead pausado e reserva mantida; confira o Gmail antes de continuar.") from None
                with sessions.begin() as s:
                    dispatch = s.get(Dispatch, dispatch_id)
                    dispatch.state, dispatch.message_id = "enviado", result["id"]
                    dispatch.thread_id = result["threadId"]
                    lead = s.get(Lead, lead_id)
                    lead.stage, lead.thread_id = stage, result["threadId"]
                    lead.first_sent = lead.first_sent or current.isoformat()
                    lead.status = "arquivado" if stage == 3 else "em_cadencia"
                    lead.next_send = None if stage == 3 else (current + timedelta(days=c.intervals[stage])).isoformat()
                    s.add(Activity(kind="envio", detail=f"{lead.name}: {'primeiro contato' if stage == 0 else f'follow-up {stage}'} enviado."))
                sent += 1
            with sessions.begin() as s:
                s.add(Activity(kind="automacao", detail=f"Execução concluída: {sent} envio(s), {replies} resposta(s)."))
        finally:
            gmail.close()
    return {"sent": sent, "replies": replies, "reason": "Execução concluída"}


def synchronize(sessions, gmail_factory=Gmail):
    with exclusive(sessions) as owner:
        gmail = gmail_factory()
        try:
            with sessions() as s:
                gmail.verify_sender(campaign(s).sender)
            return {"replies": sync_inbox(sessions, gmail, owner)}
        finally:
            gmail.close()


def start_capture(sessions, city, niche, limit):
    with exclusive(sessions):
        with sessions() as s:
            row = s.get(Config, "capture")
            if row and json.loads(row.value).get("status") in {"RUNNING", "READY"}:
                raise Busy("Já existe uma captação em andamento. Atualize o resultado antes de iniciar outra.")
        provider = Apify()
        try:
            run_id = provider.start(city, niche, limit)
        finally:
            provider.close()
        data = {"run_id": run_id, "city": city, "niche": niche, "status": "RUNNING", "created_at": utcnow()}
        with sessions.begin() as s:
            set_config(s, "capture", data)
            s.add(Activity(kind="captacao", detail=f"Busca iniciada: {niche}, {city}."))
        return data


def poll_capture(sessions):
    with exclusive(sessions):
        with sessions() as s:
            row = s.get(Config, "capture")
            if not row:
                return {"status": "NONE"}
            data = json.loads(row.value)
        if data["status"] not in {"RUNNING", "READY"}:
            return data
        provider = Apify()
        try:
            status, items = provider.poll(data["run_id"])
        finally:
            provider.close()
        data["status"] = status
        if status == "SUCCEEDED":
            added = duplicate = rejected = 0
            with sessions.begin() as s:
                for item in items:
                    try:
                        lead = map_place(item, data["city"], data["niche"])
                    except (ValueError, TypeError):
                        rejected += 1
                        continue
                    if lead is None:
                        rejected += 1
                    elif add_lead(s, lead):
                        added += 1
                    else:
                        duplicate += 1
                data.update(added=added, duplicates=duplicate, rejected=rejected)
                s.add(Activity(kind="captacao", detail=f"Captação concluída: {added} novos, {duplicate} duplicados, {rejected} fora do perfil ou inválidos."))
                set_config(s, "capture", data)
        else:
            with sessions.begin() as s:
                set_config(s, "capture", data)
        return data
