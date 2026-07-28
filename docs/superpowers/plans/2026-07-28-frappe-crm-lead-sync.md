# Frappe CRM Lead Sync Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `indiamart_erpnext_integration` route new leads to either ERPNext's `Lead` doctype (existing behavior) or Frappe CRM's `CRM Lead` doctype, selected via a new setting.

**Architecture:** A new `lead_sync_target` Select field on the existing `Indiamart Settings` singleton controls dispatch. `indiamart_lead.py`'s `after_insert`/`retry_lead_creation` read that setting and call one of two sibling functions in `indiamart_erpnext_controller.py`: the existing `make_erpnext_lead_from_inidamart` (unchanged) or the new `make_frappe_crm_lead_from_indiamart`. The new function creates a `CRM Lead` with a field mapping appropriate to that doctype's schema, and writes enquiry details to a linked `FCRM Note` (Frappe CRM's generic notes doctype) since `CRM Lead` has no free-text notes field of its own.

**Tech Stack:** Frappe Framework v16, Frappe CRM (`crm` app), Python, `frappe.tests.IntegrationTestCase`.

## Global Constraints

- Existing installs must be unaffected: `lead_sync_target` defaults to `"ERPNext CRM"`.
- No `CRM Deal`/`Opportunity` escalation for the Frappe CRM path (out of scope per approved spec).
- No address-field mapping for `CRM Lead` (doctype has none).
- Dedup match order for `CRM Lead`: `query_id_cf` → `mobile_no` → `email`, identical order to the existing ERPNext path.
- Tests run against a dedicated test site, never the developer's working site.
- Spec: `docs/superpowers/specs/2026-07-28-frappe-crm-lead-sync-design.md`

---

## File Structure

| File | Change |
|---|---|
| `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_settings/indiamart_settings.json` | Add `lead_sync_target` Select field; add 3 new `crm_*_lead_source` Link fields; make existing `direct_lead_source`/`buy_lead_source`/`call_lead_source`/`default_opportunity_sales_stage` conditionally required instead of always-required. |
| `indiamart_erpnext_integration/fixtures/custom_field.json` | Add `CRM Lead-query_id_cf` custom field entry. |
| `indiamart_erpnext_integration/hooks.py` | Add `"CRM Lead-query_id_cf"` to the fixtures filter list. |
| `indiamart_erpnext_integration/indiamart_erpnext_controller.py` | Add `make_frappe_crm_lead_from_indiamart()` and helper `add_frappe_crm_note()`. |
| `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/indiamart_lead.py` | `after_insert`/`retry_lead_creation` dispatch on `lead_sync_target`. |
| `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_settings/test_indiamart_settings.py` | Tests for the new/changed settings fields. |
| `indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py` (new) | Tests for `make_frappe_crm_lead_from_indiamart`, dedup, and dispatch. |
| `README.md` | Document the new setting. |

---

### Task 1: Test site setup

**Files:** none (infrastructure only)

**Interfaces:** none — this task produces a site name (`indiamart-test.localhost`) that every later task's test commands target.

- [ ] **Step 1: Create the test site**

```bash
bench new-site indiamart-test.localhost --admin-password admin
```

Expected: site created without error (root password is already stored in `sites/common_site_config.json` from earlier setup, so no `--db-root-password` flag needed).

- [ ] **Step 2: Install all four required apps**

```bash
bench --site indiamart-test.localhost install-app erpnext
bench --site indiamart-test.localhost install-app crm
bench --site indiamart-test.localhost install-app indiamart_erpnext_integration
```

Expected: all three complete with `Updating DocTypes for ... 100%` and no traceback. (`frappe` is installed automatically as a dependency of the first app.)

- [ ] **Step 3: Verify the app installed cleanly**

```bash
bench --site indiamart-test.localhost list-apps
```

Expected output includes all four: `frappe`, `erpnext`, `crm`, `indiamart_erpnext_integration`.

- [ ] **Step 4: Verify the existing (empty) test suite runs clean**

```bash
bench --site indiamart-test.localhost run-tests --app indiamart_erpnext_integration
```

Expected: `OK` with 0 or more tests, no errors. This confirms the test site is a valid baseline before any code changes.

No commit for this task — it creates a local site, not a file change.

---

### Task 2: `Indiamart Settings` schema — `lead_sync_target` and CRM source fields

**Files:**
- Modify: `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_settings/indiamart_settings.json`
- Test: `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_settings/test_indiamart_settings.py`

**Interfaces:**
- Produces: `Indiamart Settings.lead_sync_target` (Select, values `"ERPNext CRM"` / `"Frappe CRM"`, default `"ERPNext CRM"`), `Indiamart Settings.crm_direct_lead_source` / `crm_buy_lead_source` / `crm_call_lead_source` (Link → `CRM Lead Source`). Every later task that reads `Indiamart Settings` relies on these exact fieldnames.

- [ ] **Step 1: Write the failing test**

Replace the stub file entirely:

```python
# Copyright (c) 2021, GreyCube Technologies and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestIndiamartSettings(IntegrationTestCase):
	def setUp(self):
		frappe.db.set_single_value("Indiamart Settings", "lead_sync_target", None)

	def test_lead_sync_target_defaults_to_erpnext_crm(self):
		settings = frappe.get_single("Indiamart Settings")
		self.assertEqual(settings.lead_sync_target, "ERPNext CRM")

	def test_erpnext_sources_required_only_for_erpnext_crm_target(self):
		settings = frappe.get_single("Indiamart Settings")
		settings.lead_sync_target = "Frappe CRM"
		settings.enabled = 0
		settings.glusr_mobile = "9999999999"
		settings.glusr_mobile_key = "dummy-key"
		settings.default_lead_owner = "Administrator"
		settings.direct_lead_source = None
		settings.buy_lead_source = None
		settings.call_lead_source = None
		settings.default_opportunity_sales_stage = None
		# Should not raise MandatoryError: these fields are ERPNext-CRM-only now.
		settings.save()

	def test_erpnext_sources_still_required_for_erpnext_crm_target(self):
		settings = frappe.get_single("Indiamart Settings")
		settings.lead_sync_target = "ERPNext CRM"
		settings.enabled = 0
		settings.glusr_mobile = "9999999999"
		settings.glusr_mobile_key = "dummy-key"
		settings.default_lead_owner = "Administrator"
		settings.direct_lead_source = None
		settings.buy_lead_source = None
		settings.call_lead_source = None
		settings.default_opportunity_sales_stage = None
		self.assertRaises(frappe.MandatoryError, settings.save)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.indiamart_erpnext_integration.doctype.indiamart_settings.test_indiamart_settings -v
```

Expected: `test_lead_sync_target_defaults_to_erpnext_crm` fails with `AttributeError` (field doesn't exist yet); the other two fail or error because `lead_sync_target` isn't a real field.

- [ ] **Step 3: Edit `indiamart_settings.json`**

Replace `field_order`:

```json
 "field_order": [
  "api_access_detail_section",
  "enabled",
  "lead_sync_target",
  "last_api_call_time",
  "column_break_2",
  "glusr_mobile",
  "glusr_mobile_key",
  "section_break_4",
  "default_lead_owner",
  "default_opportunity_sales_stage",
  "column_break_5",
  "direct_lead_source",
  "buy_lead_source",
  "call_lead_source",
  "crm_direct_lead_source",
  "crm_buy_lead_source",
  "crm_call_lead_source"
 ],
```

Add a new field right after the `"enabled"` field entry in the `fields` array:

```json
  {
   "default": "ERPNext CRM",
   "description": "Which CRM new Indiamart leads are synced into.",
   "fieldname": "lead_sync_target",
   "fieldtype": "Select",
   "label": "Lead Sync Target",
   "options": "ERPNext CRM\nFrappe CRM",
   "reqd": 1
  },
```

Change the three existing source fields — replace their `"reqd": 1` line with `depends_on`/`mandatory_depends_on`:

```json
  {
   "depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "description": "QType: W (Direct) ",
   "fieldname": "direct_lead_source",
   "fieldtype": "Link",
   "label": "Direct Lead Source",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "options": "UTM Source"
  },
  {
   "depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "description": "QType: B  (Consumed Buylead)",
   "fieldname": "buy_lead_source",
   "fieldtype": "Link",
   "label": "Buy Lead Source",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "options": "UTM Source"
  },
  {
   "depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "description": "QType: P (CALL)",
   "fieldname": "call_lead_source",
   "fieldtype": "Link",
   "label": "CALL Lead Source",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "options": "UTM Source"
  },
```

Change `default_opportunity_sales_stage` the same way — replace `"reqd": 1` with the same `depends_on`/`mandatory_depends_on` pair:

```json
  {
   "depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "description": "When an existing lead is updated, an opportunity gets created based on lead status. \nDefine  default opportunity sales stage for such lead",
   "fieldname": "default_opportunity_sales_stage",
   "fieldtype": "Link",
   "label": "Default Opportunity Sales Stage",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"ERPNext CRM\"",
   "options": "Sales Stage"
  },
```

Add the three new CRM fields (place them after `call_lead_source` in the `fields` array, matching `field_order`):

```json
  {
   "depends_on": "eval:doc.lead_sync_target==\"Frappe CRM\"",
   "description": "QType: W (Direct) ",
   "fieldname": "crm_direct_lead_source",
   "fieldtype": "Link",
   "label": "CRM Direct Lead Source",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"Frappe CRM\"",
   "options": "CRM Lead Source"
  },
  {
   "depends_on": "eval:doc.lead_sync_target==\"Frappe CRM\"",
   "description": "QType: B  (Consumed Buylead)",
   "fieldname": "crm_buy_lead_source",
   "fieldtype": "Link",
   "label": "CRM Buy Lead Source",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"Frappe CRM\"",
   "options": "CRM Lead Source"
  },
  {
   "depends_on": "eval:doc.lead_sync_target==\"Frappe CRM\"",
   "description": "QType: P (CALL)",
   "fieldname": "crm_call_lead_source",
   "fieldtype": "Link",
   "label": "CRM CALL Lead Source",
   "mandatory_depends_on": "eval:doc.lead_sync_target==\"Frappe CRM\"",
   "options": "CRM Lead Source"
  },
```

- [ ] **Step 4: Migrate the test site**

```bash
bench --site indiamart-test.localhost migrate
```

Expected: completes without error, `Updating DocTypes for indiamart_erpnext_integration` reaches 100%.

- [ ] **Step 5: Run tests to verify they pass**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.indiamart_erpnext_integration.doctype.indiamart_settings.test_indiamart_settings -v
```

Expected: all 3 tests `OK`.

- [ ] **Step 6: Commit**

```bash
git add indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_settings/indiamart_settings.json indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_settings/test_indiamart_settings.py
git commit -m "feat: add lead_sync_target and CRM lead source settings"
```

---

### Task 3: `CRM Lead-query_id_cf` custom field

**Files:**
- Modify: `indiamart_erpnext_integration/fixtures/custom_field.json`
- Modify: `indiamart_erpnext_integration/hooks.py`

**Interfaces:**
- Consumes: none.
- Produces: `CRM Lead.query_id_cf` (Data field). Task 4's dedup logic and Task 5's tests rely on this field existing on `CRM Lead`.

- [ ] **Step 1: Write the failing test**

Create `indiamart_erpnext_integration/tests/__init__.py` (empty, makes the directory a package) and `indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py`:

```python
# Copyright (c) 2026, OneBook-ERP and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestCrmLeadQueryIdField(IntegrationTestCase):
	def test_crm_lead_has_query_id_cf_field(self):
		meta = frappe.get_meta("CRM Lead")
		self.assertTrue(meta.has_field("query_id_cf"))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.tests.test_frappe_crm_lead_sync -v
```

Expected: FAIL — `meta.has_field("query_id_cf")` is `False`.

- [ ] **Step 3: Add the custom field fixture**

Append to the array in `indiamart_erpnext_integration/fixtures/custom_field.json` (add a comma after the existing last `}` before this new object):

```json
 {
  "allow_in_quick_entry": 0,
  "allow_on_submit": 0,
  "bold": 0,
  "collapsible": 0,
  "collapsible_depends_on": null,
  "columns": 0,
  "default": null,
  "depends_on": null,
  "description": null,
  "docstatus": 0,
  "doctype": "Custom Field",
  "dt": "CRM Lead",
  "fetch_from": null,
  "fetch_if_empty": 0,
  "fieldname": "query_id_cf",
  "fieldtype": "Data",
  "hidden": 0,
  "hide_border": 0,
  "hide_days": 0,
  "hide_seconds": 0,
  "ignore_user_permissions": 0,
  "ignore_xss_filter": 0,
  "in_global_search": 0,
  "in_list_view": 0,
  "in_preview": 0,
  "in_standard_filter": 0,
  "insert_after": "source",
  "label": "Indiamart Query ID",
  "length": 0,
  "mandatory_depends_on": null,
  "modified": "2026-07-28 00:00:00.000000",
  "name": "CRM Lead-query_id_cf",
  "no_copy": 0,
  "non_negative": 0,
  "options": null,
  "parent": null,
  "parentfield": null,
  "parenttype": null,
  "permlevel": 0,
  "precision": "",
  "print_hide": 0,
  "print_hide_if_no_value": 0,
  "print_width": null,
  "read_only": 1,
  "read_only_depends_on": null,
  "report_hide": 0,
  "reqd": 0,
  "search_index": 0,
  "translatable": 0,
  "unique": 0,
  "width": null
 }
```

- [ ] **Step 4: Update `hooks.py`'s fixtures filter**

In `indiamart_erpnext_integration/hooks.py`, change:

```python
fixtures = [
      {
        "dt": "Custom Field", 
        "filters": [["name", "in", ["Lead-indiamart_section","Lead-query_id_cf"	]]]
      }
]
```

to:

```python
fixtures = [
      {
        "dt": "Custom Field", 
        "filters": [["name", "in", ["Lead-indiamart_section","Lead-query_id_cf","CRM Lead-query_id_cf"	]]]
      }
]
```

- [ ] **Step 5: Migrate the test site**

```bash
bench --site indiamart-test.localhost migrate
```

Expected: completes without error.

- [ ] **Step 6: Run test to verify it passes**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.tests.test_frappe_crm_lead_sync -v
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add indiamart_erpnext_integration/fixtures/custom_field.json indiamart_erpnext_integration/hooks.py indiamart_erpnext_integration/tests/__init__.py indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py
git commit -m "feat: add CRM Lead-query_id_cf custom field fixture"
```

---

### Task 4: `make_frappe_crm_lead_from_indiamart` — new lead creation

**Files:**
- Modify: `indiamart_erpnext_integration/indiamart_erpnext_controller.py`
- Test: `indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py`

**Interfaces:**
- Consumes: `Indiamart Settings.lead_sync_target`, `.default_lead_owner`, `.crm_direct_lead_source`, `.crm_buy_lead_source`, `.crm_call_lead_source` (from Task 2); `CRM Lead.query_id_cf` (from Task 3).
- Produces: `make_frappe_crm_lead_from_indiamart(lead_values: dict, indiamart_lead_name: str | None = None) -> str | None` — same signature and return contract as the existing `make_erpnext_lead_from_inidamart`: returns a human-readable status string, or `None` on an internally-caught exception (logged via `frappe.log_error`). Also produces `add_frappe_crm_note(crm_lead_name: str, content: str) -> str` (returns the new `FCRM Note` name). Task 5 (dedup) and Task 6 (dispatch) both call `make_frappe_crm_lead_from_indiamart` by this exact name.

- [ ] **Step 1: Write the failing test**

Add to `indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py`:

```python
class TestMakeFrappeCrmLeadFromIndiamart(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("CRM Lead Source", "Indiamart Direct"):
			frappe.get_doc({
				"doctype": "CRM Lead Source",
				"source_name": "Indiamart Direct",
			}).insert()

		settings = frappe.get_single("Indiamart Settings")
		settings.lead_sync_target = "Frappe CRM"
		settings.default_lead_owner = "Administrator"
		settings.crm_direct_lead_source = "Indiamart Direct"
		settings.crm_buy_lead_source = "Indiamart Direct"
		settings.crm_call_lead_source = "Indiamart Direct"
		settings.save()

	def sample_lead_values(self, **overrides):
		values = {
			"UNIQUE_QUERY_ID": "TEST-QID-0001",
			"QUERY_TYPE": "W",
			"QUERY_TIME": "2026-07-28 10:00:00",
			"SENDER_NAME": "Test Sender",
			"SENDER_MOBILE": "+91-9000000001",
			"SENDER_EMAIL": "sender@example.com",
			"SENDER_COMPANY": "Test Co",
			"QUERY_PRODUCT_NAME": "Widget",
			"QUERY_MESSAGE": "I want to buy Widget.",
		}
		values.update(overrides)
		return values

	def test_creates_crm_lead_with_mapped_fields(self):
		from indiamart_erpnext_integration.indiamart_erpnext_controller import (
			make_frappe_crm_lead_from_indiamart,
		)

		output = make_frappe_crm_lead_from_indiamart(self.sample_lead_values())

		self.assertIsNotNone(output)
		crm_lead_name = frappe.db.get_value("CRM Lead", {"query_id_cf": "TEST-QID-0001"})
		self.assertIsNotNone(crm_lead_name)

		crm_lead = frappe.get_doc("CRM Lead", crm_lead_name)
		self.assertEqual(crm_lead.first_name, "Test Sender")
		self.assertEqual(crm_lead.mobile_no, "+91-9000000001")
		self.assertEqual(crm_lead.email, "sender@example.com")
		self.assertEqual(crm_lead.organization, "Test Co")
		self.assertEqual(crm_lead.source, "Indiamart Direct")
		self.assertEqual(crm_lead.lead_owner, "Administrator")

	def test_creates_fcrm_note_with_enquiry_details(self):
		from indiamart_erpnext_integration.indiamart_erpnext_controller import (
			make_frappe_crm_lead_from_indiamart,
		)

		make_frappe_crm_lead_from_indiamart(self.sample_lead_values(UNIQUE_QUERY_ID="TEST-QID-0002"))

		crm_lead_name = frappe.db.get_value("CRM Lead", {"query_id_cf": "TEST-QID-0002"})
		notes = frappe.get_all(
			"FCRM Note",
			filters={"reference_doctype": "CRM Lead", "reference_docname": crm_lead_name},
			fields=["content"],
		)
		self.assertEqual(len(notes), 1)
		self.assertIn("Widget", notes[0].content)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.tests.test_frappe_crm_lead_sync -v
```

Expected: both new tests FAIL with `ImportError: cannot import name 'make_frappe_crm_lead_from_indiamart'`.

- [ ] **Step 3: Implement the function**

Add to `indiamart_erpnext_integration/indiamart_erpnext_controller.py` (after `make_erpnext_lead_from_inidamart`, before `update_existing_lead`):

```python
def add_frappe_crm_note(crm_lead_name, content):
	note = frappe.new_doc('FCRM Note')
	note.update({
		"title": "Indiamart Enquiry",
		"content": content,
		"reference_doctype": "CRM Lead",
		"reference_docname": crm_lead_name
	})
	note.insert(ignore_permissions=True)
	return note.name


def make_frappe_crm_lead_from_indiamart(lead_values, indiamart_lead_name=None):
	try:
		output = None
		user = frappe.db.get_single_value('Indiamart Settings', 'default_lead_owner')
		email_id = lead_values.get('SENDER_EMAIL', None)
		mobile_no = lead_values.get('SENDER_MOBILE', None)

		notes_html = "<div>Product Name :{0}</div><div>Subject :{1}</div><div>Message :{2}</div><div>Lead Date :{3}</div><div>Alternate EmailID :{4}</div><div>Alternate Mobile :{5}</div><div>India Mart Query ID :{6}</div>" \
			.format(
				frappe.bold(lead_values.get('QUERY_PRODUCT_NAME', 'Not specified')),
				frappe.bold(lead_values.get('SUBJECT', 'Not specified')),
				frappe.bold(lead_values.get('QUERY_MESSAGE', 'Not specified')),
				frappe.bold(lead_values.get('QUERY_TIME', 'Not specified')),
				frappe.bold(lead_values.get('EMAIL_ALT', 'Not specified')),
				frappe.bold(lead_values.get('MOBILE_ALT', 'Not specified')),
				frappe.bold(lead_values.get('UNIQUE_QUERY_ID', 'Not specified'))
			)

		crm_lead_name = frappe.db.get_value("CRM Lead", {"query_id_cf": lead_values.get('UNIQUE_QUERY_ID')})

		if not crm_lead_name and mobile_no:
			crm_lead_name = frappe.db.get_value("CRM Lead", {"mobile_no": mobile_no})

		if not crm_lead_name and email_id:
			crm_lead_name = frappe.db.get_value("CRM Lead", {"email": email_id})

		if crm_lead_name:
			add_frappe_crm_note(crm_lead_name, notes_html)
			output = 'Note added to existing CRM Lead {0}.'.format(crm_lead_name)
			if indiamart_lead_name:
				frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'output', output)
				frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'status', 'Completed')
			return output

		if lead_values.get('QUERY_TYPE') == 'W':
			source = frappe.db.get_single_value('Indiamart Settings', 'crm_direct_lead_source')
		elif lead_values.get('QUERY_TYPE') == 'B':
			source = frappe.db.get_single_value('Indiamart Settings', 'crm_buy_lead_source')
		elif lead_values.get('QUERY_TYPE') == 'P':
			source = frappe.db.get_single_value('Indiamart Settings', 'crm_call_lead_source')
		else:
			source = None

		crm_lead = frappe.new_doc('CRM Lead')
		crm_lead.update({
			"first_name": lead_values.get('SENDER_NAME'),
			"email": email_id,
			"mobile_no": mobile_no,
			"organization": lead_values.get('SENDER_COMPANY'),
			"source": source or '',
			"lead_owner": user,
			"query_id_cf": lead_values.get('UNIQUE_QUERY_ID')
		})
		crm_lead.flags.ignore_mandatory = True
		crm_lead.flags.ignore_permissions = True
		crm_lead.insert()

		add_frappe_crm_note(crm_lead.name, notes_html)

		output = 'CRM Lead {0} is created.'.format(crm_lead.name)
		if indiamart_lead_name:
			frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'output', output)
			frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'status', 'Completed')
		return output
	except Exception as e:
		title = _('Indiamart Error')
		seperator = "--" * 50
		error = "\n".join([
			format_datetime(now_datetime(), 'd-MMM-y  HH:mm:ss'),
			"make_frappe_crm_lead_from_indiamart",
			"indiamart_lead_name  " + (indiamart_lead_name or ''),
			str(sys.exc_info()[1]),
			seperator,
			frappe.get_traceback()
		])
		frappe.log_error(message=error, title=title)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.tests.test_frappe_crm_lead_sync -v
```

Expected: both tests `OK`.

- [ ] **Step 5: Commit**

```bash
git add indiamart_erpnext_integration/indiamart_erpnext_controller.py indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py
git commit -m "feat: create CRM Lead from Indiamart enquiries"
```

---

### Task 5: Dedup — `query_id_cf`, `mobile_no`, `email` matching

**Files:**
- Test: `indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py`
- No production code changes — this task verifies behavior already implemented in Task 4's dedup branch.

**Interfaces:**
- Consumes: `make_frappe_crm_lead_from_indiamart` (Task 4).

- [ ] **Step 1: Write the tests**

Add to `indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py`:

```python
class TestFrappeCrmLeadDedup(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("CRM Lead Source", "Indiamart Direct"):
			frappe.get_doc({
				"doctype": "CRM Lead Source",
				"source_name": "Indiamart Direct",
			}).insert()

		settings = frappe.get_single("Indiamart Settings")
		settings.lead_sync_target = "Frappe CRM"
		settings.default_lead_owner = "Administrator"
		settings.crm_direct_lead_source = "Indiamart Direct"
		settings.crm_buy_lead_source = "Indiamart Direct"
		settings.crm_call_lead_source = "Indiamart Direct"
		settings.save()

	def sample_lead_values(self, **overrides):
		values = {
			"UNIQUE_QUERY_ID": "TEST-QID-DEDUP-0001",
			"QUERY_TYPE": "W",
			"QUERY_TIME": "2026-07-28 10:00:00",
			"SENDER_NAME": "Dedup Sender",
			"SENDER_MOBILE": "+91-9000000099",
			"SENDER_EMAIL": "dedup@example.com",
			"SENDER_COMPANY": "Dedup Co",
			"QUERY_PRODUCT_NAME": "Widget",
			"QUERY_MESSAGE": "First enquiry.",
		}
		values.update(overrides)
		return values

	def test_same_query_id_does_not_create_second_lead(self):
		from indiamart_erpnext_integration.indiamart_erpnext_controller import (
			make_frappe_crm_lead_from_indiamart,
		)

		make_frappe_crm_lead_from_indiamart(self.sample_lead_values())
		make_frappe_crm_lead_from_indiamart(self.sample_lead_values())

		count = frappe.db.count("CRM Lead", {"query_id_cf": "TEST-QID-DEDUP-0001"})
		self.assertEqual(count, 1)

	def test_same_mobile_different_query_id_appends_note_not_new_lead(self):
		from indiamart_erpnext_integration.indiamart_erpnext_controller import (
			make_frappe_crm_lead_from_indiamart,
		)

		make_frappe_crm_lead_from_indiamart(
			self.sample_lead_values(UNIQUE_QUERY_ID="TEST-QID-DEDUP-0002")
		)
		make_frappe_crm_lead_from_indiamart(
			self.sample_lead_values(
				UNIQUE_QUERY_ID="TEST-QID-DEDUP-0003",
				QUERY_MESSAGE="Second enquiry, same mobile.",
			)
		)

		leads = frappe.get_all("CRM Lead", filters={"mobile_no": "+91-9000000099"})
		self.assertEqual(len(leads), 1)

		notes = frappe.get_all(
			"FCRM Note",
			filters={"reference_doctype": "CRM Lead", "reference_docname": leads[0].name},
		)
		self.assertEqual(len(notes), 2)

	def test_same_email_different_query_id_and_mobile_appends_note(self):
		from indiamart_erpnext_integration.indiamart_erpnext_controller import (
			make_frappe_crm_lead_from_indiamart,
		)

		make_frappe_crm_lead_from_indiamart(
			self.sample_lead_values(
				UNIQUE_QUERY_ID="TEST-QID-DEDUP-0004",
				SENDER_MOBILE="+91-9000000004",
				SENDER_EMAIL="samemail@example.com",
			)
		)
		make_frappe_crm_lead_from_indiamart(
			self.sample_lead_values(
				UNIQUE_QUERY_ID="TEST-QID-DEDUP-0005",
				SENDER_MOBILE="+91-9000000005",
				SENDER_EMAIL="samemail@example.com",
			)
		)

		leads = frappe.get_all("CRM Lead", filters={"email": "samemail@example.com"})
		self.assertEqual(len(leads), 1)
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.tests.test_frappe_crm_lead_sync -v
```

Expected: all 3 new tests `OK` — Task 4's implementation already handles this, these tests document and lock in the dedup contract from the spec.

If any fail: re-check the dedup branch order in `make_frappe_crm_lead_from_indiamart` (`query_id_cf` → `mobile_no` → `email`) against Task 4's implementation.

- [ ] **Step 3: Commit**

```bash
git add indiamart_erpnext_integration/tests/test_frappe_crm_lead_sync.py
git commit -m "test: lock in CRM Lead dedup match order"
```

---

### Task 6: Dispatch wiring in `indiamart_lead.py`

**Files:**
- Modify: `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/indiamart_lead.py`
- Test: `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/test_indiamart_lead.py`

**Interfaces:**
- Consumes: `make_erpnext_lead_from_inidamart` (existing, unchanged), `make_frappe_crm_lead_from_indiamart` (Task 4), `Indiamart Settings.lead_sync_target` (Task 2).

- [ ] **Step 1: Write the failing test**

Replace `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/test_indiamart_lead.py`:

```python
# Copyright (c) 2021, GreyCube Technologies and Contributors
# See license.txt

import json

import frappe
from frappe.tests import IntegrationTestCase


class TestIndiamartLead(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("CRM Lead Source", "Indiamart Direct"):
			frappe.get_doc({
				"doctype": "CRM Lead Source",
				"source_name": "Indiamart Direct",
			}).insert()

		settings = frappe.get_single("Indiamart Settings")
		settings.lead_sync_target = "Frappe CRM"
		settings.default_lead_owner = "Administrator"
		settings.crm_direct_lead_source = "Indiamart Direct"
		settings.crm_buy_lead_source = "Indiamart Direct"
		settings.crm_call_lead_source = "Indiamart Direct"
		settings.save()

	def test_after_insert_creates_crm_lead_when_target_is_frappe_crm(self):
		lead_values = {
			"UNIQUE_QUERY_ID": "TEST-QID-DISPATCH-0001",
			"QUERY_TYPE": "W",
			"QUERY_TIME": "2026-07-28 10:00:00",
			"SENDER_NAME": "Dispatch Sender",
			"SENDER_MOBILE": "+91-9000000077",
			"SENDER_EMAIL": "dispatch@example.com",
			"SENDER_COMPANY": "Dispatch Co",
			"QUERY_PRODUCT_NAME": "Widget",
			"QUERY_MESSAGE": "Dispatch test enquiry.",
		}

		indiamart_lead = frappe.get_doc({
			"doctype": "Indiamart Lead",
			"query_id": "TEST-QID-DISPATCH-0001",
			"indiamart_lead_json": json.dumps(lead_values),
			"status": "Queued",
		}).insert(ignore_permissions=True)

		crm_lead_name = frappe.db.get_value("CRM Lead", {"query_id_cf": "TEST-QID-DISPATCH-0001"})
		self.assertIsNotNone(crm_lead_name)

		indiamart_lead.reload()
		self.assertEqual(indiamart_lead.status, "Completed")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.indiamart_erpnext_integration.doctype.indiamart_lead.test_indiamart_lead -v
```

Expected: FAIL — `after_insert` currently always calls `make_erpnext_lead_from_inidamart`, so no `CRM Lead` gets created and `crm_lead_name` is `None`.

- [ ] **Step 3: Update the dispatch logic**

Replace `indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/indiamart_lead.py`'s imports and class body:

```python
# Copyright (c) 2021, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils.background_jobs import enqueue
from frappe import _
from indiamart_erpnext_integration.indiamart_erpnext_controller import (
	make_erpnext_lead_from_inidamart,
	make_frappe_crm_lead_from_indiamart,
)


class IndiamartLead(Document):
		def after_insert(self):
			frappe.db.set_value('Indiamart Lead', self.name, 'created_on', self.creation)
			indiamart_lead_json=json.loads(self.indiamart_lead_json)
			indiamart_lead_name=self.name
			lead_sync_target = frappe.db.get_single_value('Indiamart Settings', 'lead_sync_target')
			if lead_sync_target == 'Frappe CRM':
				method = 'indiamart_erpnext_integration.indiamart_erpnext_controller.make_frappe_crm_lead_from_indiamart'
			else:
				method = 'indiamart_erpnext_integration.indiamart_erpnext_controller.make_erpnext_lead_from_inidamart'
			enqueue(method=method, queue='long', **{"lead_values": indiamart_lead_json, "indiamart_lead_name":indiamart_lead_name})
			return

		@frappe.whitelist()
		def retry_lead_creation(self):
			indiamart_lead_json=json.loads(self.indiamart_lead_json)
			indiamart_lead_name=self.name
			lead_sync_target = frappe.db.get_single_value('Indiamart Settings', 'lead_sync_target')
			if lead_sync_target == 'Frappe CRM':
				output = make_frappe_crm_lead_from_indiamart(indiamart_lead_json, indiamart_lead_name)
			else:
				output = make_erpnext_lead_from_inidamart(indiamart_lead_json, indiamart_lead_name)
			if output:
				frappe.msgprint(_("Output is {0}.").format(frappe.bold(output)), alert=False,indicator="green")
			else:
				frappe.msgprint(_("Error occured. Please check error log."), alert=False,indicator="red")
```

Leave the four module-level `get_connected_*`/`get_connected_lead_for_indiamart_lead` functions below the class untouched.

- [ ] **Step 4: Run test to verify it passes**

```bash
bench --site indiamart-test.localhost run-tests --module indiamart_erpnext_integration.indiamart_erpnext_integration.doctype.indiamart_lead.test_indiamart_lead -v
```

Expected: `OK`. (Frappe's test runner executes `enqueue()` synchronously under `frappe.flags.in_test`, so `after_insert`'s background job runs inline during the test — no manual queue-draining needed.)

- [ ] **Step 5: Run the full app test suite to check for regressions**

```bash
bench --site indiamart-test.localhost run-tests --app indiamart_erpnext_integration -v
```

Expected: `OK`, all tests from Tasks 2–6 pass together.

- [ ] **Step 6: Commit**

```bash
git add indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/indiamart_lead.py indiamart_erpnext_integration/indiamart_erpnext_integration/doctype/indiamart_lead/test_indiamart_lead.py
git commit -m "feat: dispatch lead creation by lead_sync_target"
```

---

### Task 7: Document the feature in `README.md`

**Files:**
- Modify: `README.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Add a "Frappe CRM support" section**

Insert a new section right after the existing "## v16 fork changes" section (before "### Known non-blocking items"):

```markdown
## Frappe CRM support

By default the app creates ERPNext `Lead` records, same as always. If you run Frappe CRM (the `crm` app) instead, set **Indiamart Settings → Lead Sync Target = Frappe CRM** and the app creates `CRM Lead` records there instead.

Notes on the Frappe CRM path:

* Set `CRM Direct/Buy/Call Lead Source` (Link → `CRM Lead Source`) once `Lead Sync Target` is `Frappe CRM` — these replace the ERPNext-only `Direct/Buy/Call Lead Source` (UTM Source) fields, which become optional.
* `CRM Lead` has no address fields, so Indiamart's address/pincode data is not mapped for this path.
* Enquiry details (product, message, alternate contact, Indiamart query ID) are written to a linked `FCRM Note` on the `CRM Lead`, since `CRM Lead` itself has no notes field.
* Repeat enquiries (same query, or same mobile/email as an existing `CRM Lead`) append a new note to the existing lead rather than creating a duplicate. Unlike the ERPNext path, this does **not** auto-escalate to a `CRM Deal` — that's out of scope for now.
* You can only target one CRM at a time (`ERPNext CRM` or `Frappe CRM`), not both simultaneously.
```

- [ ] **Step 2: Verify rendering**

```bash
cat README.md | head -60
```

Expected: the new section reads correctly in context, no broken Markdown.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document Frappe CRM lead sync target"
```

---

## Final verification

- [ ] **Run the complete test suite one more time**

```bash
bench --site indiamart-test.localhost run-tests --app indiamart_erpnext_integration -v
```

Expected: `OK`, all tests across Tasks 2, 3, 4, 5, 6 pass.

- [ ] **Manually verify in the browser** (dev site, not the test site): set `Lead Sync Target = Frappe CRM` on `Indiamart Settings`, fill in the three `CRM *_Lead Source` fields, use **Manual Pull** (or `retry_lead_creation` on an existing `Indiamart Lead`) and confirm a `CRM Lead` with a linked `FCRM Note` appears in Frappe CRM's UI.
