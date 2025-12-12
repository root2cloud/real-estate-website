from odoo import models, fields, api, _
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class Property(models.Model):
    _name = 'property.property'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Real Estate Property'

    # Core details
    name = fields.Char(string='Property Name*', required=True, tracking=True)
    short_description = fields.Char(string='Short Description')
    detailed_description = fields.Html(string='Detailed Description')
    category_id = fields.Many2one('property.category', string='Category*')
    is_featured = fields.Boolean(string='Featured Property', default=False)

    price = fields.Monetary(string='Total Price*', currency_field='currency_id', required=True)
    plot_area = fields.Float(string='Plot Area (Sq.Ft)*',required=True)
    price_per_sqft = fields.Float(string='Price per Sq.Ft (₹)', compute='_compute_price_per_sqft', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id.id)

    facing_direction = fields.Selection([
        ('north', 'North'), ('south', 'South'), ('east', 'East'), ('west', 'West'),
        ('northeast', 'North-East'), ('northwest', 'North-West'),
        ('southeast', 'South-East'), ('southwest', 'South-West')
    ], string='Facing Direction*',required=True)
    road_width = fields.Float(string='Road Width (Feet)*',required=True)
    title_status = fields.Selection([
        ('clear', 'Clear Title'), ('registered', 'Registered'),
        ('rera', 'RERA Approved'), ('dtcp', 'DTCP Approved'),
        ('hmda', 'HMDA Approved'), ('patta', 'Patta Available'),
        ('pending', 'Pending Approval')
    ], string='Title Status*',required=True)

    adhar_image = fields.Binary(
        string="Aadhaar Card*",
        attachment=True,
        store=True,
        required=True
    )
    adhar_filename = fields.Char()

    agreement_document = fields.Binary(
        string="Agreement Document*",
        attachment=True,
        store=True,
        required=True
    )
    agreement_filename = fields.Char()

    property_website_url = fields.Char(string='Property Website*')
    image = fields.Image(string='Cover Image')

    # Address
    street = fields.Char(string='Street*')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City*', required=True)
    zip_code = fields.Char(string='ZIP*',required=True)
    state_id = fields.Many2one(
        'res.country.state', string='State*',
        domain="[('country_id','=', country_id)]", required=True
    )
    country_id = fields.Many2one('res.country', string='Country', readonly=True,
                                 default=lambda self: self.env.company.country_id.id, store=True)

    # Financials
    emi_available = fields.Boolean(string='EMI Available*', default=True,required=True)
    registration_charges = fields.Float(string='Registration Charges (%)*', default=7.0,required=True)
    registration_amount = fields.Monetary(string='Approx. Registration Amount',
                                          currency_field='currency_id',
                                          compute='_compute_registration_amount', store=True)

    # Infrastructure
    water_connection = fields.Boolean(string='Water Connection', default=True)
    electricity_connection = fields.Boolean(string='Electricity Connection', default=True)
    drainage_facility = fields.Boolean(string='Drainage Facility', default=True)
    gated_community = fields.Boolean(string='Gated Community')

    # Geolocation
    latitude = fields.Float(string='Latitude', digits=(16, 5),
                            compute='_compute_geolocation', store=True)
    longitude = fields.Float(string='Longitude', digits=(16, 5),
                             compute='_compute_geolocation', store=True)
    date_localization = fields.Date(string='Geolocation Date',
                                    compute='_compute_geolocation', store=True)

    # Contact Info
    contact_name = fields.Char(string='Contact Person*',required=True)
    contact_phone = fields.Char(string='Phone*',required=True)
    contact_email = fields.Char(string='Email*',required=True)

    # Media & SEO
    gallery_image_ids = fields.Many2many(
        'ir.attachment',
        'property_gallery_rel',
        'property_id',
        'attachment_id',
        string="Gallery Images"
    )
    image_count = fields.Integer(string='Number of Images', compute='_compute_image_count')
    seo_title = fields.Char(string='SEO Title*',required=True)
    seo_description = fields.Text(string='SEO Description')
    # Add this field to your Property model
    agent_id = fields.Many2one(
        'real.estate.agent',
        string='Assigned Agent',
        tracking=True,
        help='Real estate agent responsible for this property'
    )

    # Metadata
    is_published = fields.Boolean(string='Published', default=False)
    views = fields.Integer(string='Views', default=0)
    last_viewed = fields.Datetime(string='Last Viewed')
    nearby_landmarks = fields.Text(string='Nearby Landmarks*',required=True)

    # AI Content Fields
    ai_key_highlights = fields.Html(readonly=True)
    ai_investment_data = fields.Html(readonly=True)
    ai_nearby_places = fields.Html(readonly=True)
    ai_unique_features = fields.Html(readonly=True)
    ai_lifestyle_benefits = fields.Html(readonly=True)
    ai_content_generated = fields.Boolean(default=False)
    ai_generation_date = fields.Datetime()

    # ==================== CITY INVESTMENT FIELDS ====================
    city_investment_reasons = fields.Html(string='City Investment Reasons', readonly=True)
    city_growth_potential = fields.Html(string='City Growth Potential', readonly=True)
    city_infrastructure = fields.Html(string='City Infrastructure', readonly=True)
    city_market_trends = fields.Html(string='City Market Trends', readonly=True)
    city_investment_generated = fields.Boolean(default=False)
    city_investment_date = fields.Datetime()
    last_city_processed = fields.Char(string='Last City Processed')

    # -------------------- COMPUTE METHODS --------------------
    @api.depends('price', 'plot_area')
    def _compute_price_per_sqft(self):
        for rec in self:
            rec.price_per_sqft = round(rec.price / rec.plot_area, 2) if rec.plot_area else 0

    @api.depends('price', 'registration_charges')
    def _compute_registration_amount(self):
        for rec in self:
            rec.registration_amount = (rec.price * rec.registration_charges / 100) if rec.price else 0

    @api.depends('gallery_image_ids')
    def _compute_image_count(self):
        for rec in self:
            rec.image_count = len(rec.gallery_image_ids)

    @api.depends('street', 'street2', 'city', 'zip_code', 'state_id', 'country_id')
    def _compute_geolocation(self):
        geo = self.env['base.geocoder']
        for rec in self:
            # Construct full address
            street = ' '.join(filter(None, [rec.street, rec.street2]))
            address_components = {
                'street': street,
                'zip': rec.zip_code or '',
                'city': rec.city or '',
                'state': rec.state_id.name or '',
                'country': rec.country_id.name or '',
            }
            if not (address_components['street'] or address_components['zip'] or address_components['city']):
                rec.latitude = rec.longitude = False
                rec.date_localization = False
                _logger.info(f"Skipping geocode for {rec.name}: insufficient address info {address_components}")
                continue

            try:
                # Log the query
                _logger.info(f"Geocoding property {rec.name} with params: {address_components}")

                # Query geocoder with structured parameters
                query = geo.geo_query_address(**address_components)
                coords = geo.geo_find(query, force_country=address_components['country'])

                # Fallback: try single string query if structured fails
                if not coords or len(coords) != 2:
                    address_str = ', '.join(
                        filter(None, [rec.street, rec.street2, rec.city, rec.state_id.name, rec.country_id.name]))
                    _logger.info(
                        f"Structured geocode failed for {rec.name}, trying fallback with address string: {address_str}")
                    coords = geo.geo_find(address_str)

                if coords and len(coords) == 2:
                    rec.latitude, rec.longitude = coords
                    rec.date_localization = fields.Date.context_today(rec)
                    _logger.info(f"Geocoded {rec.name}: latitude={rec.latitude}, longitude={rec.longitude}")
                else:
                    rec.latitude = rec.longitude = False
                    rec.date_localization = False
                    _logger.error(f"Geocode failed for {rec.name}: {address_components}")

            except Exception as e:
                rec.latitude = rec.longitude = False
                rec.date_localization = False
                _logger.error(f"Geocode error for {rec.name}: {e}")

    def generate_ai_content(self):
        """Generate AI content using FREE Groq API"""
        self.ensure_one()

        # Get Groq API key (FREE from https://console.groq.com)
        api_key = self.env['ir.config_parameter'].sudo().get_param('groq.api_key')

        if not api_key:
            _logger.error("❌ Groq API key not configured. Get free key from https://console.groq.com")
            return False

        _logger.info(f"🔄 Generating AI content for property: {self.name}")

        prompt = (
            f"Generate real estate data for '{self.name}' in {self.city}.\n"
            f"Price: ₹{self.price:,.0f}, Area: {self.plot_area} sqft\n\n"
            f"Return JSON with these keys (each as array of 3-4 points):\n"
            f"- key_highlights\n"
            f"- investment_data\n"
            f"- nearby_places\n"
            f"- unique_features\n"
            f"- lifestyle_benefits\n"
            f"Return ONLY valid JSON."
        )

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'llama-3.3-70b-versatile',  # FREE Groq model
            'messages': [
                {'role': 'system', 'content': 'You are a real estate analyst. Return only JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 800,
            'temperature': 0.3
        }

        try:
            _logger.info("📤 Calling FREE Groq API...")

            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',  # Groq endpoint
                headers=headers,
                json=payload,
                timeout=30
            )

            _logger.info(f"📥 Response status: {response.status_code}")

            if response.status_code != 200:
                _logger.error(f"API Error: {response.text}")
                return False

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()

            # Clean JSON
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            try:
                ai_data = json.loads(response_text)
                _logger.info(f"✅ Parsed AI data with keys: {list(ai_data.keys())}")
            except json.JSONDecodeError as e:
                _logger.error(f"JSON parse error: {e}\nResponse: {response_text}")
                return False

            # Convert to HTML
            def to_html(data):
                if not data:
                    return '<ul><li>Information not available</li></ul>'
                if isinstance(data, list):
                    items = ''.join([f'<li>{item}</li>' for item in data])
                    return f'<ul>{items}</ul>'
                return f'<ul><li>{data}</li></ul>'

            self.write({
                'ai_key_highlights': to_html(ai_data.get('key_highlights', [])),
                'ai_investment_data': to_html(ai_data.get('investment_data', [])),
                'ai_nearby_places': to_html(ai_data.get('nearby_places', [])),
                'ai_unique_features': to_html(ai_data.get('unique_features', [])),
                'ai_lifestyle_benefits': to_html(ai_data.get('lifestyle_benefits', [])),
                'ai_content_generated': True,
                'ai_generation_date': fields.Datetime.now(),
            })

            _logger.info(f"✅ AI content saved for property: {self.name}")
            return True

        except Exception as e:
            _logger.error(f"❌ Error: {e}")
            return False

    @api.model
    def get_city_investment_info(self, city_name):
        """Generate city investment info using FREE Groq API"""
        if not city_name:
            return None

        # Check cache
        cached = self.search([
            ('last_city_processed', '=', city_name),
            ('city_investment_generated', '=', True)
        ], limit=1)

        if cached:
            _logger.info(f"✅ Found cached city data for {city_name}")
            return {
                'city': city_name,
                'ai_investment_reasons': cached.city_investment_reasons or '',
                'ai_growth_potential': cached.city_growth_potential or '',
                'ai_infrastructure': cached.city_infrastructure or '',
                'ai_market_trends': cached.city_market_trends or '',
                'ai_content_generated': True,
            }

        # Get Groq API key
        api_key = self.env['ir.config_parameter'].sudo().get_param('groq.api_key')

        if not api_key:
            _logger.error("❌ Groq API key not configured")
            return {
                'city': city_name,
                'ai_investment_reasons': '<p>Please configure Groq API key to see investment data.</p>',
                'ai_growth_potential': '<p>Get free API key from https://console.groq.com</p>',
                'ai_infrastructure': '<p>Configuration needed.</p>',
                'ai_market_trends': '<p>Configuration needed.</p>',
                'ai_content_generated': False,
            }

        _logger.info(f"📝 Generating city investment data for: {city_name}")

        prompt = (
            f"Create real estate investment summary for {city_name}, India.\n\n"
            f"Return JSON with these keys (each as array of 2-3 bullet points):\n"
            f"- investment_reasons: Why invest here\n"
            f"- growth_potential: Future developments\n"
            f"- infrastructure: Transport & amenities\n"
            f"- market_trends: Current property trends\n\n"
            f"Return ONLY valid JSON."
        )

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {'role': 'system', 'content': 'You are a real estate analyst. Return only JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 800,
            'temperature': 0.3
        }

        try:
            _logger.info("📤 Calling Groq API for city data...")

            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                _logger.error(f"API Error: {response.text}")
                return None

            response_data = response.json()
            response_text = response_data['choices'][0]['message']['content'].strip()

            # Clean JSON
            if response_text.startswith('```'):
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            try:
                city_data = json.loads(response_text)
                _logger.info(f"✅ Parsed city data with keys: {list(city_data.keys())}")
            except json.JSONDecodeError as e:
                _logger.error(f"JSON parse error: {e}")
                return None

            # Convert to HTML
            def to_html(data):
                if not data:
                    return '<p>Information not available.</p>'
                if isinstance(data, list):
                    items = ''.join([f'<li>{item}</li>' for item in data])
                    return f'<ul>{items}</ul>'
                if isinstance(data, str):
                    return f'<p>{data}</p>'
                return '<p>Information not available.</p>'

            investment_reasons = to_html(city_data.get('investment_reasons', ''))
            growth_potential = to_html(city_data.get('growth_potential', ''))
            infrastructure = to_html(city_data.get('infrastructure', ''))
            market_trends = to_html(city_data.get('market_trends', ''))

            # Cache the data
            city_property = self.search([
                ('city', '=', city_name),
                ('is_published', '=', True)
            ], limit=1)

            if city_property:
                city_property.write({
                    'city_investment_reasons': investment_reasons,
                    'city_growth_potential': growth_potential,
                    'city_infrastructure': infrastructure,
                    'city_market_trends': market_trends,
                    'city_investment_generated': True,
                    'city_investment_date': fields.Datetime.now(),
                    'last_city_processed': city_name,
                })
                _logger.info(f"✅ Cached city data in property ID: {city_property.id}")

            return {
                'city': city_name,
                'ai_investment_reasons': investment_reasons,
                'ai_growth_potential': growth_potential,
                'ai_infrastructure': infrastructure,
                'ai_market_trends': market_trends,
                'ai_content_generated': True,
            }

        except Exception as e:
            _logger.error(f"❌ Error: {e}")
            return None

    def action_regenerate_ai_content(self):
        """Button to regenerate AI content"""
        for rec in self:
            success = rec.generate_ai_content()
            if success:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'AI content regenerated successfully!',
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error',
                        'message': 'Failed to generate AI content. Check logs.',
                        'type': 'danger',
                    }
                }
