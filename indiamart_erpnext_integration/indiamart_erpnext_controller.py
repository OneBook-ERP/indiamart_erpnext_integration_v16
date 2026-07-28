from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.integrations.utils import create_request_log,make_post_request
from frappe.utils import get_datetime,now_datetime,format_datetime
from datetime import timedelta
import datetime
from frappe.utils.password import get_decrypted_password
from frappe.model.document import Document
import json
from six import string_types
import traceback,sys
from erpnext.crm.doctype.lead.lead import make_opportunity


# manually pull leads for given time frame
@frappe.whitelist()
def manual_pull_indiamart_leads(start_time,end_time):
	try:
		indiamart_settings=get_indiamart_configuration()
		if indiamart_settings!='disabled':
			api_url,now_api_call_time=get_indiamart_api_url(indiamart_settings,start_time,end_time)
			if api_url:
				fetch_indiamart_data_and_make_integration_request(api_url,now_api_call_time)
	except Exception as e:
		title=_('Indiamart Error')
		seperator = "--" * 50
		error = "\n".join([format_datetime(now_datetime(),'d-MMM-y  HH:mm:ss'), "manual_pull_indiamart_leads",str(sys.exc_info()[1]), seperator,frappe.get_traceback()])
		frappe.log_error(message=error, title=title)

# entry point for scheduler 
@frappe.whitelist()
def auto_pull_indiamart_leads():
	try:
		indiamart_settings=get_indiamart_configuration()
		if indiamart_settings!='disabled':
			api_url,now_api_call_time=get_indiamart_api_url(indiamart_settings)
			if api_url:
				fetch_indiamart_data_and_make_integration_request(api_url,now_api_call_time)
	except Exception as e:
		title=_('Indiamart Error')
		seperator = "--" * 50
		error = "\n".join([format_datetime(now_datetime(),'d-MMM-y  HH:mm:ss'), "auto_pull_indiamart_leads",str(sys.exc_info()[1]), seperator,frappe.get_traceback()])
		frappe.log_error(message=error, title=title)


def get_indiamart_configuration():
	if frappe.db.get_single_value("Indiamart Settings", "enabled"):
		indiamart_settings = frappe.get_doc("Indiamart Settings")
		return {
			"glusr_mobile": indiamart_settings.glusr_mobile,
			"glusr_mobile_key": indiamart_settings.glusr_mobile_key,
			"last_api_call_time": indiamart_settings.last_api_call_time
		}
	return "disabled"

def get_indiamart_api_url(indiamart_settings,start_time=None,end_time=None):
	URL_DATETIME_FORMAT = 'd-MMM-yHH:mm:ss'
	# INDIAMART_URL = 'https://mapi.indiamart.com/wservce/enquiry/listing/GLUSR_MOBILE/{0}/GLUSR_MOBILE_KEY/{1}/Start_Time/{2}/End_Time/{3}/'
	INDIAMART_URL = 'https://mapi.indiamart.com/wservce/crm/crmListing/v2/?glusr_crm_key={1}&start_time={2}&end_time={3}'

	#  scheduler flow
	if start_time==None:
		# set start time as minus 5 minutes the last api call time
		if indiamart_settings.get('last_api_call_time'):
			start_time=get_datetime(indiamart_settings.get('last_api_call_time')) - datetime.timedelta(minutes=5)
		else:
			# first time, last_api_call_time will be empty
			start_time= now_datetime() - datetime.timedelta(minutes=5)

		start_time=format_datetime(start_time,URL_DATETIME_FORMAT)
		now_api_call_time=now_datetime()
		end_time=format_datetime(now_api_call_time,URL_DATETIME_FORMAT)
	# manual pull flow
	else:
		start_time=format_datetime(start_time,URL_DATETIME_FORMAT)
		end_time=format_datetime(end_time,URL_DATETIME_FORMAT)
		# we don't change last call time as it is a manual attempt
		now_api_call_time=indiamart_settings.get('last_api_call_time') or now_datetime()
	#  to do : put in config
	api_url = INDIAMART_URL.format(
				indiamart_settings.get('glusr_mobile'),
				get_decrypted_password('Indiamart Settings','Indiamart Settings','glusr_mobile_key'),
				start_time,
				end_time)
	return api_url,now_api_call_time



def fetch_indiamart_data_and_make_integration_request(api_url,now_api_call_time):
	valid_error_messages=['There are no leads in the given time duration. Please try for a different duration.',
												'It is advised to hit this API once in every 5 minutes, but it seems that you have crossed this limit. Please try again after 5 minutes.']
    # v2
	#  response={'CODE': 200, 'STATUS': 'SUCCESS', 'MESSAGE': '', 'TOTAL_RECORDS': 2, 'RESPONSE': [{'UNIQUE_QUERY_ID': '2243859917', 'QUERY_TYPE': 'W', 'QUERY_TIME': '2022-09-17 09:34:45', 'SENDER_NAME': 'Shuaib', 'SENDER_MOBILE': '+91-8384869226', 'SENDER_EMAIL': '', 'SENDER_COMPANY': '', 'SENDER_ADDRESS': 'Dehradun, Uttarakhand', 'SENDER_CITY': 'Dehradun', 'SENDER_STATE': 'Uttarakhand', 'SENDER_COUNTRY_ISO': 'IN', 'SENDER_MOBILE_ALT': '', 'SENDER_PHONE': '', 'SENDER_PHONE_ALT': '', 'SENDER_EMAIL_ALT': '', 'QUERY_PRODUCT_NAME': 'Fuel Pressure Regulator Sensor', 'QUERY_MESSAGE': 'I want to buy Fuel Pressure Regulator Sensor.\r\rBefore purchasing I would like to know the price details.\r\rKindly send me price and other details.<br> Quantity :   1<br> Quantity Unit :   piece<br> Probable Order Value :   Rs. 3,000 to 10,000<br> Probable Requirement Type :   Business Use<br>Preferred Location: Suppliers from Local Area will be Preferred<br>', 'CALL_DURATION': '', 'RECEIVER_MOBILE': ''}, {'UNIQUE_QUERY_ID': '2243945858', 'QUERY_TYPE': 'W', 'QUERY_TIME': '2022-09-17 10:56:07', 'SENDER_NAME': 'Mamilla Ganga Shekhar', 'SENDER_MOBILE': '+91-9100843314', 'SENDER_EMAIL': 'gangadharmamilla@gmail.com', 'SENDER_COMPANY': 'VS Automation', 'SENDER_ADDRESS': 'KTR Colony, Hyderabad, Telangana,         500072', 'SENDER_CITY': 'Hyderabad', 'SENDER_STATE': 'Telangana', 'SENDER_COUNTRY_ISO': 'IN', 'SENDER_MOBILE_ALT': '', 'SENDER_PHONE': '', 'SENDER_PHONE_ALT': '', 'SENDER_EMAIL_ALT': '', 'QUERY_PRODUCT_NAME': 'Capacitive Proximity Sensors', 'QUERY_MESSAGE': 'I want to buy Capacitive Proximity Sensors.<br> Model :   Prk3pl1.btt3x4t<br> Quantity :   6<br> Quantity Unit :   piece<br> Sensing Distance :   0-0.3 Meter<br> Probable Order Value :   Rs. 3,000 to 10,000<br> Probable Requirement Type :   Business Use<br>Preferred Location: Suppliers from all over India can contact<br>', 'CALL_DURATION': '', 'RECEIVER_MOBILE': ''}]}
	response = make_post_request(api_url)
	if not response:
		return

	if isinstance(response, string_types):
		response = json.loads(response)	
	response_result =list(response.get("RESPONSE"))
	data={
		'api_url':api_url
	}
	request_log_data={
		'api_url':api_url,
		"reference_doctype":"Indiamart Lead"
	}
	error=None
	output={
		'output':response_result
	}

	if response.get('MESSAGE') and response.get('MESSAGE')!="":
		error=response.get('MESSAGE')
		
	if not error:
		integration_request=create_request_log(data=frappe._dict(request_log_data),integration_type="Remote",service_name="Indiamart")
		frappe.db.set_value('Integration Request', integration_request.name, 'output',json.dumps(output) )
	else:
		integration_request=create_request_log(data=frappe._dict(request_log_data),integration_type="Remote",service_name="Indiamart",error=frappe._dict({"error":error}))
		frappe.db.set_value('Integration Request', integration_request.name, 'output', json.dumps(output))

	error_message=response.get('MESSAGE')
	status=None

	if (not error_message):
		status='Queued'
	elif error_message in valid_error_messages:
		frappe.db.set_value('Integration Request', integration_request.name, 'status', 'Cancelled')
		frappe.db.set_value('Indiamart Settings','Indiamart Settings', 'last_api_call_time', now_api_call_time)
		status='Failed'
	else: 
		frappe.db.set_value('Integration Request', integration_request.name, 'status', 'Failed')
		status='Failed'	
		# serious error. log it
		error_message=error_message+'\nIntegration Request ID :'+integration_request.name
		frappe.log_error(error_message, title=_('Indiamart Error'))	

	if 	status!='Failed':
		#  use response_result
		for index in range(len(response_result)):
				lead_values={}
				for key in response_result[index]:
						lead_values.update({key:response_result[index][key]})
				# make_lead_from_inidamart(lead_values)
				make_indiamart_lead_records(lead_values,integration_request.name)
		frappe.db.set_value('Integration Request', integration_request.name, 'status', 'Completed')
		frappe.db.set_value('Indiamart Settings','Indiamart Settings', 'last_api_call_time', now_api_call_time)
	return

def make_indiamart_lead_records(lead_values,integration_request,status='Queued',output='Not Processed'):
	existing_indiamart_lead = frappe.db.get_value("Indiamart Lead", {"query_id": lead_values.get('UNIQUE_QUERY_ID')})
	if not existing_indiamart_lead:
		indiamart_lead=frappe.new_doc('Indiamart Lead')
		indiamart_lead.query_id=lead_values.get('UNIQUE_QUERY_ID',None)
		indiamart_lead.indiamart_lead_json=json.dumps(lead_values)
		indiamart_lead.status=status
		indiamart_lead.output=output
		indiamart_lead.integration_request=integration_request
		indiamart_lead.save(ignore_permissions=True)
		return indiamart_lead.name
	return


def make_erpnext_lead_from_inidamart(lead_values,indiamart_lead_name=None):
	try:
		output=None
		user=frappe.db.get_single_value('Indiamart Settings', 'default_lead_owner')
		country=frappe.get_value("Country", {"code": lead_values.get("SENDER_COUNTRY_ISO", "IN").lower()}) or 'India'
		state=lead_values.get('SENDER_STATE',None)
		city=lead_values.get('SENDER_CITY',None)
		email_id=lead_values.get('SENDER_EMAIL',None)
		mobile_no=lead_values.get('SENDER_MOBILE',None)		

		lead_owner=user
		lead_name = None
		lead_name = frappe.db.get_value("Lead", {"query_id_cf": lead_values.get('UNIQUE_QUERY_ID')})
		# It is a new lead from indiamart
		if not lead_name :
			check_duplicate_mobile_no=mobile_no
			lead_name = frappe.db.get_value("Lead", {"mobile_no": check_duplicate_mobile_no})
			#  It is a repeat user having same mobile_no
			if lead_name:
				existing_lead_output=update_existing_lead(lead_name,lead_values)
				output='Duplicate Mobile No: {0}'.format(existing_lead_output)
				frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'output', output)
				frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'status', 'Completed')			
				return output
			# It is may be a fresh lead 
			elif not lead_name:
					if email_id and email_id!='':
						lead_name = frappe.db.get_value("Lead", {"email_id": email_id})
					# It is a repeat user having same email id
					if lead_name:
						existing_lead_output=update_existing_lead(lead_name,lead_values)
						output='Duplicate Email ID: {0}'.format(existing_lead_output)
						frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'output', output)
						frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'status', 'Completed')					
						return output
					elif not lead_name:
					# it is finally a fresh lead
						# source logic 
						if lead_values.get('QUERY_TYPE') == 'W' :
							source= frappe.db.get_single_value('Indiamart Settings', 'direct_lead_source')
						elif lead_values.get('QUERY_TYPE') == 'B' :
							source= frappe.db.get_single_value('Indiamart Settings', 'buy_lead_source')
						elif lead_values.get('QUERY_TYPE') == 'P' :
							source= frappe.db.get_single_value('Indiamart Settings', 'call_lead_source')
							
						if lead_values.get('SENDER_COMPANY'):
							organization_lead=1
							company_name=lead_values.get('SENDER_COMPANY')
							address_type='Office'
							address_title='Work'
						else:
							organization_lead=0
							company_name=None
							address_type='Personal'
							address_title='Work'
						
						notes_html="<div>Product Name :{0}</div><div>Subject :{1}</div><div>Message :{2}</div><div>Lead Date :{3}</div><div>Alternate EmailID :{4}</div><div>Alternate Mobile :{5}</div><div>India Mart Query ID :{6}</div>" \
						.format( \
										frappe.bold(lead_values.get('QUERY_PRODUCT_NAME','Not specified')),
										frappe.bold(lead_values.get('SUBJECT','Not specified')),
										frappe.bold(lead_values.get('QUERY_MESSAGE','Not specified')),
										frappe.bold(lead_values.get('QUERY_TIME','Not specified')),
										frappe.bold(lead_values.get('EMAIL_ALT','Not specified')),
										frappe.bold(lead_values.get('MOBILE_ALT','Not specified')),
										frappe.bold(lead_values.get('UNIQUE_QUERY_ID','Not specified'))
										)

						n  = 140
						address=lead_values.get('SENDER_ADDRESS')
						pincode=None
						address_line1,address_line2=None,None

						if address:
							# extract pincode
							for word in address.rsplit():
								if word.isdigit() and len(word)==6:
										pincode=int(word)

							for index in range(0, len(address), n):
									if index==0:
										address_line1=address[index : index + n]
									elif index==1:
										address_line2=address[index : index + n]
						lead=frappe.new_doc('Lead')
						lead_value_dict={
							"lead_name": lead_values.get('SENDER_NAME'),
							"email_id":email_id,
							"mobile_no": mobile_no,
							"utm_source":source or '',
							"organization_lead":organization_lead,
							"company_name":company_name,
							"notes":notes_html,
							"state":state,
							"country":country ,
							"city": city or 'Not specified',
							"query_id_cf":lead_values.get('UNIQUE_QUERY_ID'),
							"address_title":address_title or 'Other',
							"address_type":address_type or 'Other',
							"address_line1":address_line1 or 'Not specified',
							"address_line2":address_line2,
							"pincode":pincode,
							'contact_by':'',
							'lead_owner':lead_owner
						}
						lead.update(lead_value_dict)
						lead.flags.ignore_mandatory = True
						lead.flags.ignore_permissions = True
						lead.save()
						
						# update details to indiamart lead doctype
						output='Lead {0} is created.'.format(lead.name)
						frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'output', output)
						frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'status', 'Completed')					
						return output
				
		else:
				# indiamart has send lead with same query id. Almost impossilble
				output='Duplicate Query_ID. It is in existing Lead {0}'.format(lead_name)
				frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'output', output)
				frappe.db.set_value('Indiamart Lead', indiamart_lead_name, 'status', 'Completed')			
				return output
	except Exception as e:
		title=_('Indiamart Error')
		seperator = "--" * 50
		error = "\n".join([format_datetime(now_datetime(),'d-MMM-y  HH:mm:ss'), "make_erpnext_lead_from_inidamart","indiamart_lead_name  "+indiamart_lead_name,str(sys.exc_info()[1]), seperator,frappe.get_traceback()])
		frappe.log_error(message=error, title=title)

def update_existing_lead(lead_name,lead_values):
		existing_lead_output=None
		lead_status = frappe.db.get_value('Lead', lead_name, 'status')

		if lead_status not in ['Converted','Quotation']:
			notes_html="<br><br><div><B>New Requirement</B></div><div>Product Name :{0}</div><div>Subject :{1}</div><div>Message :{2}</div><div>Lead Date :{3}</div><div>Alternate EmailID :{4}</div><div>Alternate Mobile :{5}</div><div>India Mart Query ID :{6}</div>" \
			.format( \
								frappe.bold(lead_values.get('QUERY_PRODUCT_NAME','Not specified')),
								frappe.bold(lead_values.get('SUBJECT','Not specified')),
								frappe.bold(lead_values.get('QUERY_MESSAGE','Not specified')),
								frappe.bold(lead_values.get('QUERY_TIME','Not specified')),
								frappe.bold(lead_values.get('EMAIL_ALT','Not specified')),
								frappe.bold(lead_values.get('MOBILE_ALT','Not specified')),
								frappe.bold(lead_values.get('UNIQUE_QUERY_ID','Not specified'))
								)

			lead=frappe.get_doc('Lead', lead_name)
			lead.reload()
			if lead.notes:
				lead.notes=lead.notes+notes_html
			else:
				lead.notes=notes_html
			lead.query_id_cf=lead_values.get('UNIQUE_QUERY_ID')
			lead.status='Lead'
			lead.flags.ignore_mandatory = True
			lead.flags.ignore_permissions = True
			lead.contact_date=''
			lead.contact_by=''
			lead.save()	
			existing_lead_output='Lead notes updated for {0}'.format(lead_name)
			return existing_lead_output	
		else:
			to_discuss_html="New Requirement \n Product Name : {0} \n Subject :{1} \n Message :{2} \n Lead Date :{3} \n Alternate EmailID :{4} \n Alternate Mobile :{5} \n India Mart Query ID :{6}" \
			.format( \
								frappe.bold(lead_values.get('QUERY_PRODUCT_NAME','Not specified')),
								frappe.bold(lead_values.get('SUBJECT','Not specified')),
								frappe.bold(lead_values.get('QUERY_MESSAGE','Not specified')),
								frappe.bold(lead_values.get('QUERY_TIME','Not specified')),
								frappe.bold(lead_values.get('EMAIL_ALT','Not specified')),
								frappe.bold(lead_values.get('MOBILE_ALT','Not specified')),
								frappe.bold(lead_values.get('UNIQUE_QUERY_ID','Not specified'))
								)

			opportunity=make_opportunity(source_name=lead_name)
			opportunity.flags.ignore_mandatory = True
			opportunity.flags.ignore_permissions = True
			opportunity.to_discuss=to_discuss_html
			opportunity.sales_stage= frappe.db.get_single_value('Indiamart Settings', 'default_opportunity_sales_stage')
			opportunity.save()			

			opportunity_html='<br><br><div><B>New Oppurtunity {0} was created</B>'.format(opportunity.name)
			lead=frappe.get_doc('Lead', lead_name)
			lead.reload()
			lead.query_id_cf=lead_values.get('UNIQUE_QUERY_ID')
			if lead.notes:
				lead.notes=lead.notes+opportunity_html
			else:
				lead.notes=opportunity_html
			lead.contact_date=''
			lead.contact_by=''
			lead.flags.ignore_mandatory = True
			lead.flags.ignore_permissions = True
			lead.save()		
			existing_lead_output='Opportunity is {0} created for Lead{1}'.format(opportunity.name,lead_name)
			return existing_lead_output			



def get_integration_request_dashboard_data(data):
	if len(data.get("transactions"))>0:
		for d in data.get("transactions",[]):
			d.update({"items":d.get("items") +["ToDo"]})
	else:
		data.get("transactions").append({"items":["ToDo"]})
	return data