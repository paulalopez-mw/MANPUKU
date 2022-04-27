from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class MWProduct(models.Model):
    _inherit = 'product.template'
    _name = 'product.template'

    mw_category = fields.Many2one('mw.electronic_invoice_cabys', store=True, string='Category')

class MWInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    _name = 'account.move.line'

    # related fields
    # invoice_currency_id = fields.Many2one('res.currency', related="invoice_id.currency_id", readonly=True)
    # invoice_residual = fields.Monetary(related="invoice_id.ammount_residual", readonly=True, currency_field='currency_id')
    
    mw_code = fields.Char(string="Code")
    mw_code_type = fields.Selection([('01', 'Seller Product'),('02', 'Buyer Product'),('03', 'Product Assigned by the Industry'),('04', 'Internal Use'),('99', 'Other')], string="Code Type")
    mw_departure = fields.Char(string="Departure", default="", index=True)
    mw_discount_description = fields.Char(default="", string="Discount Description")

    mw_measurement_is_a_service = fields.Boolean(compute='compute_measurement', string="Measurement is a service")
    mw_measurement_unit = fields.Selection([('Al', 'Al - Rental of Residential Use'), ('Alc', 'Alc - Rental of Commercial Use'), ('Cmm', 'Cm - Commissions'), ('I', 'I - Interests'), ('Os', 'Os- Other Service'), ('Sp', 'Sp - Professional Service'), ('Spe', 'Spe - Personal Service'), ('St', 'St - Technical Services'), ('1', '1 - One'), 
            ('´', '´ - Minute'), ('´´', '´´ - second'), ('°C', '°C - Celsius Grade'), ('1/m', '1/m - 1 per meter'), ('A', 'A - Ampere'), ('A/m', 'A - Ampere per meter'), ('A/A/m²', 'A/m² - Ampere per square meter'), ('B', 'B - Bel'), ('Bq', 'Bq - Becquerel'), ('C', 'C - Coulomb'), ('C/kg', 'C/kg - Coulomb per kilogram'), 
            ('C/m²', 'C/m² - Coulomb per square meter'), ('C/m³', 'C/m³ - Coulomb per cubic meter'), ('cd', 'cd - Candela'), ('cd/m²', 'cd/m² - Candela per square meter'), ('cm', 'cm - Centimeter'), ('d', 'd - Day'), ('eV', 'eV - Electronvolt'), ('F', 'F - Farad'), ('F/m', 'F/m - Farad per meter'), ('g', 'g - Gram'), 
            ('Gal', 'Gal - Gallon'), ('Gy', 'Gy - Gray'), ('Gy/s', 'Gy/s - Gray per second'), ('He', 'H - Henry'), ('H/m', 'H/m - Henry per meter') , ('h', 'h - Hour'), ('J', 'J - Joule'), ('J/(kg·K)', 'J/(kg·K) - Joule per kilogram kelvin'), ('J/(mol·K)', 'J/(mol·K) - Joule per mol kelvin'), ('J/K', 'J/K - Joule per kelvin'), 
            ('J/kg', 'J/kg - Joule per kilogram'), ('J/m³', 'J/m³ - Joule per cubic meter'), ('J/mol', 'J/mol - Joule per mol'), ('K', 'K - Kelvin'), ('kat', 'kat - Katal'), ('K/m³', 'K/m³ - Katal per cubic meter'), ('Kg', 'Kg - Kilogram'), ('Kg/m³', 'Kg/m³ - Kilogram per cubic meter'), ('Km', 'Km - Kilometer'), ('Kw', 'Kw - Kilovatios'), 
            ('L', 'L - Liter'), ('lm', 'lm - Lumen'), ('In', 'In - Inch'), ('lx', 'lx - Lux'), ('m', 'm - Meter'), ('m/s', 'm/s - Meter per second'), ('m/s²', 'm/s² - Meter per square second'), ('m²', 'm² - Square meter'), ('m³', 'm³ - Cubic meter'), ('min', 'min - Minute'), ('mol', 'mol - Mol'), ('mol/m³', 'mol/m³ - Mol per cubic meter'), 
            ('N', 'N - Newton'), ('N/m', 'N/m - Newton per meter'), ('N·m', 'N·m - Newton meter'), ('Np', 'Np - Neper'), ('°', '° - Grade'), ('Oz', 'Oz - Ounces'), ('Pa', 'Pa - Pascal'), ('Pa·s', 'Pa·s - Pascal second'), ('rad', 'rad - Radian'), ('rad/s', 'rad/s - Radian per second'), ('rad/s²', 'rad/s² - Radian per square second'), 
            ('s', 's - Second'), ('Si', 'S - Siemens'), ('sr', 'sr - Stereoradian'), ('Sv', 'Sv - Sievert'), ('Te', 'T - Tesla'), ('t', 't - Ton'), ('u', 'u - Unified Atomic Mass Unit'), ('ua', 'ua - Astronomical Unit'), ('Unid', 'Unid - Unit'), ('V', 'V - Volt'), ('V/m', 'V/m - Volt per meter'), ('W', 'W - Watt'), ('W/(mol·K)', 'W/(mol·K) - Watt per meter kelvin'), 
            ('W/(m²·sr)', 'W/(m²·sr) - Watt per square meter stereoradian'), ('W/m²', 'W/m² - Watt per square meter'), ('W/sr', 'W/sr - Watt per stereoradian'), ('Wb', 'Wb - Weber'), ('Ω', 'Ω - Ohm'), ('Otros', 'Other')], required=True, default='Sp', string="Measurement Unit")
    mw_tax_base = fields.Float(required=True, digits=(18,3), default=0.0, string='Tax Base')
    mw_trade_measure = fields.Char(string="Trade Measure")

    def get_mw_measurement_unit(self):
        if self.mw_measurement_unit == 'Cmm':
            return 'Cm'
        elif self.mw_measurement_unit == 'He':
            return 'H'
        elif self.mw_measurement_unit == 'Si':
            return 'S'
        elif self.mw_measurement_unit == 'Te':
            return 'T'
        else:
            return self.mw_measurement_unit

    @api.constrains('mw_departure')
    def _check_departure(self):
        for record in self:
            departure_len = len(str(record.mw_departure))
            if departure_len > 15:
                raise ValidationError("Departure must be a maximum of 15 characters.")

    @api.constrains('mw_discount_description')
    def _check_discount_description(self):
        for record in self:
            discount_description_len = len(str(record.mw_discount_description))
            if discount_description_len > 80:
                raise ValidationError("Discount Description must be a maximum of 80 characters.")

    @api.constrains('mw_trade_measure')
    def _check_trade_measure(self):
        for record in self:
            trade_measure_len = len(str(record.mw_trade_measure))
            if trade_measure_len > 20:
                raise ValidationError("Trade Measure must be a maximum of 20 characters.")

    @api.depends('mw_measurement_unit')
    def compute_measurement(self):
        for line in self:
            result = False
            services = 	['Al' , 'Alc', 'Cmm', 'I', 'Os', 'Sp', 'Spe', 'St', '´´', 'd', 'h']
            if line.mw_measurement_unit in services:
                result = True
            line.mw_measurement_is_a_service = result