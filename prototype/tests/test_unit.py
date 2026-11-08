from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from app.contracts import CreateTicket, Login, Assignment
from app.security import hasher, verify, digest, LoginLimits
from app.main import serial
from app.errors import Problem
from app.services import mutable
from app.schema import metadata


def test_normalization_and_untrusted_fields():
    t = CreateTicket(title="  Друк  ", description=" Опис ", categoryId=uuid4())
    assert t.title == "Друк" and t.description == "Опис"
    with pytest.raises(ValidationError):
        CreateTicket(title=" ", description="x", categoryId=uuid4())
    with pytest.raises(ValidationError):
        CreateTicket(title="x", description="x", categoryId=uuid4(), owner="someone")


@pytest.mark.parametrize("text", ["a", "😀"])
def test_password_limits(text):
    assert len(Login(login="requester", password=text * 64).password) == 64
    with pytest.raises(ValidationError):
        Login(login="requester", password=text * 65)


def test_version_is_strict_integer():
    for value in [True, "1", 0, -1]:
        with pytest.raises(ValidationError):
            Assignment(expectedVersion=value, assigneeId=uuid4())


def test_argon_parameters_and_hashing():
    password = "синтетичний-пароль-" + str(uuid4())
    hashed = hasher.hash(password)
    assert "$argon2id$v=19$m=19456,t=2,p=1$" in hashed
    assert verify(hashed, password)
    assert not verify(hashed, password + "x")
    assert digest(password) != password


def test_throttle_has_bounded_fail_closed_state():
    limits = LoginLimits()
    for _ in range(10):
        limits.failure("requester", "local")
    assert limits.blocked("requester", "local")
    assert not limits.blocked("different", "local")
    limits.entries.update({str(i): (10**20, 0) for i in range(10000)})
    assert limits.blocked("unknown", "new")


def test_conflict_and_closed_are_rejected():
    with pytest.raises(Problem) as e:
        mutable({"state": "assigned", "version": 2}, 1)
    assert e.value.code == "VERSION_CONFLICT"
    with pytest.raises(Problem):
        mutable({"state": "closed", "version": 2}, 2)


def test_datetime_uses_contract_utc_suffix():
    assert (
        serial(datetime(2026, 11, 5, tzinfo=timezone.utc)) == "2026-11-05T00:00:00.000Z"
    )


def test_postgres_schema_compiles_and_excludes_full_scope():
    assert len(metadata.tables) == 13
    assert "notifications" not in metadata.tables
    for table in metadata.tables.values():
        assert str(CreateTable(table).compile(dialect=postgresql.dialect()))
    assert "uq_open_interval" in {
        i.name for t in metadata.tables.values() for i in t.indexes
    }


def test_optional_fields_reject_explicit_null():
    with pytest.raises(ValidationError):
        CreateTicket(
            title="x", description="x", categoryId=uuid4(), previousTicketId=None
        )
