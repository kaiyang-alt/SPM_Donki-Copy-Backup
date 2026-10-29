# ConnectSphere Common Structure

This is a quick reference for the established application flow and canonical
repository locations.

## Application Flow

Frontend → Flask Route → Service / Business Logic → Supabase

## Canonical Paths

- Templates: `app/templates/`
- Static assets: `app/static/`
- Flask routes: `app/routes/`
- Business and service logic: `app/services/`
- Shared Supabase connection: `app/supabase_client.py`

Routes receive requests and delegate business decisions to services. Services
use the shared Supabase connection where persistence is required.

## Detailed References

| Document | Purpose |
| --- | --- |
| `docs/architecture/project_context.md` | Shared service/domain responsibilities and the current reconciled project baseline |
| `docs/architecture/database_schema.md` | Exact current approved/documented table, column, relationship and RLS structure |
| `docs/requirements/README.md` | Requirement precedence and customer-change process |
| `AGENTS.md` | Development and structural guardrails |

Do not use this quick reference as a second database catalogue. Consult the
documents above for approved detail.
