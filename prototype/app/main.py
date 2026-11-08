import base64
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from secrets import token_urlsafe, compare_digest
from time import monotonic
from uuid import UUID, uuid4
from fastapi import FastAPI, Request, Depends, Header, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
from sqlalchemy import select, insert, update, and_, or_, exists
from sqlalchemy.exc import SQLAlchemyError
from . import schema as s, services as service
from .config import origin
from .db import make_engine
from .contracts import Login, CreateTicket, Assignment, StateChange, CommentInput
from .errors import Problem, require
from .security import now, digest, verify, dummy_hash, LoginLimits

log = logging.getLogger("support")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)sZ %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
formatter.converter = time.gmtime
handler.setFormatter(formatter)
log.addHandler(handler)
log.setLevel(logging.INFO)
log.propagate = False
limits = LoginLimits()
ROOT = Path(__file__).parent


@asynccontextmanager
async def lifespan(app):
    app.state.origin = origin()
    app.state.engine = make_engine()
    yield
    await app.state.engine.dispose()


app = FastAPI(
    title="Навчальна технічна підтримка",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")


def serial(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def reply(value, status=200, headers=None):
    return JSONResponse(serial(value), status_code=status, headers=headers)


def error(request, status, code, message, fields=None):
    return reply(
        dict(
            code=code,
            message=message,
            correlationId=request.state.cid,
            fieldErrors=fields or [],
        ),
        status,
    )


@app.exception_handler(Problem)
async def problem_handler(request, exc):
    return error(request, exc.status, exc.code, exc.message, exc.fields)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request, exc):
    return error(
        request,
        exc.status_code,
        "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR",
        "Операцію не знайдено." if exc.status_code == 404 else "Запит відхилено.",
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    invalid_json = any(
        e["type"] == "json_invalid" or e["loc"][0] in ("path", "query", "header")
        for e in exc.errors()
    )
    fields = [
        {
            "field": ".".join(str(x) for x in e["loc"][1:])[:100] or "request",
            "message": "Некоректне значення.",
        }
        for e in exc.errors()
    ]
    return error(
        request,
        400 if invalid_json else 422,
        "VALIDATION_ERROR",
        "Перевірте введені дані.",
        fields,
    )


@app.middleware("http")
async def transaction_and_headers(request, call_next):
    request.state.cid = str(uuid4())
    start = monotonic()
    try:
        if request.url.path.startswith("/api/"):
            if request.method not in ("GET", "HEAD"):
                if request.headers.get("origin") != request.app.state.origin:
                    response = error(
                        request, 403, "CSRF_FAILED", "Походження запиту не дозволене."
                    )
                elif (
                    request.method != "DELETE"
                    and request.headers.get("content-type", "").split(";")[0]
                    != "application/json"
                ):
                    response = error(
                        request, 400, "VALIDATION_ERROR", "Потрібен JSON-запит."
                    )
                else:
                    response = None
            else:
                response = None
            if response is None:
                async with request.app.state.engine.connect() as conn:
                    transaction = await conn.begin()
                    request.state.conn = conn
                    try:
                        response = await call_next(request)
                        if response.status_code < 400:
                            await transaction.commit()
                        else:
                            await transaction.rollback()
                    except BaseException:
                        await transaction.rollback()
                        raise
        else:
            response = await call_next(request)
    except SQLAlchemyError:
        response = error(
            request,
            503,
            "STORAGE_UNAVAILABLE",
            "Сховище тимчасово недоступне; результат дії не підтверджено.",
        )
    response.headers["X-Correlation-ID"] = request.state.cid
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    # Log route template, never URL parameters, request bodies, cookies or exceptions.
    route = getattr(request.scope.get("route"), "path", "unmatched")
    log.info(
        "operation=%s method=%s status=%s duration_ms=%s correlation_id=%s",
        route,
        request.method,
        response.status_code,
        round((monotonic() - start) * 1000),
        request.state.cid,
    )
    return response


async def authenticated(request: Request):
    token = request.cookies.get("support_session", "")
    require(0 < len(token) <= 256, 401, "UNAUTHENTICATED", "Потрібен чинний сеанс.")
    conn = request.state.conn
    row = (
        (
            await conn.execute(
                select(s.sessions)
                .join(s.users)
                .where(
                    s.sessions.c.token_digest == digest(token),
                    s.sessions.c.revoked_at.is_(None),
                    s.sessions.c.expires_at > now(),
                    s.users.c.active,
                )
            )
        )
        .mappings()
        .first()
    )
    require(row is not None, 401, "UNAUTHENTICATED", "Потрібен чинний сеанс.")
    if request.method not in ("GET", "HEAD"):
        csrf = request.headers.get("X-CSRF-Token", "")
        require(
            len(csrf) <= 256 and compare_digest(digest(csrf), row["csrf_digest"]),
            403,
            "CSRF_FAILED",
            "Оновіть сеанс і підтвердіть дію знову.",
        )
    return dict(row)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/session")
async def login(body: Login, request: Request):
    conn = request.state.conn
    login_name = body.login
    address = request.client.host if request.client else "unknown"
    require(
        not limits.blocked(login_name, address),
        401,
        "UNAUTHENTICATED",
        "Не вдалося увійти.",
    )
    user = (
        (await conn.execute(select(s.users).where(s.users.c.login == login_name)))
        .mappings()
        .first()
    )
    valid = await run_in_threadpool(
        verify, user["credential_hash"] if user else dummy_hash, body.password
    )
    if not valid or not user or not user["active"]:
        limits.failure(login_name, address)
        raise Problem(401, "UNAUTHENTICATED", "Не вдалося увійти.")
    token, csrf = token_urlsafe(32), token_urlsafe(32)
    stamp = now()
    expiry = stamp + timedelta(hours=8)
    await conn.execute(
        insert(s.sessions).values(
            id=uuid4(),
            user_id=user["id"],
            token_digest=digest(token),
            csrf_digest=digest(csrf),
            created_at=stamp,
            expires_at=expiry,
        )
    )
    response = reply(
        dict(
            userId=user["id"],
            roles=await service.roles(conn, user["id"]),
            csrfToken=csrf,
            expiresAt=expiry,
        )
    )
    response.set_cookie(
        "support_session",
        token,
        max_age=28800,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return response


@app.get("/api/v1/session")
async def session(request: Request, current=Depends(authenticated)):
    csrf = token_urlsafe(32)
    conn = request.state.conn
    await conn.execute(
        update(s.sessions)
        .where(s.sessions.c.id == current["id"])
        .values(csrf_digest=digest(csrf))
    )
    return reply(
        dict(
            userId=current["user_id"],
            roles=await service.roles(conn, current["user_id"]),
            csrfToken=csrf,
            expiresAt=current["expires_at"],
        )
    )


@app.delete("/api/v1/session")
async def logout(request: Request, current=Depends(authenticated)):
    await request.state.conn.execute(
        update(s.sessions)
        .where(s.sessions.c.id == current["id"])
        .values(revoked_at=now())
    )
    response = Response(status_code=204)
    response.delete_cookie(
        "support_session", path="/", secure=True, httponly=True, samesite="strict"
    )
    return response


@app.post("/api/v1/tickets")
async def create_ticket(
    body: CreateTicket,
    request: Request,
    key: UUID = Header(alias="Idempotency-Key"),
    current=Depends(authenticated),
):
    t, status = await service.create(request.state.conn, current["user_id"], body, key)
    return reply(
        service.ticket_view(t), status, {"Location": f"/api/v1/tickets/{t['id']}"}
    )


@app.get("/api/v1/tickets/{ticket_id}")
async def get_ticket(ticket_id: UUID, request: Request, current=Depends(authenticated)):
    return reply(
        service.ticket_view(
            await service.ticket(request.state.conn, current["user_id"], ticket_id)
        )
    )


@app.post("/api/v1/tickets/{ticket_id}/assignment")
async def assign(
    ticket_id: UUID, body: Assignment, request: Request, current=Depends(authenticated)
):
    return reply(
        service.ticket_view(
            await service.assign(
                request.state.conn, current["user_id"], ticket_id, body
            )
        )
    )


@app.post("/api/v1/tickets/{ticket_id}/state")
async def state(
    ticket_id: UUID, body: StateChange, request: Request, current=Depends(authenticated)
):
    return reply(
        service.ticket_view(
            await service.transition(
                request.state.conn, current["user_id"], ticket_id, body
            )
        )
    )


@app.post("/api/v1/tickets/{ticket_id}/comments")
async def comment(
    ticket_id: UUID,
    body: CommentInput,
    request: Request,
    current=Depends(authenticated),
):
    return reply(
        service.ticket_view(
            await service.comment(
                request.state.conn, current["user_id"], ticket_id, body
            )
        )
    )


async def page(conn, query, limit, cursor, mapper):
    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
            if not 0 <= offset <= 1000000:
                raise ValueError()
        except (ValueError, UnicodeError):
            raise Problem(400, "INVALID_CURSOR", "Некоректний курсор.")
    rows = (await conn.execute(query.limit(limit + 1).offset(offset))).mappings().all()
    next_cursor = (
        base64.urlsafe_b64encode(str(offset + limit).encode()).decode()
        if len(rows) > limit
        else None
    )
    return reply(
        {"items": [mapper(r) for r in rows[:limit]], "nextCursor": next_cursor}
    )


@app.get("/api/v1/tickets/{ticket_id}/comments")
async def comments(
    ticket_id: UUID,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=300),
    current=Depends(authenticated),
):
    conn = request.state.conn
    uid = current["user_id"]
    t = await service.ticket(conn, uid, ticket_id)
    query = select(s.comments).where(s.comments.c.ticket_id == ticket_id)
    if t["requester_id"] == uid:
        query = query.where(s.comments.c.visibility == "public")
    return await page(
        conn,
        query.order_by(s.comments.c.created_at, s.comments.c.id),
        limit,
        cursor,
        lambda r: service.present(
            r,
            [
                "id",
                "ticket_id",
                "author_id",
                "created_at",
                "body",
                "visibility",
                "kind",
            ],
        ),
    )


@app.get("/api/v1/tickets/{ticket_id}/history")
async def history(
    ticket_id: UUID,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=300),
    current=Depends(authenticated),
):
    conn = request.state.conn
    uid = current["user_id"]
    t = await service.ticket(conn, uid, ticket_id)
    query = select(s.history_events).where(s.history_events.c.ticket_id == ticket_id)
    if t["requester_id"] == uid:
        query = query.where(s.history_events.c.visibility == "public")
    return await page(
        conn,
        query.order_by(s.history_events.c.occurred_at, s.history_events.c.id),
        limit,
        cursor,
        lambda r: service.present(
            r, ["id", "occurred_at", "actor_id", "event_type", "changes"]
        ),
    )


@app.get("/api/v1/categories")
async def categories(request: Request, current=Depends(authenticated)):
    conn = request.state.conn
    require("requester" in await service.roles(conn, current["user_id"]))
    query = (
        select(s.categories.c.id, s.categories.c.name)
        .join(s.queues)
        .where(
            s.categories.c.active,
            s.queues.c.active,
            exists(
                select(s.sla_policies.c.id).where(
                    s.sla_policies.c.category_id == s.categories.c.id,
                    s.sla_policies.c.priority == "normal",
                    s.sla_policies.c.active,
                )
            ),
        )
        .order_by(s.categories.c.name, s.categories.c.id)
    )
    return reply({"items": [dict(r) for r in (await conn.execute(query)).mappings()]})


@app.get("/api/v1/queues/{queue_id}/assignees")
async def assignees(queue_id: UUID, request: Request, current=Depends(authenticated)):
    conn = request.state.conn
    require(await service.member(conn, current["user_id"], queue_id, "coordinator"))
    query = (
        select(s.users.c.id, s.users.c.display_name)
        .join(s.queue_memberships)
        .join(s.user_roles, s.user_roles.c.user_id == s.users.c.id)
        .where(
            s.users.c.active,
            s.queue_memberships.c.queue_id == queue_id,
            s.queue_memberships.c.active,
            s.queue_memberships.c.member_role == "specialist",
            s.user_roles.c.role_code == "specialist",
            s.user_roles.c.active,
        )
        .order_by(s.users.c.display_name, s.users.c.id)
    )
    return reply(
        {
            "items": [
                service.present(r, ["id", "display_name"])
                for r in (await conn.execute(query)).mappings()
            ]
        }
    )


@app.get("/api/v1/tickets")
async def tickets(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=300),
    current=Depends(authenticated),
):
    conn = request.state.conn
    uid = current["user_id"]
    allowed = (
        select(s.queue_memberships.c.queue_id)
        .join(s.queues)
        .join(
            s.user_roles,
            and_(
                s.user_roles.c.user_id == s.queue_memberships.c.user_id,
                s.user_roles.c.role_code == s.queue_memberships.c.member_role,
            ),
        )
        .where(
            s.queue_memberships.c.user_id == uid,
            s.queue_memberships.c.active,
            s.queues.c.active,
            s.user_roles.c.active,
        )
    )
    query = (
        select(s.tickets)
        .where(or_(s.tickets.c.requester_id == uid, s.tickets.c.queue_id.in_(allowed)))
        .order_by(s.tickets.c.created_at.desc(), s.tickets.c.id.desc())
    )
    # shortcut: extended filters are outside the minimal prototype; reject rather than ignore.
    require(
        set(request.query_params) <= {"limit", "cursor"},
        400,
        "VALIDATION_ERROR",
        "Розширені фільтри не входять до прототипу.",
    )
    fields = [
        "id",
        "number",
        "title",
        "state",
        "priority",
        "category_id",
        "queue_id",
        "assignee_id",
        "created_at",
        "version",
    ]
    return await page(conn, query, limit, cursor, lambda r: service.present(r, fields))
