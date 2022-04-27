import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions

class MWResponseCode(models.Model):

	_name = "mw.response_code"
	_model = "mw.response_code"
	_description = "Midware ATV Response Code"

	code = fields.Char(required=True, readonly=True)
	message = fields.Char(required=True, readonly=True)
	comments = fields.Char(required=True, readonly=True)