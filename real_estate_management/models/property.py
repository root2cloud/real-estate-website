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
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not api_key:
            _logger.error("OpenAI API key not configured")
            return

        _logger.info(f"Generating AI content for property: {self.name}")

        prompt = (
            f"Generate factual real estate data for '{self.name}' located at {self.street}, {self.city}, {self.state_id.name or ''}, {self.zip_code}. "
            f"Price: ₹{self.price:,}, Area: {self.plot_area} sqft, Category: {self.category_id.name or 'Plot'}. "
            "Return a JSON object with the following keys (each value a bullet-point list, max 80 words): "
            "'key_highlights' (3 main property features with exact data), "
            "'investment_data' (3 exact financial benefits with numbers or percentages), "
            "'nearby_places' (actual distances to 4 key nearby locations), "
            "'unique_features' (3 standout factual features that make this property unique), "
            "'lifestyle_benefits' (3 precise lifestyle benefits with real distances or details). "
            "Focus solely on actual data sourced from property records, measurements, and verified local info. Do not include generic marketing text or assumptions."
        )

        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system',
                 'content': '"You are a real estate data analyst. Provide only factual data sourced from property records,""measurements, and verified local information. Do not include any generic marketing language or assumptions."'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 400,
            'temperature': 0.3
        }

        try:
            res = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            res.raise_for_status()
            response_data = res.json()
            response_text = response_data['choices'][0]['message']['content']
            print(response_text)
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "")

            try:
                js = json.loads(response_text)
                print(js)

                # Convert lists to HTML <ul> format
                def list_to_html(lst):
                    if not isinstance(lst, list) or not lst:
                        return str(lst) if lst else ''
                    return '<ul>' + ''.join(f'<li>{item}</li>' for item in lst) + '</ul>'

            except Exception as e:
                print(f"JSON parse error: {e}")
                js = {'key_highlights': response_text}

            self.write({
                'ai_key_highlights': list_to_html(js.get('key_highlights', '')),
                'ai_investment_data': list_to_html(js.get('investment_data', '')),
                'ai_nearby_places': list_to_html(js.get('nearby_places', '')),
                'ai_unique_features': list_to_html(js.get('unique_features', '')),
                'ai_content_generated': True,
                'ai_generation_date': fields.Datetime.now(),
            })
            print(f"AI content generated for {self.name}")

        except Exception as e:
            print(f"AI generation failed for {self.name}: {e}")

    def action_regenerate_ai_content(self):
        for rec in self:
            rec.generate_ai_content()

    @api.model
    def get_city_investment_info(self, city_name):
        """
        Get or generate AI investment information for a city
        """
        if not city_name:
            return None

        # Search if we already have this city's investment data in any property
        existing = self.search([
            ('last_city_processed', '=', city_name),
            ('city_investment_generated', '=', True)
        ], limit=1)

        if existing:
            return {
                'city': city_name,
                'ai_investment_reasons': existing.city_investment_reasons,
                'ai_growth_potential': existing.city_growth_potential,
                'ai_infrastructure': existing.city_infrastructure,
                'ai_market_trends': existing.city_market_trends,
                'ai_content_generated': True,
            }

        # Get API key
        api_key = self.env['ir.config_parameter'].sudo().get_param('openai.api_key')
        if not api_key:
            _logger.error("OpenAI API key not configured")
            return None

        print(f"Generating AI investment content for city: {city_name}")

        prompt = (
            f"Create a concise, premium, and trustworthy real estate investment summary for {city_name}, India. "
            "Return a JSON object with exactly four keys, each containing a short paragraph (2–3 sentences max): "
            "'investment_reasons' — Explain why this city is a reliable and smart choice for real estate investment. Focus on safety, job growth, lifestyle, and investor confidence. "
            "'growth_potential' — Highlight upcoming developments, government initiatives, and economic growth that boost long-term value. "
            "'infrastructure' — Summarize key transport links, urban projects, and quality-of-life improvements. "
            "'market_trends' — Describe current property and rental trends that indicate steady demand and appreciation. "
            "Use warm, confident language that builds trust with first-time investors — make it sound like expert advice backed by real urban and economic growth data. "
            "Avoid lists — write naturally in full sentences with a realistic tone suitable for a luxury real estate website."
        )



        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system',
                 'content': 'You are a real estate investment analyst. Provide factual data about cities in India with focus on real estate investment potential.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 600,
            'temperature': 0.3
        }

        try:
            res = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            res.raise_for_status()
            response_data = res.json()
            response_text = response_data['choices'][0]['message']['content']

            if response_text.startswith:
                response_text = response_text.replace("```json", "").replace("```", "")

            try:
                js = json.loads(response_text)

                def list_to_html(lst):
                    if not isinstance(lst, list) or not lst:
                        return str(lst) if lst else ''
                    return '<ul>' + ''.join(f'<li>{item}</li>' for item in lst) + '</ul>'

                investment_reasons = list_to_html(js.get('investment_reasons', ''))
                growth_potential = list_to_html(js.get('growth_potential', ''))
                infrastructure = list_to_html(js.get('infrastructure', ''))
                market_trends = list_to_html(js.get('market_trends', ''))

                # Store in a dummy property record to cache the data
                city_cache = self.search([('last_city_processed', '=', city_name)], limit=1)
                if not city_cache:
                    # Create a dummy record just to store city data
                    city_cache = self.create({
                        'name': f'City Data - {city_name}',
                        'city': city_name,
                        'city_investment_reasons': investment_reasons,
                        'city_growth_potential': growth_potential,
                        'city_infrastructure': infrastructure,
                        'city_market_trends': market_trends,
                        'city_investment_generated': True,
                        'city_investment_date': fields.Datetime.now(),
                        'last_city_processed': city_name,
                        'is_published': False,
                    })
                else:
                    city_cache.write({
                        'city_investment_reasons': investment_reasons,
                        'city_growth_potential': growth_potential,
                        'city_infrastructure': infrastructure,
                        'city_market_trends': market_trends,
                        'city_investment_generated': True,
                        'city_investment_date': fields.Datetime.now(),
                        'last_city_processed': city_name,
                    })

                print(f"AI city investment content generated and stored for {city_name}")

                return {
                    'city': city_name,
                    'ai_investment_reasons': investment_reasons,
                    'ai_growth_potential': growth_potential,
                    'ai_infrastructure': infrastructure,
                    'ai_market_trends': market_trends,
                    'ai_content_generated': True,
                }

            except Exception as e:
                print(f"JSON parse error for city: {e}")
                return None

        except Exception as e:
            print(f"AI generation failed for city {city_name}: {e}")
            return None
