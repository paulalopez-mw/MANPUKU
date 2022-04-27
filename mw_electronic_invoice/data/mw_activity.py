import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions

class MWActivty(models.Model):

	_name = "mw.activity"
	_model = "mw.activity"
	_description = "Midware Activity"

	code = fields.Char(required=True, readonly=True)
	name = fields.Char(required=True)
	description = fields.Char(readonly=True)