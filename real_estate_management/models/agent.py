from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class RealEstateAgent(models.Model):
    _name = 'real.estate.agent'
    _description = 'Real Estate Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'total_sales_volume desc, total_deals desc'

    # Basic Information
    name = fields.Char(string='Agent Name*', required=True, tracking=True)
    image = fields.Image(string='Profile Photo', max_width=400, max_height=400)
    designation = fields.Selection([
        ('agent', 'Agent'),
        ('senior_agent', 'Senior Agent'),
        ('principal_agent', 'Principal Agent'),
        ('broker', 'Broker'),
    ], string='Designation*', required=True, default='agent')

    expertise_level = fields.Selection([
        ('standard', 'Standard Agent'),
        ('luxury', 'Luxury Expert'),
    ], string='Expertise Level', default='standard')

    # Contact Details
    email = fields.Char(string='Email*', required=True)
    phone = fields.Char(string='Phone*', required=True)
    whatsapp = fields.Char(string='WhatsApp Number')

    # Location
    city = fields.Char(string='City*', required=True)
    state_id = fields.Many2one('res.country.state', string='State')
    zip_code = fields.Char(string='ZIP Code')

    # Professional Details
    license_number = fields.Char(string='License Number')
    experience_years = fields.Integer(string='Years of Experience', default=0)
    specializations = fields.Many2many(
        'property.category',
        'agent_category_rel',
        'agent_id',
        'category_id',
        string='Property Specializations'
    )

    # Performance Metrics
    total_sales_volume = fields.Monetary(
        string='Total Sales Volume',
        currency_field='currency_id',
        help='Total value of properties sold'
    )
    total_deals = fields.Integer(string='Total Deals Closed', default=0)
    avg_rating = fields.Float(string='Average Rating', digits=(2, 1), default=5.0)
    review_count = fields.Integer(string='Number of Reviews', default=0)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Linked Properties
    property_ids = fields.One2many(
        'property.property',
        'agent_id',
        string='Assigned Properties'
    )
    active_property_count = fields.Integer(
        string='Active Listings',
        compute='_compute_active_property_count',
        store=True
    )

    # Bio & Description
    short_bio = fields.Text(string='Short Bio', help='Brief introduction (100-200 chars)')
    detailed_bio = fields.Html(string='Detailed Biography')

    # Achievements
    awards = fields.Text(string='Awards & Certifications')
    languages_spoken = fields.Char(string='Languages Spoken', default='English, Hindi')

    # Availability
    is_active = fields.Boolean(string='Active Agent', default=True)
    is_accepting_clients = fields.Boolean(string='Accepting New Clients', default=True)

    # SEO
    seo_keywords = fields.Char(string='SEO Keywords')

    # Social Media
    linkedin_url = fields.Char(string='LinkedIn Profile')
    facebook_url = fields.Char(string='Facebook Profile')

    @api.depends('property_ids', 'property_ids.is_published')
    def _compute_active_property_count(self):
        for agent in self:
            agent.active_property_count = len(agent.property_ids.filtered('is_published'))

    @api.constrains('email')
    def _check_email(self):
        for agent in self:
            if agent.email and '@' not in agent.email:
                raise ValidationError("Please enter a valid email address")

    @api.constrains('avg_rating')
    def _check_rating(self):
        for agent in self:
            if agent.avg_rating < 0 or agent.avg_rating > 5:
                raise ValidationError("Rating must be between 0 and 5")

    def action_view_properties(self):
        """View all properties assigned to this agent"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - Properties',
            'res_model': 'property.property',
            'view_mode': 'list,form',
            'domain': [('agent_id', '=', self.id)],
            'context': {'default_agent_id': self.id},
        }
