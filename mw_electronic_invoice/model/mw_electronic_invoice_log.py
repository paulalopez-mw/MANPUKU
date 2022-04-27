# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class MWElectronicInvoiceLog(models.Model):

    _name = "mw.electronic_invoice_log"
    _model = "mw.electronic_invoice_log"
    _description = "Midware Electronic Invoice Log"

    acceptance = fields.Many2one('mw.electronic_invoice_acceptance', readonly=True)
    amount = fields.Char(readonly=True)
    credit_note = fields.Many2one('mw.credit_note', readonly=True)
    electronic_invoice = fields.Many2one('mw.electronic_invoice', readonly=True)
    electronic_invoice_number = fields.Char(readonly=True, related='electronic_invoice.invoice_number', string="Invoice")
    is_a_request = fields.Boolean(default=True, readonly=True)
    issue_datetime = fields.Datetime(readonly=True)
    rejection_message = fields.Char(readonly=True)
    request = fields.Char(readonly=True)
    response = fields.Char(readonly=True)
    response_code = fields.Many2one('mw.response_code', readonly=True)
    code = fields.Char(readonly=True, related='response_code.code')
    comments = fields.Char(readonly=True, related='response_code.comments')
    message = fields.Char(readonly=True, related='response_code.message')
    success = fields.Boolean(default=False, readonly=True)
    url = fields.Char(string="URL", readonly=True)