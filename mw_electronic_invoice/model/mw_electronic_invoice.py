# -*- coding: utf-8 -*-
import time
import datetime
import base64
from datetime import timedelta, date
from random import SystemRandom

import logging
#Import math library
import math
from odoo import http
from odoo.http import request
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import _, api, fields, models, exceptions
from openerp.http import Response
import requests
import json
import ast
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

_logger = logging.getLogger(__name__)

class MWElectronicInvoice(models.Model):

	_name = "mw.electronic_invoice"
	_model = "mw.electronic_invoice"
	_description = "Midware Electronic Invoice"

	def default_economic_activity(self):
		economic_activity = self.env['mw.activity'].sudo().search([('code','=',722003)])
		return economic_activity[0].id if economic_activity else 0
	def default_province(self):
		province = self.env['mw.province'].sudo().search([])
		return province[0].id if province else 0
	def default_canton(self):
		canton = self.env['mw.canton'].sudo().search([])
		return canton[0].id if canton else 0
	def default_district(self):
		district = self.env['mw.district'].sudo().search([])
		return district[0].id if district else 0
	def default_street(self):
		street = self.env['mw.street'].sudo().search([])
		return street[0].id if street else 0

	on_error = fields.Boolean(default=False)
	request_logs = fields.One2many('mw.electronic_invoice_log', 'electronic_invoice', readonly=True)
	credit_notes = fields.One2many('mw.credit_note', 'electronic_invoice', readonly=True)
	state = fields.Selection([('pending', 'Pending'),('waiting', 'Waiting Response'),('completed', 'Completed')], readonly=True, default="pending")
	name = fields.Char(readonly=True, related="invoice.name")

	# Resulting key and files 
	key = fields.Char()
	sent_XML_file = fields.Binary(attachment=True)
	sent_XML_file_name = fields.Char(string="Sent File Name", size=64)
	received_XML_file = fields.Binary(readonly=True, attachment=True)
	received_XML_file_name = fields.Char(string="Received File Name", size=64)

	# Header Details 
	document_type = fields.Selection([('01', 'Electronic Invoice'),('02', 'Electronic Debit Note'),('03', 'Electronic Credit Note'),('04', 'Electronic Ticket'),('05', 'Confirmation of Electronic Proof Acceptance'),('06', 'Confirmation of Electronic Proof Partial Acceptance'),('07', 'Confirmation of Electronic Proof Rejection'),('08', 'Electronic Purchase Invoice'),('09', 'Electronic Export Invoice')], required=True, default='01')
	exchange_rate = fields.Float(digits=(18,5), default=0, compute='compute_exchange_rate', readonly=True)
	presentation_situation = fields.Selection([('1', 'Normal'),('2', 'Contingency'),('3', 'Without Internet')], required=True, default='1')
	sale_condition = fields.Selection([('01', 'Cash'),('02', 'Credit'),('03', 'Consignment'),('04', 'Separated'),('05', 'Lease with Purchase Option'),('06', 'Lease in Financial Function'),('07', 'Payment in Favor of a Third Party'),('08', 'Provided Services to the State on credit'),('09', 'Service Provided Payments to the State'),('99', 'Other')], required=True, default='01')
	sale_condition_credit_term = fields.Char(compute='compute_credit_term', readonly=True)
	sale_condition_other = fields.Char()
	payment_method_cash = fields.Boolean()
	payment_method_card = fields.Boolean()
	payment_method_check = fields.Boolean()
	payment_method_transfer = fields.Boolean(default=True)	
	payment_method_third = fields.Boolean()
	payment_method_other = fields.Boolean()
	payment_method_other_char = fields.Char(default="")

	# Invoice details	
	invoice = fields.Many2one('account.move')
	invoice_amount_untaxed = fields.Monetary(readonly=True, compute='compute_amount_untaxed', currency_field='invoice_currency_id', store=True)
	invoice_amount_tax = fields.Monetary(readonly=True, compute='compute_amount_tax', currency_field='invoice_currency_id', store=True)
	invoice_amount_total = fields.Monetary(readonly=True, compute='compute_amount_total', currency_field='invoice_currency_id', store=True)
	invoice_cash_rounding_id = fields.Many2one('account.cash.rounding', compute='compute_cash_rounding_id', readonly=True, store=True)
	invoice_currency_id = fields.Many2one('res.currency', compute='compute_currency_id', readonly=True, store=True)
	invoice_customer = fields.Many2one('res.partner', compute='compute_customer', readonly=True, store=True)
	invoice_date = fields.Date(compute='compute_date', readonly=True, store=True)
	invoice_date_due = fields.Date(compute='compute_date_due', readonly=True, store=True)
	invoice_id = fields.Integer(compute='compute_id', readonly=True, store=True)
	invoice_lines = fields.One2many('account.move.line', related='invoice.invoice_line_ids', readonly=False)
	invoice_number = fields.Char(compute='compute_number', readonly=True, store=True)
	invoice_payment_term_id = fields.Many2one('account.payment.term', compute='compute_payment_term_id', readonly=True, store=True)
	invoice_residual = fields.Monetary(compute='compute_residual', readonly=True, currency_field='invoice_currency_id', store=True)
	invoice_state = fields.Selection([('not_paid', 'Not Paid'),('in_payment', 'In Payment'),('paid', 'Paid'),('partial', 'Partially Paid'),('reversed', 'Reversed'),('invoicing_legacy', 'Invoicing App Legacy')], compute='compute_state', readonly=True, store=True)
	invoice_type = fields.Selection([('out_invoice', 'Customer Invoice'),('in_invoice', 'Vendor Bill'),('out_refund', 'Customer Credit Note'),('in_refund', 'Vendor Credit Note')], compute='compute_invoice_type', readonly=True, store=True)
	invoice_user_id = fields.Many2one('res.users', compute='compute_user_id', readonly=True, store=True)

	# Emitter details
	emitter = fields.Many2one('res.partner', default=1, readonly=True, compute="compute_emitter", store=True)
	emitter_branch = fields.Integer(required=True, default=1, readonly=True, compute="compute_emitter_branch", store=True)
	emitter_branch_number = fields.Integer(default=1, required=True, readonly=True, compute="compute_emitter_branch_number", store=True)
	emitter_branch_terminal = fields.Integer(default=1, required=True, readonly=True, compute="compute_emitter_branch_terminal", store=True)
	emitter_city = fields.Char(compute='compute_emitter_city', readonly=True, store=True)
	emitter_country_id = fields.Many2one('res.country', compute='compute_emitter_country_id', readonly=True, store=True)
	emitter_economic_activity = fields.Many2one('mw.activity', required=True, default=default_economic_activity, readonly=True, compute="compute_emitter_economic_activity", store=True)
	emitter_email = fields.Char(compute='compute_emitter_email', readonly=True, store=True)
	emitter_image = fields.Binary('Image', compute='compute_emitter_image', store=True)
	emitter_image_medium = fields.Binary('Image', compute='compute_emitter_image_medium', store=True)
	emitter_lang = fields.Selection([('en_US', 'English'),], compute='compute_emitter_lang', readonly=True, store=True)
	emitter_mobile = fields.Char(compute='compute_emitter_mobile', readonly=True, store=True)
	emitter_name = fields.Char(compute='compute_emitter_name', readonly=True, store=True)
	emitter_other_signs = fields.Char(compute='compute_emitter_other_signs', default="Other Signs", string="Other Signs", required=True, readonly=True, store=True)
	emitter_phone = fields.Char(compute='compute_emitter_phone', readonly=True, store=True)
	emitter_phone_code = fields.Integer(default=506, required=True, readonly=True, compute="compute_emitter_phone_code", store=True)
	emitter_phone_number = fields.Char(readonly=True, compute="compute_emitter_phone_number", store=True, index=True)
	emitter_state_id = fields.Many2one('res.country.state', compute='compute_emitter_state_id', readonly=True, store=True)
	emitter_street = fields.Char(compute='compute_emitter_street', readonly=True, store=True)
	emitter_street2 = fields.Char(compute='compute_emitter_street2', readonly=True, store=True)
	emitter_ubication_canton = fields.Many2one('mw.canton', required=True, default=default_canton, readonly=True, compute="compute_emitter_ubication_canton", store=True)
	emitter_ubication_district = fields.Many2one('mw.district', required=True, default=default_district, readonly=True, compute="compute_emitter_ubication_district", store=True)
	emitter_ubication_province = fields.Many2one('mw.province', required=True, default=default_province, readonly=True, compute="compute_emitter_ubication_province", store=True)
	emitter_ubication_street = fields.Many2one('mw.street', required=True, default=default_street, readonly=True, compute="compute_emitter_ubication_street", store=True)
	emitter_vat = fields.Char(compute='compute_emitter_vat', readonly=True, store=True)
	emitter_vat_id = fields.Char(readonly=True, compute="compute_emitter_vat_id", store=True)
	emitter_vat_type = fields.Selection([('01', 'Physical ID'),('02', 'Legal ID'),('03', 'DIMEX'),('04', 'NITE')], default='01', required=True, readonly=True, compute="compute_emitter_vat_type", store=True)
	emitter_zip = fields.Char(compute='compute_emitter_zip', readonly=True, store=True)

	# Receiver details
	receiver_city = fields.Char(compute='compute_receiver_city', readonly=True, store=True)
	receiver_country_id = fields.Many2one('res.country', compute='compute_receiver_country_id', readonly=True, store=True)
	receiver_email = fields.Char(compute='compute_receiver_email', readonly=True, store=True)
	receiver_image = fields.Binary('Image', compute='compute_receiver_image', store=True)
	receiver_image_medium = fields.Binary('Image', compute='compute_receiver_image_medium', store=True)
	receiver_lang = fields.Selection([('en_US', 'English'),], compute='compute_receiver_lang', readonly=True, store=True)
	receiver_mobile = fields.Char(compute='compute_receiver_mobile', readonly=True, store=True)
	receiver_name = fields.Char(compute='compute_receiver_name', readonly=True, store=True)
	receiver_other_signs = fields.Char(compute='compute_receiver_other_signs', default="Other Signs", string="Other Signs", required=True, readonly=True, store=True)
	receiver_phone = fields.Char(compute='compute_receiver_phone', readonly=True, store=True)	
	receiver_phone_code = fields.Integer(readonly=True, compute="compute_receiver_phone_code", store=True)
	receiver_phone_number = fields.Char(readonly=True, compute="compute_receiver_phone_number", store=True)
	receiver_state_id = fields.Many2one('res.country.state', compute='compute_receiver_state_id', readonly=True, store=True)
	receiver_street = fields.Char(compute='compute_receiver_street', readonly=True, store=True)
	receiver_street2 = fields.Char(compute='compute_receiver_street2', readonly=True, store=True)
	receiver_vat = fields.Char(compute='compute_receiver_vat', readonly=True, store=True)
	receiver_ubication_canton = fields.Many2one('mw.canton', required=True, default=default_canton, readonly=True, compute="compute_receiver_ubication_canton", store=True)
	receiver_ubication_district = fields.Many2one('mw.district', required=True, default=default_district, readonly=True, compute="compute_receiver_ubication_district", store=True)
	receiver_ubication_province = fields.Many2one('mw.province', required=True, default=default_province, readonly=True, compute="compute_receiver_ubication_province", store=True)
	receiver_ubication_street = fields.Many2one('mw.street', required=True, default=default_street, readonly=True, compute="compute_receiver_ubication_street", store=True)
	receiver_vat_id = fields.Char(default='000000001', readonly=True, compute="compute_receiver_vat_id", store=True)
	receiver_vat_type = fields.Selection([('01', 'Physical ID'),('02', 'Legal ID'),('03', 'DIMEX'),('04', 'NITE')], default='01', required=True, readonly=True, compute="compute_receiver_vat_type", store=True)
	receiver_zip = fields.Char(compute='compute_receiver_zip', readonly=True, store=True)

	# Electronic Invoice details
	detail_estate_code = fields.Char()

	# Electronic Invoice other charges
	other_charges_amount = fields.Float(digits=(18,5))
	other_charges_details = fields.Char()
	other_charges_id = fields.Float(digits=(12,0), default=0)
	other_charges_id_type = fields.Selection([('01', 'Physical ID'),('02', 'Legal ID'),('03', 'DIMEX'),('04', 'NITE')])
	other_charges_name = fields.Char()
	other_charges_percentage = fields.Integer(default=0)
	other_charges_type = fields.Selection([('01', 'Parafiscal Contribution'), ('02', 'Stamp of the Cruz Roja'), ('03', 'Stamp of Worthy Fire Department of Costa Rica '), ('04', 'Third Party Charge'), ('05', 'Export costs'), ('06', 'Service Tax 10%'), ('07', 'Stamp of Professional Colleges'), ('99', 'Other Charges')])

	# Reference 
	reference_code = fields.Selection([('01', 'Cancel Reference Document'),('02', 'Correct Amount'),('04', 'Reference to another document'),('05', 'Replaces provisional proof for contingency'),('99', 'Others')], default="01")
	reference_date =  fields.Date()
	reference_document_type = fields.Selection([('01', 'Electronic Invoice'),('02', 'Electronic Debit Note'),('03', 'Electronic Credit Note'),('04', 'Electronic Ticket'),('05', 'Spite Note'),('06', 'Contract'),('07', 'Process'),('08', 'Proof issued in contingency'),('09', 'Merchandise return'),('10', 'Replaces invoice rejected by the Ministry of Finance'),('11', 'Replaces invoice rejected by the Receiver of the receipt'),('12', 'Replace Export invoice'),('13', 'Overdue month billing'),('99', 'Others')], default="01")
	reference_reason = fields.Char()

	# Final values
	total_amount = fields.Float(digits=(18,5), default=0, readonly=True)
	total_commodity = fields.Float(digits=(18,5), default=0, readonly=True)
	total_commodity_exempt = fields.Float(digits=(18,5), default=0, readonly=True)
	total_commodity_exonerated = fields.Float(digits=(18,5), default=0, readonly=True)
	total_discount = fields.Float(digits=(18,5), default=0, readonly=True)
	total_service = fields.Float(digits=(18,5), default=0, readonly=True)
	total_service_exempt = fields.Float(digits=(18,5), default=0, readonly=True)
	total_service_exonerated = fields.Float(digits=(18,5), default=0, readonly=True)
	total_sell = fields.Float(digits=(18,5), default=0, readonly=True)
	total_net_sell = fields.Float(digits=(18,5), default=0, readonly=True)
	total_tax = fields.Float(digits=(18,5), default=0, readonly=True)
	total_voucher = fields.Float(digits=(18,5), default=0, readonly=True)

	def save_changes(self):
		data = {
			'emitter' : self.emitter.id, 'invoice' : self.invoice.id, 'name' : self.emitter_name + " to " + self.receiver_name + "  " + self.invoice_number
		}
		self.write(data)

	def consultarespuestahacienda(self):
		if not self.key:
			result_message = "Electronic Invoice does not have 'key' yet."

			message = {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('ERROR ON SEND ELECTRONIC INVOICE'),
					'message': result_message,
					'sticky': True,
				}
			}
			return message

		constants = self.env['ir.config_parameter'].sudo()
		url = 'https://www.comprobanteselectronicoscr.com/api/consultahacienda.stag.43'
		if not bool(constants.get_param('mw_electronic_invoice.is_sandbox')):
			url = 'https://www.comprobanteselectronicoscr.com/api/consultahacienda.prod.43'
		headers = {'Content-Type': 'application/json'}

		json_data = {
			'api_key': constants.get_param('mw_electronic_invoice.api_key'),
			'clave': self.key
		}

		data = json.dumps(json_data)
		response = requests.post(url=url, data=data, headers=headers).json()
		if str(response['code']) != "1":
			message = self.env['mw.response_code'].sudo().search([('code','=',str(response['code']))])[0].message
			result_message = 'Message (' + str(response['code']) + '): ' + message

			message = {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('CONSULT RESPONSE'),
					'message': result_message,
					'sticky': True,
				}
			}
			return message
		
		self.write({
			'received_XML_file' : response['hacienda_result']['respuesta-xml'],
			'received_XML_file_name' : 'ARC-' + self.key + '.xml',
			'on_error' : False, 
			'state' : 'completed'
			}) 

		request.env['mw.electronic_invoice_log'].sudo().create({
			'electronic_invoice': self.id,
			'is_a_request' : True,
			'issue_datetime': datetime.datetime.now(),
			'request': str(data),
			'response': str(response),
			'response_code': self.env['mw.response_code'].sudo().search([('code','=',str(response['code']))])[0].id,
			'success': True,
			'url': url
		})

		result_message = 'Success!!'

		message = {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': _('CONSULT RESPONSE'),
				'message': result_message,
				'sticky': True,
			}
		}
		return message


	def generate_bill(self):
		result_message = ""
		if self.state != 'pending':
			result_message = "The Electronic Invoice has already been generated !!"
		else:
			json_data = self.generate_json()
			if type(json_data) == dict and json_data.get('type') and json_data['type'] == 'ir.actions.client':
				return json_data

			invalid_consecutive = True
			constants = self.env['ir.config_parameter'].sudo()
			while invalid_consecutive:
				new_consecutive = int(constants.get_param('mw_electronic_invoice.next_consecutive'))
				json_data['clave']['comprobante'] = new_consecutive
				if self.make_XML(json_data):
					invalid_consecutive = False
				else:
					constants.set_param('mw_electronic_invoice.next_consecutive', new_consecutive+1)
			constants.set_param('mw_electronic_invoice.next_consecutive', int(constants.get_param('mw_electronic_invoice.next_consecutive'))+1)

			result_message = "The Electronic Invoice has been sent!!"

		message = {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': _('CONSULT RESPONSE'),
				'message': result_message,
				'sticky': True,
			}
		}
		return message

	def create_credit_note(self):
		if self.state != 'completed':
			result_message = "The Electronic Invoice is not completed!!"
				
			message = {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('ERROR ON SEND CREDIT NOTE'),
					'message': result_message,
					'sticky': True,
				}
			}
			return message

		else:   
			context = {
				'default_electronic_invoice': self.id		
			}
			
			view = self.sudo().env.ref('mw_electronic_invoice.mw_electronic_invoice_notes').read()
			
			return {
                'context': context,
				'name': "Create Note",
				'res_model': 'mw.credit_note',
				'target': 'new',
				'type': 'ir.actions.act_window',
				'view_id': view[0]['id'] if view else False,
				'view_mode': 'form',
				'view_type': 'form'
			}

	def make_XML(self, json_data):

		constants = self.env['ir.config_parameter'].sudo()
		url = 'https://www.comprobanteselectronicoscr.com/api/makeXML.stag.43'
		if not bool(constants.get_param('mw_electronic_invoice.is_sandbox')):
			url = 'https://www.comprobanteselectronicoscr.com/api/makeXML.prod.43'

		headers = {'Content-Type': 'application/json'}
		data = json.dumps(json_data)
		response = requests.post(url=url, data=data, headers=headers).json()
		success = False
		valid_consecutive = True
		slack_message = ':robot_face: '

		if response['code']==1:
			self.key = response['clave']
			self.write({ 'key' : response['clave'], 'sent_XML_file' : response['data'], 'sent_XML_file_name' : 'FE-' + self.key + '.xml', 'on_error' : False, 'state' : 'waiting'})
			self.invoice.sudo().write({ 'mw_electronic_invoice_date' : datetime.datetime.now()})

			ATTACHMENT_NAME = 'FE-' + self.key
			self.env['ir.attachment'].sudo().create({
				'name': ATTACHMENT_NAME + '.xml',
				'type': 'binary',
				'datas': response['data'],
				# 'datas_fname': ATTACHMENT_NAME + '.xml',
				'store_fname': ATTACHMENT_NAME,
				'res_model': 'account.invoice',
				'res_id': self.invoice_id,
				'mimetype': 'application/xml'
			})

			try:
				self.create_pdf(ATTACHMENT_NAME)
			except:
				_logger.info('PDF cannot be created')

			success = True
			slack_message += "Electronic Invoice generated with success!"
		elif response['code']==44:
			valid_consecutive = False
			slack_message += "Electronic Invoice generated with repeated code!"
		else :		
			self.write({ 'on_error' : True})
			slack_message += "Electronic Invoice error! (" + str(response['code']) + " )"

		self.env['mw.electronic_invoice_log'].sudo().create({
			'amount': self.invoice_currency_id.symbol + " " + str(round(self.total_amount, 5)),
			'electronic_invoice': self.id,
			'issue_datetime': datetime.datetime.now(),
			'request': str(data),
			'response': str(response),
			'response_code': self.env['mw.response_code'].sudo().search([('code','=',str(response['code']))])[0].id,
			'success': success,
			'url': url
		})

		slack = self.env['mw.slack'].sudo()
		
		slack.sendDM('UG3F08BN0', slack_message, '') # Jose Arias
		slack.sendDM('UHUKTGBA9', slack_message, '') # Renato Mainieri
		if not bool(constants.get_param('mw_electronic_invoice.is_sandbox')):
			slack.sendDM('UDR1NA7SQ', slack_message, '') # Veronica Sanchez
		return valid_consecutive

	def generate_json(self):
		
		now = (datetime.datetime.now() - datetime.timedelta(hours=6))
		format_date = str(now.year) + "-" + str('{:02d}'.format(now.month)) + "-" + str('{:02d}'.format(now.day)) + "T" + str('{:02d}'.format(now.hour)) + ":" + str('{:02d}'.format(now.minute)) + ":" + str('{:02d}'.format(now.second)) + "-06:00"

		credit_term = self.sale_condition_credit_term
		if credit_term == "0:00:00": 
			credit_term = ""
		if self.sale_condition == '01':
			credit_term = "0"

		detail_lines = self.generate_lines(format_date)
		if type(detail_lines) == dict and detail_lines['type'] == 'ir.actions.client':
			return detail_lines

		constants = self.env['ir.config_parameter'].sudo() 
		data = {
			"api_key": constants.get_param('mw_electronic_invoice.api_key'),
			"clave":{
				"sucursal": self.emitter_branch,
				"terminal": self.emitter_branch_terminal,
				"tipo":  "03" if self.invoice_type == 'out_refund' else self.document_type, # Credit Note
				"comprobante": "",
				"pais": str(self.emitter_phone_code),
				"dia": '{:02d}'.format(now.day),
				"mes": '{:02d}'.format(now.month),
				"anno": str(now.year)[2:4],
				"situacion_presentacion": self.presentation_situation,
				"codigo_seguridad": self.generate_security_code()
			},
			"encabezado":{
				"codigo_actividad": self.emitter_economic_activity.code,
				"fecha": format_date,
				"condicion_venta": self.sale_condition,
				"plazo_credito": credit_term,
				"medio_pago": self._calc_selected_payment_methods()[1]
			},
			"emisor":{
				"nombre": self.emitter_name,
				"identificacion":{
					"tipo": self.emitter_vat_type,
					"numero": self.emitter_vat_id
				},
				"nombre_comercial": self.emitter_name,
				"ubicacion":{
					"provincia": self.emitter_ubication_province.code,
					"canton": self.emitter_ubication_canton.code,
					"distrito": self.emitter_ubication_district.code,
					"barrio": self.emitter_ubication_street.code,
					"sennas": self.emitter_other_signs
				},
				"telefono":{
					"cod_pais": str(self.emitter_phone_code),
					"numero": self.emitter_phone_number
				},
				"fax":{
					"cod_pais": "",
					"numero": ""
				},
				"correo_electronico": self.emitter_email
			},
			"receptor":{
				"nombre": self.receiver_name,
				"identificacion":{
					"tipo": self.receiver_vat_type,
					"numero": self.receiver_vat_id
				},
				"IdentificacionExtranjero": "" if not self.receiver_vat else self.receiver_vat,
				"ubicacion":{
					"provincia": self.receiver_ubication_province.code if self.receiver_vat_id == '01' or self.receiver_vat_id == '02' else "",
					"canton": self.receiver_ubication_canton.code if self.receiver_vat_id == '01' or self.receiver_vat_id == '02' else "",
					"distrito": self.receiver_ubication_district.code if self.receiver_vat_id == '01' or self.receiver_vat_id == '02' else "",
					"barrio": self.receiver_ubication_street.code if self.receiver_vat_id == '01' or self.receiver_vat_id == '02' else "",
					"sennas": self.receiver_other_signs if self.receiver_vat_id == '01' or self.receiver_vat_id == '02' else ""
				},
				"sennas_extranjero": "",
				"telefono":{
					"cod_pais": str(self.receiver_phone_code),
					"numero": self.receiver_phone_number
				},
				"fax":{
					"cod_pais": "",
					"numero": ""
				},
				"correo_electronico": self.receiver_email
			},
			"detalle": detail_lines,
			"otroscargos":[
				{
					"tipodocumento": "" if not self.other_charges_type else self.other_charges_type,
					"nombre": "" if not self.other_charges_name or not self.other_charges_type else self.other_charges_name,
					"numeroidentificacion": "" if not self.other_charges_type else str(self.other_charges_id).split(".")[0],
					"detalle": "" if not self.other_charges_details else self.other_charges_details,
					"porcentaje": "" if not self.other_charges_type else str(self.other_charges_percentage),
					"montocargo": "" if not self.other_charges_type else str(self.other_charges_amount)
				}
			],
			"resumen":{
				"moneda": self.invoice_currency_id.name,
				"tipo_cambio": str(round(self.exchange_rate,5)) if self.exchange_rate and self.exchange_rate > 0 else "",
				"totalserviciogravado": str(round(self.total_service, 5)),
				"totalservicioexento": str(round(self.total_service_exempt,5)),
				"totalservicioexonerado": str(round(self.total_service_exonerated, 5)),
				"totalmercaderiagravado": str(round(self.total_commodity, 5)),
				"totalmercaderiaexento": str(self.total_commodity_exempt),
				"totalmercaderiaexonerado": str(self.total_commodity_exonerated),
				"totalgravado": str(round(self.total_commodity + self.total_service, 5)),
				"totalexento": str(round(self.total_service_exempt + self.total_commodity_exempt,5)),
				"totalexonerado": str(round(self.total_service_exonerated + self.total_commodity_exonerated, 5)),
				"totalventa": str(round(self.total_sell, 5)),
				"totaldescuentos": str(round(self.total_discount,5)),
				"totalventaneta": str(round(self.total_net_sell, 5)),
				"totalimpuestos": str(round(self.total_tax, 5)),
				"totalivadevuelto": "0.0",
				"totalotroscargos": str(self.other_charges_amount),
				"totalcomprobante": str(round(self.total_voucher, 5))
			},
			"referencia": [{
				"tipo_documento": "" if self.document_type!='02' and self.document_type!='03' else self.reference_document_type,
				"numero_documento": "" if self.document_type!='02' and self.document_type!='03' else self.key,
				"fecha_emision": "" if self.document_type!='02' and self.document_type!='03' else format_date,
				"codigo": "" if self.document_type!='02' and self.document_type!='03' else str(self.reference_code),
				"razon": "" if self.document_type!='02' and self.document_type!='03' else self.reference_reason
			}],
			"parametros":{
				"enviodgt": "A"
			},
			"otros":[
				{
					"codigo": "",
					"texto": "",
					"contenido": ""
				}
			],
			"envio":{
				"aplica": "1",
				"emisor":{
					"correo": constants.get_param('mw_electronic_invoice.receptor_email')
				},
				"receptor":{
					"correo": self.receiver_email if bool(constants.get_param('mw_electronic_invoice.is_sandbox')) and self.receiver_country_id.name == "Costa Rica" else constants.get_param('mw_electronic_invoice.receptor_email')
				},
				"logo": "",
				"texto": ""
			}
		}

		return data


	def create_pdf(self, ATTACHMENT_NAME):

		#Create the Midware PDF report
		pdf = self.env.ref('studio_customization.midware_electronic_i_d6e6f970-aa20-4d65-aa9f-5635ac4bbe11')._render_qweb_pdf(self.id)[0]
		#pdf result is a list
		self.env['ir.attachment'].create({
			'name': ATTACHMENT_NAME + '.pdf',
			'type': 'binary',
			'datas': base64.encodebytes(pdf),
			# 'datas_fname': ATTACHMENT_NAME + '.pdf',
			'store_fname': ATTACHMENT_NAME,
			'res_model': 'account.move',
			'res_id': self.invoice_id,
			'mimetype': 'application/x-pdf'
		})

	def generate_security_code(self):			
		codeLen = 8
		vals = "0123456789"
		cryptogen = SystemRandom()
		code = ""
		while codeLen > 0:
			code = code + cryptogen.choice(vals)
			codeLen = codeLen - 1
		return code

	def generate_lines(self, format_date):
		result = []
		number = 1

		# Resets all the total values
		self.total_service = 0
		self.total_service_exempt = 0		
		self.total_service_exonerated = 0
		self.total_commodity = 0
		self.total_commodity_exempt = 0
		self.total_commodity_exonerated = 0
		self.total_amount = 0
		self.total_discount = 0
		self.total_sell = 0
		self.total_net_sell = 0
		self.total_tax = 0
		self.total_voucher = 0

		# Checks all the lines of the Electronic Invoice
		for line in self.invoice_lines:
			line_in_json = {}
			line_in_json['numero'] = str(number)

			# Departure field is required if it is a Electronic Export Invoice and is not a service sell
			if self.document_type == "09":
				if not line.mw_measurement_is_a_service and (line.mw_departure == "" or not line.mw_departure):
					raise exceptions.ValidationError("If you selected Electronic Export Invoice and a Measurement Unit of merchandise, the Departure fields are required.")

			line_in_json['partida'] = "" if not line.mw_departure else line.mw_departure
			line_in_json['codigo_hacienda'] = line.product_id.product_tmpl_id.mw_category.category if line.product_id and line.product_id.product_tmpl_id.mw_category else ""
			code = []
			code_elements = {}
			code_elements['tipo'] = "" if not line.mw_code_type else line.mw_code_type
			code_elements['codigo'] = "" if not line.mw_code else line.mw_code
			code.append(code_elements)
			line_in_json['codigo'] = code
			line_in_json['cantidad'] = str(line.quantity)
			line_in_json['unidad_medida'] = line.get_mw_measurement_unit()
			line_in_json['unidad_medida_comercial'] = "" if not line.mw_trade_measure else line.mw_trade_measure
			line_in_json['detalle'] = "" if not line.name else line.name
			# Total amount without discount or taxes
			total_amount = round(line.quantity * line.price_unit,2)
			discount_amount = 0.0 if line.discount == 0.0 else (total_amount - line.price_subtotal)
			line_in_json['precio_unitario'] = str(round(line.price_unit, 5))
			line_in_json['monto_total'] = str(total_amount)
			discount = []
			discount_elements = {}
			# Discounts as a number and not as a percentage
			discount_elements['monto'] = "" if discount_amount == 0.0 else str(discount_amount)

			# If the line has a Discount but does not have a Discount Description
			if line.discount and not line.mw_discount_description:
				
				result_message = "The Discount Description of Line number " + str(number) + " is required."
				
				message = {
					'type': 'ir.actions.client',
					'tag': 'display_notification',
					'params': {
						'title': _('ERROR ON SEND ELECTRONIC INVOICE'),
						'message': result_message,
						'sticky': True,
					}
				}
				return message

			discount_elements['naturaleza'] = line.mw_discount_description
			discount.append(discount_elements)
			line_in_json['descuento'] = discount
			line_in_json['subtotal'] = str(line.price_subtotal)
			line_in_json['baseimponible'] = str(line.price_subtotal)
			taxes = []
			
			# Total Exoneration Amount by line
			exoneration_amount = 0.0
			# Total Tax Amount by line
			tax_amount = 0.0

			# Checks all the taxes of the Line
			for tax in line.tax_ids:
				tax_in_json = {}
				if tax.mw_tax_code:
					mw_tax_amount = tax.get_tax_amount(line.mw_tax_base, line.price_subtotal)
					
					mw_exoneration_amount = tax.get_exoneration_amount(line.price_subtotal)

					tax_in_json['codigo'] = "" if not tax.mw_tax_code else str(tax.mw_tax_code)
					tax_in_json['codigotarifa'] = "" if not tax.mw_tax_rate_code or not tax.mw_tax_code else str(tax.mw_tax_rate_code)
					tax_in_json['tarifa'] = "" if not tax.mw_tax_code else str(tax.mw_tax_rate)
					tax_in_json['factoriva'] = "" if not tax.mw_tax_code else str(tax.mw_tax_iva_factor)
					tax_in_json['monto'] = "" if not tax.mw_tax_code else str(round(mw_tax_amount, 5))
					tax_in_json['exportacion'] = "" if not tax.mw_tax_code else str(tax.mw_tax_export)
					exoneration = {}
					exoneration['tipodocumento'] = "" if not tax.mw_exoneration_type else tax.mw_exoneration_type
					exoneration['numerodocumento'] = "" if not tax.mw_exoneration_type else str(tax.mw_exoneration_number)
					exoneration['nombreinstitucion'] = "" if not tax.mw_exoneration_institution or not tax.mw_exoneration_type else tax.mw_exoneration_institution
					exoneration['fechaemision'] = "" if not tax.mw_exoneration_type else format_date
					exoneration['porcentajeexoneracion'] = "" if not tax.mw_exoneration_type else str(tax.mw_exoneration_percentage)
					exoneration['montoexoneracion'] = "" if not tax.mw_exoneration_type else str(exoneration_amount)			
					tax_in_json['exoneracion'] = exoneration
					taxes.append(tax_in_json)
				
					exoneration_amount += exoneration_amount
					tax_amount += round(mw_tax_amount,5)

					# Calculates the Exonerated Percentage according to the number of taxes
					exonerated = tax.mw_exoneration_percentage
					temporal_amount = total_amount / len(line.tax_ids)
					if exonerated != 0:
						exonerated = (exonerated * temporal_amount) / 100
					
					# Checks if the tax is for a service or a commodity
					if line.mw_measurement_is_a_service:
						self.total_service += round(temporal_amount - exonerated, 5)
						self.total_service_exonerated += round(exonerated, 5)
					else:
						self.total_commodity += round(temporal_amount - exonerated, 5)
						self.total_commodity_exonerated += round(exonerated, 5)

			# If the line does not have taxes, assigns empty values
			if not line.tax_ids:
				tax_in_json = {}
				tax_in_json['codigo'] = ""
				tax_in_json['codigotarifa'] = ""
				tax_in_json['tarifa'] = ""
				tax_in_json['factoriva'] = ""
				tax_in_json['monto'] = ""
				tax_in_json['exportacion'] = ""
				exoneration = {}
				exoneration['tipodocumento'] = ""
				exoneration['numerodocumento'] = ""
				exoneration['nombreinstitucion'] = ""
				exoneration['fechaemision'] = ""
				exoneration['porcentajeexoneracion'] = ""
				exoneration['montoexoneracion'] = ""	
				tax_in_json['exoneracion'] = exoneration
				taxes.append(tax_in_json)

				# Checks if the line is for a service or a commodity
				if line.mw_measurement_is_a_service:
					self.total_service_exempt += round(total_amount, 5)
				else:
					self.total_commodity_exempt += round(total_amount, 5)
			
			tax_net = tax_amount - exoneration_amount if exoneration_amount != line.price_subtotal else 0
			
			subtotal = total_amount - discount_amount + tax_net
			price_total = line.price_total - exoneration_amount
			difference = price_total - subtotal
			if round(difference,3) == 0.005:
				subtotal = math.ceil(subtotal*100)/100
			elif round(difference,2) == 0.01 or round(difference,2) == -0.01:
				subtotal = price_total

			if price_total != subtotal:
				result_message = "The Subtotal of Line number " + str(number) + " (" + str(price_total) + ") does not match the sum of its taxes (" + str(subtotal) + ")."
					
				message = {
					'type': 'ir.actions.client',
					'tag': 'display_notification',
					'params': {
						'title': _('ERROR ON SEND ELECTRONIC INVOICE'),
						'message': result_message,
						'sticky': True,
					}
				}
				return message

			line_in_json['impuestos'] = taxes
			line_in_json['impuestoneto'] = str(round(tax_net,5))
			total_line_amount = round(line.price_subtotal + tax_net, 5)
			line_in_json['montototallinea'] = str(total_line_amount)
			result.append(line_in_json)
			number = number + 1
			self.total_amount += total_amount - discount_amount + tax_net
			self.total_discount += discount_amount
			self.total_sell += total_amount
			self.total_net_sell = self.total_sell - self.total_discount
			self.total_tax += tax_net
			self.total_voucher = self.total_net_sell + self.total_tax
		return (result)
	
	#def calc_receiver_foreigner_address(self):
		# return ""
		#if self.receiver_vat_type == '04':
		#	return self.receiver_street + ", " + self.receiver_city + ", " + self.receiver_state_id.name + ', ' + self.receiver_zip + ', ' + self.receiver_country_id.name
		#else:
		#	return ""

	def _calc_selected_payment_methods(self):
		list = ""
		counter = 0
		if self.payment_method_cash:
			list += "01"
			counter += 1
		if self.payment_method_card:
			if counter > 0 :
				list += ","
			list += "02"
			counter += 1
		if self.payment_method_check:
			if counter > 0 :
				list += ","
			list += "03"
			counter += 1
		if self.payment_method_transfer:
			if counter > 0 :
				list += ","
			list += "04"
			counter += 1
		if self.payment_method_third:
			if counter > 0 :
				list += ","
			list += "05"
			counter += 1
		if self.payment_method_other:
			if counter > 0 :
				list += ","
			list += "99"
			counter += 1
		return [counter, list]

	def is_a_service_activity(self):
		result = False
		services = 	['Al' , 'Alc', 'Cm', 'I', 'Os', 'Sp', 'Spe', 'St', '´´', 'd', 'h']
		if self.detail_measurement_unit in services :
			result = True
		return result

	@api.onchange('emitter')
	def _onchange_emitter(self):		
		self.emitter_city = self.emitter.city
		self.emitter_country_id = self.emitter.country_id.id
		self.emitter_email = self.emitter.email
		self.emitter_image_medium = self.emitter.image_medium
		self.emitter_image = self.emitter.image_1920
		self.emitter_lang = self.emitter.lang
		self.emitter_mobile = self.emitter.mobile
		self.emitter_name =self.emitter.name
		self.emitter_phone = self.emitter.phone
		self.emitter_state_id = self.emitter.state_id.id
		self.emitter_street = self.emitter.street
		self.emitter_street2 = self.emitter.street2
		self.emitter_vat = self.emitter.vat
		self.emitter_zip = self.emitter.zip

	@api.constrains('payment_method_cash', 'payment_method_card', 'payment_method_check', 'payment_method_transfer', 'payment_method_third', 'payment_method_other')
	def _check_payment_method(self):
		for record in self:
			payment_methods = record._calc_selected_payment_methods()[0]
			if payment_methods > 4:
				raise exceptions.Warning("You must select a maximum of 4 Payment Methods.")
			if record.document_type == '01' or record.document_type == '04':
				if payment_methods == 0:
					raise exceptions.ValidationError("If you selected Electronic Invoice or Electronic Ticket as Document Type, you must select at least 1 Payment Method.")

	@api.constrains('emitter_branch_number')
	def _check_branch_number(self):
		for record in self:
			branch_number_len = len(str(record.emitter_branch_number))
			if branch_number_len > 3:
				raise exceptions.ValidationError("Branch Number must be a maximum of 3 digits.")

	@api.constrains('emitter_branch_terminal')
	def _check_branch_terminal(self):
		for record in self:
			branch_terminal_len = len(str(record.emitter_branch_terminal))
			if branch_terminal_len > 5:
				raise exceptions.ValidationError("Branch Terminal must be a maximum of 5 digits.")

	@api.constrains('emitter_phone_code', 'emitter_phone_number')
	def _check_emitter_phone(self):
		for record in self:
			phone_code_len = len(str(record.emitter_phone_code))
			phone_number_len = len(record.emitter_phone_number)
			if phone_code_len > 3 or phone_code_len < 1:
				raise exceptions.ValidationError("Emitter phone code must be a maximun of 3 digits.")
			if phone_number_len > 20 or phone_number_len < 1 or not record.emitter_phone_number.isdigit():
				raise exceptions.ValidationError("Emitter phone number must be a maximun of 20 digits.")

	@api.constrains('emitter_vat_id')
	def _check_emitter_vat_id(self):
		for record in self:
			actual_id_type = record.emitter_vat_type
			actual_id_size = len(record.emitter_vat_id)
			id_type = "Physical ID"
			id_digits = "9"
			isValid = False

			if record.emitter_vat_id.isdigit():
				if actual_id_type == '01' and actual_id_size != 9:
					id_type = "Physical ID"
					id_digits = "9"
				elif actual_id_type == '02' and actual_id_size != 10:
					id_type = "Legal ID"
					id_digits = "10"
				elif actual_id_type == '03' and (actual_id_size != 11 and actual_id_size != 12):
					id_type = "DIMEX"
					id_digits = "11 or 12"
				elif actual_id_type == '04' and actual_id_size != 10:
					id_type = "NITE"
					id_digits = "10"
				else :
					isValid = True
			if not isValid:
				raise exceptions.ValidationError("If you selected " + id_type + " as Emitter ID type, the ID must be a NUMBER and have " + id_digits + " digits.")

	@api.constrains('receiver_phone_code', 'receiver_phone_number')
	def _check_receiver_phone(self):
		for record in self:
			phone_code_len = len(str(record	.receiver_phone_code))
			if phone_code_len > 3 or phone_code_len < 1:
				raise exceptions.ValidationError("Receiver phone code must be a maximun of 3 digits.")
			if record.receiver_phone_number:
				phone_number_len = len(record.receiver_phone_number)
				if phone_number_len > 20 or phone_number_len < 1 or not record.receiver_phone_number.isdigit():
					raise exceptions.ValidationError("Receiver phone number must be a NUMBER, with a maximun of 20 digits.")

	@api.constrains('receiver_vat_id')
	def _check_receiver_vat_id(self):
		for record in self:
			actual_id_type = record.receiver_vat_type
			actual_id_size = len(record.receiver_vat_id)
			id_type = "Physical ID"
			id_digits = "9"
			isValid = False
			if record.receiver_vat_id.isdigit():
				if actual_id_type == '01' and actual_id_size != 9:
					id_type = "Physical ID"
					id_digits = "9"
				elif actual_id_type == '02' and actual_id_size != 10:
					id_type = "Legal ID"
					id_digits = "10"
				elif actual_id_type == '03' and (actual_id_size != 11 and actual_id_size != 12):
					id_type = "DIMEX"
					id_digits = "11 or 12"
				elif actual_id_type == '04' and actual_id_size != 10:
					id_type = "NITE"
					id_digits = "10"
				else :
					isValid = True
			if not isValid:
				raise exceptions.ValidationError("If you selected " + id_type + " as Receiver ID type, the ID must have " + id_digits + " digits.")

	@api.constrains('exchange_rate')
	def _check_exchange_rate(self):
		for record in self:
			exchange_rate_len = len(str(record.exchange_rate).split(".")[0])
			if exchange_rate_len > 13:
				raise exceptions.ValidationError("Exchange Rate must have a maximum of 13 digits in the integer part.")	

	@api.constrains('detail_estate_code')
	def _check_estate_code(self):
		for record in self:
			detail_estate_code_len = len(str(record.detail_estate_code))
			if detail_estate_code_len > 13:
				raise exceptions.ValidationError("Estate Code must be a maximum of 13 characters.")

	@api.constrains('other_charges_amount')
	def _check_other_charges_amount(self):
		for record in self:
			other_charges_amount_len = len(str(record.other_charges_amount).split(".")[0])
			if other_charges_amount_len > 13:
				raise exceptions.ValidationError("Amount of Other Charges must have a maximum of 13 digits in the integer part.")

	@api.constrains('other_charges_details')
	def _check_other_charges_details(self):
		for record in self:
			other_charges_details_len = len(str(record.other_charges_details))
			if other_charges_details_len > 160:
				raise exceptions.ValidationError("Details of Other Charges must be a maximum of 160 characters.")

	@api.constrains('other_charges_name')
	def _check_other_charges_name(self):
		for record in self:
			other_charges_name_len = len(str(record.other_charges_name))
			if other_charges_name_len > 100:
				raise exceptions.ValidationError("Third Party Name of Other Charges must be a maximum of 100 characters.")

	@api.constrains('other_charges_percentage')
	def _check_other_charges_percentage(self):
		for record in self:
			if record.other_charges_percentage >= 10:
				raise exceptions.ValidationError("Percentage of Other Charges must be less than 10.")

	@api.constrains('other_charges_id')
	def _check_other_charges_id(self):
		for record in self:
			actual_id_type = record.other_charges_id_type
			actual_id_size = len(str(record.other_charges_id))
			id_type = "Physical ID"
			id_digits = "9"
			isValid = False
			if actual_id_type == '01' and actual_id_size != 9:
				id_type = "Physical ID"
				id_digits = "9"
			elif actual_id_type == '02' and actual_id_size != 10:
				id_type = "Legal ID"
				id_digits = "10"
			elif actual_id_type == '03' and (actual_id_size != 11 and actual_id_size != 12):
				id_type = "DIMEX"
				id_digits = "11 or 12"
			elif actual_id_type == '04' and actual_id_size != 10:
				id_type = "NITE"
				id_digits = "10"
			else :
				isValid = True
			
			if not isValid:
				raise exceptions.ValidationError("If you selected " + id_type + " as ID type, the ID must have " + id_digits + " digits.")

	@api.constrains('reference_reason')
	def _check_reference_reason(self):
		for record in self:
			if record.reference_reason and len(record.reference_reason) >= 180:
				raise exceptions.ValidationError("Reference Reason must be a maximum of 180 characters.")

	@api.onchange('sale_condition')
	def onchange_sale_condition(self):
		self.sale_condition_credit_term = self.invoice_date_due - self.invoice_date_due

	@api.onchange('emitter_ubication_province')
	def onchange_emitter_province(self):
		canton = self.env['mw.canton'].sudo().search([('province','=',self.emitter_ubication_province.id)])
		self.emitter_ubication_canton = canton[0].id if canton else 0

	@api.onchange('emitter_ubication_canton')
	def onchange_emitter_canton(self):
		district = self.env['mw.district'].sudo().search([('canton','=',self.emitter_ubication_canton.id)])
		self.emitter_ubication_district = district[0].id if district else 0
	
	@api.onchange('emitter_ubication_district')
	def onchange_emitter_district(self):
		street = self.env['mw.street'].sudo().search([('district','=',self.emitter_ubication_district.id)])
		self.emitter_ubication_street = street[0].id if street else 0

	@api.onchange('receiver_ubication_province')
	def onchange_receiver_province(self):
		canton = self.env['mw.canton'].sudo().search([('province','=',self.receiver_ubication_province.id)])
		self.receiver_ubication_canton = canton[0].id if canton else 0

	@api.onchange('receiver_ubication_canton')
	def onchange_receiver_canton(self):
		district = self.env['mw.district'].sudo().search([('canton','=',self.receiver_ubication_canton.id)])
		self.receiver_ubication_district = district[0].id if district else 0
	
	@api.onchange('receiver_ubication_district')
	def onchange_receiver_district(self):
		street = self.env['mw.street'].sudo().search([('district','=',self.receiver_ubication_district.id)])
		self.receiver_ubication_street = street[0].id if street else 0

	def compute_credit_term(self):
		for record in self:
			record.sale_condition_credit_term = record.invoice_date_due - record.invoice_date if record.invoice_date else record.invoice_date_due
			 
	# Invoice Field Computes
	@api.depends('invoice')
	def compute_amount_untaxed(self):
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_amount_untaxed = electronic_invoice.invoice.amount_untaxed
	@api.depends('invoice')
	def compute_amount_tax(self):
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_amount_tax = electronic_invoice.invoice.amount_tax
	@api.depends('invoice')
	def compute_amount_total(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_amount_total = electronic_invoice.invoice.amount_total
	@api.depends('invoice')
	def compute_cash_rounding_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_cash_rounding_id = electronic_invoice.invoice.invoice_cash_rounding_id
	@api.depends('invoice')
	def compute_currency_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_currency_id = electronic_invoice.invoice.currency_id
	@api.depends('invoice')
	def compute_customer(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_customer = electronic_invoice.invoice.partner_id.id
	@api.depends('invoice')
	def compute_date(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_date = electronic_invoice.invoice.invoice_date
	@api.depends('invoice')
	def compute_date_due(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_date_due = electronic_invoice.invoice.invoice_date_due
	@api.depends('invoice')
	def compute_exchange_rate(self):
		for electronic_invoice in self:
			electronic_invoice.exchange_rate = electronic_invoice.invoice.mw_exchange_rate
	@api.depends('invoice')
	def compute_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_id = electronic_invoice.invoice.id
	@api.depends('invoice')
	def compute_invoice_type(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_type = electronic_invoice.invoice.move_type
	@api.depends('invoice')
	def compute_number(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_number = electronic_invoice.invoice.name
	@api.depends('invoice')
	def compute_payment_term_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_payment_term_id = electronic_invoice.invoice.invoice_payment_term_id.id
	@api.depends('invoice')
	def compute_residual(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_residual = electronic_invoice.invoice.amount_residual
	@api.depends('invoice')
	def compute_state(self):
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_state = electronic_invoice.invoice.payment_state
	@api.depends('invoice')
	def compute_user_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.invoice_user_id = electronic_invoice.invoice.user_id.id	

	# Emitter Field Computes
	@api.depends('state')
	def compute_emitter(self):
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter = int(self.env['ir.config_parameter'].sudo().get_param('mw_electronic_invoice.emitter'))
	@api.depends('emitter')
	def compute_emitter_branch_number(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_branch_number = electronic_invoice.emitter.mw_branch_number
	@api.depends('emitter')
	def compute_emitter_branch_terminal(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_branch_terminal = electronic_invoice.emitter.mw_branch_terminal
	@api.depends('emitter')
	def compute_emitter_city(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_city = electronic_invoice.emitter.city
	@api.depends('emitter')
	def compute_emitter_country_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_country_id = electronic_invoice.emitter.country_id.id
	@api.depends('emitter')
	def compute_emitter_economic_activity(self):
		for electronic_invoice in self:	
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_economic_activity = electronic_invoice.emitter.mw_economic_activity
	@api.depends('emitter')
	def compute_emitter_email(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_email = electronic_invoice.emitter.email
	@api.depends('emitter')
	def compute_emitter_image(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_image = electronic_invoice.emitter.image_1920
	@api.depends('emitter')
	def compute_emitter_image_medium(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_image_medium = electronic_invoice.emitter.image_medium
	@api.depends('emitter')
	def compute_emitter_lang(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_lang = electronic_invoice.emitter.lang
	@api.depends('emitter')
	def compute_emitter_mobile(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_mobile = electronic_invoice.emitter.mobile
	@api.depends('emitter')
	def compute_emitter_name(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_name = electronic_invoice.emitter.name	
	@api.depends('emitter')
	def compute_emitter_other_signs(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_other_signs = electronic_invoice.emitter.mw_other_signs
	@api.depends('emitter')
	def compute_emitter_phone(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_phone = electronic_invoice.emitter.phone
	@api.depends('emitter')
	def compute_emitter_phone_code(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_phone_code = electronic_invoice.emitter.mw_phone_code
	@api.depends('emitter')
	def compute_emitter_phone_number(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_phone_number = electronic_invoice.emitter.mw_phone_number
	@api.depends('emitter')
	def compute_emitter_state_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_state_id = electronic_invoice.emitter.state_id.id
	@api.depends('emitter')
	def compute_emitter_street(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_street = electronic_invoice.emitter.street
	@api.depends('emitter')
	def compute_emitter_street2(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_street2 = electronic_invoice.emitter.street2
	@api.depends('emitter')
	def compute_emitter_ubication_canton(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_ubication_canton = electronic_invoice.emitter.mw_canton
	@api.depends('emitter')
	def compute_emitter_ubication_district(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_ubication_district = electronic_invoice.emitter.mw_district
	@api.depends('emitter')
	def compute_emitter_ubication_province(self):
		for electronic_invoice in self:	
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_ubication_province = electronic_invoice.emitter.mw_province
	@api.depends('emitter')
	def compute_emitter_ubication_street(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_ubication_street = electronic_invoice.emitter.mw_street
	@api.depends('emitter')
	def compute_emitter_vat(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_vat = electronic_invoice.emitter.vat
	@api.depends('emitter')
	def compute_emitter_vat_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_vat_id = electronic_invoice.emitter.mw_id
	@api.depends('emitter')
	def compute_emitter_vat_type(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_vat_type = electronic_invoice.emitter.mw_id_type
	@api.depends('emitter')
	def compute_emitter_zip(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.emitter_zip = electronic_invoice.emitter.zip

	# Receiver Field Computes
	@api.depends('invoice_customer')
	def compute_receiver_city(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_city = electronic_invoice.invoice_customer.city
	@api.depends('invoice_customer')
	def compute_receiver_country_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_country_id = electronic_invoice.invoice_customer.country_id.id
	@api.depends('invoice_customer')
	def compute_receiver_email(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_email = electronic_invoice.invoice_customer.email
	@api.depends('invoice_customer')
	def compute_receiver_image(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_image = electronic_invoice.invoice_customer.image_1920
	@api.depends('invoice_customer')
	def compute_receiver_image_medium(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_image_medium = electronic_invoice.invoice_customer.image_medium
	@api.depends('invoice_customer')
	def compute_receiver_lang(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_lang = electronic_invoice.invoice_customer.lang
	@api.depends('invoice_customer')
	def compute_receiver_mobile(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_mobile = electronic_invoice.invoice_customer.mobile
	@api.depends('invoice_customer')
	def compute_receiver_name(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_name = electronic_invoice.invoice_customer.name	
	@api.depends('invoice_customer')
	def compute_receiver_other_signs(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_other_signs = electronic_invoice.invoice_customer.mw_other_signs
	@api.depends('invoice_customer')
	def compute_receiver_phone(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_phone = electronic_invoice.invoice_customer.phone	
	@api.depends('invoice_customer')	
	def compute_receiver_phone_code(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_phone_code = electronic_invoice.invoice_customer.mw_phone_code
	@api.depends('invoice_customer')
	def compute_receiver_phone_number(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_phone_number = electronic_invoice.invoice_customer.mw_phone_number
	@api.depends('invoice_customer')
	def compute_receiver_state_id(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_state_id = electronic_invoice.invoice_customer.state_id.id
	@api.depends('invoice_customer')
	def compute_receiver_street(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_street = electronic_invoice.invoice_customer.street
	@api.depends('invoice_customer')
	def compute_receiver_street2(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_street2 = electronic_invoice.invoice_customer.street2
	@api.depends('invoice_customer')
	def compute_receiver_ubication_canton(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_ubication_canton = electronic_invoice.invoice_customer.mw_canton
	@api.depends('invoice_customer')
	def compute_receiver_ubication_district(self):
		for electronic_invoice in self:	
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_ubication_district = electronic_invoice.invoice_customer.mw_district
	@api.depends('invoice_customer')
	def compute_receiver_ubication_province(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_ubication_province = electronic_invoice.invoice_customer.mw_province
	@api.depends('invoice_customer')
	def compute_receiver_ubication_street(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_ubication_street = electronic_invoice.invoice_customer.mw_street
	@api.depends('invoice_customer')
	def compute_receiver_vat(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_vat = electronic_invoice.invoice_customer.vat
	@api.depends('invoice_customer')
	def compute_receiver_vat_id(self):
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_vat_id = electronic_invoice.invoice_customer.mw_id
	@api.depends('invoice_customer')
	def compute_receiver_vat_type(self):
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':	
				electronic_invoice.receiver_vat_type = electronic_invoice.invoice_customer.mw_id_type
	@api.depends('invoice_customer')
	def compute_receiver_zip(self):	
		for electronic_invoice in self:
			if electronic_invoice.state == 'pending':
				electronic_invoice.receiver_zip = electronic_invoice.invoice_customer.zip