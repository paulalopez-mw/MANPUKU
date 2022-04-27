# -*- coding: utf-8 -*-
import time
import datetime
import base64
from datetime import timedelta
import base64

import logging
from odoo import http
from odoo.http import request
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models
from openerp.http import Response
import requests
import json
import ast
import yaml
from odoo.exceptions import UserError
from xml.etree.ElementTree import fromstring, ElementTree

_logger = logging.getLogger(__name__)

class ElectronicInvoice(http.Controller):

    @http.route('/electronic-invoice/callback', type='json', auth='public', methods=['POST', 'GET'], website=True, csrf=False)
    def callback_function(self, **arg):

        data = request.httprequest.data
        data_in_json = yaml.load(data)
        result = "Ok"
        success = False

        if not data_in_json.get('clave') is None:
            is_a_electronic_invoice = True

            # Electronic Invoice
            object = request.env['mw.electronic_invoice'].sudo().search([('key','=',data_in_json['clave'])])
            if not object:
                # Credit Note
                object = request.env['mw.credit_note'].sudo().search([('key','=',data_in_json['clave'])])
                is_a_electronic_invoice = False
        
            if object:
                object = object[0]
                message = False
                if not data_in_json.get('respuesta-xml') is None:
                    success = data_in_json['ind-estado'] == 'aceptado'
                    result = data_in_json['respuesta-xml']

                    if not success:
                        string = base64.b64decode(result)
                        tree = ElementTree(fromstring(string))
                        children = tree.getroot().getchildren()
                        for element in children:
                            element_tag = element.tag.split('}')[1]
                            if element_tag == 'DetalleMensaje':
                                message = element.text
                            
                    object.write({
                        'on_error': not success,
                        'received_XML_file' : result,
                        'received_XML_file_name' : 'ARC-' + data_in_json['clave'] + '.xml',
                        'state' : 'completed' if success else 'pending'
                        }) 

                    # invoice = request.env['account.invoice'].sudo().search([('mw_electronic_invoice','=',electronic_invoice.id)])
                    # obj = request.env['mail.message'].sudo()
                    # data = {
                    #     'subject': 'Testing',
                    #     'body': str(datetime.datetime.now()),
                    #     'subtype_id': 16,
                    #     'message_type': 'email',
                    #     'res_id': invoice.id,
                    #     'model': 'account.invoice',
                    #     'author_id': 1
                    # }
                    # obj.create(data)
                    # ATTACHMENT_NAME = 'ARC-' + data_in_json['clave']
                    # request.env['ir.attachment'].sudo().create({
                    #     'name': ATTACHMENT_NAME + '.xml',
                    #     'type': 'binary',
                    #     'datas': data_in_json['respuesta-xml'],
                    #     # 'datas_fname': ATTACHMENT_NAME + '.xml',
                    #     'store_fname': ATTACHMENT_NAME,
                    #     'res_model': 'account.invoice',
                    #     'res_id': invoice.id,
                    #     'mimetype': 'application/xml'
                    # }) 
                    
                elif not data_in_json.get('ind-estado') is None:
                    result = data_in_json['ind-estado']
                    object.write({ 'on_error' : True, 'state' : 'pending'})
                else:
                    result = 'The Request does not contain XML Response or State.'

                request.env['mw.electronic_invoice_log'].sudo().create({
                    'electronic_invoice': object.id if is_a_electronic_invoice else object.electronic_invoice.id,
                    'credit_note': False if is_a_electronic_invoice else object.id,
                    'is_a_request' : False,
                    'issue_datetime': datetime.datetime.now(),
                    'rejection_message': message,
                    'request': str(data),
                    'response': str({'status' : '200', 'result': result}),
                    'response_code': False,
                    'success': success,
                    'url': '/electronic-invoice/callback'
                })
            else:
                request.env['mw.electronic_invoice_log'].sudo().create({
                    'electronic_invoice': False,
                    'is_a_request' : False,
                    'issue_datetime': datetime.datetime.now(),
                    'request': str(data),
                    'response': str({'status' : '200', 'result': 'The Electronic Invoice does not exist.'}),
                    'response_code': False,
                    'success': success,
                    'url': '/electronic-invoice/callback'
                })
        else:
            result = 'The Request does not contain key.'

            request.env['mw.electronic_invoice_log'].sudo().create({
                'electronic_invoice': False,
                'is_a_request' : False,
                'issue_datetime': datetime.datetime.now(),
                'request': str(data),
                'response': str({'status' : '200', 'result': result}),
                'response_code': False,
                'success': success,
                'url': '/electronic-invoice/callback'
            })
        return {'status' : '200', 'result': result}