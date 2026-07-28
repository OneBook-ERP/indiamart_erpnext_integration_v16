# Copyright (c) 2021, GreyCube Technologies and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

# Skip auto-generating test records for these doctypes:
# - User: the dependency chain reaches Payment Gateway (upstream gap).
# - Sales Stage, UTM Source, CRM Lead Source: our tests only reference existing
#   records (default "Sales Stage", "UTM Source", "CRM Lead Source" values).
IGNORE_TEST_RECORD_DEPENDENCIES = ["User", "Sales Stage", "UTM Source", "CRM Lead Source"]


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
