# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions

class MWStreet(models.Model):

    _name = "mw.street"
    _model = "mw.street"
    _description = "Midware Street"

    district = fields.Many2one('mw.district', required=True, default=1, readonly=True)
    name = fields.Char(required=True, readonly=True)
    code = fields.Char(size=2, required=True, readonly=True)