# Frappe CRM lead sync target — design

## Problem

The app currently only creates ERPNext `Lead` records from Indiamart enquiries. Sites running Frappe CRM (the `crm` app) instead of, or alongside, ERPNext's CRM module have no way to route Indiamart leads there. `CRM Lead` in Frappe CRM is a structurally different doctype (different field names, no address fields, no `notes` field, different Lead Source doctype) — it cannot reuse the ERPNext lead-creation function as-is.

## Investigated and rejected: Frappe CRM's `Lead Sync Source`

Frappe CRM ships a `Lead Sync Source` doctype (module `Lead Syncing`) that looks purpose-built for exactly this — a pluggable "sync leads from an external source" framework with background-sync scheduling. On inspection it is hardcoded to Facebook:

- `type` field: `Select`, options literally just `"Facebook"` (`crm/lead_syncing/doctype/lead_sync_source/lead_sync_source.json`)
- `_sync_leads()` (`lead_sync_source.py`): `if self.type == "Facebook" and self.access_token: ...` — no hook, no dispatch table, no extension point for a third-party `type`.

Plugging Indiamart into it would require patching Frappe CRM's own core doctype (Property Setter to add a Select option) and monkeypatching its controller method to add an `elif` branch — modifying another app's internals from within this app, fragile across `crm` app updates. Rejected in favor of keeping the new logic entirely inside `indiamart_erpnext_integration`.

## Design

### Settings (`Indiamart Settings`)

New fields:

| Fieldname | Type | Notes |
|---|---|---|
| `lead_sync_target` | Select (`ERPNext CRM`, `Frappe CRM`) | Default `ERPNext CRM` — existing installs keep current behavior unchanged. |
| `crm_direct_lead_source` | Link → `CRM Lead Source` | Shown only when `lead_sync_target == "Frappe CRM"` (`depends_on`). Equivalent of `direct_lead_source`. |
| `crm_buy_lead_source` | Link → `CRM Lead Source` | Same, equivalent of `buy_lead_source`. |
| `crm_call_lead_source` | Link → `CRM Lead Source` | Same, equivalent of `call_lead_source`. |

`default_lead_owner` (existing field, Link → User) is reused unchanged — `CRM Lead.lead_owner` is the same fieldname/type.

### New custom field

`CRM Lead-query_id_cf` (Data), added via the fixtures list in `hooks.py`, alongside the existing `Lead-query_id_cf` / `Lead-indiamart_section` custom fields. Used for idempotency exactly like the ERPNext path: detect if a CRM Lead already exists for this specific Indiamart query before creating a new one.

### Field mapping: Indiamart enquiry → CRM Lead

| Indiamart field | CRM Lead field | Notes |
|---|---|---|
| `SENDER_NAME` | `first_name` | Full name goes into `first_name` only, `last_name` left blank. No name-splitting heuristics — CRM Lead's display name derives from first/last regardless, and splitting "Shuaib Khan" style names reliably isn't worth the complexity for v1. |
| `SENDER_MOBILE` | `mobile_no` | Same fieldname as ERPNext path. |
| `SENDER_EMAIL` | `email` | Note: fieldname is `email`, not `email_id` like ERPNext's `Lead`. |
| `SENDER_COMPANY` | `organization` | Equivalent of ERPNext's `company_name`. |
| `QUERY_TYPE` (W/B/P) | `source` | Looked up from the new `crm_direct_lead_source` / `crm_buy_lead_source` / `crm_call_lead_source` settings, same W/B/P branching as the existing ERPNext logic. |
| — | `lead_owner` | From `Indiamart Settings.default_lead_owner`, same as ERPNext path. |
| `UNIQUE_QUERY_ID` | `query_id_cf` | New custom field, see above. |

**Not mapped (CRM Lead has no equivalent field):**
- Address (`SENDER_ADDRESS`, city, state, country, pincode) — `CRM Lead` has no address/geography fields at all. Dropped for this path.
- `notes` — `CRM Lead` has no free-text notes field. See below.

### Enquiry details → FCRM Note

Frappe CRM's mechanism for free-text notes on any document is a separate `FCRM Note` doctype (`title`, `content`, `reference_doctype`, `reference_docname` — a generic backlink, not a child table). On CRM Lead creation, create one `FCRM Note` with `reference_doctype="CRM Lead"`, `reference_docname=<new lead name>`, and `content` built from the same HTML block the ERPNext path already builds (product name, subject, message, query date, alternate email/mobile, Indiamart query ID).

### Dedup logic

Mirrors the existing ERPNext flow's matching order:

1. Match by `query_id_cf` (idempotency — this exact enquiry already synced).
2. Match by `mobile_no` (repeat customer, different enquiry).
3. Match by `email` (repeat customer, different enquiry).
4. No match — create a new `CRM Lead`.

On a repeat match (2 or 3), append a new `FCRM Note` to the existing CRM Lead with the new enquiry's details. **No Deal escalation** — the ERPNext path's behavior of auto-creating an `Opportunity` when a repeat lead is already `Converted`/`Quotation` stage does not apply here. `CRM Deal` escalation is out of scope for v1.

### Dispatch point

`indiamart_lead.py`: `IndiamartLead.after_insert()` and `IndiamartLead.retry_lead_creation()` currently call `make_erpnext_lead_from_inidamart` unconditionally. Both change to read `Indiamart Settings.lead_sync_target` and call either `make_erpnext_lead_from_inidamart` (existing, unchanged) or the new `make_frappe_crm_lead_from_indiamart`, based on that value.

### New function: `make_frappe_crm_lead_from_indiamart`

Lives in `indiamart_erpnext_controller.py`, alongside the existing `make_erpnext_lead_from_inidamart`. Same signature (`lead_values`, `indiamart_lead_name=None`), same error-handling pattern (try/except → `frappe.log_error` with the `Indiamart Error` title), same return-a-status-string-and-write-it-to-`Indiamart Lead.output`/`.status` behavior as the existing function, so `retry_lead_creation`'s success/failure messaging in the desk UI keeps working unchanged for both paths.

## Known gaps (not fixed in this feature, documented for later)

- The existing `public/js/lead.js` / `integration_request.js` sidebar badges (showing linked Indiamart Lead count) only work on the ERPNext desk UI. Frappe CRM has its own separate Vue frontend — there is no equivalent badge there in v1. A future enhancement could add a Frappe CRM UI extension for this, out of scope here.
- `crm` app must be installed on the site for the Frappe CRM target to work; no install-time validation is added to enforce this in v1 (selecting "Frappe CRM" as target on a site without `crm` installed will fail at lead-creation time with a clear error, not at settings-save time).

## Out of scope

- CRM Deal / Opportunity escalation for repeat Frappe CRM leads.
- Migrating/backfilling existing ERPNext Leads into Frappe CRM.
- UI badge equivalent for the Frappe CRM frontend.
- Supporting both targets simultaneously (single-select only, per user decision).
