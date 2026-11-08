"""Idempotent synthetic accounts and dictionaries; no ticket deletion or password reset."""

import os
from uuid import UUID
from sqlalchemy import create_engine, select, insert
from .config import database_url
from .security import hasher
from . import schema as s


def uid(n):
    return UUID(f"00000000-0000-4000-8000-{n:012d}")


ACCOUNTS = [
    (1, "requester", "Заявник", ["requester"], "DEMO_REQUESTER_PASSWORD"),
    (
        2,
        "specialist",
        "Спеціаліст",
        ["requester", "specialist"],
        "DEMO_SPECIALIST_PASSWORD",
    ),
    (
        3,
        "coordinator",
        "Координатор",
        ["requester", "coordinator", "specialist"],
        "DEMO_COORDINATOR_PASSWORD",
    ),
    (4, "administrator", "Адміністратор", ["administrator"], "DEMO_ADMIN_PASSWORD"),
    (5, "other", "Інший заявник", ["requester"], "DEMO_OTHER_PASSWORD"),
]


def seed():
    passwords = {name: os.environ[name] for *_, name in ACCOUNTS}
    if any(not 15 <= len(p) <= 64 for p in passwords.values()):
        raise ValueError("Demo passwords must contain 15–64 Unicode code points")
    engine = create_engine(database_url(), hide_parameters=True)
    with engine.begin() as conn:
        for code in ["requester", "specialist", "coordinator", "administrator"]:
            if (
                conn.execute(select(s.roles).where(s.roles.c.code == code)).first()
                is None
            ):
                conn.execute(insert(s.roles).values(code=code))
        for n, login, name, roles, password_var in ACCOUNTS:
            existing = conn.execute(
                select(s.users).where(s.users.c.id == uid(n))
            ).first()
            if existing is not None:
                continue
            conn.execute(
                insert(s.users).values(
                    id=uid(n),
                    login=login,
                    display_name=name,
                    credential_hash=hasher.hash(passwords[password_var]),
                )
            )
            for role in roles:
                conn.execute(
                    insert(s.user_roles).values(user_id=uid(n), role_code=role)
                )
        if (
            conn.execute(select(s.queues).where(s.queues.c.id == uid(201))).first()
            is None
        ):
            conn.execute(
                insert(s.queues).values(id=uid(201), name="Навчальна підтримка")
            )
            conn.execute(
                insert(s.categories).values(
                    id=uid(301), name="Робоче місце", queue_id=uid(201)
                )
            )
            conn.execute(
                insert(s.sla_policies).values(
                    id=uid(401),
                    category_id=uid(301),
                    priority="normal",
                    revision=1,
                    response_target_ms=1800000,
                    resolution_target_ms=7200000,
                )
            )
            for n, user, role in [
                (501, 2, "specialist"),
                (502, 3, "coordinator"),
                (503, 3, "specialist"),
            ]:
                conn.execute(
                    insert(s.queue_memberships).values(
                        id=uid(n),
                        user_id=uid(user),
                        queue_id=uid(201),
                        member_role=role,
                    )
                )
    engine.dispose()
    print(
        "Synthetic accounts and dictionaries initialized; existing records preserved."
    )


if __name__ == "__main__":
    seed()
