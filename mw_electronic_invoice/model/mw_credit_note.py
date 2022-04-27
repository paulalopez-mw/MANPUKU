from odoo import _, api, fields, models
import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import requests
import json


class MWCreditNote(models.Model):

	_name = "mw.credit_note"
	_model = "mw.credit_note"
	_description = "Midware Electronic Invoice Credit Note"

	def _default_reference_date(self):
		return datetime.datetime.now()

	# Electronic Invoice
	electronic_invoice = fields.Many2one('mw.electronic_invoice', required=True, domain="[('state','=','completed')]")
	electronic_invoice_document_type = fields.Selection([('01', 'Electronic Invoice'),('02', 'Electronic Debit Note'),('03', 'Electronic Credit Note'),('04', 'Electronic Ticket'),('05', 'Confirmation of Electronic Proof Acceptance'),('06', 'Confirmation of Electronic Proof Partial Acceptance'),('07', 'Confirmation of Electronic Proof Rejection'),('08', 'Electronic Purchase Invoice'),('09', 'Electronic Export Invoice')], string="Document type", default="03", required=True)
	electronic_invoice_key = fields.Char(string="Electronic Invoice Key", related="electronic_invoice.key", readonly=True, required=True)
	electronic_invoice_state = fields.Selection([('pending', 'Pending'),('waiting', 'Waiting Response'),('completed', 'Completed')], string="State", default="pending", related="electronic_invoice.state", readonly=True)
	invoice = fields.Many2one('account.move', string="Invoice (Credit Note)", domain="[('move_type', '=', 'out_refund')]")
	name = fields.Char(readonly=True, related="electronic_invoice.name")
	
	# Reference 
	reference_code = fields.Selection([('01', 'Cancel Reference Document'),('02', 'Correct Amount'),('04', 'Reference to another document'),('05', 'Replaces provisional proof for contingency'),('99', 'Others')], string="Code", default="01", required=True)
	reference_date =  fields.Datetime(string="Issue Date", default=_default_reference_date, required=True)
	reference_document_type = fields.Selection([('01', 'Electronic Invoice'),('02', 'Electronic Debit Note'),('03', 'Electronic Credit Note'),('04', 'Electronic Ticket'),('05', 'Spite Note'),('06', 'Contract'),('07', 'Process'),('08', 'Proof issued in contingency'),('09', 'Merchandise return'),('10', 'Replaces invoice rejected by the Ministry of Finance'),('11', 'Replaces invoice rejected by the Receiver of the receipt'),('12', 'Replace Export invoice'),('13', 'Overdue month billing'),('99', 'Others')], string="Document Type", default="03", required=True)
	reference_reason = fields.Char(string="Reason", required=True)

	# Response fields
	key = fields.Char(readonly=True)
	received_XML_file = fields.Binary(readonly=True, attachment=True)
	received_XML_file_name = fields.Char(string="Received File Name", size=64)
	sent_XML_file = fields.Binary(readonly=True, attachment=True)
	sent_XML_file_name = fields.Char(string="Sent File Name", size=64)
	state = fields.Selection([('pending', 'Pending'),('waiting', 'Waiting Response'),('completed', 'Completed')], string="State", default="pending", readonly=True)
	on_error = fields.Boolean(default=False, readonly=True)

	def create_note(self):
		result_message = ""
		if self.electronic_invoice_state != 'completed':
			result_message = "The Electronic Invoice is not completed!!"
		else:    
			json_data = self.electronic_invoice.generate_json()
			format_date = False
			if self.reference_date:
				format_date = str(self.reference_date.year) + "-" + str('{:02d}'.format(self.reference_date.month)) + "-" + str('{:02d}'.format(self.reference_date.day)) + "T" + str('{:02d}'.format(self.reference_date.hour)) + ":" + str('{:02d}'.format(self.reference_date.minute)) + ":" + str('{:02d}'.format(self.reference_date.second)) + "-06:00"

			reference = [{
				"tipo_documento": self.electronic_invoice_document_type if self.electronic_invoice_document_type else "",
				"numero_documento": self.electronic_invoice_key if self.electronic_invoice_key else "",
				"fecha_emision": format_date if format_date else "",
				"codigo": self.reference_code if self.reference_code else "",
				"razon": self.reference_reason if self.reference_reason else ""
			}]

			json_data['referencia'] = reference
			constants = self.env['ir.config_parameter'].sudo()
			invalid_consecutive = True

			while invalid_consecutive:
				new_consecutive = int(constants.get_param('mw_electronic_invoice.next_credit_note_consecutive'))
				json_data['clave']['comprobante'] = new_consecutive
				if self.make_XML(json_data):
					invalid_consecutive = False
				else:
					constants.set_param('mw_electronic_invoice.next_credit_note_consecutive', new_consecutive+1)
			constants.set_param('mw_electronic_invoice.next_credit_note_consecutive', int(constants.get_param('mw_electronic_invoice.next_credit_note_consecutive'))+1)
			result_message = "Success!!"		

		message = {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'params': {
				'title': _('CREATE NOTE MESSAGE'),
				'message': result_message,
				'sticky': True,
			}
		}
		return message
		

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

		if str(response['code'])=="1":
			self.key = response['clave']
			self.sudo().write({ 'key' : response['clave'], 'sent_XML_file' : response['data'], 'sent_XML_file_name' : 'NC-' + self.key + '.xml', 'on_error' : False, 'state' : 'waiting'})
			success = True
		elif str(response['code']) == "44":
			valid_consecutive = False
		else:
			self.write({ 'on_error' : True})

		self.env['mw.electronic_invoice_log'].sudo().create({
			'credit_note': self.id,
			'amount': self.electronic_invoice.invoice_currency_id.symbol + " " + str(round(self.electronic_invoice.total_amount, 5)),
			'electronic_invoice': self.electronic_invoice.id,
			'issue_datetime': datetime.datetime.now(),
			'request': str(data),
			'response': str(response),
			'response_code': self.env['mw.response_code'].sudo().search([('code','=',str(response['code']))])[0].id,
			'success': success,
			'url': url
		})

		return valid_consecutive


	def consultarespuestahacienda(self):
		if not self.key:
			result_message = "Electronic Invoice does not have 'key' yet."
							
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
			'electronic_invoice': self.electronic_invoice.id,
			'credit_note': self.id,
			'is_a_request' : True,
			'issue_datetime': datetime.datetime.now(),
			'request': str(data),
			'response': str(response),
			'response_code': self.env['mw.response_code'].sudo().search([('code','=',str(response['code']))])[0].id,
			'success': True,
			'url': url
		})

		result_message = "Success!!"
						
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