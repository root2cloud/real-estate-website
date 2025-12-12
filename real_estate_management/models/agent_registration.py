# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AgentRegistration(models.Model):
    _name = 'agent.registration'
    _description = 'Agent Registration Requests'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Registration ID', readonly=True, default='New', copy=False)
    agent_name = fields.Char(string='Full Name', required=True, tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone Number', required=True, tracking=True)
    whatsapp = fields.Char(string='WhatsApp Number')

    designation = fields.Selection([
        ('agent', 'Agent'),
        ('senior_agent', 'Senior Agent'),
        ('principal_agent', 'Principal Agent'),
        ('broker', 'Broker'),
    ], string='Desired Designation', required=True, default='agent')

    expertise_level = fields.Selection([
        ('standard', 'Standard Agent'),
        ('luxury', 'Luxury Expert'),
    ], string='Expertise Level', required=True, default='standard')

    license_number = fields.Char(string='License Number')
    experience_years = fields.Integer(string='Years of Experience', default=0)

    city = fields.Char(string='City', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    zip_code = fields.Char(string='ZIP Code')
    country_id = fields.Many2one('res.country', string='Country')

    short_bio = fields.Text(string='Short Bio')
    detailed_bio = fields.Html(string='Detailed Biography')
    qualifications = fields.Text(string='Qualifications')
    languages_spoken = fields.Char(string='Languages Spoken', default='English, Hindi')

    specialization_ids = fields.Many2many(
        'property.category',
        'agent_registration_category_rel',
        'registration_id',
        'category_id',
        string='Property Specializations'
    )

    profile_image = fields.Image(string='Profile Photo', max_width=400, max_height=400)
    license_document = fields.Binary(string='License Document', attachment=True)
    license_filename = fields.Char()
    id_proof = fields.Binary(string='ID Proof', attachment=True)
    id_proof_filename = fields.Char()
    resume = fields.Binary(string='Resume/CV', attachment=True)
    resume_filename = fields.Char()

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'agent_registration_attachment_rel',
        'registration_id',
        'attachment_id',
        string='Portfolio Images'
    )

    linkedin_url = fields.Char(string='LinkedIn Profile')
    facebook_url = fields.Char(string='Facebook Profile')

    status = fields.Selection([
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='submitted', required=True, tracking=True)

    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    reviewed_by = fields.Many2one('res.users', string='Reviewed By', readonly=True)
    review_date = fields.Datetime(string='Review Date', readonly=True)
    agent_id = fields.Many2one('real.estate.agent', string='Agent Profile', readonly=True)
    submission_date = fields.Datetime(string='Submission Date', default=fields.Datetime.now, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('agent.registration') or 'New'
        return super(AgentRegistration, self).create(vals_list)

    def action_approve(self):
        self.ensure_one()
        if self.status == 'approved':
            raise ValidationError("This registration is already approved!")

        agent_vals = {
            'name': self.agent_name,
            'email': self.email,
            'phone': self.phone,
            'whatsapp': self.whatsapp or self.phone,
            'designation': self.designation,
            'expertise_level': self.expertise_level,
            'city': self.city,
            'state_id': self.state_id.id,
            'zip_code': self.zip_code,
            'license_number': self.license_number,
            'experience_years': self.experience_years,
            'short_bio': self.short_bio or f"Real estate professional from {self.city}",
            'detailed_bio': self.detailed_bio or self.short_bio,
            'languages_spoken': self.languages_spoken,
            'linkedin_url': self.linkedin_url,
            'facebook_url': self.facebook_url,
            'specializations': [(6, 0, self.specialization_ids.ids)] if self.specialization_ids else False,
            'image': self.profile_image,
            'is_active': True,
            'is_accepting_clients': True,
            'total_sales_volume': 0,
            'total_deals': 0,
            'avg_rating': 5.0,
            'review_count': 0,
        }

        try:
            agent = self.env['real.estate.agent'].create(agent_vals)
            self.write({
                'status': 'approved',
                'agent_id': agent.id,
                'reviewed_by': self.env.user.id,
                'review_date': fields.Datetime.now(),
            })
            self.message_post(
                body=f"✅ Approved by {self.env.user.name}. Agent profile created.",
                message_type='notification'
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success!',
                    'message': f'Agent {agent.name} created successfully.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f"Error: {str(e)}")
            raise ValidationError(f"Error creating agent: {str(e)}")

    def action_reject(self):
        self.ensure_one()
        if self.status == 'rejected':
            raise ValidationError("Already rejected!")
        return {
            'name': 'Reject Registration',
            'type': 'ir.actions.act_window',
            'res_model': 'agent.registration.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_registration_id': self.id}
        }

    def action_view_agent_profile(self):
        self.ensure_one()
        if not self.agent_id:
            raise ValidationError("No agent profile created!")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Agent Profile',
            'res_model': 'real.estate.agent',
            'res_id': self.agent_id.id,
            'view_mode': 'form',
        }
