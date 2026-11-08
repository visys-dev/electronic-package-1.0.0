import json
from uuid import uuid4
from sqlalchemy import select, insert, update
from . import schema as s
from .errors import require
from .security import now, digest


async def roles(conn, uid):
    return list(
        (
            await conn.execute(
                select(s.user_roles.c.role_code).where(
                    s.user_roles.c.user_id == uid, s.user_roles.c.active
                )
            )
        ).scalars()
    )


async def member(conn, uid, queue, role):
    if role not in await roles(conn, uid):
        return False
    return bool(
        (
            await conn.execute(
                select(s.queue_memberships.c.id)
                .join(s.queues)
                .where(
                    s.queue_memberships.c.user_id == uid,
                    s.queue_memberships.c.queue_id == queue,
                    s.queue_memberships.c.member_role == role,
                    s.queue_memberships.c.active,
                    s.queues.c.active,
                )
            )
        ).first()
    )


async def support(conn, uid, queue):
    return await member(conn, uid, queue, "specialist") or await member(
        conn, uid, queue, "coordinator"
    )


async def ticket(conn, uid, tid, lock=False):
    query = select(s.tickets).where(s.tickets.c.id == tid)
    if lock:
        query = query.with_for_update()
    row = (await conn.execute(query)).mappings().first()
    require(
        row
        and (row["requester_id"] == uid or await support(conn, uid, row["queue_id"])),
        404,
        "NOT_FOUND",
        "Заявку не знайдено.",
    )
    return dict(row)


async def history(conn, t, uid, event, changes, stamp):
    await conn.execute(
        insert(s.history_events).values(
            id=uuid4(),
            ticket_id=t["id"],
            actor_id=uid,
            event_type=event,
            changes=changes,
            visibility="public",
            occurred_at=stamp,
        )
    )


async def interval(conn, t, state, stamp):
    await conn.execute(
        update(s.ticket_intervals)
        .where(
            s.ticket_intervals.c.ticket_id == t["id"],
            s.ticket_intervals.c.ended_at.is_(None),
        )
        .values(ended_at=stamp)
    )
    await conn.execute(
        insert(s.ticket_intervals).values(
            id=uuid4(),
            ticket_id=t["id"],
            state=state,
            started_at=stamp,
            ended_at=stamp if state == "closed" else None,
        )
    )


async def create(conn, uid, body, key):
    require("requester" in await roles(conn, uid))
    require(
        body.previousTicketId is None,
        422,
        "VALIDATION_ERROR",
        "Пов’язані заявки не входять до прототипу.",
    )
    normalized = body.model_dump(mode="json")
    hashed = digest(
        json.dumps(
            normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    )
    # Serialize creates by user; the key constraint is a second line of defence.
    await conn.execute(
        select(s.users.c.id).where(s.users.c.id == uid).with_for_update()
    )
    previous = (
        (
            await conn.execute(
                select(s.idempotency_keys).where(
                    s.idempotency_keys.c.user_id == uid,
                    s.idempotency_keys.c.operation_key == key,
                )
            )
        )
        .mappings()
        .first()
    )
    if previous:
        require(
            previous["request_digest"] == hashed,
            409,
            "IDEMPOTENCY_CONFLICT",
            "Ключ уже використано для іншого вмісту.",
        )
        return await ticket(conn, uid, previous["ticket_id"]), 200
    cat = (
        (
            await conn.execute(
                select(s.categories).where(s.categories.c.id == body.categoryId)
            )
        )
        .mappings()
        .first()
    )
    require(
        cat is not None,
        422,
        "INVALID_CATEGORY",
        "Категорія недоступна.",
        field="categoryId",
    )
    queue = (
        (
            await conn.execute(
                select(s.queues)
                .where(s.queues.c.id == cat["queue_id"])
                .with_for_update()
            )
        )
        .mappings()
        .first()
    )
    cat = (
        (
            await conn.execute(
                select(s.categories)
                .where(s.categories.c.id == body.categoryId)
                .with_for_update()
            )
        )
        .mappings()
        .one()
    )
    require(
        cat["active"] and queue["active"],
        422,
        "INVALID_CATEGORY",
        "Категорія недоступна.",
        field="categoryId",
    )
    policy = (
        (
            await conn.execute(
                select(s.sla_policies)
                .where(
                    s.sla_policies.c.category_id == body.categoryId,
                    s.sla_policies.c.priority == "normal",
                    s.sla_policies.c.active,
                )
                .with_for_update()
            )
        )
        .mappings()
        .first()
    )
    require(
        policy is not None,
        422,
        "INVALID_POLICY",
        "Для категорії не задано цілі строків.",
        field="categoryId",
    )
    stamp = now()
    values = dict(
        id=uuid4(),
        requester_id=uid,
        category_id=body.categoryId,
        queue_id=cat["queue_id"],
        title=body.title,
        description=body.description,
        priority="normal",
        state="new",
        policy_id=policy["id"],
        response_target_ms=policy["response_target_ms"],
        resolution_target_ms=policy["resolution_target_ms"],
        created_at=stamp,
        updated_at=stamp,
    )
    t = dict(
        (await conn.execute(insert(s.tickets).values(**values).returning(s.tickets)))
        .mappings()
        .one()
    )
    await interval(conn, t, "new", stamp)
    await history(
        conn, t, uid, "created", {"state": {"old": None, "new": "new"}}, stamp
    )
    await conn.execute(
        insert(s.idempotency_keys).values(
            user_id=uid,
            operation_key=key,
            request_digest=hashed,
            ticket_id=t["id"],
            created_at=stamp,
        )
    )
    return t, 201


def mutable(t, version):
    require(
        t["state"] != "closed",
        409,
        "INVALID_STATE",
        "Закрита заявка доступна лише для читання.",
    )
    require(
        t["version"] == version,
        409,
        "VERSION_CONFLICT",
        "Заявку вже змінено. Оновіть її дані.",
    )


async def save(conn, t, values, stamp):
    values.update(updated_at=stamp, version=t["version"] + 1)
    return dict(
        (
            await conn.execute(
                update(s.tickets)
                .where(s.tickets.c.id == t["id"], s.tickets.c.version == t["version"])
                .values(**values)
                .returning(s.tickets)
            )
        )
        .mappings()
        .one()
    )


async def assign(conn, uid, tid, body):
    visible = await ticket(conn, uid, tid)
    require(await member(conn, uid, visible["queue_id"], "coordinator"))
    await conn.execute(
        select(s.users.c.id)
        .where(s.users.c.id.in_([uid, body.assigneeId]))
        .order_by(s.users.c.id)
        .with_for_update()
    )
    await conn.execute(
        select(s.queues.c.id)
        .where(s.queues.c.id == visible["queue_id"])
        .with_for_update()
    )
    t = await ticket(conn, uid, tid, True)
    mutable(t, body.expectedVersion)
    require(
        t["state"] == "new",
        409,
        "INVALID_STATE",
        "Прототип підтримує лише перше призначення.",
    )
    active = (
        await conn.execute(
            select(s.users.c.active).where(s.users.c.id == body.assigneeId)
        )
    ).scalar()
    require(
        active and await member(conn, body.assigneeId, t["queue_id"], "specialist"),
        422,
        "INVALID_ASSIGNEE",
        "Виконавець недоступний у цій черзі.",
        field="assigneeId",
    )
    stamp = now()
    await interval(conn, t, "assigned", stamp)
    await history(
        conn,
        t,
        uid,
        "assigned",
        {
            "assigneeId": {"old": None, "new": str(body.assigneeId)},
            "state": {"old": "new", "new": "assigned"},
        },
        stamp,
    )
    return await save(
        conn,
        t,
        dict(assignee_id=body.assigneeId, state="assigned", first_assigned_at=stamp),
        stamp,
    )


async def add_message(conn, t, uid, body, kind, role, stamp):
    cid = uuid4()
    await conn.execute(
        insert(s.comments).values(
            id=cid,
            ticket_id=t["id"],
            author_id=uid,
            author_role=role,
            visibility="public",
            kind=kind,
            body=body,
            created_at=stamp,
        )
    )
    await history(
        conn, t, uid, "comment_added", {"commentId": str(cid), "kind": kind}, stamp
    )
    return cid


async def comment(conn, uid, tid, body):
    t = await ticket(conn, uid, tid, True)
    require(
        body.visibility == "public",
        403,
        "FORBIDDEN",
        "Внутрішні нотатки не входять до прототипу.",
    )
    mutable(t, body.expectedVersion)
    role = (
        "requester"
        if t["requester_id"] == uid
        else "specialist"
        if await member(conn, uid, t["queue_id"], "specialist")
        else "coordinator"
    )
    stamp = now()
    await add_message(conn, t, uid, body.body, "comment", role, stamp)
    values = {}
    if role != "requester" and t["first_response_at"] is None:
        values["first_response_at"] = stamp
    return await save(conn, t, values, stamp)


async def transition(conn, uid, tid, body):
    t = await ticket(conn, uid, tid, True)
    if body.toState == "closed":
        require(t["requester_id"] == uid)
    else:
        require(
            t["assignee_id"] == uid
            and await member(conn, uid, t["queue_id"], "specialist")
        )
    mutable(t, body.expectedVersion)
    require(
        (t["state"], body.toState)
        in [
            ("assigned", "in_progress"),
            ("in_progress", "resolved"),
            ("resolved", "closed"),
        ],
        409,
        "INVALID_STATE",
        "Перехід недоступний у прототипі.",
    )
    stamp = now()
    values = {"state": body.toState}
    if body.toState == "resolved":
        require(
            body.text is not None,
            422,
            "VALIDATION_ERROR",
            "Потрібен текст рішення.",
            field="text",
        )
        cid = await add_message(
            conn, t, uid, body.text, "solution", "specialist", stamp
        )
        values["solution_comment_id"] = cid
        if t["first_response_at"] is None:
            values["first_response_at"] = stamp
    if body.toState == "closed":
        require(
            body.solutionCommentId == t["solution_comment_id"],
            409,
            "SOLUTION_CONFLICT",
            "Підтвердіть поточне рішення.",
        )
    await interval(conn, t, body.toState, stamp)
    await history(
        conn,
        t,
        uid,
        "state_changed",
        {"state": {"old": t["state"], "new": body.toState}},
        stamp,
    )
    return await save(conn, t, values, stamp)


FIELDS = [
    "id",
    "number",
    "requester_id",
    "category_id",
    "queue_id",
    "assignee_id",
    "previous_ticket_id",
    "title",
    "description",
    "priority",
    "state",
    "response_target_ms",
    "resolution_target_ms",
    "created_at",
    "updated_at",
    "first_assigned_at",
    "first_response_at",
    "solution_comment_id",
    "version",
]


def camel(name):
    first, *parts = name.split("_")
    return first + "".join(p.title() for p in parts)


def present(row, fields):
    return {camel(k): row[k] for k in fields}


def ticket_view(t):
    return present(t, FIELDS)
