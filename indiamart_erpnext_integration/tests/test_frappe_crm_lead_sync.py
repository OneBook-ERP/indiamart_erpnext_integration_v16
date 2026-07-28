# Copyright (c) 2026, OneBook-ERP and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestCrmLeadQueryIdField(IntegrationTestCase):
	def test_crm_lead_has_query_id_cf_field(self):
		meta = frappe.get_meta("CRM Lead")
		self.assertTrue(meta.has_field("query_id_cf"))


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

		make_frappe_crm_lead_from_indiamart(self.sample_lead_values(
			UNIQUE_QUERY_ID="TEST-QID-0002",
			SENDER_MOBILE="+91-9000000002",
			SENDER_EMAIL="sender2@example.com",
		))

		crm_lead_name = frappe.db.get_value("CRM Lead", {"query_id_cf": "TEST-QID-0002"})
		notes = frappe.get_all(
			"FCRM Note",
			filters={"reference_doctype": "CRM Lead", "reference_docname": crm_lead_name},
			fields=["content"],
		)
		self.assertEqual(len(notes), 1)
		self.assertIn("Widget", notes[0].content)

	def test_writes_status_and_output_to_indiamart_lead_when_name_given(self):
		import json

		from indiamart_erpnext_integration.indiamart_erpnext_controller import (
			make_frappe_crm_lead_from_indiamart,
		)

		lead_values = self.sample_lead_values(
			UNIQUE_QUERY_ID="TEST-QID-0003",
			SENDER_MOBILE="+91-9000000003",
			SENDER_EMAIL="sender3@example.com",
		)
		indiamart_lead = frappe.get_doc({
			"doctype": "Indiamart Lead",
			"query_id": "TEST-QID-0003",
			"indiamart_lead_json": json.dumps(lead_values),
			"status": "Queued",
		}).insert(ignore_permissions=True)

		output = make_frappe_crm_lead_from_indiamart(lead_values, indiamart_lead_name=indiamart_lead.name)

		indiamart_lead.reload()
		self.assertEqual(indiamart_lead.status, "Completed")
		self.assertEqual(indiamart_lead.output, output)
		self.assertIn("CRM Lead", indiamart_lead.output)


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

		values = self.sample_lead_values(
			SENDER_MOBILE="+91-9000000098",
			SENDER_EMAIL="samequeryid@example.com",
		)
		make_frappe_crm_lead_from_indiamart(values)
		make_frappe_crm_lead_from_indiamart(values)

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
