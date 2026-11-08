"""Physical schema for the minimal prototype; full-project tables are excluded."""

from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Text,
    Boolean,
    BigInteger,
    Identity,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("login", Text, nullable=False, unique=True),
    Column("display_name", Text, nullable=False),
    Column("credential_hash", Text, nullable=False),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Column("version", BigInteger, nullable=False, server_default=text("1")),
    CheckConstraint("version >= 1"),
)

roles = Table(
    "roles",
    metadata,
    Column("code", Text, primary_key=True),
)

user_roles = Table(
    "user_roles",
    metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_user_roles_user_id", use_alter=False),
        primary_key=True,
    ),
    Column(
        "role_code",
        Text,
        ForeignKey("roles.code", name="fk_user_roles_role_code", use_alter=False),
        primary_key=True,
    ),
    Column("active", Boolean, nullable=False, server_default=text("true")),
)

queues = Table(
    "queues",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", Text, nullable=False),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Column("version", BigInteger, nullable=False, server_default=text("1")),
    CheckConstraint("version >= 1"),
)

queue_memberships = Table(
    "queue_memberships",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "queue_id",
        UUID(as_uuid=True),
        ForeignKey("queues.id", name="fk_queue_memberships_queue_id", use_alter=False),
        nullable=False,
    ),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_queue_memberships_user_id", use_alter=False),
        nullable=False,
    ),
    Column("member_role", Text, nullable=False),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Column("version", BigInteger, nullable=False, server_default=text("1")),
    CheckConstraint("version >= 1"),
)

categories = Table(
    "categories",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("name", Text, nullable=False),
    Column(
        "queue_id",
        UUID(as_uuid=True),
        ForeignKey("queues.id", name="fk_categories_queue_id", use_alter=False),
        nullable=False,
    ),
    Column("active", Boolean, nullable=False, server_default=text("true")),
    Column("version", BigInteger, nullable=False, server_default=text("1")),
    CheckConstraint("version >= 1"),
)

sla_policies = Table(
    "sla_policies",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey(
            "categories.id", name="fk_sla_policies_category_id", use_alter=False
        ),
        nullable=False,
    ),
    Column("priority", Text, nullable=False, server_default=text("'normal'")),
    Column("revision", BigInteger, nullable=False),
    CheckConstraint("revision >= 1"),
    Column("response_target_ms", BigInteger, nullable=False),
    CheckConstraint("response_target_ms > 0"),
    Column("resolution_target_ms", BigInteger, nullable=False),
    CheckConstraint("resolution_target_ms > 0"),
    Column("active", Boolean, nullable=False, server_default=text("true")),
)

tickets = Table(
    "tickets",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("number", BigInteger, Identity(), nullable=False, unique=True),
    CheckConstraint("number >= 1"),
    Column(
        "requester_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_tickets_requester_id", use_alter=False),
        nullable=False,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("categories.id", name="fk_tickets_category_id", use_alter=False),
        nullable=False,
    ),
    Column(
        "queue_id",
        UUID(as_uuid=True),
        ForeignKey("queues.id", name="fk_tickets_queue_id", use_alter=False),
        nullable=False,
    ),
    Column(
        "assignee_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_tickets_assignee_id", use_alter=False),
        nullable=True,
    ),
    Column(
        "previous_ticket_id",
        UUID(as_uuid=True),
        ForeignKey("tickets.id", name="fk_tickets_previous_ticket_id", use_alter=False),
        nullable=True,
    ),
    Column("title", Text, nullable=False),
    Column("description", Text, nullable=False),
    Column("priority", Text, nullable=False, server_default=text("'normal'")),
    Column("state", Text, nullable=False),
    Column(
        "policy_id",
        UUID(as_uuid=True),
        ForeignKey("sla_policies.id", name="fk_tickets_policy_id", use_alter=False),
        nullable=False,
    ),
    Column("response_target_ms", BigInteger, nullable=False),
    CheckConstraint("response_target_ms > 0"),
    Column("resolution_target_ms", BigInteger, nullable=False),
    CheckConstraint("resolution_target_ms > 0"),
    Column("created_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
    Column("updated_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
    Column("first_assigned_at", TIMESTAMP(timezone=True, precision=3), nullable=True),
    Column("first_response_at", TIMESTAMP(timezone=True, precision=3), nullable=True),
    Column(
        "solution_comment_id",
        UUID(as_uuid=True),
        ForeignKey(
            "comments.id", name="fk_tickets_solution_comment_id", use_alter=True
        ),
        nullable=True,
        unique=True,
    ),
    Column("response_breached", Boolean, nullable=False, server_default=text("false")),
    Column(
        "resolution_breached", Boolean, nullable=False, server_default=text("false")
    ),
    Column("version", BigInteger, nullable=False, server_default=text("1")),
    CheckConstraint("version >= 1"),
)

comments = Table(
    "comments",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "ticket_id",
        UUID(as_uuid=True),
        ForeignKey("tickets.id", name="fk_comments_ticket_id", use_alter=False),
        nullable=False,
    ),
    Column(
        "author_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_comments_author_id", use_alter=False),
        nullable=False,
    ),
    Column("author_role", Text, nullable=False),
    Column("visibility", Text, nullable=False),
    Column("kind", Text, nullable=False),
    Column("body", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
)

history_events = Table(
    "history_events",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "ticket_id",
        UUID(as_uuid=True),
        ForeignKey("tickets.id", name="fk_history_events_ticket_id", use_alter=False),
        nullable=False,
    ),
    Column(
        "actor_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_history_events_actor_id", use_alter=False),
        nullable=True,
    ),
    Column("event_type", Text, nullable=False),
    Column("visibility", Text, nullable=False),
    Column("changes", JSONB, nullable=False),
    Column("occurred_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
)

ticket_intervals = Table(
    "ticket_intervals",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "ticket_id",
        UUID(as_uuid=True),
        ForeignKey("tickets.id", name="fk_ticket_intervals_ticket_id", use_alter=False),
        nullable=False,
    ),
    Column("state", Text, nullable=False),
    Column("started_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
    Column("ended_at", TIMESTAMP(timezone=True, precision=3), nullable=True),
)

idempotency_keys = Table(
    "idempotency_keys",
    metadata,
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_idempotency_keys_user_id", use_alter=False),
        primary_key=True,
    ),
    Column("operation_key", UUID(as_uuid=True), primary_key=True),
    Column("request_digest", Text, nullable=False),
    Column(
        "ticket_id",
        UUID(as_uuid=True),
        ForeignKey("tickets.id", name="fk_idempotency_keys_ticket_id", use_alter=False),
        nullable=False,
    ),
    Column("created_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
)

sessions = Table(
    "sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "user_id",
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_sessions_user_id", use_alter=False),
        nullable=False,
    ),
    Column("token_digest", Text, nullable=False, unique=True),
    Column("csrf_digest", Text, nullable=False),
    Column("created_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
    Column("expires_at", TIMESTAMP(timezone=True, precision=3), nullable=False),
    Column("revoked_at", TIMESTAMP(timezone=True, precision=3), nullable=True),
)

UniqueConstraint(
    queue_memberships.c.queue_id,
    queue_memberships.c.user_id,
    queue_memberships.c.member_role,
)
UniqueConstraint(
    sla_policies.c.category_id, sla_policies.c.priority, sla_policies.c.revision
)
Index(
    "uq_active_policy",
    sla_policies.c.category_id,
    sla_policies.c.priority,
    unique=True,
    postgresql_where=sla_policies.c.active,
)
Index(
    "uq_open_interval",
    ticket_intervals.c.ticket_id,
    unique=True,
    postgresql_where=ticket_intervals.c.ended_at.is_(None),
)
ticket_intervals.append_constraint(
    CheckConstraint("ended_at IS NULL OR ended_at >= started_at")
)
sessions.append_constraint(CheckConstraint("expires_at > created_at"))
for table, fields in [
    (tickets, [("title", 150), ("description", 4000)]),
    (comments, [("body", 2000)]),
]:
    for field, maximum in fields:
        table.append_constraint(
            CheckConstraint(f"char_length(btrim({field})) BETWEEN 1 AND {maximum}")
        )
for table, field, values in [
    (roles, "code", "'requester','specialist','coordinator','administrator'"),
    (queue_memberships, "member_role", "'specialist','coordinator'"),
    (
        tickets,
        "state",
        "'new','assigned','in_progress','waiting_requester','resolved','closed'",
    ),
    (tickets, "priority", "'low','normal','high','critical'"),
    (comments, "visibility", "'public','internal'"),
    (history_events, "visibility", "'public','internal'"),
]:
    table.append_constraint(CheckConstraint(f"{field} IN ({values})"))
for table, fields in [
    (tickets, ("requester_id", "queue_id", "assignee_id")),
    (comments, ("ticket_id",)),
    (history_events, ("ticket_id",)),
    (sessions, ("user_id",)),
]:
    for field in fields:
        Index(f"ix_{table.name}_{field}", table.c[field])
