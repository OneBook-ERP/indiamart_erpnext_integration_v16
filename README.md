### Indiamart Erpnext Integration (v16 fork) by OneBook-ERP

> Fork of [ashish-greycube/indiamart_erpnext_integration](https://github.com/ashish-greycube/indiamart_erpnext_integration) by [GreyCube.in](https://greycube.in/), updated and fixed for **Frappe / ERPNext v16** compatibility.

[Indiamart CRM API **Version 2**(Lead)](https://help.indiamart.com/knowledge-base/lms-crm-integration-v2/), integration with ERPNext.

![](https://greycube.in/files/indiamart_greycube.png)

**What does the app do?**

* Indiamart.com : It is a market place where buyers come to fulfill their purchase requirements. i.e. they generate Leads
* ERPNext : It is open source ERP
* Indiamart Erpnext Integration (App): It automatically pulls purchase inquires from indiamart and creats lead in ERPNext.

---

## v16 fork changes

The upstream app was last updated for v13/v14 and no longer installs or runs cleanly on Frappe/ERPNext v16. This fork fixes that:

* **`Lead Source` → `UTM Source`** — ERPNext v16 removed the `Lead Source` DocType entirely in favor of `UTM Source`/`UTM Medium`/`UTM Campaign`. The three source-mapping fields on `Indiamart Settings` (`direct_lead_source`, `buy_lead_source`, `call_lead_source`) now link to `UTM Source` instead of the now-nonexistent `Lead Source`.
* **Lead creation uses `utm_source`** — `indiamart_erpnext_controller.py` now writes to the Lead doctype's `utm_source` field instead of the removed `source` field.
* **Workspace fixed for the block-based UI** — the shipped `Indiamart Integration` workspace predated Frappe's block-based `content` layout (introduced in v14+, required by the v15/v16 Vue desk). Without it the workspace page hung indefinitely on a loading skeleton. Added a proper `content` block layout referencing the existing card groups (Transaction / Logs / Setup).
* **Workspace naming fixed** — the original workspace record shipped with a double-space typo in its name (`"Indiamart  Integration"`), which mangled its URL slug to `indiamart--integration` and threw `Workspace indiamart--integration does not exist` when opened. Renamed to `Indiamart Integration` (folder, JSON `name`/`label`/`cards_label`), and marked public so it's visible to all users, not just the installer.

Everything else — the lead-pull logic, duplicate handling, dashboard hooks, JS sidebar badges — is unchanged from upstream.

### Known non-blocking items (not fixed in this fork, worth knowing)

* `hooks.py` ships an unfilled `user_data_fields` GDPR template (`"{doctype_1}"` placeholders) — only matters if you run Frappe's "Delete Data" tooling against this site.
* `from six import string_types` is an undeclared dependency (not in `requirements.txt`) — currently works because `six` is pulled in transitively by other packages.
* The `public/js/lead.js` and `integration_request.js` sidebar-badge scripts manipulate the desk DOM directly (`.document-link[data-doctype=...]`) rather than using a supported API — functional on v16 but fragile against future desk UI changes.

---

**Benefits**

* No Manual Entry/intervention required
* No Human Erorr
* Pulls all leads based on the time
* Don't miss out any potential leads
* Focus on lead conversion and not on lead data entry/handling
* Make full use of ERPNext CRM module
* As the lead gets generated automatically in ERPNext, you can serve your customers with no delay and do more business than competitors

**Features**

* Pull Leads from IndiaMart via API every 5 mins. Overlap is such that no lead is lost.
* Create Leads automatically in ERPNext
* Maps respective fields of IndiaMart with ERPNext Lead.👀️
  *![](https://greycube.in/files/lead_data_captured_erpnext_greycube.png)
* Auto creation of contacts/address in ERPNext
* Handle Duplicate/ Repeat Leads based on mobile_no/ email
* Automatically create Opportunity for repeat leads
* IndiaMart Integration Log maintained
* Facility to map indiamart provided Query Type in Inquiry to your UTM Source
* Facility to manaully pull leads for specific time frame
* App workspace with all related links
  *![](https://greycube.in/files/indiamart_workspace_erpnext_greycube.png)
* Connection dashboard at top of releated doctypes in ERPNext
* Receive Auto Notification incase of error during Lead Integration
* All [IndiaMart Integration Best Practices ](https://help.indiamart.com/knowledge-base/lms-crm-integration-v2/)followed

**How to setup?**

1. Get mobile no and API Key from indiamart

* Mobile: This is the primary mobile number of your account registered with IndiaMART
* API Key : Go to seller.indiamart.com->Login to Account->Lead Manager( under 3 dots menu)->Click on CRM Integreation, it generates a unique API Key which is received on your primary email.
* OR  go to key generation page direct link : https://seller.indiamart.com/leadmanager/crmapi
  *![](https://greycube.in/files/indiamart_api_crm_key.png)

2. Enter all details in Indiamart Settings doctype. ex URL https://<yourdomain.com>/app/indiamart-settings
   *![](https://greycube.in/files/erpnext_indiamart_settings_greycube.png)
3. Since `Lead Source` no longer exists in v16, make sure you have `UTM Source` records created for your Direct/Buy/Call lead channels before selecting them in Indiamart Settings.

**Installation (v16)**

```bash
bench get-app indiamart_erpnext_integration https://github.com/OneBook-ERP/indiamart_erpnext_integration_v16 --branch main
bench --site <your-site> install-app indiamart_erpnext_integration
```

**Credits**

* Original app by [GreyCube.in](https://greycube.in/) — [ashish-greycube/indiamart_erpnext_integration](https://github.com/ashish-greycube/indiamart_erpnext_integration)
* v16 compatibility fork maintained by [OneBook-ERP](https://github.com/OneBook-ERP)

**Support**

* For issues with the v16 fork itself, open an issue on this repository.
* For the original app / GreyCube's commercial support: Email at <admin@greycube.in>

**[Contact GreyCube](https://greycube.in/contact) for customization**

* Automatic mapping of Territory based on IndiaMart Lead Origin
* Automatic mapping of Leads based on Territory Manager
* Automatic mapping of Leads based on Round Robin ALgorithm for multiple Sales person in a specific Territory
* Single dashboard view of lead response
* Integrate your sales team call data with lead
