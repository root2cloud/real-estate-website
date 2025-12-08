# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class PropertyRegistration(models.Model):
    _name = 'property.registration'
    _description = 'Property Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    customer_name = fields.Char(string='Customer Name*', required=True)
    property_name = fields.Char(string='Property Name*', required=True)
    phone_number = fields.Char(string='Phone Number*', required=True)
    place = fields.Char(string='Place*', required=True)
    category = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('agricultural', 'Agricultural'),
    ], string='Category*', required=True)
    sq_yards = fields.Float(string='Square Yards*', required=True)
    price = fields.Float(string='Expected Price*', required=True)
    location = fields.Char(string='Exact Location*', required=True)
    city = fields.Char(string='City*', required=True)
    state = fields.Char(string='State*', required=True)
    country_id = fields.Many2one(
        'res.country', string='Country*', required=True,
        default=lambda self: self.env['res.country'].search([('code', '=', 'IN')], limit=1).id
    )
    image = fields.Image(string='Main Image*', max_width=1024, max_height=1024)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # ✅ Gallery images field
    attachment_ids = fields.One2many('ir.attachment', 'res_id',
                                     domain=lambda self: [('res_model', '=', self._name)],
                                     string='Additional Images')



    email = fields.Char(string="Customer Email*")  # Required for rejection email

    def action_approve(self):
        for rec in self:
            if rec.status == 'approved':
                raise UserError("Already approved.")
            # Build property.property values dict mapping ONLY to existing fields!
            vals = {
                'name': rec.customer_name or 'Property',
                'city': rec.city,
                'state_id': rec.state and self.env['res.country.state'].search([('name', '=', rec.state)], limit=1).id or False,
                'country_id': rec.country_id.id if rec.country_id else False,
                'category_id': rec.category and self.env['property.category'].search([('name', '=', rec.category)], limit=1).id or False,
                'image': rec.image,
                'price': rec.price or 0.0,
                'plot_area': rec.sq_yards or 0.0
            }
            # Ensure all mandatory fields exist or fill with default/False
            property_obj = self.env['property.property'].create(vals)
            # Copy attachments to new property
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'property.registration'), ('res_id', '=', rec.id)
            ])
            for attach in attachments:
                attach.copy({'res_model': 'property.property', 'res_id': property_obj.id})
            rec.status = 'approved'

    # def action_reject(self):
    #     for rec in self:
    #         if rec.status == 'rejected':
    #             raise UserError("Already rejected.")
    #         rec.status = 'rejected'
    #         if rec.email:
    #             template = self.env.ref('real_estate_management.mail_template_property_rejection')
    #             template.send_mail(rec.id, force_send=True)

                # template = self.env.ref('your_module.property_rejection_email_template', raise_if_not_found=False)
                # if template:
                #     try:
                #         template.send_mail(rec.id, force_send=True)
                #     except Exception as e:
                #         raise UserError(_("Failed to send rejection email: %s") % str(e))
                # else:
                #     # No mail template found, just show warning
                #     raise UserError(_("Rejection mail template not found. Please create it."))
                #

    def action_reject(self):
        """When rejected, send a rejection email to the user"""
        for record in self:
            record.status = 'rejected'

            # ✅ Send email only if user email exists
            if record.create_uid and record.create_uid.email:
                mail_template = self.env.ref('real_estate_management.mail_template_property_rejection',
                                             raise_if_not_found=False)
                if mail_template:
                    mail_template.send_mail(record.id, force_send=True)
                else:
                    # fallback message in chatter
                    record.message_post(
                        body=f"Rejection mail template not found, but property '{record.name}' was rejected.",
                    )

        # ❌ Reject Button
    # def action_reject(self):
    #         for record in self:
    #             record.state = 'rejected'
    #
    #             # Step 1️⃣: Send rejection email
    #             template = self.env.ref('real_estate_management.mail_template_property_rejection',
    #                                     raise_if_not_found=False)
    #             if template:
    #                 template.send_mail(record.id, force_send=True)
    #                 record.message_post(body="❌ Property registration rejected. Email notification sent.")
    #             else:
    #                 raise UserError("Email template for rejection not found.")



