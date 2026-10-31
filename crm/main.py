import csv
import base64
import html
import hashlib
import hmac
import io
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .environment import load_environment
from .db import Activity, Attachment, Config, Dispatch, Lead, Lease, Suppression, connect
from .domain import Campaign, LeadInput, NICHES, STATUSES, TZ, add_lead, campaign, duplicate, render_message, serialize, set_config
from .providers import ProviderError
from .service import Busy, daily_counts, exclusive, execute, now, poll_capture, start_capture, synchronize

STATIC = Path(__file__).parent / "static"
load_environment()


def create_app(database_url=None):
    production = os.getenv("CRM_ENV", "development") == "production"
    password = os.getenv("CRM_ADMIN_PASSWORD", "")
    session_key = os.getenv("CRM_SESSION_SECRET", "") or secrets.token_hex(32)
    worker_token = os.getenv("CRM_WORKER_TOKEN", "")
    attempts = {}
    engine, sessions = connect(database_url)

    @asynccontextmanager
    async def lifespan(app):
        if production and (len(password) < 16 or len(os.getenv("CRM_SESSION_SECRET", "")) < 32 or len(worker_token) < 32):
            raise RuntimeError("Produção requer CRM_ADMIN_PASSWORD (16+), CRM_SESSION_SECRET (32+) e CRM_WORKER_TOKEN (32+)")
        yield
        engine.dispose()

    app = FastAPI(title="Vértice • CRM Brasil", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.sessions = sessions
    app.state.engine = engine

    def authorized(request: Request):
        # Acesso sem senha apenas no desenvolvimento em loopback.
        if not password and not production and request.client and request.client.host in {"127.0.0.1", "::1", "testclient"}:
            return
        token = request.cookies.get("crm2_session", "")
        try:
            expiry, signature = token.split(".")
            expected = hmac.new(session_key.encode(), expiry.encode(), hashlib.sha256).hexdigest()
            if int(expiry) < time.time() or not hmac.compare_digest(signature, expected):
                raise ValueError
        except (ValueError, TypeError):
            raise HTTPException(401, "Entre com a senha do painel")
        if request.method not in {"GET", "HEAD"}:
            origin = request.headers.get("origin")
            allowed = (os.getenv("CRM_PUBLIC_URL") or str(request.base_url)).rstrip("/")
            if not origin or origin.rstrip("/") != allowed:
                raise HTTPException(403, "Origem da solicitação não autorizada")

    @app.middleware("http")
    async def headers(request, call_next):
        if request.headers.get("content-length", "").isdigit() and int(request.headers["content-length"]) > 12 * 1024 * 1024:
            return JSONResponse({"detail": "Arquivo muito grande"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        preview_document = request.url.path.startswith("/api/preview/") and request.url.path.endswith("/document")
        if preview_document:
            response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'; base-uri 'none'; form-action 'none'; sandbox"
        else:
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ProviderError)
    async def provider_error(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(Busy)
    async def busy_error(_, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(IntegrityError)
    async def duplicate_error(_, exc):
        return JSONResponse({"detail": "Já existe um lead com esse email, telefone ou identificação do Google."}, status_code=409)

    @app.exception_handler(Exception)
    async def unexpected_error(_, exc):
        # Não expõe URLs de banco, tokens nem dados de resposta de provedores.
        return JSONResponse({"detail": "Não foi possível concluir a operação. Verifique a configuração e tente novamente."}, status_code=500)

    @app.get("/healthz")
    def health():
        with sessions() as s:
            s.execute(select(1))
        return {"status": "ok", "app": "crm2-brasil"}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/login")
    def login_page():
        return FileResponse(STATIC / "login.html")

    class Login(BaseModel):
        password: str = Field(max_length=500)

    @app.post("/auth/login")
    def login(data: Login, request: Request, response: Response):
        host = request.client.host
        recent = [t for t in attempts.get(host, []) if time.time() - t < 60]
        attempts[host] = recent
        if len(recent) >= 5:
            raise HTTPException(429, "Aguarde um minuto antes de tentar novamente")
        recent.append(time.time())
        if not password or not secrets.compare_digest(data.password, password):
            raise HTTPException(401, "Senha inválida")
        expiry = str(int(time.time()) + 8 * 3600)
        sig = hmac.new(session_key.encode(), expiry.encode(), hashlib.sha256).hexdigest()
        response.set_cookie("crm2_session", expiry + "." + sig, httponly=True, secure=production, samesite="strict", max_age=28800)
        return {"ok": True}

    @app.post("/api/logout", dependencies=[Depends(authorized)])
    def logout(response: Response):
        response.delete_cookie("crm2_session")
        return {"ok": True}

    @app.get("/api/dashboard", dependencies=[Depends(authorized)])
    def dashboard():
        with sessions() as s:
            counts = dict(s.execute(select(Lead.status, func.count()).where(Lead.deleted.is_(False)).group_by(Lead.status)).all())
            total = sum(counts.values())
            c = campaign(s)
            reserved = daily_counts(s)
            sent = s.scalar(select(func.count()).select_from(Dispatch).where(Dispatch.day == now().astimezone(TZ).date().isoformat(), Dispatch.state == "enviado"))
            replied = sum(counts.get(x, 0) for x in ["respondeu", "negociacao", "ganho"])
            sync = s.get(Config, "last_inbox_sync")
            return {"total": total, "counts": counts, "daily": reserved, "sent_today": sent,
                    "reply_rate": round(100 * replied / total, 1) if total else 0,
                    "campaign": c.model_dump(), "last_sync": json.loads(sync.value) if sync else None,
                    "activity": [serialize(x) for x in s.scalars(select(Activity).order_by(Activity.id.desc()).limit(12))]}

    @app.get("/api/leads", dependencies=[Depends(authorized)])
    def leads(q: str = "", status: str = "", niche: str = "", page: int = 1):
        q, niche = q[:200], niche[:120]
        filters = [Lead.deleted.is_(False)]
        if q:
            from sqlalchemy import or_
            filters.append(or_(Lead.name.ilike(f"%{q}%"), Lead.email.ilike(f"%{q}%"), Lead.city.ilike(f"%{q}%")))
        if status:
            filters.append(Lead.status == status)
        if niche:
            filters.append(Lead.niche == niche)
        with sessions() as s:
            total = s.scalar(select(func.count()).select_from(Lead).where(*filters))
            rows = s.scalars(select(Lead).where(*filters).order_by(Lead.id.desc()).offset((max(1, page) - 1) * 25).limit(25))
            return {"items": [serialize(x) for x in rows], "total": total, "page": max(1, page)}

    @app.post("/api/leads", dependencies=[Depends(authorized)])
    def create_lead(item: LeadInput):
        with exclusive(sessions), sessions.begin() as s:
            lead = add_lead(s, item)
            if not lead:
                raise HTTPException(409, "Lead já cadastrado, inclusive em registros excluídos")
            s.add(Activity(kind="lead", detail=f"{lead.name}: lead adicionado."))
            return serialize(lead)

    @app.put("/api/leads/{lead_id}", dependencies=[Depends(authorized)])
    def edit_lead(lead_id: int, item: LeadInput):
        with exclusive(sessions), sessions.begin() as s:
            lead = s.get(Lead, lead_id)
            if not lead or lead.deleted:
                raise HTTPException(404, "Lead não encontrado")
            if lead.first_sent and item.email != lead.email:
                raise HTTPException(409, "O email de um lead já contatado não pode ser alterado; preserve o histórico")
            if duplicate(s, item.model_dump(), exclude=lead_id):
                raise HTTPException(409, "Outro lead já utiliza esses dados")
            for k, v in item.model_dump().items():
                setattr(lead, k, v)
            s.add(Activity(kind="lead", detail=f"{lead.name}: cadastro atualizado."))
            return serialize(lead)

    class Bulk(BaseModel):
        ids: list[int] = Field(min_length=1, max_length=500)
        action: str
        status: str = ""

    @app.post("/api/leads/bulk", dependencies=[Depends(authorized)])
    def bulk(data: Bulk):
        if data.action not in {"status", "delete"} or (data.action == "status" and data.status not in STATUSES):
            raise HTTPException(422, "Ação inválida")
        with exclusive(sessions), sessions.begin() as s:
            rows = list(s.scalars(select(Lead).where(Lead.id.in_(data.ids), Lead.deleted.is_(False))))
            for lead in rows:
                if data.action == "delete":
                    lead.deleted, lead.next_send = True, None
                    if lead.email and not s.get(Suppression, lead.email):
                        s.add(Suppression(email=lead.email, reason="exclusao"))
                else:
                    if data.status == "novo" and lead.stage != -1:
                        raise HTTPException(409, "Leads contatados não podem voltar a novos")
                    if data.status == "em_cadencia" and (lead.stage < 0 or lead.stage >= 3):
                        raise HTTPException(409, "A cadência começa no primeiro envio e termina no follow-up 3")
                    if data.status == "em_cadencia" and lead.email and s.get(Suppression, lead.email):
                        raise HTTPException(409, "Contato bloqueado por resposta, exclusão ou desinteresse")
                    lead.status = data.status
                    if data.status in {"sem_interesse", "respondeu", "negociacao", "ganho"} and lead.email and not s.get(Suppression, lead.email):
                        s.add(Suppression(email=lead.email, reason="optout" if data.status == "sem_interesse" else "resposta"))
            s.add(Activity(kind="lead", detail=f"{len(rows)} lead(s): {'excluídos' if data.action == 'delete' else 'status atualizado para ' + data.status}."))
            return {"updated": len(rows)}

    @app.post("/api/import", dependencies=[Depends(authorized)])
    async def import_csv(file: UploadFile = File(...)):
        data = await file.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise HTTPException(413, "CSV deve ter até 2 MB")
        try:
            reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
            rows = list(reader)
        except (UnicodeError, csv.Error):
            raise HTTPException(422, "Use CSV UTF-8 com cabeçalho")
        if len(rows) > 500:
            raise HTTPException(422, "Importe no máximo 500 linhas por vez")
        added, duplicates, errors = 0, 0, []
        with exclusive(sessions), sessions.begin() as s:
            for i, row in enumerate(rows, 2):
                try:
                    item = LeadInput(**{k: v for k, v in row.items() if k in LeadInput.model_fields and v != ""})
                except ValueError:
                    errors.append({"line": i, "detail": "Dados inválidos; revise nome, email, telefone e links"})
                    continue
                if add_lead(s, item):
                    added += 1
                else:
                    duplicates += 1
            s.add(Activity(kind="importacao", detail=f"CSV: {added} adicionados, {duplicates} duplicados, {len(errors)} inválidos."))
        return {"added": added, "duplicates": duplicates, "errors": errors}

    @app.get("/api/export", dependencies=[Depends(authorized)])
    def export_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        fields = list(LeadInput.model_fields) + ["status", "stage"]
        writer.writerow(fields)
        with sessions() as s:
            for lead in s.scalars(select(Lead).where(Lead.deleted.is_(False))):
                values = []
                for f in fields:
                    v = getattr(lead, f)
                    if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")):
                        v = "'" + v
                    values.append(v)
                writer.writerow(values)
        return Response("\ufeff" + output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="leads-brasil.csv"'})

    @app.get("/api/campaign", dependencies=[Depends(authorized)])
    def get_campaign():
        with sessions() as s:
            return campaign(s).model_dump()

    @app.put("/api/campaign", dependencies=[Depends(authorized)])
    def save_campaign(data: Campaign):
        with exclusive(sessions), sessions.begin() as s:
            set_config(s, "campaign", data.model_dump())
            s.add(Activity(kind="campanha", detail="Campanha atualizada; " + ("envios habilitados." if data.enabled else "envios pausados.")))
        return data.model_dump()

    @app.get("/api/preview/{stage}", dependencies=[Depends(authorized)])
    def preview(stage: int, lead_id: int | None = None):
        if stage not in range(4):
            raise HTTPException(404)
        with sessions() as s:
            sample = s.get(Lead, lead_id) if lead_id is not None else Lead(name="Empresa Exemplo", city="São Paulo")
            if sample is None or (lead_id is not None and sample.deleted):
                raise HTTPException(404, 'Lead não encontrado')
            subject, plain, content = render_message(campaign(s), sample, stage)
            return {"subject": subject, "plain": plain, "html": content}

    @app.get("/api/preview/{stage}/document", dependencies=[Depends(authorized)])
    def preview_document(stage: int):
        if stage not in range(4):
            raise HTTPException(404)
        with sessions() as s:
            sample = Lead(name="Empresa Exemplo", city="São Paulo")
            _, _, content = render_message(campaign(s), sample, stage)
            for a in s.scalars(select(Attachment).where(Attachment.inline.is_(True))):
                content += '<p><img alt="' + html.escape(a.name, quote=True) + '" style="max-width:100%" src="data:' + a.content_type + ';base64,' + base64.b64encode(a.data).decode() + '"></p>'
        document = '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"></head><body style="padding:24px;background:white">' + content + '</body></html>'
        return Response(document, media_type="text/html")

    @app.get("/api/attachments", dependencies=[Depends(authorized)])
    def attachments():
        with sessions() as s:
            return [{**serialize(x), "size": len(x.data)} for x in s.scalars(select(Attachment))]

    @app.post("/api/attachments", dependencies=[Depends(authorized)])
    async def upload(file: UploadFile = File(...), inline: bool = False):
        data = await file.read(5 * 1024 * 1024 + 1)
        allowed = {"image/png", "image/jpeg", "image/webp", "application/pdf", "text/plain", "application/zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        if file.content_type not in allowed or (inline and not file.content_type.startswith("image/")):
            raise HTTPException(422, "Formato não suportado. Use PNG, JPEG, WebP, PDF, TXT, ZIP, DOCX ou XLSX")
        if not data or len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "Cada arquivo deve ter entre 1 byte e 5 MB")
        with exclusive(sessions), sessions.begin() as s:
            rows = list(s.scalars(select(Attachment)))
            if len(rows) >= 5 or sum(len(x.data) for x in rows) + len(data) > 10 * 1024 * 1024:
                raise HTTPException(413, "Limite: 5 arquivos e 10 MB por campanha")
            row = Attachment(name=Path(file.filename or "arquivo").name[:200], content_type=file.content_type, data=data, inline=inline)
            s.add(row)
            s.flush()
            return {**serialize(row), "size": len(data)}

    @app.delete("/api/attachments/{attachment_id}", dependencies=[Depends(authorized)])
    def remove_attachment(attachment_id: int):
        with exclusive(sessions), sessions.begin() as s:
            row = s.get(Attachment, attachment_id)
            if not row:
                raise HTTPException(404)
            s.delete(row)
        return {"ok": True}

    class Capture(BaseModel):
        city: str = Field(min_length=2, max_length=120)
        niche: str = Field(min_length=2, max_length=120)
        limit: int = Field(default=50, ge=1, le=100)

    @app.post("/api/capture", dependencies=[Depends(authorized)])
    def capture(data: Capture):
        return start_capture(sessions, data.city, data.niche, data.limit)

    @app.post("/api/capture/poll", dependencies=[Depends(authorized)])
    def capture_poll():
        return poll_capture(sessions)

    class SendSelection(BaseModel):
        ids: list[int] = Field(min_length=1, max_length=60)

    @app.post("/api/send", dependencies=[Depends(authorized)])
    def send(data: SendSelection):
        return execute(sessions, selected=data.ids)

    class SingleTest(BaseModel):
        lead_id: int = Field(ge=1)
        confirmed: bool = False

    @app.post('/api/send/test-one', dependencies=[Depends(authorized)])
    def send_single_test(data: SingleTest):
        if not data.confirmed:
            raise HTTPException(422, 'Revise a mensagem e confirme o teste real de um único email.')
        return execute(sessions, selected=[data.lead_id], single_test=True)

    @app.post("/api/inbox/sync", dependencies=[Depends(authorized)])
    def inbox_sync():
        return synchronize(sessions)

    @app.get("/api/settings", dependencies=[Depends(authorized)])
    def settings():
        names = ["CRM_DATABASE_URL", "CRM_ADMIN_PASSWORD", "CRM_SESSION_SECRET", "CRM_WORKER_TOKEN", "CRM_APIFY_TOKEN", "CRM_GMAIL_CLIENT_ID", "CRM_GMAIL_CLIENT_SECRET", "CRM_GMAIL_REFRESH_TOKEN"]
        return {"production": production, "timezone": "America/Sao_Paulo", "database": "PostgreSQL" if engine.dialect.name == "postgresql" else "SQLite local",
                "variables": {k: bool(os.getenv(k)) for k in names}, "niches": NICHES}

    @app.get("/api/activity", dependencies=[Depends(authorized)])
    def activity():
        with sessions() as s:
            return [serialize(x) for x in s.scalars(select(Activity).order_by(Activity.id.desc()).limit(200))]

    def authorize_worker(request: Request):
        token = request.headers.get("authorization", "")
        if len(worker_token) < 32 or not secrets.compare_digest(token, "Bearer " + worker_token):
            raise HTTPException(401, "Token de automação inválido")

    @app.post("/api/automation/prepare", dependencies=[Depends(authorize_worker)])
    def prepare_automation():
        # Acorda o servidor e verifica as tabelas sem iniciar captação, reservar
        # cotas, alterar a campanha ou acessar provedores externos.
        with sessions() as s:
            if not s.get(Lease, 1):
                raise HTTPException(503, "Estrutura do banco incompleta")
            c = campaign(s)
        return {"status": "awake", "database": "ok", "campaign_enabled": c.enabled,
                "emails_sent": 0, "capture_started": False,
                "timezone": "America/Sao_Paulo"}

    @app.post("/api/automation/run", dependencies=[Depends(authorize_worker)])
    def automation():
        return execute(sessions, scheduled=True, batch=20)

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
