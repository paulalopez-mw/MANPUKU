# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions

class MWCanton(models.Model):

	_name = "mw.canton"
	_model = "mw.canton"
	_description = "Midware Canton"

	province = fields.Many2one('mw.province', readonly=True, required=True)
	name = fields.Char(required=True, readonly=True)
	code = fields.Char(size=2, required=True, readonly=True)