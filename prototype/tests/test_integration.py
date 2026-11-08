"""Against the actual HTTPS Docker app; opt in with RUN_INTEGRATION=1."""

import os
import ssl
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="Requires running Docker prototype"
)
ROOT = Path(__file__).resolve().parents[1]
SPEC = yaml.safe_load((ROOT.parent / "api/openapi.yaml").read_text())


def settings():
    return dict(
        line.split("=", 1)
        for line in (ROOT / ".env").read_text().splitlines()
        if line and not line.startswith("#")
    )


def validate(name, data):
    schema = {"$ref": f"#/components/schemas/{name}", "components": SPEC["components"]}
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)


@pytest.fixture
def clients():
    env = settings()
    result = {}
    for login, key in [
        ("requester", "REQUESTER"),
        ("specialist", "SPECIALIST"),
        ("coordinator", "COORDINATOR"),
        ("administrator", "ADMIN"),
        ("other", "OTHER"),
    ]:
        c = httpx.Client(
            base_url=env["APP_ORIGIN"] + "/api/v1",
            verify=ssl.create_default_context(cafile=str(ROOT / ".local/tls/ca.crt")),
            headers={"Origin": env["APP_ORIGIN"]},
            timeout=15,
            trust_env=False,
        )
        response = c.post(
            "/session", json={"login": login, "password": env[f"DEMO_{key}_PASSWORD"]}
        )
        assert response.status_code == 200, response.text
        validate("Session", response.json())
        c.headers["X-CSRF-Token"] = response.json()["csrfToken"]
        result[login] = c
    yield result
    for c in result.values():
        c.close()


def create(c, key=None):
    categories = c.get("/categories")
    assert categories.status_code == 200
    body = {
        "title": "Навчальна заявка " + str(uuid4()),
        "description": "Синтетична перевірка",
        "categoryId": categories.json()["items"][0]["id"],
    }
    response = c.post(
        "/tickets", json=body, headers={"Idempotency-Key": key or str(uuid4())}
    )
    assert response.status_code == 201, response.text
    validate("Ticket", response.json())
    assert response.json()["state"] == "new"
    assert response.json()["priority"] == "normal"
    assert response.json()["responseTargetMs"] == 1800000
    assert response.json()["resolutionTargetMs"] == 7200000
    return response.json(), body


def test_end_to_end_and_access(clients):
    owner = clients["requester"]
    coord = clients["coordinator"]
    specialist = clients["specialist"]
    t, _ = create(owner)
    path = "/tickets/" + t["id"]
    for login in ["other", "administrator"]:
        response = clients[login].get(path)
        for suffix in ["/comments", "/history"]:
            assert clients[login].get(path + suffix).status_code == 404
        assert response.status_code == 404
        validate("Error", response.json())
        response = clients[login].get("/tickets")
        assert all(x["id"] != t["id"] for x in response.json()["items"])
        validate("TicketPage", response.json())
    forbidden = owner.post(
        path + "/assignment",
        json={"expectedVersion": t["version"], "assigneeId": t["requesterId"]},
    )
    assert forbidden.status_code == 403
    candidates = coord.get("/queues/" + t["queueId"] + "/assignees")
    validate("AssigneeChoices", candidates.json())
    specialist_session = specialist.get("/session").json()
    specialist.headers["X-CSRF-Token"] = specialist_session["csrfToken"]
    assigned = coord.post(
        path + "/assignment",
        json={
            "expectedVersion": t["version"],
            "assigneeId": specialist_session["userId"],
        },
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["createdAt"] == t["createdAt"]
    assert assigned.json()["responseTargetMs"] == t["responseTargetMs"]
    assert assigned.json()["resolutionTargetMs"] == t["resolutionTargetMs"]
    t = assigned.json()
    validate("Ticket", t)
    conflict = specialist.post(
        path + "/state", json={"expectedVersion": 1, "toState": "in_progress"}
    )
    assert conflict.status_code == 409
    started = specialist.post(
        path + "/state",
        json={"expectedVersion": t["version"], "toState": "in_progress"},
    )
    assert started.status_code == 200, started.text
    t = started.json()
    response = owner.post(
        path + "/comments",
        json={
            "expectedVersion": t["version"],
            "body": "Додатковий опис",
            "visibility": "public",
        },
    )
    assert response.status_code == 200, response.text
    t = response.json()
    assert t["firstResponseAt"] is None
    resolved = specialist.post(
        path + "/state",
        json={
            "expectedVersion": t["version"],
            "toState": "resolved",
            "text": "Роботу виконано.",
        },
    )
    assert resolved.status_code == 200, resolved.text
    t = resolved.json()
    assert t["firstResponseAt"] and t["solutionCommentId"]
    wrong = owner.post(
        path + "/state",
        json={
            "expectedVersion": t["version"],
            "toState": "closed",
            "solutionCommentId": str(uuid4()),
        },
    )
    assert wrong.status_code == 409
    closed = owner.post(
        path + "/state",
        json={
            "expectedVersion": t["version"],
            "toState": "closed",
            "solutionCommentId": t["solutionCommentId"],
        },
    )
    assert closed.status_code == 200, closed.text
    t = closed.json()
    assert t["state"] == "closed"
    validate("Ticket", t)
    assert (
        owner.post(
            path + "/comments",
            json={
                "expectedVersion": t["version"],
                "body": "Зміна",
                "visibility": "public",
            },
        ).status_code
        == 409
    )
    for suffix, schema in [("comments", "CommentPage"), ("history", "HistoryPage")]:
        r = owner.get(path + "/" + suffix)
        assert r.status_code == 200
        validate(schema, r.json())
        if suffix == "history":
            assigned_event = next(
                e for e in r.json()["items"] if e["eventType"] == "assigned"
            )
            assert assigned_event["actorId"] == "00000000-0000-4000-8000-000000000003"
            assert (
                assigned_event["changes"]["assigneeId"]["new"]
                == specialist_session["userId"]
            )
        if suffix == "comments":
            assert any(
                x["kind"] == "solution" and x["body"] == "Роботу виконано."
                for x in r.json()["items"]
            )
    validate("TicketPage", owner.get("/tickets").json())


def test_idempotency_concurrency(clients):
    c = clients["requester"]
    key = str(uuid4())
    t, body = create(c, key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(
            pool.map(
                lambda _: c.post(
                    "/tickets", json=body, headers={"Idempotency-Key": key}
                ),
                range(2),
            )
        )
    assert all(r.status_code == 200 and r.json()["id"] == t["id"] for r in replies)
    response = c.post(
        "/tickets",
        json={**body, "title": "Інший вміст"},
        headers={"Idempotency-Key": key},
    )
    assert response.status_code == 409
    assert len(c.get("/tickets/" + t["id"] + "/history").json()["items"]) == 1


def test_validation_csrf_and_session_revocation(clients):
    c = clients["requester"]
    t, body = create(c)
    r = c.post(
        "/tickets",
        json={**body, "state": "closed"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 422
    validate("Error", r.json())
    r = c.post(
        "/tickets",
        json={**body, "title": "  "},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 422
    r = c.post(
        "/tickets",
        json=body,
        headers={"Idempotency-Key": str(uuid4()), "X-CSRF-Token": "wrong"},
    )
    assert r.status_code == 403
    r = c.post(
        "/tickets",
        json=body,
        headers={"Idempotency-Key": str(uuid4()), "Origin": "https://wrong.invalid"},
    )
    assert r.status_code == 403
    old = c.cookies.get("support_session")
    assert c.delete("/session").status_code == 204
    c.cookies.set("support_session", old, domain="localhost.local", path="/")
    assert c.get("/session").status_code == 401


def test_own_ticket_support_and_public_projection(clients):
    c = clients["coordinator"]
    t, _ = create(c)
    path = "/tickets/" + t["id"]
    r = c.post(
        path + "/assignment",
        json={"expectedVersion": t["version"], "assigneeId": t["requesterId"]},
    )
    assert r.status_code == 200, r.text
    t = r.json()
    r = c.post(
        path + "/comments",
        json={
            "expectedVersion": t["version"],
            "body": "Внутрішня",
            "visibility": "internal",
        },
    )
    assert r.status_code == 403
    r = c.post(
        path + "/comments",
        json={
            "expectedVersion": t["version"],
            "body": "Публічна",
            "visibility": "public",
        },
    )
    assert r.status_code == 200
    t = r.json()
    assert t["firstResponseAt"] is None
    r = c.post(
        path + "/state",
        json={"expectedVersion": t["version"], "toState": "in_progress"},
    )
    assert r.status_code == 200
    t = r.json()
    r = c.post(
        path + "/state",
        json={
            "expectedVersion": t["version"],
            "toState": "resolved",
            "text": "Виконано особисто",
        },
    )
    assert r.status_code == 200
    t = r.json()
    assert t["firstResponseAt"] is not None


def test_invalid_transitions_and_empty_solution(clients):
    owner = clients["requester"]
    coord = clients["coordinator"]
    specialist = clients["specialist"]
    t, _ = create(owner)
    path = "/tickets/" + t["id"]
    candidates = coord.get("/queues/" + t["queueId"] + "/assignees").json()["items"]
    sid = next(x["id"] for x in candidates if x["displayName"] == "Спеціаліст")
    r = coord.post(
        path + "/assignment", json={"expectedVersion": t["version"], "assigneeId": sid}
    )
    assert r.status_code == 200
    t = r.json()
    history_before = owner.get(path + "/history").json()
    r = owner.post(
        path + "/state", json={"expectedVersion": t["version"], "toState": "closed"}
    )
    assert r.status_code == 409
    assert owner.get(path + "/history").json() == history_before
    r = specialist.post(
        path + "/state",
        json={"expectedVersion": t["version"], "toState": "in_progress"},
    )
    assert r.status_code == 200
    t = r.json()
    for who, body, expected in [
        (specialist, {"text": "  "}, 422),
        (specialist, {}, 422),
        (coord, {"text": "Чуже рішення"}, 403),
    ]:
        r = who.post(
            path + "/state",
            json={"expectedVersion": t["version"], "toState": "resolved", **body},
        )
        assert r.status_code == expected
        assert owner.get(path).json()["version"] == t["version"]
    r = specialist.post(
        path + "/state",
        json={
            "expectedVersion": t["version"],
            "toState": "resolved",
            "text": "Виконано",
        },
    )
    assert r.status_code == 200
    t = r.json()
    r = owner.post(
        path + "/state",
        json={
            "expectedVersion": t["version"],
            "toState": "closed",
            "solutionCommentId": t["solutionCommentId"],
        },
    )
    assert r.status_code == 200
    t = r.json()
    before = owner.get(path + "/history").json()
    assert (
        specialist.post(
            path + "/state",
            json={"expectedVersion": t["version"], "toState": "in_progress"},
        ).status_code
        == 409
    )
    assert owner.get(path + "/history").json() == before


def test_stale_change_does_not_add_history(clients):
    c = clients["requester"]
    t, _ = create(c)
    path = "/tickets/" + t["id"]
    body = {
        "expectedVersion": t["version"],
        "body": "Перша зміна",
        "visibility": "public",
    }
    a = c.post(path + "/comments", json=body)
    assert a.status_code == 200
    before = c.get(path + "/history").json()
    b = c.post(path + "/comments", json={**body, "body": "Застаріла зміна"})
    assert b.status_code == 409
    assert c.get(path).json() == a.json()
    assert c.get(path + "/history").json() == before


def sql(command):
    import subprocess

    completed = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "coursework_owner",
            "-d",
            settings()["DB_NAME"],
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
        ],
        cwd=ROOT,
        input=command,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout.strip()


def test_history_failure_rolls_back_whole_transaction(clients):
    c = clients["coordinator"]
    t, _ = create(c)
    path = "/tickets/" + t["id"]
    tid = t["id"]
    assigned = c.post(
        path + "/assignment",
        json={"expectedVersion": t["version"], "assigneeId": t["requesterId"]},
    )
    assert assigned.status_code == 200
    t = assigned.json()
    started = c.post(
        path + "/state",
        json={"expectedVersion": t["version"], "toState": "in_progress"},
    )
    assert started.status_code == 200
    t = started.json()
    before_history = c.get(path + "/history").json()
    sql(f"""CREATE FUNCTION test_history_failure() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN IF NEW.ticket_id='{tid}'::uuid THEN RAISE EXCEPTION 'Controlled history failure'; END IF; RETURN NEW; END $$;
    CREATE TRIGGER test_history_failure BEFORE INSERT ON history_events FOR EACH ROW EXECUTE FUNCTION test_history_failure();""")
    try:
        r = c.post(
            path + "/state",
            json={
                "expectedVersion": t["version"],
                "toState": "resolved",
                "text": "Має бути відкочено",
            },
        )
        assert r.status_code == 503, r.text
        validate("Error", r.json())
        assert c.get(path).json() == t
        assert c.get(path + "/history").json() == before_history
        assert c.get(path + "/comments").json()["items"] == []
    finally:
        sql(
            "DROP TRIGGER IF EXISTS test_history_failure ON history_events; DROP FUNCTION IF EXISTS test_history_failure();"
        )


def test_login_limits_cookie_rotation_and_current_permissions(clients):
    c = clients["other"]
    env = settings()
    r = c.get("/session")
    old = c.headers["X-CSRF-Token"]
    c.headers["X-CSRF-Token"] = r.json()["csrfToken"]
    r = c.post(
        "/tickets",
        json={},
        headers={"X-CSRF-Token": old, "Idempotency-Key": str(uuid4())},
    )
    assert r.status_code == 403
    # Temporary database changes are confined to a synthetic account and always reverted.
    sql("UPDATE users SET active=false WHERE login='other';")
    try:
        assert c.get("/session").status_code == 401
        r = c.post(
            "/session", json={"login": "other", "password": env["DEMO_OTHER_PASSWORD"]}
        )
        assert r.status_code == 401
    finally:
        sql("UPDATE users SET active=true WHERE login='other';")
    client = httpx.Client(
        base_url=env["APP_ORIGIN"] + "/api/v1",
        verify=ssl.create_default_context(cafile=str(ROOT / ".local/tls/ca.crt")),
        headers={"Origin": env["APP_ORIGIN"]},
        trust_env=False,
    )
    try:
        r = client.post(
            "/session", json={"login": "other", "password": env["DEMO_OTHER_PASSWORD"]}
        )
        assert r.status_code == 200
        header = r.headers["set-cookie"].lower()
        assert (
            "secure" in header
            and "httponly" in header
            and "samesite=strict" in header
            and "path=/" in header
        )
        client.headers["X-CSRF-Token"] = r.json()["csrfToken"]
        client.cookies.clear()
        assert client.get("/session").status_code == 401
    finally:
        client.close()


def test_history_survives_restart(clients):
    import subprocess

    c = clients["coordinator"]
    t, _ = create(c)
    path = "/tickets/" + t["id"]
    assigned = c.post(
        path + "/assignment",
        json={"expectedVersion": t["version"], "assigneeId": t["requesterId"]},
    )
    assert assigned.status_code == 200
    t = assigned.json()
    started = c.post(
        path + "/state",
        json={"expectedVersion": t["version"], "toState": "in_progress"},
    )
    assert started.status_code == 200
    t = started.json()
    r = c.post(
        path + "/comments",
        json={
            "expectedVersion": t["version"],
            "body": "Історія зберігається",
            "visibility": "public",
        },
    )
    assert r.status_code == 200
    before = c.get(path + "/history").json()
    subprocess.run(
        ["docker", "compose", "restart", "app", "db"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=60,
    )
    import time

    env = settings()
    context = ssl.create_default_context(cafile=str(ROOT / ".local/tls/ca.crt"))
    for _ in range(30):
        try:
            with httpx.Client(
                base_url=env["APP_ORIGIN"] + "/api/v1",
                verify=context,
                cookies=c.cookies,
                trust_env=False,
                timeout=3,
            ) as fresh:
                response = fresh.get(path + "/history")
                if response.status_code == 200:
                    assert response.json() == before
                    return
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    pytest.fail("History was not available after restart")
