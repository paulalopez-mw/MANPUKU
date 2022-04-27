# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions

class MWProvince(models.Model):

	_name = "mw.province"
	_model = "mw.province"
	_description = "Midware Province"

	name = fields.Char(required=True, readonly=True)
	code = fields.Char(size=1, required=True, readonly=True)