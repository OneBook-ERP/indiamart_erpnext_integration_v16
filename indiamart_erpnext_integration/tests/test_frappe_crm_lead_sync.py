# Copyright (c) 2026, OneBook-ERP and contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestCrmLeadQueryIdField(IntegrationTestCase):
	def test_crm_lead_has_query_id_cf_field(self):
		meta = frappe.get_meta("CRM Lead")
		self.assertTrue(meta.has_field("query_id_cf"))
