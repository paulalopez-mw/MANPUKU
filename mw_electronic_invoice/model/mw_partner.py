from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

class MWPartner(models.Model):
    _inherit = 'res.partner'
    _name = 'res.partner'

    def default_economic_activity(self):      
        # If not ubication, activity or response, create it again
        if not self.env['mw.electronic_invoice_cabys'].sudo().search_count([]):
            cabys = self.env['mw.electronic_invoice_cabys'].read_categories()
        if not self.env['mw.ubication'].sudo().search_count([]):
            ubication = self.env['mw.ubication'].read_ubications()
        if not self.env['mw.activity_creator'].sudo().search_count([]):
            activity_creator = self.env['mw.activity_creator'].read_activities()
        if not self.env['mw.response_code_creator'].sudo().search_count([]):
            response_creator = self.env['mw.response_code_creator'].read_responses()

        result = self.env['mw.activity'].sudo().search([('code','=',722003)])
        return result[0].id if result else 0
        
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

    mw_branch = fields.Integer(required=True, default=1, string="Branch")
    mw_branch_number = fields.Integer(default=1, required=True, string="Branch Number")
    mw_branch_terminal = fields.Integer(default=1, index=True, required=True, string="Branch Terminal")
    mw_id = fields.Char(default='000000001', string="USER ID", required=True)
    mw_id_type = fields.Selection([('01', 'Physical ID'),('02', 'Legal ID'),('03', 'DIMEX'),('04', 'NITE')], default='01', required=True, string="USER ID Type")
    mw_economic_activity = fields.Many2one('mw.activity', required=True, index=True, default=default_economic_activity, string="Economic Activity")
    mw_phone_code = fields.Integer(default=506, required=True, string="Phone Code")
    mw_phone_number = fields.Char(string="Phone Number", default="00000000")    
    mw_canton = fields.Many2one('mw.canton', required=True, index=True, default=default_canton, string="Canton")
    mw_district = fields.Many2one('mw.district', required=True, index=True, default=default_district, string="District")
    mw_province = fields.Many2one('mw.province', index=True, required=True, default=default_province, string="Province")
    mw_other_signs = fields.Char(default="Other Signs", string="Other Signs", required=True)
    mw_street = fields.Many2one('mw.street', required=True, index=True, default=default_street, string="Street")

    @api.constrains('mw_branch_number')
    def _check_branch_number(self):
        for record in self:
            branch_number_len = len(str(record.mw_branch_number))
            if branch_number_len > 3:
                raise ValidationError("Branch Number must be a maximum of 3 digits.")

    @api.constrains('mw_branch_terminal')
    def _check_branch_terminal(self):
        for record in self:
            branch_terminal_len = len(str(record.mw_branch_terminal))
            if branch_terminal_len > 5:
                raise ValidationError("Branch Terminal must be a maximum of 5 digits.")

    @api.constrains('mw_id', 'mw_id_type')
    def _check_id(self):
        for record in self:
            actual_id_type = record.mw_id_type
            actual_id_size = len(record.mw_id)
            id_type = "Physical ID"
            id_digits = "9"
            isValid = False
            #raise ValidationError(actual_id_type + " " + actual_id_size)
            if record.mw_id.isdigit():
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
                else:
                    isValid = True
            if not isValid:
                raise ValidationError("If you selected " + id_type + " as USER ID type, the USER ID must have " + id_digits + " digits.")

    @api.constrains('mw_phone_code', 'mw_phone_number')
    def _check_phone(self):
        for record in self:
            phone_code_len = len(str(record.mw_phone_code))
            phone_number_len = len(record.mw_phone_number)
            if phone_code_len > 3 or phone_code_len < 1:
                raise ValidationError("Phone code must be a maximun of 3 digits.")
            if phone_number_len > 20 or phone_number_len < 1 or not record.mw_phone_number.isdigit():
                raise ValidationError("Phone number must be a number, with a maximun of 20 digits.")

    @api.constrains('mw_other_signs')
    def _check_other_signs(self):
        for record in self:
            other_signs_len = len(str(record.mw_other_signs))
            if other_signs_len > 250:
                raise ValidationError("Other Signs must be a maximun of 250 characters.")