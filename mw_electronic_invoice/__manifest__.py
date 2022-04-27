# -*- coding: utf-8 -*-
{
    'name': "Electronic Invoice",
    'summary': "Midware Billing",
    'description': '',
    'author': "Midware",
    'category': 'Extra Tools',
    'version': '2.0',
    'application': True,
    'depends': ['base', 'web', 'base_geolocalize', 'mail', 'account'],
    'data': [
        'views/mw_invoice_line.xml',
        'views/mw_credit_note.xml',
        'views/mw_tax.xml',
        'views/mw_partner.xml',        
        'views/mw_acceptance_list.xml',
        'views/mw_acceptance.xml',
        'views/mw_electronic_invoice_log.xml',
        'views/mw_electronic_invoice.xml',
        'views/mw_electronic_invoice_list.xml',
        'actions/automated_actions.xml',
        'actions/view_electronic_invoice.xml',
        #'actions/mw_multiple_electronic_invoices.xml',
        'views/mw_electronic_invoice_settings.xml',
        'views/mw_product.xml',
        'security/ir.model.access.csv',
        # 'reports.xml',
    ]
}
