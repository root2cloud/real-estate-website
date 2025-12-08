{
    'name': 'Real Estate Management',
    'version': '1.0',
    'license': 'LGPL-3',
    'category': 'Website',
    'summary': 'Module for managing real estate properties and website integration',
    'description': 'Manage real estate properties with interactive map, listings, and contact forms.',
    'depends': ['base', 'base_geolocalize', 'web', 'website_sale', 'mail', 'base_setup'],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # data
        'data/mail_property_rejection.xml',

        # Views
        'views/property_views.xml',
        'views/property_category_views.xml',
        'views/menu.xml',
        'views/property_registration_views.xml',

        # Qweb Templates
        'views/qweb_templates/property_map_template.xml',
        'views/qweb_templates/property_detail_page.xml',
        'views/qweb_templates/properties_menu_page.xml',
        'views/qweb_templates/website_registration_template.xml',

    ],
    'assets': {
        'web.assets_frontend': [
            'real_estate_management/static/src/js/property_map.js',
            # 'real_estate_management/static/src/css/property_map.css',
        ],
    },
    'installable': True,
    'application': True,
}
