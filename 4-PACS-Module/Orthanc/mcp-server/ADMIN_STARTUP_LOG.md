MCP Server — Admin startup notes and fixes

This file records the startup log excerpt and quick admin dashboard notes.

Server startup excerpt (user-provided):

```
╔═══════════════════════════════════════════════════════════╗

║                                                           ║

║           MCP Server - SSO Gateway                        ║

║           Ubuntu Patient Care System                      ║

║                                                           ║

╚═══════════════════════════════════════════════════════════╝

🚀 Starting server...

📍 URL: http://0.0.0.0:8080

📚 API Docs: http://0.0.0.0:8080/docs

🔐 SSO Providers: Google, Microsoft

Press CTRL+C to stop

... (truncated) ...

INFO:     127.0.0.1:51634 - "GET /admin HTTP/1.1" 200 OK

INFO:     127.0.0.1:51634 - "GET /users HTTP/1.1" 307 Temporary Redirect

INFO:     127.0.0.1:51634 - "GET /users/ HTTP/1.1" 500 Internal Server Error

ERROR:    Exception in ASGI application

fastapi.exceptions.ResponseValidationError: 3 validation errors:
  {'type': 'string_type', 'loc': ('response', 0, 'hpcsa_number'), 'msg': 'Input should be a valid string', 'input': None}
  {'type': 'string_type', 'loc': ('response', 2, 'hpcsa_number'), 'msg': 'Input should be a valid string', 'input': None}
  {'type': 'string_type', 'loc': ('response', 3, 'hpcsa_number'), 'msg': 'Input should be a valid string', 'input': None}
```

Action taken in repository:

- Made the `hpcsa_number` field optional in the API response model to avoid Pydantic validation errors when the database contains NULL for that column.
  - File modified: `app/routes/users.py` (changed field to `Optional[str] = None`).

- Improved the admin dashboard UI (`static/admin-dashboard.html`) to match the login page theme and added a "System Modules" panel showing the four modules with online/offline status and quick "Open" links:
  1. Dictation: http://localhost:5443
  2. PACS: http://localhost:5000
  3. RIS: http://localhost:3000
  4. Medical Billing: http://localhost:5443

Notes on module checks:
- The dashboard performs a lightweight fetch() to each module using `mode: 'no-cors'` and a short timeout. Many services block cross-origin requests; the check assumes the service is online if the fetch does not throw an error. If you need a more accurate health-check, expose a /health endpoint on each module and call that from the MCP server (or implement server-side health checks).

How to verify locally:

1. Start MCP server:

```powershell
py run.py
```

2. Open the admin dashboard (as an admin user):

- http://localhost:8080/admin

3. Confirm the modules panel shows green dots for services that are up and red dots for offline.

4. Try the Users CRUD:

- GET /users — should return a JSON list without validation errors
- POST /users — create a user (email, name, role)
- PUT /users/{id} — update role

If you still see ResponseValidationError, check the database rows for NULLs in fields expected to be strings and either populate them or update response models to allow None.

Next steps (optional):
- Add server-side health endpoints and use the MCP server to aggregate statuses.
- Add role-management API integration to the UI for editing role permissions.
- Add unit tests for the users endpoints to catch schema issues early.
