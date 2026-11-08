"""Optional browser smoke test; default requires a trusted local CA.
UI_TEST_PIN_CERT=1 confines a certificate-key exception to this disposable browser.
The HTTPS health check always validates the CA and hostname first.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import urllib.request
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
config = dict(
    line.split("=", 1)
    for line in (ROOT / ".env").read_text().splitlines()
    if line and not line.startswith("#")
)
url = config["APP_ORIGIN"]
ctx = ssl.create_default_context(cafile=str(ROOT / ".local/tls/ca.crt"))
with urllib.request.urlopen(url + "/health", context=ctx, timeout=5) as response:
    assert response.status == 200
args = []
if os.getenv("UI_TEST_PIN_CERT") == "1":
    pub = subprocess.run(
        [
            "openssl",
            "x509",
            "-in",
            str(ROOT / ".local/tls/server.crt"),
            "-pubkey",
            "-noout",
        ],
        capture_output=True,
        check=True,
    ).stdout
    der = subprocess.run(
        ["openssl", "pkey", "-pubin", "-outform", "DER"],
        input=pub,
        capture_output=True,
        check=True,
    ).stdout
    pin = base64.b64encode(hashlib.sha256(der).digest()).decode()
    args.append("--ignore-certificate-errors-spki-list=" + pin)

with sync_playwright() as p:
    browser = p.chromium.launch(args=args)
    contexts = []
    errors = []

    def login(name, password_key):
        context = browser.new_context(viewport={"width": 1280, "height": 960})
        contexts.append(context)
        page = context.new_page()
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.locator("#login input[name=login]").fill(name)
        page.locator("#login input[name=password]").fill("😀" * 64)
        expect(page.locator("#login input[name=password]")).to_have_value("😀" * 64)
        page.locator("#login input[name=password]").fill(config[password_key])
        page.locator("#login button").click()
        expect(page.locator("#workspace")).to_be_visible()
        return page

    owner = login("requester", "DEMO_REQUESTER_PASSWORD")
    owner.locator("#create input[name=title]").fill("   ")
    owner.locator("#create textarea").fill("Значення має зберегтися після помилки")
    owner.locator("#create button").click()
    expect(owner.locator("#create input[name=title]")).to_have_attribute(
        "aria-invalid", "true"
    )
    expect(owner.locator("#create input[name=title]")).to_be_focused()
    expect(owner.locator("#create textarea")).to_have_value(
        "Значення має зберегтися після помилки"
    )
    expect(owner.locator("#error-create-title")).to_be_visible()
    title = "Браузерна перевірка " + str(uuid4())
    owner.locator("#create input[name=title]").fill(title)
    owner.locator("#create textarea").fill(
        "Синтетичне звернення для перевірки трьох потоків."
    )
    owner.locator("#create button").click()
    expect(owner.locator("#ticket-heading")).to_contain_text(title)
    expect(owner.locator("#ticket-details")).to_contain_text("Нова")
    number = re.search(r"№(\d+)", owner.locator("#ticket-heading").inner_text()).group(
        1
    )
    coordinator = login("coordinator", "DEMO_COORDINATOR_PASSWORD")
    coordinator.get_by_role("button", name=re.compile(re.escape(title))).click()
    coordinator.locator("#assignment select").select_option(label="Спеціаліст")
    coordinator.locator("#assignment button").click()
    expect(coordinator.locator("#ticket-details")).to_contain_text("Призначена")
    specialist = login("specialist", "DEMO_SPECIALIST_PASSWORD")
    specialist.get_by_role("button", name=re.compile(re.escape(title))).click()
    specialist.locator("#start").click()
    expect(specialist.locator("#ticket-details")).to_contain_text("У роботі")
    specialist.locator("#solution textarea").fill(
        "Виконання перевірено через вебінтерфейс."
    )
    specialist.locator("#solution button").click()
    expect(specialist.locator("#ticket-details")).to_contain_text("Вирішена")
    owner.locator("#refresh").click()
    owner.locator("#tickets").get_by_role(
        "button", name=re.compile(re.escape(title))
    ).click()
    expect(owner.locator("#confirm")).to_be_visible()
    owner.locator("#confirm").click()
    expect(owner.locator("#ticket-details")).to_contain_text("Закрита")
    expect(owner.locator("#comment")).to_be_hidden()
    expect(owner.locator("#comments")).to_contain_text(
        "Виконання перевірено через вебінтерфейс."
    )
    assert not errors, errors
    output = ROOT.parent / "tests/evidence/2026-11-06"
    output.mkdir(parents=True, exist_ok=True)
    owner.locator("#card").screenshot(path=str(output / "ui-closed.png"))
    (output / "ui-smoke.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "flows": ["FLOW-01", "FLOW-02", "FLOW-03"],
                "ticketNumber": int(number),
                "browser": "Chromium headless",
                "certificateMode": "SPKI allowlist for disposable test only"
                if args
                else "normal trust store",
                "caAndHostnameValidatedBeforeBrowser": True,
                "javascriptErrors": len(errors),
                "fieldErrorAssociationAndDraftPreservation": "passed for blank title",
                "keyboardAccessibilityChecked": False,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    for context in contexts:
        context.close()
    browser.close()
print(
    "UI FLOW-01–FLOW-03 passed; screenshot and result saved. Keyboard accessibility is not assessed."
)
