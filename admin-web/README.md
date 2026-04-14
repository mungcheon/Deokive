# Deokive Admin Web

Separated admin web for Deokive operations.

## Scope

- Admin login
- Dashboard summary
- User list
- Backup list
- Placeholder support and catalog panels

## Environment

Use `VITE_DEOKIVE_ADMIN_API_BASE_URL` to point at the FastAPI server.

Example:

```powershell
$env:VITE_DEOKIVE_ADMIN_API_BASE_URL="http://127.0.0.1:8000"
npm install
npm run dev
```

## Required backend env vars

```powershell
$env:BOOTSTRAP_ADMIN_EMAIL="admin"
$env:BOOTSTRAP_ADMIN_PASSWORD="admin"
```
