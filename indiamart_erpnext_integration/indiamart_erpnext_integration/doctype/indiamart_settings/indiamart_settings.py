# Copyright (c) 2021, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


class IndiamartSettings(Document):
	def load_from_db(self):
		super().load_from_db()
		# Backfill default for existing records loaded from DB (pre-migration installs)
		if not self.lead_sync_target:
			self.lead_sync_target = "ERPNext CRM"

	def validate(self):
		# Validate ERPNext CRM required fields
		# Note: mandatory_depends_on in JSON doesn't override reqd, so we validate here
		if self.lead_sync_target == "ERPNext CRM":
			if not self.direct_lead_source:
				frappe.throw(_("Direct Lead Source is required for ERPNext CRM"), exc=frappe.MandatoryError)
			if not self.buy_lead_source:
				frappe.throw(_("Buy Lead Source is required for ERPNext CRM"), exc=frappe.MandatoryError)
			if not self.call_lead_source:
				frappe.throw(_("CALL Lead Source is required for ERPNext CRM"), exc=frappe.MandatoryError)
			if not self.default_opportunity_sales_stage:
				frappe.throw(_("Default Opportunity Sales Stage is required for ERPNext CRM"), exc=frappe.MandatoryError)
