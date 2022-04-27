# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions
import json
import os
import xlrd

_logger = logging.getLogger(__name__)

class MWCabys(models.Model):

    _name = "mw.electronic_invoice_cabys"
    _description = "Midware Electronic Invoice CABYS"

    category = fields.Char(size=13, required=True, readonly=True)
    name = fields.Text(required=True, readonly=True)
    # parent_category = fields.Many2one('mw.cabys', readonly=True, default=False)
    tax = fields.Char(size=3, readonly=True, default=False)
    
    def read_categories(self):
        try:
            # Open the Workbook
            workbook = xlrd.open_workbook(os.path.dirname(os.path.realpath(__file__)) + '/cabys.xlsx')
            # Open the worksheet
            worksheet = workbook.sheet_by_index(0)
            counter = 0
            for i in range(2, worksheet.nrows):
                # CHECK CATEGORY                 
                code = worksheet.cell_value(i, 16)
                category_record = self.env['mw.electronic_invoice_cabys'].sudo().search([('category','=',code)])
                if not category_record:
                    description = worksheet.cell_value(i, 17)
                    tax = worksheet.cell_value(i, 18)
                    self.env['mw.electronic_invoice_cabys'].sudo().create({'category': code, 'name': code + ' - ' + description, 'tax': tax})
            
        except:
            _logger.info("CABYS file not found.")