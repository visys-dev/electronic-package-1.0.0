# Операції API

Контракт OpenAPI 3.1.1; базовий шлях /api/v1. Версія контракту 0.1.0. Ідентифікатори операцій сталі. Захист сеансу та CSRF задається контрактом; проєктні параметри деталізовано 05.11.2026 у security/session-policy.md, суміщення ролей — security/access-matrix.md. Це не підтвердження реалізації.

| ID | Метод | Шлях | Дозвіл | Вимога | Дія |
|---|---|---|---|---|---|
| API-LOGIN | POST | /session | Неавтентифікований користувач |  | Локальний вхід |
| API-ME | GET | /session | Активний користувач |  | Поточний сеанс |
| API-LOGOUT | DELETE | /session | Активний користувач |  | Відкликати поточний сеанс |
| API-01 | POST | /tickets | Заявник | US-01 | Створити заявку |
| API-02 | GET | /tickets | Заявник, спеціаліст, координатор | US-02 | Список доступних заявок |
| API-03 | GET | /tickets/{ticketId} | Власник або підтримка дозволеної черги | US-02 | Картка доступної заявки |
| API-04 | POST | /tickets/{ticketId}/assignment | Координатор своєї черги | US-03 | Призначити або перепризначити |
| API-05 | POST | /tickets/{ticketId}/priority | Координатор своєї черги | US-03 | Уточнити пріоритет |
| API-06 | POST | /tickets/{ticketId}/state | Призначений спеціаліст або власник згідно з переходом | US-04 | Виконати дозволений перехід |
| API-07 | POST | /tickets/{ticketId}/comments | Власник або підтримка дозволеної черги | US-05 | Додати повідомлення |
| API-08 | GET | /tickets/{ticketId}/comments | Власник або підтримка дозволеної черги | US-05 | Дозволені повідомлення |
| API-09 | GET | /tickets/{ticketId}/history | Власник або підтримка дозволеної черги | US-06 | Дозволена історія |
| API-10 | GET | /tickets/{ticketId}/timing | Спеціаліст або координатор дозволеної черги | US-07 | Поточні часові показники |
| API-11 | GET | /notifications | Заявник, спеціаліст, координатор | US-08 | Власні внутрішні сповіщення |
| API-12 | PUT | /notifications/{notificationId} | Адресат з актуальним доступом до заявки | US-08 | Позначити власне сповіщення прочитаним |
| API-13 | GET | /reports/tickets | Координатор своїх черг | US-09 | Поточне зведення |
| API-14 | GET | /categories | Заявник | US-01 | Категорії для створення |
| API-15 | GET | /queues/{queueId}/assignees | Координатор своєї черги | US-03 | Допустимі виконавці |
| API-ADMIN-USERS-LIST | GET | /admin/users | Адміністратор | US-10 | Адміністративний список users |
| API-ADMIN-USERS-CREATE | POST | /admin/users | Адміністратор | US-10 | Створити users |
| API-ADMIN-USERS-UPDATE | PUT | /admin/users/{userId} | Адміністратор | US-10 | Оновити users |
| API-ADMIN-QUEUES-LIST | GET | /admin/queues | Адміністратор | US-10 | Адміністративний список queues |
| API-ADMIN-QUEUES-CREATE | POST | /admin/queues | Адміністратор | US-10 | Створити queues |
| API-ADMIN-QUEUES-UPDATE | PUT | /admin/queues/{queueId} | Адміністратор | US-10 | Оновити queues |
| API-ADMIN-CATEGORIES-LIST | GET | /admin/categories | Адміністратор | US-10 | Адміністративний список categories |
| API-ADMIN-CATEGORIES-CREATE | POST | /admin/categories | Адміністратор | US-10 | Створити categories |
| API-ADMIN-CATEGORIES-UPDATE | PUT | /admin/categories/{categoryId} | Адміністратор | US-10 | Оновити categories |
| API-ADMIN-MEMBERS-LIST | GET | /admin/queues/{queueId}/memberships | Адміністратор | US-10 | Склад черги |
| API-ADMIN-MEMBERS-CREATE | POST | /admin/queues/{queueId}/memberships | Адміністратор | US-10 | Додати учасника черги |
| API-ADMIN-MEMBERS-UPDATE | PUT | /admin/queues/{queueId}/memberships/{membershipId} | Адміністратор | US-10 | Змінити активність членства |
| API-ADMIN-POLICIES-LIST | GET | /admin/policies | Адміністратор | US-10 | Редакції політик строків |
| API-ADMIN-POLICIES-CREATE | POST | /admin/policies | Адміністратор | US-10 | Створити нову редакцію політики |
| API-ADMIN-POLICIES-DEACTIVATE | POST | /admin/policies/{policyId}/deactivate | Адміністратор | US-10 | Деактивувати чинну політику |
