# Deokive Admin Platform Architecture

## Goal

Build a separate administrator product for operating Deokive across user accounts, backups, support, and future product catalog management.

## Separation Principles

- User app and admin web are separate clients.
- User API and admin API are separate namespaces.
- Admin authentication is separate from user authentication.
- Admin actions must be auditable.

## Recommended Topology

### User Clients

- Flutter Web
- Flutter macOS
- Flutter Android
- Flutter iOS

### Admin Client

- Separate web app
- Recommended stack: React + Vite or Next.js
- Reason: admin workflows are table-heavy and form-heavy

### Backend

- FastAPI
- User API namespace:
  - `/auth`
  - `/me`
  - `/backup`
- Admin API namespace:
  - `/admin-api/v1/auth`
  - `/admin-api/v1/dashboard`
  - `/admin-api/v1/users`
  - `/admin-api/v1/backups`
  - `/admin-api/v1/support`
  - `/admin-api/v1/catalog`

## Auth Model

### User Auth

- Local login: user JWT
- Google login: Google auth + app-side Drive backup
- Optional future improvement: server-issued user JWT after Google token verification

### Admin Auth

- Separate admin JWT secret
- Separate login route
- No shared tokens with user accounts
- Role-based access required

## Admin Roles

- `super_admin`
- `admin`
- `support_manager`
- `catalog_manager`
- `read_only_analyst`

## Initial Admin Capabilities

### Dashboard

- Total users
- Local users
- Google users
- Premium users
- Snapshot count
- Pending support count
- Catalog item count

### User Management

- Search and list users
- Inspect provider and profile info
- Inspect premium state
- Future:
  - suspend account
  - reset migration state
  - inspect login activity

### Backup Management

- List latest server snapshots
- Inspect uploaded time and payload size
- Future:
  - delete snapshot
  - force expiration
  - restore audit trail

### Support Management

- Ticket list
- Ticket status transitions
- Replies
- Future SLA dashboards

### Catalog Management

- Item list
- Brand / series taxonomy
- Barcode registry
- Publish / unpublish workflow

## Data Model Direction

### Current Admin Tables

- `admin_users`
- `admin_audit_logs`

### Existing User-Side Operational Tables

- `users`
- `profiles`
- `backup_snapshots`

### Planned Next Tables

- `support_tickets`
- `support_replies`
- `catalog_items`
- `catalog_series`
- `catalog_brands`
- `catalog_barcodes`
- `announcements`

## Backup Policy

### Google Accounts

- Source of truth for personal backup: Google Drive `appDataFolder`
- Server may store sync metadata later, but should not be the mandatory source

### Local Accounts

- Server snapshot is the migration bridge between devices
- Snapshot format should match the app payload format
- Add TTL and cleanup job before production

Recommended production policy:

- keep latest snapshot per user
- expire snapshots after 30 days of inactivity
- log all admin reads/deletes

## Admin Web Screens

### Phase 1

- Login
- Dashboard
- User list
- Backup list

### Phase 2

- User detail
- Backup detail
- Support queue
- Catalog item list

### Phase 3

- Catalog edit workflows
- Announcement management
- Audit log explorer

## Security Requirements

- Admin and user JWT secrets must remain separate
- Enforce HTTPS in deployed environments
- Add 2FA for privileged admin roles
- Add audit logs for destructive operations
- Never expose raw user backup payloads in bulk list APIs

## Current Backend Scaffold

Implemented in this repository:

- admin auth login/me
- admin dashboard summary
- admin users list
- admin backups list
- placeholder support and catalog endpoints
- optional bootstrap admin creation from env vars

## Required Next Steps

1. Add admin frontend app
2. Add admin audit logging on login and mutations
3. Add support ticket models and APIs
4. Add catalog models and APIs
5. Move production DB to PostgreSQL
6. Add snapshot retention cleanup job
