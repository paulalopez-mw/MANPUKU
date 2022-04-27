from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

import logging

_logger = logging.getLogger(__name__)

class MWTax(models.Model):

    _name = "mw.tax"
    _model = "mw.tax"
    _description = "Midware Electronic Invoice Tax"

class MWAccountTax(models.Model):

    _inherit = "account.tax"
    _name = "account.tax"

    # Exoneration Fields    
    mw_exoneration_date = fields.Datetime(string="Exoneration Date")
    mw_exoneration_institution = fields.Char(string="Exoneration Institution")
    mw_exoneration_number = fields.Integer(default=0, string="Exoneration Number")
    mw_exoneration_percentage = fields.Float(default=0, string="Exoneration Percentage")
    mw_exoneration_type = fields.Selection([('01', 'Authorized Purchases'), ('02', 'Exempt from Diplomats Sales'), ('03', 'Authorized by Special Law'), ('04', 'Exemptions General Directorate of Finance'), ('05', 'Transient V'), ('06', 'Transient IX'), ('07', 'Transient XVII'), ('99', 'Others')], string="Exoneration Type")
    
    mw_tax_amount = fields.Float(digits=(18,5), readonly=True, string="Amount", default=0.0, compute='compute_tax_amount', index=True)
    mw_tax_code = fields.Selection([('01', 'Value Added Tax'), ('02', 'Selective Consumption Tax'), ('03', 'Single Fuel Tax'), ('04', 'Specific on Alcoholic Beverages Tax'), ('05', 'Specific About non-alcoholic Packaged Drinks and Toilet Soaps Tax'), ('06', 'Tobacco Products Tax'), ('07', 'IVA (special calculation)'), ('08', 'IVA Used Goods Regime (Factor)'), ('12', 'Cement Specific Tax'), ('98', 'Others')], string="Code")
    mw_tax_export = fields.Float(digits=(18,3), default=0.0, string="Export")
    mw_tax_iva_factor = fields.Float(digits=(5,4), default=0.0, string="IVA Factor")
    mw_tax_rate = fields.Float(digits=(5,2), string="Rate", compute='compute_tax_rate', index=True)
    mw_tax_rate_code = fields.Selection([('01', 'Rate 0% (Exempt)'), ('02', 'Reduced Rate 1%'), ('03', 'Reduced Rate 2%'), ('04', 'Reduced Rate 4%'), ('05', 'Transient 0%'), ('06', 'Transient 4%'), ('07', 'Transient 8%'), ('08', 'General Rate 13%')], string="Rate Code")


    @api.constrains('mw_tax_iva_factor')
    def _check_tax_iva_factor(self):		
        if self.mw_tax_iva_factor >= 10.0:
            raise ValidationError("IVA Factor must be less than 10.")

    @api.constrains('mw_tax_rate')
    def _check_tax_rate(self):
        if self.mw_tax_rate >= 100:
            raise ValidationError("Tax Rate must be less than 100.")

    @api.constrains('mw_exoneration_institution')
    def _check_institution(self):		
        if len(str(self.mw_exoneration_institution)) > 160:
            raise ValidationError("Exoneration Institution must have a maximum of 160 characters.")

    @api.constrains('mw_exoneration_number')
    def _check_exoneration_number(self):		
        if len(str(self.mw_exoneration_number)) > 40:
            raise ValidationError("Exoneration Number must have a maximum of 40 digits.")

    @api.constrains('mw_exoneration_percentage')
    def _check_exoneration_percentage(self):		
        if self.mw_exoneration_percentage > 100 or self.mw_exoneration_percentage < 0:
            raise ValidationError("Exoneration Percentage must be less than or equal to 100.")

    @api.constrains('mw_tax_export')
    def _check_export(self):
        tax_export_len = len(str(self.mw_tax_export).split(".")[0])
        if tax_export_len > 13:
            raise ValidationError("Tax Export must have a maximum of 13 digits in the integer part.")

    @api.constrains('mw_tax_rate')
    def _check_rate(self):
        if self.mw_tax_rate >= 100.0:
            raise ValidationError("Tax Rate must be less than 100.")
        if (self.mw_tax_code and self.mw_tax_code != '08') and (self.mw_tax_rate != self.amount):
            raise ValidationError("Tax Rate must be equal to Amount.")

    def get_exoneration_amount(self, price_subtotal):
        value = 0
        product = self.mw_exoneration_percentage * price_subtotal
        if product > 0:
            value = round(product / 100, 5)
        return value

    def get_tax_amount(self, tax_base, price_subtotal):
        actual_tax_code = self.mw_tax_code
        if actual_tax_code == '08':
            if self.mw_tax_base > 0.0:
                self.mw_tax_amount = (mw_tax_base * self.mw_tax_iva_factor) / 100
            else :
                self.mw_tax_amount = (price_subtotal * self.mw_tax_iva_factor) / 100
        else:
            self.mw_tax_iva_factor = False
            value = price_subtotal * self.mw_tax_rate
            if value > 0:
                value = value / 100        
        return round(value, 5)

    @api.depends('mw_tax_code', 'mw_tax_rate_code')
    def compute_tax_rate(self):
        for tax in self:
            actual_tax_code = tax.mw_tax_code
            if actual_tax_code == '01' or actual_tax_code == '07':
                actual_rate_code = tax.mw_tax_rate_code
                if actual_rate_code == '01':
                    tax.mw_tax_rate = 0.00
                elif actual_rate_code == '02':
                    tax.mw_tax_rate = 1.00
                elif actual_rate_code == '03':
                    tax.mw_tax_rate = 2.00
                elif actual_rate_code == '04':
                    tax.mw_tax_rate = 4.00
                elif actual_rate_code == '05':
                    tax.mw_tax_rate = 0.00
                elif actual_rate_code == '06':
                    tax.mw_tax_rate = 4.00
                elif actual_rate_code == '07':
                    tax.mw_tax_rate = 8.00
                elif actual_rate_code == '08':
                    tax.mw_tax_rate = 13.00           
                else:
                    tax.mw_tax_rate_code = False
                    tax.mw_tax_rate = 0.00
            else:
                tax.mw_tax_rate_code = False
                tax.mw_tax_rate = 0.00