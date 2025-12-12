from odoo import http, fields
from odoo.http import request
import json
from odoo.tools.json import scriptsafe as json_scriptsafe
import base64
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RealEstateController(http.Controller):

    @http.route('/', type='http', auth='public', website=True)
    def property_map(self, **kwargs):

        # Fetch published properties from database
        Property = request.env['property.property'].sudo()
        # Get the selected city from URL parameters (if any)
        selected_city = kwargs.get('city', '')
        all_properties = Property.search([('is_published', '=', True)])
        city_list = sorted(list(set([p.city for p in all_properties if p.city])))
        # Build the search domain with city filter if selected
        search_domain = [
            ('is_published', '=', True),
            ('latitude', '!=', False),
            ('longitude', '!=', False)
        ]
        # Add city filter if a city is selected
        if selected_city:
            search_domain.append(('city', '=', selected_city))

        # Fetch properties based on the search domain
        properties = Property.search(search_domain)

        # Fetch featured properties for selected city, limit to 5
        featured_domain = [('is_published', '=', True), ('is_featured', '=', True)]
        if selected_city:
            featured_domain.append(('city', '=', selected_city))
        featured_properties = Property.search(featured_domain)

        # Get city investment info
        city_investment_info = None
        if selected_city:
            city_investment_info = Property.get_city_investment_info(selected_city)

        # Define a reusable color palette
        palette = ["#059669", "#dc2626", "#7c3aed", "#ea580c", "#2563eb", "#d97706", "#0891b2", "#9333ea"]
        category_colors = {}
        idx = 0

        # Build comprehensive data
        property_data = []
        for prop in properties:
            if prop.latitude and prop.longitude:
                cat = prop.category_id.name if prop.category_id else 'Property'
                if cat not in category_colors:
                    category_colors[cat] = palette[idx % len(palette)]
                    idx += 1

                image_url = None
                if prop.image:
                    # Create base64 data URL for the image
                    image_url = f"data:image/png;base64,{prop.image.decode('utf-8')}"
                elif prop.gallery_image_ids:
                    # Use first image from gallery if main image not available
                    first_image = prop.gallery_image_ids[0]
                    if first_image.datas:
                        image_url = f"data:image/png;base64,{first_image.datas.decode('utf-8')}"

                full_address = ", ".join(filter(None, [prop.street, prop.city, prop.zip_code]))

                # Build property data
                property_data.append({
                    'id': prop.id,
                    'name': prop.name or '',
                    'latitude': float(prop.latitude),
                    'longitude': float(prop.longitude),
                    'street': prop.street or '',
                    'city': prop.city or '',
                    'zip_code': prop.zip_code or '',
                    'price': float(prop.price) if prop.price else 0,
                    'contact_phone': prop.contact_phone or '',
                    'contact_email': prop.contact_email or '',
                    'contact_name': prop.contact_name or '',
                    'short_description': prop.short_description or '',
                    'image_url': image_url,
                    'property_type': cat,
                    'nearby_landmarks': prop.nearby_landmarks or '',
                    'views': prop.views or 0,
                    'seo_title': prop.seo_title or '',
                    'marker_color': category_colors[cat],
                    'full_address': full_address,
                })

        return request.render('real_estate_management.property_map_template', {
            'property_count': len(property_data),
            'properties_json': json_scriptsafe.dumps(property_data) if property_data else '[]',
            'category_colors': json_scriptsafe.dumps(category_colors),
            'city_list': city_list,
            'selected_city': selected_city,
            'featured_properties': featured_properties,
            'city_investment_info': city_investment_info,

        })

    @http.route('/property/<int:property_id>', type='http', auth='public', website=True)
    def property_detail(self, property_id, **kwargs):
        """Individual property detail page"""
        prop = request.env['property.property'].sudo().browse(property_id)
        if not prop.exists() or not prop.is_published:
            return request.not_found()
        if not prop.ai_content_generated:
            try:
                prop.generate_ai_content()
            except Exception as e:
                _logger.error(f"Failed to generate AI content for property {prop.id}: {e}")
        try:
            prop.write({'views': prop.views + 1})
        except Exception as e:
            _logger.error(f"Failed to update views for property {prop.id}: {e}")
        return request.render('real_estate_management.property_detail_page', {
            'property': prop,

        })

    @http.route('/properties', type='http', auth='public', website=True)
    def property_listing(self, **kwargs):
        search = kwargs.get('search', '')
        city = kwargs.get('city', '')
        zip_code = kwargs.get('zip_code', '')

        domain = [('is_published', '=', True)]
        if search:
            domain += ['|', '|',
                       ('name', 'ilike', search),
                       ('city', 'ilike', search),
                       ('zip_code', 'ilike', search)]
        if city:
            domain.append(('city', 'ilike', city))
        if zip_code:
            domain.append(('zip_code', 'ilike', zip_code))

        properties = request.env['property.property'].sudo().search(domain)

        property_card_data = []
        for prop in properties:
            property_card_data.append({
                'id': prop.id,
                'name': prop.name,
                'image_url': f"data:image/png;base64,{prop.image.decode('utf-8')}" if prop.image else '',
                'category': prop.category_id.name or '',
                'price': prop.price,
                'plot_area': prop.plot_area,
                'price_per_sqft': prop.price_per_sqft,
                'city': prop.city,
                'zip_code': prop.zip_code,
            })

        return request.render('real_estate_management.property_listing_template', {
            'properties': property_card_data,
            'search': search,
            'city': city,
            'zip_code': zip_code,
        })

    @http.route('/property/register', type='http', auth='public', website=True)
    def show_registration_form(self, **kwargs):
        return request.render('real_estate_management.property_registration_form')

    @http.route('/property/submit', type='http', auth='public', website=True, csrf=False)
    def submit_registration(self, **post):
        """Handle property registration form submission"""
        try:
            upload_files = request.httprequest.files.getlist('images')
            property_vals = {
                'customer_name': post.get('customer_name'),
                'phone_number': post.get('phone_number'),
                'place': post.get('place'),
                'category': post.get('category'),
                'sq_yards': post.get('sq_yards'),
                'price': post.get('price'),
                'location': post.get('location'),
                'city': post.get('city'),
                'state': post.get('state'),
                'status': 'submitted',
            }

            # Create property record
            property_rec = request.env['property.registration'].sudo().create(property_vals)

            # Save uploaded images (main + gallery)
            for idx, file in enumerate(upload_files):
                content = base64.b64encode(file.read())
                if idx == 0:
                    property_rec.image = content  # First image as main
                else:
                    request.env['ir.attachment'].sudo().create({
                        'name': file.filename,
                        'res_model': 'property.registration',
                        'res_id': property_rec.id,
                        'type': 'binary',
                        'datas': content,
                        'mimetype': file.content_type,
                    })

            return request.render('real_estate_management.property_submission_success')

        except Exception as e:
            _logger.exception("Error in property registration")
            return request.render('real_estate_management.property_submission_error', {'error': str(e)})

    @http.route('/agents', type='http', auth='public', website=True)
    def agent_directory(self, **kwargs):
        """Agent listing page - similar to Redfin agents page"""

        # Get filters from URL
        search_query = kwargs.get('search', '')
        city_filter = kwargs.get('city', '')
        expertise_filter = kwargs.get('expertise', '')
        sort_by = kwargs.get('sort', 'recommended')  # recommended, sales_volume, deals, rating

        # Build domain
        domain = [('is_active', '=', True)]

        if search_query:
            domain += ['|', '|',
                       ('name', 'ilike', search_query),
                       ('city', 'ilike', search_query),
                       ('zip_code', 'ilike', search_query)]

        if city_filter:
            domain.append(('city', '=', city_filter))

        if expertise_filter:
            domain.append(('expertise_level', '=', expertise_filter))

        # Sorting
        order = 'total_sales_volume desc, total_deals desc'  # Default: recommended
        if sort_by == 'sales_volume':
            order = 'total_sales_volume desc'
        elif sort_by == 'deals':
            order = 'total_deals desc'
        elif sort_by == 'rating':
            order = 'avg_rating desc, review_count desc'

        # Fetch agents
        Agent = request.env['real.estate.agent'].sudo()
        agents = Agent.search(domain, order=order)

        # Get unique cities for filter dropdown
        all_agents = Agent.search([('is_active', '=', True)])
        cities = sorted(list(set([a.city for a in all_agents if a.city])))

        # Count agents
        agent_count = len(agents)
        total_agents = len(all_agents)

        # Build agent card data
        agent_data = []
        for agent in agents:
            # Format sales volume
            sales_volume_str = f"₹{agent.total_sales_volume / 10000000:.1f}M" if agent.total_sales_volume >= 10000000 else f"₹{agent.total_sales_volume / 100000:.1f}L"

            # Get profile image URL
            image_url = None
            if agent.image:
                image_url = f"data:image/png;base64,{agent.image.decode('utf-8')}"

            agent_data.append({
                'id': agent.id,
                'name': agent.name,
                'designation': dict(agent._fields['designation'].selection).get(agent.designation),
                'expertise_level': agent.expertise_level,
                'city': agent.city or '',
                'state': agent.state_id.name or '',
                'email': agent.email,
                'phone': agent.phone,
                'image_url': image_url,
                'total_sales_volume': agent.total_sales_volume,
                'sales_volume_display': sales_volume_str,
                'total_deals': agent.total_deals,
                'avg_rating': agent.avg_rating,
                'short_bio': agent.short_bio or '',
                'active_listings': agent.active_property_count,
            })

        return request.render('real_estate_management.agent_directory_template', {
            'agents': agent_data,
            'agent_count': agent_count,
            'total_agents': total_agents,
            'cities': cities,
            'search_query': search_query,
            'city_filter': city_filter,
            'expertise_filter': expertise_filter,
            'sort_by': sort_by,
        })

    @http.route('/agent/<int:agent_id>', type='http', auth='public', website=True)
    def agent_detail(self, agent_id, **kwargs):
        """Individual agent profile page"""
        agent = request.env['real.estate.agent'].sudo().browse(agent_id)

        if not agent.exists() or not agent.is_active:
            return request.not_found()

        # Get agent's published properties
        properties = request.env['property.property'].sudo().search([
            ('agent_id', '=', agent_id),
            ('is_published', '=', True)
        ], limit=12, order='create_date desc')

        # Format property data
        property_data = []
        for prop in properties:
            image_url = None
            if prop.image:
                image_url = f"data:image/png;base64,{prop.image.decode('utf-8')}"

            property_data.append({
                'id': prop.id,
                'name': prop.name,
                'image_url': image_url,
                'price': prop.price,
                'plot_area': prop.plot_area,
                'city': prop.city,
                'category': prop.category_id.name if prop.category_id else 'Property',
            })

        return request.render('real_estate_management.agent_detail_template', {
            'agent': agent,
            'properties': property_data,
        })

    @http.route('/agent/<int:agent_id>/contact', type='json', auth='public', methods=['POST'], csrf=False)
    def contact_agent(self, agent_id, **kwargs):
        """Handle contact form submission (AJAX)"""
        try:
            agent = request.env['real.estate.agent'].sudo().browse(agent_id)

            if not agent.exists():
                return {'success': False, 'message': 'Agent not found'}

            # You can create a lead/inquiry record here
            # Or send email notification to agent

            return {
                'success': True,
                'message': f'Thank you! {agent.name} will contact you shortly.',
                'agent_email': agent.email,
                'agent_phone': agent.phone,
            }

        except Exception as e:
            _logger.error(f"Contact agent error: {e}")
            return {'success': False, 'message': 'An error occurred. Please try again.'}

    # Add these routes to your existing agent_controller.py file

    @http.route('/agent/register', type='http', auth='public', website=True)
    def agent_registration_form(self, **kwargs):
        """Public agent registration form"""

        # Get property categories for specializations
        categories = request.env['property.category'].sudo().search([])

        # Get states
        states = request.env['res.country.state'].sudo().search([
            ('country_id', '=', request.env.company.country_id.id)
        ], order='name')

        return request.render('real_estate_management.agent_registration_form_template', {
            'categories': categories,
            'states': states,
        })

    @http.route('/agent/register/submit', type='http', auth='public', website=True, csrf=False, methods=['POST'])
    def submit_agent_registration(self, **post):
        """Handle agent registration form submission"""
        try:
            # Get uploaded files
            profile_image = request.httprequest.files.get('profile_image')
            id_proof = request.httprequest.files.get('id_proof')
            license_doc = request.httprequest.files.get('license_document')
            resume = request.httprequest.files.get('resume')
            portfolio_images = request.httprequest.files.getlist('portfolio_images')

            # Prepare registration values
            registration_vals = {
                'agent_name': post.get('agent_name'),
                'email': post.get('email'),
                'phone': post.get('phone'),
                'whatsapp': post.get('whatsapp'),
                'designation': post.get('designation'),
                'expertise_level': post.get('expertise_level'),
                'license_number': post.get('license_number'),
                'experience_years': int(post.get('experience_years', 0)),
                'city': post.get('city'),
                'state_id': int(post.get('state_id')),
                'zip_code': post.get('zip_code'),
                'short_bio': post.get('short_bio'),
                'detailed_bio': post.get('detailed_bio'),
                'qualifications': post.get('qualifications'),
                'languages_spoken': post.get('languages_spoken', 'English, Hindi'),
                'linkedin_url': post.get('linkedin_url'),
                'facebook_url': post.get('facebook_url'),
                'status': 'submitted',
            }

            # Handle profile image
            if profile_image:
                registration_vals['profile_image'] = base64.b64encode(profile_image.read())

            # Handle ID proof
            if id_proof:
                registration_vals['id_proof'] = base64.b64encode(id_proof.read())
                registration_vals['id_proof_filename'] = id_proof.filename

            # Handle license document
            if license_doc:
                registration_vals['license_document'] = base64.b64encode(license_doc.read())
                registration_vals['license_filename'] = license_doc.filename

            # Handle resume
            if resume:
                registration_vals['resume'] = base64.b64encode(resume.read())
                registration_vals['resume_filename'] = resume.filename

            # Handle specializations
            specialization_ids = request.httprequest.form.getlist('specialization_ids')
            if specialization_ids:
                registration_vals['specialization_ids'] = [(6, 0, [int(sid) for sid in specialization_ids])]

            # Create registration record
            registration = request.env['agent.registration'].sudo().create(registration_vals)

            # Handle portfolio images
            for idx, img_file in enumerate(portfolio_images):
                if img_file:
                    attachment = request.env['ir.attachment'].sudo().create({
                        'name': f'Portfolio_{idx + 1}_{img_file.filename}',
                        'res_model': 'agent.registration',
                        'res_id': registration.id,
                        'type': 'binary',
                        'datas': base64.b64encode(img_file.read()),
                        'mimetype': img_file.content_type,
                    })
                    registration.attachment_ids = [(4, attachment.id)]

            _logger.info(f"Agent registration submitted: {registration.name} - {registration.agent_name}")

            return request.render('real_estate_management.agent_registration_success_template', {
                'registration': registration,
            })

        except Exception as e:
            _logger.exception("Error in agent registration submission")
            return request.render('real_estate_management.agent_registration_error_template', {
                'error': str(e)
            })


