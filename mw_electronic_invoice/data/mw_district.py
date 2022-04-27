# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions

class MWDistrict(models.Model):

	_name = "mw.district"
	_model = "mw.district"
	_description = "Midware District"

	canton = fields.Many2one('mw.canton', required=True, default=1, readonly=True)
	name = fields.Char(required=True, readonly=True)
	code = fields.Char(size=2, required=True, readonly=True)