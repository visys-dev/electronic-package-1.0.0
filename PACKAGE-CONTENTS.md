# Склад електронного пакета

Версія пакета — **1.0.0**, дата — **08.11.2026**. Версія прототипу — **0.1.0**.

Це окрема копія матеріалів із відносними шляхами. report/ містить лише шість додатків А–Е. Вступ, основні розділи й підрозділи, висновки, Word/PDF записки та презентацію не включено.

## Перевірений склад

- Специфікації, ADR, логічна модель даних, OpenAPI, макети, правила доступу, тести й первинні докази.
- Прототип із зафіксованими залежностями, конфігурацією Docker Compose, міграціями та скриптом генерації локальних налаштувань.
- Усі 31 аркуш Drawio та узгоджені окремі/групові копії. Сім новіших аркушів отримано через Drawio MCP без зміни їхнього вмісту та синхронізовано в копіях пакета.
- Наявні PNG, для яких підтверджено відповідність вбудованого XML редагованому джерелу (еквівалентні нульові координати не вважаються відмінністю). Старі SVG, дублікати й авторський файл-зразок не включено.
- Бібліографія та нотатки перевірки джерел, журнал допомоги ШІ.

## Графічні подання

Усі 31 аркуш мають актуальні PNG для перегляду. За дозволом користувача створено п’ять експортів: context-dfd, dfd-level0-interfaces, uml-state, erd-tickets та erd-events. Експорт виконано локальним Drawio viewer з Times New Roman, масштабом 2× і білим тлом. Шрифти використано тимчасово, до пакета їх не включено. Вбудований у кожен новий PNG XML точно відповідає джерелу; усі п’ять зображень переглянуто. Редаговані файли не змінені. Протокол — docs/validation-graphic-exports.json.

## Виключені матеріали

Не включено локальні .env, .local, private keys, бази й резервні копії, Docker volumes, .venv, кеші, __pycache__, .git, навички агента, AGENTS.md та робочі пам’ятки перенесення тексту у Word. Приклад prototype/.env.example не містить паролів. Реальні налаштування створюються лише на комп’ютері одержувача за README.

## Перевірка комплектування

Після виправлення ізоляції Compose 29 із 31 контрольних сум збігаються з історичними доказами 06.11.2026; змінено лише prototype/scripts/init_local.py та prototype/.env.example. Історичні докази залишено без змін; поточний склад перевіряється за SHA256SUMS. Фактичний повторний запуск підтверджено в docs/validation-compose-isolation.json. Перевірено синтаксис Python, наявність локальних Markdown-посилань, структуру всіх Drawio-копій і логічну модель (16 сутностей, 36 синтетичних рядків, 44 ненульові зовнішні посилання). На тимчасовій копії успішно виконано початкову й повторну ініціалізацію налаштувань, Docker Compose config та перевірку сертифіката для localhost. Під час початкової перевірки комплектування контейнери не запускалися; після виправлення ізоляції виконано окремий успішний запуск і вхід користувача. Вміст пакета перевірено на збіг із сімома локальними паролями та маркерами приватних ключів; збігів немає. Це перевірка комплектування, а не повний security-аудит чи повторне проходження TEST-01–TEST-39.

Первинні протоколи тестування залишено без змін. Датовані історичні записи в специфікаціях і журналах описують стан на дату запису. Прототип підтримує 13 із 33 операцій повного контракту. Завершено 11 із 39 планових випадків; окремо протокол містить 19 успішних pytest-перевірок.

## Файли

- `PACKAGE-CONTENTS.md`
- `README.md`
- `SHA256SUMS`
- `api/README.md`
- `api/examples/assignment-request.json`
- `api/examples/confirm-request.json`
- `api/examples/create-request.json`
- `api/examples/create-response.json`
- `api/examples/duplicate-key-error.json`
- `api/examples/empty-report.json`
- `api/examples/manifest.json`
- `api/examples/not-found-error.json`
- `api/examples/resolve-request.json`
- `api/examples/timing-response.json`
- `api/examples/validation-error.json`
- `api/examples/version-error.json`
- `api/openapi.yaml`
- `api/operations.md`
- `api/validation/README.md`
- `api/validation/password-length-2026-11-05.json`
- `api/validation/requirements.txt`
- `api/validation/result.json`
- `api/validation/validate_contract.py`
- `data/data-dictionary.md`
- `data/erd-events.png`
- `data/erd-tickets.png`
- `data/erd.drawio`
- `data/erd.png`
- `data/fixtures.json`
- `data/fixtures.md`
- `data/invariants.md`
- `data/model-validation.md`
- `data/model.json`
- `data/validate_model.py`
- `data/validation-result.json`
- `demo-scenario.md`
- `docs/acceptance-criteria.md`
- `docs/adr/ADR-01.md`
- `docs/adr/ADR-02.md`
- `docs/adr/ADR-03.md`
- `docs/adr/ADR-04.md`
- `docs/ai-usage.md`
- `docs/architecture.md`
- `docs/change-log.md`
- `docs/glossary.md`
- `docs/models/architecture.drawio`
- `docs/models/architecture.png`
- `docs/models/context-dfd.drawio`
- `docs/models/context-dfd.md`
- `docs/models/context-dfd.png`
- `docs/models/coursework-diagrams.drawio`
- `docs/models/dfd-level0-data.drawio`
- `docs/models/dfd-level0-data.png`
- `docs/models/dfd-level0-interfaces.drawio`
- `docs/models/dfd-level0-interfaces.png`
- `docs/models/dfd-level0.drawio`
- `docs/models/dfd-level1-data.drawio`
- `docs/models/dfd-level1-data.png`
- `docs/models/dfd-level1-interfaces.drawio`
- `docs/models/dfd-level1-interfaces.png`
- `docs/models/dfd-level1.drawio`
- `docs/models/dfd-level2-data.drawio`
- `docs/models/dfd-level2-data.png`
- `docs/models/dfd-level2-interfaces.drawio`
- `docs/models/dfd-level2-interfaces.png`
- `docs/models/dfd-level2.drawio`
- `docs/models/model-index.md`
- `docs/models/sequence-source.md`
- `docs/models/uml-sequence-errors.drawio`
- `docs/models/uml-sequence-errors.png`
- `docs/models/uml-sequence-main.drawio`
- `docs/models/uml-sequence-main.png`
- `docs/models/uml-sequence.drawio`
- `docs/models/uml-state.drawio`
- `docs/models/uml-state.png`
- `docs/models/uml-usecase-common.drawio`
- `docs/models/uml-usecase-common.png`
- `docs/models/uml-usecase-specific.drawio`
- `docs/models/uml-usecase-specific.png`
- `docs/models/uml-usecase.drawio`
- `docs/models/validation.md`
- `docs/prototype-scope.md`
- `docs/requirements.md`
- `docs/sources.md`
- `docs/traceability.md`
- `docs/validation-graphic-exports.json`
- `package.json`
- `prototype/.dockerignore`
- `prototype/.env.example`
- `prototype/.gitignore`
- `prototype/Dockerfile`
- `prototype/alembic.ini`
- `prototype/app/__init__.py`
- `prototype/app/config.py`
- `prototype/app/contracts.py`
- `prototype/app/db.py`
- `prototype/app/errors.py`
- `prototype/app/grants.py`
- `prototype/app/main.py`
- `prototype/app/schema.py`
- `prototype/app/security.py`
- `prototype/app/seed.py`
- `prototype/app/services.py`
- `prototype/app/static/app.js`
- `prototype/app/static/style.css`
- `prototype/app/templates/index.html`
- `prototype/compose.yaml`
- `prototype/docker/init-user.sh`
- `prototype/migrations/env.py`
- `prototype/migrations/schema_v1.py`
- `prototype/migrations/versions/0001_initial.py`
- `prototype/pyproject.toml`
- `prototype/requirements.lock.txt`
- `prototype/scripts/init_local.py`
- `prototype/scripts/ui_smoke.py`
- `prototype/tests/test_integration.py`
- `prototype/tests/test_unit.py`
- `prototype/uv.lock`
- `report/Додаток А Специфікація вимог.md`
- `report/Додаток Б Моделі процесів та архітектура.md`
- `report/Додаток В Дані та програмний інтерфейс.md`
- `report/Додаток Г Макети та правила доступу і захисту даних.md`
- `report/Додаток Д Тестові сценарії та результати перевірок.md`
- `report/Додаток Е Електронний пакет та використання ШІ.md`
- `security/access-matrix.md`
- `security/pii-policy.md`
- `security/session-policy.md`
- `security/threat-model.md`
- `tests/defects.md`
- `tests/evidence/2026-11-06/README.md`
- `tests/evidence/2026-11-06/code-sha256.json`
- `tests/evidence/2026-11-06/contract.json`
- `tests/evidence/2026-11-06/pytest.xml`
- `tests/evidence/2026-11-06/repro.json`
- `tests/evidence/2026-11-06/runtime.json`
- `tests/evidence/2026-11-06/ui-smoke.json`
- `tests/results.md`
- `tests/test-cases.md`
- `ux/accessibility-check.md`
- `ux/flows/README.md`
- `ux/flows/confirm-solution.drawio`
- `ux/flows/confirm-solution.png`
- `ux/flows/create-ticket.drawio`
- `ux/flows/create-ticket.png`
- `ux/flows/process-ticket.drawio`
- `ux/flows/process-ticket.png`
- `ux/forms.md`
- `ux/mockups/README.md`
- `ux/mockups/ui-01.drawio`
- `ux/mockups/ui-01.png`
- `ux/mockups/ui-02.drawio`
- `ux/mockups/ui-02.png`
- `ux/mockups/ui-03.drawio`
- `ux/mockups/ui-03.png`
- `ux/mockups/ui-04.drawio`
- `ux/mockups/ui-04.png`
- `ux/mockups/ui-05.drawio`
- `ux/mockups/ui-05.png`
- `ux/mockups/ui-06.drawio`
- `ux/mockups/ui-06.png`
- `ux/mockups/ui-07.drawio`
- `ux/mockups/ui-07.png`
- `ux/mockups/ui-08.drawio`
- `ux/mockups/ui-08.png`
- `ux/mockups/ui-09.drawio`
- `ux/mockups/ui-09.png`
- `ux/mockups/ui-10.drawio`
- `ux/mockups/ui-10.png`
- `ux/mockups/ui-11.drawio`
- `ux/mockups/ui-11.png`
- `ux/mockups/ui-12.drawio`
- `ux/mockups/ui-12.png`
- `verification.json`
- `Джерела/Database Design – 2nd Edition by Adrienne Watt.pdf`
- `Джерела/NIST.SP.800-160v1r1.pdf`
- `Джерела/Метадані джерел підрозділу 1.1.json`
- `Джерела/Метадані джерел підрозділу 1.2.json`
- `Джерела/Метадані джерел підрозділу 1.3.json`
- `Джерела/Перевірка джерел вступу.md`
- `Джерела/Перевірка джерел підрозділу 1.1.md`
- `Джерела/Перевірка джерел підрозділу 1.2.md`
- `Джерела/Перевірка джерел підрозділу 1.3.md`
- `Джерела/Перевірка джерел підрозділу 2.1.md`
- `Джерела/Перевірка джерел підрозділу 2.2.md`
- `Джерела/Перевірка джерел підрозділу 2.3.md`
- `Джерела/Перевірка джерел підрозділу 3.1.md`
- `Джерела/Проєктування ІС - КПІ.pdf`
- `Джерела/Проєктування ІС - Черкаський НУІБХ - Авраменко В.С., Авраменко А.С..pdf`
- `Джерела/Підстави підрозділу 3.2.md`
- `Джерела/Підстави підрозділу 3.3.md`
- `docs/validation-compose-isolation.json`
