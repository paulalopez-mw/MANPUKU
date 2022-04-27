# -*- coding: utf-8 -*-
import logging
import json
from urllib.parse import unquote
from odoo.http import request
from odoo import SUPERUSER_ID
from odoo import registry as registry_get
from odoo import api, fields, models, exceptions
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

_logger = logging.getLogger(__name__)

class MWResponseCreator(models.Model):

    _name = "mw.response_code_creator"
    _model = "mw.response_code_creator"
    _description = "Midware Response Creator"

    @api.model
    def read_responses(self):

        responses = [
            {
                'code': '0',
                'message': 'Unknown Error',
                'comments': 'Unknown error during process execution.'
            },
            {
                'code': '1',
                'message': 'Success',
                'comments': 'Correct execution of the process, the return data is included for reference.'
            },
            {
                'code': '2',
                'message': 'HTTPS Required',
                'comments': 'Requires execution via https.'
            },
            {
                'code': '3',
                'message': 'Authentication Required',
                'comments': 'It requires that the KEY API be included within the parameters in order to perform the process.'
            },
            {
                'code': '4',
                'message': 'Authentication Failed',
                'comments': 'Authentication process failed due to incorrect KEY API.'
            },
            {
                'code': '5',
                'message': 'Invalid Request',
                'comments': 'Invalid Request.'
            },
            {
                'code': '6',
                'message': 'Invalid Response Format',
                'comments': 'Invalid request response format.'
            },
            {
                'code': '10',
                'message': 'Incomplete Data',
                'comments': 'Incomplete data in the application.'
            },
            {
                'code': '11',
                'message': 'Incorrect Email',
                'comments': 'Incorrect Email.'
            },
            {
                'code': '12',
                'message': 'Incorrect Phone Number',
                'comments': 'Incorrect telephone number, only accept numerical values.'
            },
            {
                'code': '13',
                'message': 'Incorrect Exchange Rate',
                'comments': 'Incorrect Exchange Rate, only accept numerical values.'
            },
            {
                'code': '14',
                'message': 'Incorrect Id',
                'comments': 'The ID of the request is incorrect or no data related to it is found.'
            },
            {
                'code': '15',
                'message': 'Incorrect Numerical Value',
                'comments': 'Incorrect Numerical Value.'
            },
            {
                'code': '16',
                'message': 'Incorrect Id Client',
                'comments': 'The Client ID included in the request is not in the system.'
            },
            {
                'code': '17',
                'message': 'Incorrect Currency Type',
                'comments': 'The currency format is incorrect.'
            },
            {
                'code': '18',
                'message': 'Total amount do not match',
                'comments': 'The amounts of the invoices do not match the amounts of the corresponding details.'
            },
            {
                'code': '19',
                'message': 'Incorrect Invoice Number',
                'comments': 'The Invoice Number included in the application is not in the system.'
            },
            {
                'code': '20',
                'message': 'Incorrect Payment Type',
                'comments': 'The type of payment indicated is not correct.'
            },
            {
                'code': '21',
                'message': 'Incorrect Payment Amount',
                'comments': 'The payment amount indicated is greater than the invoice amount.'
            },
            {
                'code': '22',
                'message': 'Company not found',
                'comments': 'No company linked to email.'
            },
            {
                'code': '23',
                'message': 'Incorrect address',
                'comments': 'Incorrect URL.'
            },
            {
                'code': '24',
                'message': 'Incorrect version number',
                'comments': 'Incorrect Electronic Invoice version number.'
            },
            {
                'code': '25',
                'message': 'Incorrect method name',
                'comments': 'Incorrect method name.'
            },
            {
                'code': '26',
                'message': 'Incorrect environment param',
                'comments': 'Incorrect environment.'
            },
            {
                'code': '27',
                'message': 'XML Error',
                'comments': 'Error en el XML.'
            },
            {
                'code': '28',
                'message': 'Validation Error',
                'comments': 'XML validation failed.'
            },
            {
                'code': '29',
                'message': 'Document presented previously',
                'comments': 'Document number previously used.'
            },
            {
                'code': '30',
                'message': 'Error signing document',
                'comments': 'Error signing document.'
            },
            {
                'code': '31',
                'message': 'Error in logging with Hacienda',
                'comments': 'Logging error with the General Directorate of Taxation.'
            },
            {
                'code': '32',
                'message': 'Error presenting document in Hacienda',
                'comments': 'Error in the presentation of the document before the General Directorate of Taxation.'
            },
            {
                'code': '33',
                'message': 'Document not found',
                'comments': 'Document consulted not found.'
            },
            {
                'code': '34',
                'message': 'Invalid JSON',
                'comments': 'Invalid JSON structure.'
            },
            {
                'code': '35',
                'message': 'Incorrect Parameters',
                'comments': 'Use: UPDATE_CRT and UPDATE_USER to correct this error. It is required to update user information (user or password in the DGT).'
            },
            {
                'code': '36',
                'message': 'Pending Confirmation',
                'comments': 'Pending confirmation of acceptance - rejection, pending by the DGT.'
            },
            {
                'code': '37',
                'message': 'Check Date',
                'comments': 'Verify the date of the document.'
            },
            {
                'code': '38',
                'message': 'Invalid emails',
                'comments': 'The emails are invalid or you must separate the emails with semicolons (;).'
            },
            {
                'code': '39',
                'message': 'Invalid Key',
                'comments': 'Invalid document key or does not correspond to the emitter.'
            },
            {
                'code': '40',
                'message': 'Document Rejected',
                'comments': 'Unable to send, the document is rejected by the DGT..'
            },
            {
                'code': '41',
                'message': 'Incorrect Values',
                'comments': 'Review the parameters and values ​​sent.'
            },
            {
                'code': '42',
                'message': 'Check IP',
                'comments': 'Verify the list of IP enabled for the presentation of documents.\nThis is presented when a request is received from an IP not enabled within the panel.\nIf you do not have an added IP, all documents received from any IP are processed.'
            },
            {
                'code': '43',
                'message': 'Check Key',
                'comments': 'Verify the information of the document sent, the document key is already registered.'
            },
            {
                'code': '44',
                'message': 'Check Consecutive',
                'comments': 'Verify the information of the document sent, the number of consecutive is already registered.'
            },
            {
                'code': '45',
                'message': 'Verify D.G.T. parameters',
                'comments': 'There was an error processing the document, please check the ATV parameters.'
            },
            {
                'code': '46',
                'message': 'Queued Document',
                'comments': 'The document is pending submission.'
            },
            {
                'code': '47',
                'message': 'Inquiry not available',
                'comments': 'According to the instructions of the DGT, the period of 3 hours must be given to consult the document.'
            }
        ]

        for response in responses:
            response_code = self.env['mw.response_code'].sudo().search([('code','=',response['code'])])
            # If the Response Code doesn't exist, create it.
            if not response_code:        
                self.env['mw.response_code'].sudo().create({'code': response['code'], 'message': str(response['message']), 'comments': response['comments']})

        _logger.info("The Response Codes were stored in the database.")