# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
import base64
import requests
import json
from odoo import http
from odoo.http import request
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'

    api_key = fields.Char(string="API Key", required=True)
    emitter = fields.Many2one('res.partner', default=1, index=True, required=True)
    is_sandbox = fields.Boolean(default=True)
    next_consecutive = fields.Integer(default=0, required=True)    
    next_credit_note_consecutive = fields.Integer(string="Next Consecutive (Credit Notes)", default=0, required=True)
    next_full_acceptance_consecutive = fields.Integer(default=0, required=True, string="Next Acceptance")
    next_partial_acceptance_consecutive = fields.Integer(default=0, required=True, string="Next Partial Acceptance")
    next_rejection_consecutive = fields.Integer(default=0, required=True, string="Next Rejection")
    receptor_email = fields.Char(default="ac@midwr.com", required=True)

    # Comprobantes Electronicos parameters
    frm_ws_ambiente = fields.Char(compute='compute_ambiente')
    frm_usuario = fields.Char('User', required=True)
    frm_password = fields.Char('Password', required=True)
    frm_callback_url = fields.Char('Callback URL')
    frm_crt = fields.Binary('Certificate')
    frm_crt_name = fields.Char(index=True)
    frm_pin = fields.Char('PIN', required=True, size=4)

    def __encode_to_base64(self, string):
        message_bytes = str(string).encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
        return base64_message

    def update_crt(self):
        url = 'https://www.comprobanteselectronicoscr.com/api/client.php?action=update_crt'
        headers = {'Content-Type': 'application/json'}

        json_data = {
            'api_key': self.api_key,
            'frm_ws_ambiente': self.frm_ws_ambiente,
            'frm_crt': self.frm_crt.decode(),
            'frm_pin': self.frm_pin
        }

        data = json.dumps(json_data)
        response = requests.post(url=url, data=data, headers=headers).json()

        result_message = str(json_data) + '\n\n\n\n' + str(response)

        if response['status'] == 1:
            result_message = 'Success!!'
				
        message = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('UPDATE RESULT'),
                'message': result_message,
                'sticky': True,
            }
        }
        return message

    def update_user(self):
        url = 'https://www.comprobanteselectronicoscr.com/api/client.php?action=update_user'
        headers = {'Content-Type': 'application/json'}

        json_data = {
            'api_key': self.api_key,
            'frm_ws_ambiente': self.frm_ws_ambiente,
            'frm_usuario': self.__encode_to_base64(self.frm_usuario),
            'frm_password': self.__encode_to_base64(self.frm_password),
            'frm_callback_url': self.frm_callback_url + '/electronic-invoice/callback'
        }

        data = json.dumps(json_data)
        response = requests.post(url=url, data=data, headers=headers).json()

        result_message = 'Success!!'

        if response['status'] != 1:
            result_message = response['msg']
				
        message = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('UPDATE RESULT'),
                'message': result_message,
                'sticky': True,
            }
        }
        return message


    @ api.depends('is_sandbox')
    def compute_ambiente(self):
        self.frm_ws_ambiente = "c3RhZw=="
        if not self.is_sandbox:
            self.frm_ws_ambiente = "cHJvZA=="

    def set_values(self):

        super(ResConfigSettings, self).set_values()

        select_type = self.env['ir.config_parameter'].sudo()
        select_type.set_param('mw_electronic_invoice.api_key', self.api_key)
        select_type.set_param('mw_electronic_invoice.emitter',self.emitter.id)
        select_type.set_param('mw_electronic_invoice.is_sandbox',self.is_sandbox)

        select_type.set_param('mw_electronic_invoice.next_consecutive', self.next_consecutive)
        select_type.set_param('mw_electronic_invoice.next_credit_note_consecutive', self.next_credit_note_consecutive)
        select_type.set_param('mw_electronic_invoice.next_full_acceptance_consecutive',self.next_full_acceptance_consecutive)
        select_type.set_param('mw_electronic_invoice.next_partial_acceptance_consecutive', self.next_partial_acceptance_consecutive)
        select_type.set_param('mw_electronic_invoice.next_rejection_consecutive',self.next_rejection_consecutive)
        select_type.set_param('mw_electronic_invoice.receptor_email',self.receptor_email)

        select_type.set_param('mw_electronic_invoice.frm_ws_ambiente',self.frm_ws_ambiente)
        select_type.set_param('mw_electronic_invoice.frm_usuario', self.frm_usuario)
        select_type.set_param('mw_electronic_invoice.frm_password',self.frm_password)
        select_type.set_param('mw_electronic_invoice.frm_callback_url',self.frm_callback_url)
        select_type.set_param('mw_electronic_invoice.frm_crt', self.frm_crt)
        select_type.set_param('mw_electronic_invoice.frm_crt_name',self.frm_crt_name)
        select_type.set_param('mw_electronic_invoice.frm_pin',self.frm_pin)

    @api.model
    def get_values(self):

        res = super(ResConfigSettings, self).get_values()

        select_type = self.env['ir.config_parameter'].sudo()
        api_key = select_type.get_param('mw_electronic_invoice.api_key')
        emitter = select_type.get_param('mw_electronic_invoice.emitter')
        is_sandbox = select_type.get_param('mw_electronic_invoice.is_sandbox')

        next_consecutive = select_type.get_param('mw_electronic_invoice.next_consecutive')
        next_credit_note_consecutive = select_type.get_param('mw_electronic_invoice.next_credit_note_consecutive')
        next_full_acceptance_consecutive = select_type.get_param('mw_electronic_invoice.next_full_acceptance_consecutive')
        next_partial_acceptance_consecutive = select_type.get_param('mw_electronic_invoice.next_partial_acceptance_consecutive')
        next_rejection_consecutive = select_type.get_param('mw_electronic_invoice.next_rejection_consecutive')
        receptor_email = select_type.get_param('mw_electronic_invoice.receptor_email')

        frm_ws_ambiente = select_type.get_param('mw_electronic_invoice.frm_ws_ambiente')
        frm_usuario = select_type.get_param('mw_electronic_invoice.frm_usuario')
        frm_password = select_type.get_param('mw_electronic_invoice.frm_password')
        frm_callback_url = select_type.get_param('mw_electronic_invoice.frm_callback_url')
        frm_crt = select_type.get_param('mw_electronic_invoice.frm_crt')
        frm_crt_name = select_type.get_param('mw_electronic_invoice.frm_crt_name')
        frm_pin = select_type.get_param('mw_electronic_invoice.frm_pin')
        
        res.update({'api_key': api_key})
        res.update({'emitter': int(emitter)})
        res.update({'is_sandbox': bool(is_sandbox)})

        res.update({'next_consecutive': int(next_consecutive)})
        res.update({'next_credit_note_consecutive': int(next_credit_note_consecutive)})
        res.update({'next_full_acceptance_consecutive': int(next_full_acceptance_consecutive)})
        res.update({'next_partial_acceptance_consecutive': int(next_partial_acceptance_consecutive)})
        res.update({'next_rejection_consecutive': int(next_rejection_consecutive)})
        res.update({'receptor_email': receptor_email})

        res.update({'frm_ws_ambiente': frm_ws_ambiente})
        res.update({'frm_usuario': frm_usuario})
        res.update({'frm_password': frm_password})
        res.update({'frm_callback_url': frm_callback_url})
        res.update({'frm_crt': frm_crt})
        res.update({'frm_crt_name': frm_crt_name})
        res.update({'frm_pin': frm_pin})

        return res