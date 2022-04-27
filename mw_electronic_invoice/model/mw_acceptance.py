from odoo import _, api, fields, models
import requests
import json
from random import SystemRandom
from odoo import http
from odoo.http import request
import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from xml.etree.ElementTree import fromstring, ElementTree
import base64
import logging
import re


_logger = logging.getLogger(__name__)

class MWAcceptance(models.Model):

    _name = "mw.electronic_invoice_acceptance"
    _model = "mw.electronic_invoice_acceptance"
    _description = "Midware Electronic Invoice Acceptance"

    activity_code = fields.Char(required=True, readonly=True, default="00000")
    applicable_expense = fields.Float(digits=(18,5))
    branch = fields.Char(required=True, readonly=True, compute='compute_branch')
    emitter_name = fields.Char(required=True, readonly=True, default="Emitter Name")
    emitter_vat_id = fields.Char(size=12, required=True, readonly=True, default="000000000000")
    emitter_vat_type = fields.Char(size=2, required=True, readonly=True, default="01")
    issue_date = fields.Char(required=True, readonly=True, default="-")
    key = fields.Char(required=True, readonly=True, default="0000000000")
    message = fields.Selection([('1', 'Full Acceptance'),('2', 'Parcial Acceptance'),('3', 'Rejection')], default='1', required=True)
    message_detail = fields.Text(size=160)
    presentation_situation = fields.Selection([('1', 'Normal'),('2', 'Contingency'),('3', 'Without Internet')], default='1', required=True)
    receiver_consecutive = fields.Char(size=10, compute='compute_consecutive')
    receiver_economic_activity = fields.Many2one('mw.activity', compute='compute_activity', readonly=True, string="Economic Activity")
    receiver_vat_id = fields.Char(size=12, compute='compute_receiver_vat', readonly=True)
    state = fields.Selection([('open', 'Open'),('accepted', 'Accepted')], required=True, default='open', readonly=True)
    tax_condition = fields.Selection([('01', 'Generate IVA Credit'),('02', 'Generate parcial IVA Credit'),('03', 'Capital Property'),('04', 'Does not Generate Credit'),('05', 'Proportionality')])
    tax_credit = fields.Float(digits=(18,5))
    tax_total_amount = fields.Char(required=True, readonly=True, default="0")
    total_invoice = fields.Float(required=True, readonly=True, default="0")
    type = fields.Selection([('05', 'Full Acceptance'),('06', 'Parcial Acceptance'),('07', 'Rejection')], required=True, compute='compute_type')
    terminal = fields.Char(required=True, readonly=True, compute='compute_terminal')
    xml_file = fields.Binary('Document')
    xml_name = fields.Char(index=True)
    xml_response = fields.Binary(readonly=True)
    xml_response_name = fields.Char(index=True)

    response_key = fields.Char(readonly=True, default="0000000000")
    response_total_invoice = fields.Float(required=True, readonly=True, default="0")
    pdf_preview = fields.Binary( attachment=True)

    def update_PDF_preview(self):
        report = self.env['ir.actions.report'].sudo().search([('model','=','mw.electronic_invoice_acceptance')])
        if report:
            pdf = self.env.ref(report[0].xml_id)._render_qweb_pdf(self.id)[0]
            base64PDF = base64.encodestring(pdf)
            self.write({'pdf_preview': base64PDF})
        else:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                        'title': _('Warning!'),
                        'message': 'There are not any Reports to create a PDF file.',
                    'sticky': False,
                }
            }
            return message

    def generate_security_code(self):			
        codeLen = 8
        vals = "0123456789"
        cryptogen = SystemRandom()
        code = ""
        while codeLen > 0:
            code = code + cryptogen.choice(vals)
            codeLen = codeLen - 1
        return code
    
    def load_document(self):
        try:
            string = base64.b64decode(self.xml_file)
            tree = ElementTree(fromstring(string))
            children = tree.getroot().getchildren()
            
            for element in children:
                element_tag = element.tag.split('}')[1]
                if element_tag == 'Clave':
                    self.key = element.text # Clave
                elif element_tag == 'CodigoActividad':                
                    self.activity_code = element.text # Codigo Actividad
                elif element_tag == 'FechaEmision':
                    self.issue_date = element.text # Fecha Emision
                elif element_tag == 'Emisor':
                    for var in element:
                        var_tag = var.tag.split('}')[1]
                        if var_tag == 'Nombre':
                            self.emitter_name = var.text # Nombre
                        if var_tag == 'Identificacion':
                            self.emitter_vat_type = var[0].text # Tipo de Identificación
                            self.emitter_vat_id = var[1].text # Numero de Identificación
                elif element_tag == 'ResumenFactura':
                    for var in element:
                        var_tag = var.tag.split('}')[1]
                        if var_tag == 'TotalImpuesto':
                            self.tax_total_amount = var.text # Total Impuesto
                        if var_tag == 'TotalComprobante':
                            self.total_invoice = var.text
                    break

        except:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('LOAD DOCUMENT ERROR'),
                    'message': "Document does not exist or is not valid.",
                    'sticky': False,
                }
            }
            return message

    def accept_bounce(self):

        constants = self.env['ir.config_parameter'].sudo()
        url = 'https://www.comprobanteselectronicoscr.com/api/acceptbounce.stag.43'
        if not bool(constants.get_param('mw_electronic_invoice.is_sandbox')):
            url = 'https://www.comprobanteselectronicoscr.com/api/acceptbounce.prod.43'
        headers = {'Content-Type': 'application/json'}

        json_data = {
            "api_key": constants.get_param('mw_electronic_invoice.api_key'),
            "clave":{
                "tipo": self.type,
                "sucursal": self.branch,
                "terminal": self.terminal,
                "numero_documento": self.key,
                "numero_cedula_emisor": self.emitter_vat_id,
                "fecha_emision_doc": self.issue_date,
                "mensaje": self.message,
                "detalle_mensaje": self.message_detail,
                "codigo_actividad": self.receiver_economic_activity.code,
                "condicion_impuesto": self.tax_condition,
                "impuesto_acreditar": self.tax_credit,
                "gasto_aplicable": self.applicable_expense,
                "monto_total_impuesto": self.tax_total_amount,
                "total_factura": self.total_invoice,
                "numero_cedula_receptor": self.receiver_vat_id,
                "num_consecutivo_receptor": "1",
                "situacion_presentacion": self.presentation_situation,
                "codigo_seguridad": self.generate_security_code()
            },
            "emisor":{
                "identificacion":{
                    "tipo": self.emitter_vat_type,
                    "numero": self.emitter_vat_id
                }
            },
            "parametros":{
                "enviodgt": "A"
            }
        }

        data = json.dumps(json_data)
        response = requests.post(url=url, data=data, headers=headers).json()
        response_code = response['code']
        
        success = response_code == 1 or response_code == 44

        if success:
            self.sudo().write({'state':'accepted'})
            self.xml_response = response['data']
            self.xml_response_name = 'XML-' + self.key + '.xml'
            
            string = base64.b64decode(self.xml_response)
            tree = ElementTree(fromstring(string))
            children = tree.getroot().getchildren()
            self.response_total_invoice = children[9].text
            self.sudo().write({'response_key' : children[11].text})
            self.update_PDF_preview()
            
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('LOAD DOCUMENT'),
                    'message': "Success!!",
                    'sticky': False,
                }
            }
            return message
        
        electronic_invoice_log = self.env['mw.electronic_invoice_log'].sudo().create({
            'amount': self.tax_total_amount,
            'acceptance': self.id,
            'issue_datetime': datetime.datetime.now(),
            'request': str(data),
            'response': str(response),
            'response_code': self.env['mw.response_code'].sudo().search([('code','=',str(response['code']))])[0].id,
            'success': success,
            'url': url
        })


    @api.depends('receiver_economic_activity')
    def compute_activity(self):	
        for record in self:
            emitter_id = int(self.env['ir.config_parameter'].sudo().get_param('mw_electronic_invoice.emitter'))
            emitter = self.env['res.partner'].sudo().search([('id','=',emitter_id)])
            record.receiver_economic_activity = emitter.mw_economic_activity.id if emitter else False

    @api.depends('branch')
    def compute_branch(self):	
        for record in self:
            emitter_id = int(self.env['ir.config_parameter'].sudo().get_param('mw_electronic_invoice.emitter'))
            emitter = self.env['res.partner'].sudo().search([('id','=',emitter_id)])
            record.branch = emitter.mw_branch if emitter else False

    @api.depends('message')
    def compute_consecutive(self):	
        for record in self:
            constants = self.env['ir.config_parameter'].sudo()
            if record.message == '1':
                record.receiver_consecutive = int(constants.get_param('mw_electronic_invoice.next_full_acceptance_consecutive'))
            elif record.message == '2':
                record.receiver_consecutive = int(constants.get_param('mw_electronic_invoice.next_partial_acceptance_consecutive'))
            else:
                record.receiver_consecutive = int(constants.get_param('mw_electronic_invoice.next_rejection_consecutive'))

    @api.depends('terminal')
    def compute_terminal(self):	
        for record in self:
            emitter_id = int(self.env['ir.config_parameter'].sudo().get_param('mw_electronic_invoice.emitter'))
            emitter = self.env['res.partner'].sudo().search([('id','=',emitter_id)])
            record.terminal = emitter.mw_branch_terminal if emitter else False

    @api.depends('receiver_vat_id')
    def compute_receiver_vat(self):	
        for record in self:
            emitter_id = int(self.env['ir.config_parameter'].sudo().get_param('mw_electronic_invoice.emitter'))
            emitter = self.env['res.partner'].sudo().search([('id','=',emitter_id)])
            record.receiver_vat_id = emitter.mw_id if emitter else False

    @api.depends('message')
    def compute_type(self):	
        for record in self:
            if record.message == '1':
                record.type = '05'
            elif record.message == '2':
                record.type = '06'
            else:
                record.type = '07'