import requests
import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class ReliefWebAPI:
    BASE_URL = "https://api.reliefweb.int/v1"
    APP_NAME = "sudan-assessment-registry"
    MAX_LIMIT = 1000  # ReliefWeb API maximum limit
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'{self.APP_NAME}/1.0',
            'Content-Type': 'application/json'
        })
    
    def fetch_reports(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch reports from ReliefWeb API with exact country matching
        """
        try:
            # Build the API payload
            payload = self._build_payload(filters)
            
            logger.info(f"Sending API request with payload: {self._format_payload_for_log(payload)}")
            
            # Make the API request with appname in URL as per docs
            url = f"{self.BASE_URL}/reports"
            params = {"appname": self.APP_NAME}
            
            response = self.session.post(url, json=payload, params=params, timeout=30)
            
            # Log response status
            logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"API Error ({response.status_code}). Response: {response.text}")
                response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched {data.get('totalCount', 0)} total results from API")
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise Exception(f"Failed to fetch data from ReliefWeb API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise Exception(f"Failed to fetch data from ReliefWeb API: {e}")
    
    def _build_payload(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the API payload with exact matching for primary countries
        """
        conditions = []
        
        # Country filter - use basic filtering in API, then filter strictly on client side
        country = filters.get('country')
        country_filter_type = filters.get('country_filter_type', 'primary')
        
        if country:
            if country_filter_type == 'primary':
                # Use exact matching for primary country
                conditions.append({
                    "field": "primary_country.name",
                    "value": country
                })
                logger.info(f"Using primary country filter: primary_country.name = '{country}'")
                    
            elif country_filter_type == 'associated':
                # Countries mentioned but not primary
                conditions.append({
                    "operator": "AND",
                    "conditions": [
                        {"field": "country.name", "value": country},
                        {"field": "primary_country.name", "value": country, "negate": True}
                    ]
                })
                logger.info(f"Using associated country filter: '{country}'")
                    
            else:  # 'all' - any mention
                conditions.append({
                    "field": "country.name",
                    "value": country
                })
                logger.info(f"Using country filter (all mentions): country.name = '{country}'")
        
        # Format filter
        format_type = filters.get('format')
        if format_type:
            conditions.append({
                "field": "format.name",
                "value": format_type
            })
            logger.info(f"Using format filter: format.name = '{format_type}'")
        
        # Date range filter
        date_from = filters.get('date_from')
        date_to = filters.get('date_to')
        
        if date_from or date_to:
            date_condition = {"field": "date.created"}
            
            if date_from and date_to:
                date_condition["value"] = {
                    "from": f"{date_from}T00:00:00+00:00",
                    "to": f"{date_to}T23:59:59+00:00"
                }
            elif date_from:
                date_condition["value"] = {"from": f"{date_from}T00:00:00+00:00"}
            elif date_to:
                date_condition["value"] = {"to": f"{date_to}T23:59:59+00:00"}
                
            conditions.append(date_condition)
            logger.info(f"Using date filter: {date_condition}")
        
        # Theme filter
        theme = filters.get('theme')
        if theme:
            conditions.append({
                "field": "theme.name",
                "value": theme
            })
            logger.info(f"Using theme filter: theme.name = '{theme}'")
        
        # Source filter
        source = filters.get('source')
        if source:
            conditions.append({
                "field": "source.name",
                "value": source
            })
            logger.info(f"Using source filter: source.name = '{source}'")
        
        # Language filter
        language = filters.get('language')
        if language:
            conditions.append({
                "field": "language.name",
                "value": language
            })
            logger.info(f"Using language filter: language.name = '{language}'")
        
        # Build the filter structure
        if len(conditions) == 0:
            main_filter = None
        elif len(conditions) == 1:
            main_filter = conditions[0]
        else:
            main_filter = {
                "operator": "AND",
                "conditions": conditions
            }
        
        # Validate and set limit
        requested_limit = int(filters.get('limit', 1000))
        actual_limit = min(requested_limit, self.MAX_LIMIT)
        
        if requested_limit > self.MAX_LIMIT:
            logger.warning(f"Requested limit {requested_limit} exceeds API maximum {self.MAX_LIMIT}. Using {actual_limit}")
        
        # Build payload
        payload = {
            "preset": "latest",
            "fields": {
                "include": [
                    "id", "title", "body", "body-html", "date", "source", "format",
                    "theme", "primary_country", "country", "language", "status",
                    "url", "url_alias", "file", "headline"
                ]
            },
            "limit": actual_limit
        }
        
        # Only add filter if we have conditions
        if main_filter:
            payload["filter"] = main_filter
        
        # Override sort if specific sorting is needed
        custom_sort = filters.get('sort')
        if custom_sort:
            payload["sort"] = custom_sort
        
        return payload
    
    def _format_payload_for_log(self, payload: Dict) -> str:
        """Format payload for logging"""
        return json.dumps(payload, indent=2)
    
    def get_available_formats(self) -> List[str]:
        """Get available formats using facets API"""
        try:
            payload = {
                "facets": [{"field": "format.name", "limit": 100, "sort": "value:asc"}],
                "limit": 0
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/reports",
                json=payload,
                params={"appname": self.APP_NAME},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                facets_data = data.get('facets', {}).get('format.name', {}).get('data', [])
                
                if facets_data:
                    formats = [item['value'] for item in facets_data]
                    logger.info(f"Retrieved {len(formats)} formats from facets")
                    return sorted(formats)
                    
            logger.info("Using verified working formats")
            return self._get_verified_formats()
                
        except Exception as e:
            logger.error(f"Error fetching formats via facets: {e}")
            return self._get_verified_formats()
    
    def get_available_countries(self) -> List[str]:
        """Get available countries using facets API"""
        try:
            payload = {
                "facets": [{"field": "primary_country.name", "limit": 500, "sort": "value:asc"}],
                "limit": 0
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/reports",
                json=payload,
                params={"appname": self.APP_NAME},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                facets_data = data.get('facets', {}).get('primary_country.name', {}).get('data', [])
                
                if facets_data:
                    countries = [item['value'] for item in facets_data]
                    logger.info(f"Retrieved {len(countries)} countries from facets")
                    return sorted(countries)
                    
            logger.info("Using verified working countries")
            return self._get_verified_countries()
                
        except Exception as e:
            logger.error(f"Error fetching countries via facets: {e}")
            return self._get_verified_countries()
    
    def get_available_themes(self) -> List[str]:
        """Get available themes"""
        return self._get_verified_themes()
    
    def get_available_sources(self) -> List[str]:
        """Get available sources"""
        return self._get_verified_sources()
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            test_payload = {"preset": "minimal", "limit": 1}
            response = self.session.post(
                f"{self.BASE_URL}/reports",
                json=test_payload,
                params={"appname": self.APP_NAME},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False

    def get_filter_options(self) -> Dict[str, List[str]]:
        """Get all available filter options"""
        try:
            return {
                'countries': self.get_available_countries(),
                'formats': self.get_available_formats(),
                'themes': self.get_available_themes(),
                'sources': self.get_available_sources(),
                'languages': self._get_verified_languages()
            }
        except Exception as e:
            logger.error(f"Error fetching filter options: {e}")
            return self._get_verified_options()
    
    def _get_verified_formats(self) -> List[str]:
        """Verified working formats"""
        return [
            'Assessment', 'Situation Report', 'Analysis', 'Evaluation', 'Update',
            'Map', 'Infographic', 'News and Press Release', 'Flash Update',
            'Bulletin', 'Appeal', 'Plan', 'Guidelines', 'Manual and Guideline', 'Other'
        ]
    
    def _get_verified_countries(self) -> List[str]:
        """Verified working countries"""
        return [
            'Sudan', 'South Sudan', 'Chad', 'Ethiopia', 'Libya', 'Egypt',
            'Kenya', 'Somalia', 'Central African Republic', 'Eritrea',
            'Uganda', 'Democratic Republic of the Congo', 'Afghanistan',
            'Syria', 'Yemen', 'Nigeria', 'Mali', 'Niger', 'Burkina Faso'
        ]
    
    def _get_verified_themes(self) -> List[str]:
        """Verified humanitarian themes"""
        return [
            'Food and Nutrition', 'Health', 'Protection and Human Rights',
            'Water Sanitation Hygiene', 'Shelter and Non-Food Items',
            'Education', 'Coordination', 'Agriculture', 'Disaster Management',
            'Recovery and Reconstruction', 'Logistics and Telecommunications',
            'Mine Action', 'Early Recovery', 'Gender', 'Cash and Voucher Assistance'
        ]
    
    def _get_verified_sources(self) -> List[str]:
        """Verified humanitarian sources"""
        return [
            'OCHA', 'WFP', 'UNHCR', 'UNICEF', 'WHO', 'REACH Initiative',
            'ACAPS', 'FEWS NET', 'IOM', 'Save the Children', 'Oxfam',
            'MSF', 'IRC', 'NRC', 'DRC', 'ACF', 'CARE', 'World Vision',
            'CRS', 'Islamic Relief'
        ]
    
    def _get_verified_languages(self) -> List[str]:
        """Verified working languages"""
        return ['English', 'Arabic', 'French', 'Spanish', 'Portuguese', 'Russian', 'Chinese']
    
    def _get_verified_options(self) -> Dict[str, List[str]]:
        """Get verified working filter options as fallback"""
        return {
            'countries': self._get_verified_countries(),
            'formats': self._get_verified_formats(),
            'themes': self._get_verified_themes(),
            'sources': self._get_verified_sources(),
            'languages': self._get_verified_languages()
        }

# Create global instance
reliefweb_api = ReliefWebAPI()

def contains_south_sudan(text: str) -> bool:
    """
    Check if text contains South Sudan references
    """
    if not text:
        return False
    
    text_lower = text.lower()
    south_sudan_indicators = [
        'south sudan',
        'southern sudan',
        'republic of south sudan',
        'rss',
        'south sudanese'
    ]
    
    return any(indicator in text_lower for indicator in south_sudan_indicators)

def is_exact_sudan_match(text: str, target_country: str) -> bool:
    """
    Check if text contains exact Sudan match without South Sudan contamination
    """
    if not text or not target_country:
        return False
    
    text_lower = text.lower()
    target_lower = target_country.lower()
    
    # If searching for Sudan, ensure it's not South Sudan
    if target_lower == 'sudan':
        # Check if text contains South Sudan indicators
        if contains_south_sudan(text):
            return False
        
        # Check for exact Sudan mentions
        sudan_indicators = [
            'sudan,',
            'sudan ',
            'sudan.',
            'sudan;',
            'sudan:',
            'sudan\'s',
            'sudanese',
            'republic of the sudan',
            'republic of sudan'
        ]
        
        # Check if text ends with Sudan
        if text_lower.strip().endswith('sudan') and not text_lower.strip().endswith('south sudan'):
            return True
            
        # Check for exact Sudan patterns
        return any(indicator in text_lower for indicator in sudan_indicators)
    
    # For other countries, simple exact match
    return target_lower in text_lower

def apply_strict_country_filter(metadata_list: List[Dict], target_country: str, filter_type: str) -> Tuple[List[Dict], int]:
    """
    Apply ultra-strict client-side country filtering with detailed logging
    """
    if not target_country:
        return metadata_list, 0
    
    filtered_list = []
    filtered_out_count = 0
    
    logger.info(f"🔍 STARTING STRICT FILTERING: Target='{target_country}', Type='{filter_type}', Input Records={len(metadata_list)}")
    
    for i, record in enumerate(metadata_list):
        should_include = False
        filter_reason = ""
        
        # Get country data from the record
        primary_country = record.get('primary_country', '').strip()
        all_countries = record.get('country', '').strip()
        title = record.get('title', '').strip()
        
        # Debug logging for first 5 records
        if i < 5:
            logger.info(f"DEBUG Record {i+1}: Primary='{primary_country}', All='{all_countries}', Title='{title[:100]}...'")
        
        if filter_type == 'primary':
            # Must be exact match in primary countries ONLY
            if is_exact_sudan_match(primary_country, target_country):
                # Double-check: ensure no South Sudan contamination anywhere
                if target_country.lower() == 'sudan':
                    if contains_south_sudan(primary_country) or contains_south_sudan(all_countries) or contains_south_sudan(title):
                        should_include = False
                        filter_reason = f"Contains South Sudan indicators"
                    else:
                        should_include = True
                        filter_reason = "Clean Sudan match"
                else:
                    should_include = True
                    filter_reason = "Exact country match"
            else:
                should_include = False
                filter_reason = f"Primary country '{primary_country}' doesn't match '{target_country}'"
                
        elif filter_type == 'associated':
            # Must be in all countries but NOT in primary
            in_all = is_exact_sudan_match(all_countries, target_country)
            in_primary = is_exact_sudan_match(primary_country, target_country)
            
            if in_all and not in_primary:
                # Double-check for South Sudan contamination
                if target_country.lower() == 'sudan':
                    if contains_south_sudan(all_countries) or contains_south_sudan(title):
                        should_include = False
                        filter_reason = "Associated but contains South Sudan"
                    else:
                        should_include = True
                        filter_reason = "Clean associated match"
                else:
                    should_include = True
                    filter_reason = "Associated match"
            else:
                should_include = False
                filter_reason = f"Not associated: in_all={in_all}, in_primary={in_primary}"
                
        else:  # 'all'
            # Must be mentioned exactly anywhere
            if is_exact_sudan_match(all_countries, target_country) or is_exact_sudan_match(primary_country, target_country):
                # Double-check for South Sudan contamination
                if target_country.lower() == 'sudan':
                    if contains_south_sudan(all_countries) or contains_south_sudan(primary_country) or contains_south_sudan(title):
                        should_include = False
                        filter_reason = "Mentioned but contains South Sudan"
                    else:
                        should_include = True
                        filter_reason = "Clean mention"
                else:
                    should_include = True
                    filter_reason = "Country mentioned"
            else:
                should_include = False
                filter_reason = f"No mention of '{target_country}'"
        
        if should_include:
            filtered_list.append(record)
            if i < 3:  # Log first few included records
                logger.info(f"✅ INCLUDED Record {i+1}: {filter_reason}")
        else:
            filtered_out_count += 1
            if i < 10:  # Log first few filtered records
                logger.info(f"❌ FILTERED Record {i+1}: {filter_reason}")
    
    logger.info(f"🎯 FILTERING COMPLETE: {len(metadata_list)} → {len(filtered_list)} records (filtered out {filtered_out_count})")
    
    # Additional validation for Sudan searches
    if target_country.lower() == 'sudan' and filtered_list:
        contaminated_count = 0
        for record in filtered_list:
            if (contains_south_sudan(record.get('primary_country', '')) or 
                contains_south_sudan(record.get('country', '')) or 
                contains_south_sudan(record.get('title', ''))):
                contaminated_count += 1
                logger.warning(f"⚠️ CONTAMINATION DETECTED in final results: {record.get('title', '')[:100]}")
        
        if contaminated_count > 0:
            logger.error(f"🚨 CRITICAL: {contaminated_count} South Sudan records still present in final results!")
        else:
            logger.info(f"✅ VALIDATION PASSED: No South Sudan contamination in final {len(filtered_list)} records")
    
    return filtered_list, filtered_out_count

def fetch_assessments(params: Dict[str, Any], downloads_dir: str) -> Tuple[List[Dict], List[str]]:
    """
    Fetch assessments with inclusive Sudan filtering
    """
    try:
        logger.info(f"🚀 Starting assessment fetch with parameters: {params}")
        
        # Validate limit parameter
        requested_limit = int(params.get('limit', 1000))
        if requested_limit > reliefweb_api.MAX_LIMIT:
            logger.warning(f"Adjusting limit from {requested_limit} to {reliefweb_api.MAX_LIMIT}")
            params['limit'] = str(reliefweb_api.MAX_LIMIT)
        
        # Use the API class to fetch reports
        api_response = reliefweb_api.fetch_reports(params)
        
        if not api_response.get('data'):
            logger.warning("No data returned from API")
            return [], []
        
        logger.info(f"📥 Successfully received {len(api_response['data'])} records from API")
        
        # Extract metadata (existing code...)
        metadata_list = []
        download_paths = []
        
        for i, item in enumerate(api_response['data']):
            fields = item.get('fields', {})
            
            # Extract and format metadata (existing extraction code...)
            metadata = {
                'report_id': item.get('id'),
                'title': fields.get('title', ''),
                'body': fields.get('body', ''),
                'body_html': fields.get('body-html', ''),
                'url': fields.get('url', ''),
                'url_alias': fields.get('url_alias', ''),
                'status': fields.get('status', ''),
                'origin': fields.get('origin', ''),
                'date_created': '',
                'country': '',
                'primary_country': '',
                'source': '',
                'format': '',
                'theme': '',
                'language': '',
                'disaster': '',
                'disaster_type': '',
                'file_info': ''
            }
            
            # Extract date information
            date_info = fields.get('date', {})
            if isinstance(date_info, dict) and 'created' in date_info:
                metadata['date_created'] = date_info['created']
            
            # Extract primary country information
            primary_countries = fields.get('primary_country', [])            
            if primary_countries:
                if isinstance(primary_countries, list):
                    primary_country_names = []
                    for pc in primary_countries:
                        if isinstance(pc, dict) and pc.get('name'):
                            primary_country_names.append(pc['name'])
                        elif isinstance(pc, str):
                            primary_country_names.append(pc)
                    metadata['primary_country'] = ', '.join(primary_country_names)
                elif isinstance(primary_countries, str):
                    metadata['primary_country'] = primary_countries
                elif isinstance(primary_countries, dict) and primary_countries.get('name'):
                    metadata['primary_country'] = primary_countries['name']
            
            # Extract all countries information
            all_countries = fields.get('country', [])
            if all_countries:
                if isinstance(all_countries, list):
                    country_names = []
                    for c in all_countries:
                        if isinstance(c, dict) and c.get('name'):
                            country_names.append(c['name'])
                        elif isinstance(c, str):
                            country_names.append(c)
                    metadata['country'] = ', '.join(country_names)
                elif isinstance(all_countries, str):
                    metadata['country'] = all_countries
                elif isinstance(all_countries, dict) and all_countries.get('name'):
                    metadata['country'] = all_countries['name']
            
            # Extract other fields (source, format, theme, etc.)
            sources = fields.get('source', [])
            if sources and isinstance(sources, list):
                source_names = [s.get('name', '') for s in sources if s.get('name')]
                metadata['source'] = ', '.join(source_names)
            
            formats = fields.get('format', [])
            if formats and isinstance(formats, list):
                format_names = [f.get('name', '') for f in formats if f.get('name')]
                metadata['format'] = ', '.join(format_names)
            
            themes = fields.get('theme', [])
            if themes and isinstance(themes, list):
                theme_names = [t.get('name', '') for t in themes if t.get('name')]
                metadata['theme'] = ', '.join(theme_names)
            
            languages = fields.get('language', [])
            if languages and isinstance(languages, list):
                language_names = [l.get('name', '') for l in languages if l.get('name')]
                metadata['language'] = ', '.join(language_names)
            
            disasters = fields.get('disaster', [])
            if disasters and isinstance(disasters, list):
                disaster_names = [d.get('name', '') for d in disasters if d.get('name')]
                metadata['disaster'] = ', '.join(disaster_names)
                
                disaster_types = []
                for disaster in disasters:
                    if disaster.get('type') and isinstance(disaster['type'], list):
                        disaster_types.extend([dt.get('name', '') for dt in disaster['type'] if dt.get('name')])
                metadata['disaster_type'] = ', '.join(disaster_types)
            
            files = fields.get('file', [])
            if files and isinstance(files, list):
                file_info = []
                for file_obj in files:
                    if isinstance(file_obj, dict):
                        file_desc = f"File: {file_obj.get('filename', 'Unknown')} ({file_obj.get('mimetype', 'Unknown type')})"
                        if file_obj.get('url'):
                            file_desc += f" - URL: {file_obj['url']}"
                        file_info.append(file_desc)
                metadata['file_info'] = ' | '.join(file_info)
            
            metadata_list.append(metadata)
            
            # Handle document downloads if requested
            if params.get('download_docs', False) and files:
                for file_obj in files:
                    if isinstance(file_obj, dict) and file_obj.get('url'):
                        try:
                            file_path = download_document(
                                file_obj['url'], 
                                file_obj.get('filename', f"document_{item.get('id')}.pdf"),
                                downloads_dir
                            )
                            if file_path:
                                download_paths.append(file_path)
                        except Exception as e:
                            logger.warning(f"Failed to download file {file_obj.get('filename', 'unknown')}: {e}")
        
        logger.info(f"📋 Extracted metadata for {len(metadata_list)} records")
        
        # APPLY NEW INCLUSIVE FILTERING
        target_country = params.get('country', '').strip()
        filter_type = params.get('country_filter_type', 'primary')
        
        if target_country:
            logger.info(f"🔧 Applying INCLUSIVE filtering: '{target_country}' ({filter_type})")
            metadata_list, filtered_count, validation_report = apply_inclusive_sudan_filtering(
                metadata_list, target_country, filter_type
            )
            
            logger.info(f"🎯 FINAL RESULT: {len(metadata_list)} records included (removed {filtered_count} irrelevant records)")
        else:
            logger.info("No country filter specified, returning all records")
        
        return metadata_list, download_paths
        
    except Exception as e:
        logger.error(f"Error fetching assessments: {e}")
        raise

def download_document(url: str, filename: str, downloads_dir: str) -> Optional[str]:
    """Download a document from a URL"""
    try:
        os.makedirs(downloads_dir, exist_ok=True)
        
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        if not safe_filename:
            safe_filename = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        file_path = os.path.join(downloads_dir, safe_filename)
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Downloaded document: {safe_filename}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to download document from {url}: {e}")
        return None

def get_filter_options() -> Dict[str, List[str]]:
    """Get filter options for the web interface"""
    return reliefweb_api.get_filter_options()

def get_available_fields() -> List[str]:
    """Get available fields from the ReliefWeb API"""
    return [
        'id', 'title', 'body', 'body-html', 'date', 'date.created', 'date.original',
        'source', 'source.name', 'source.shortname', 'source.longname',
        'format', 'format.name', 'theme', 'theme.name', 
        'primary_country', 'primary_country.name', 'primary_country.iso3',
        'country', 'country.name', 'country.iso3',
        'language', 'language.name', 'language.code',
        'status', 'url', 'url_alias', 'file', 'file.url', 'file.filename',
        'disaster', 'disaster.name', 'disaster.type',
        'headline', 'headline.title', 'headline.summary',
        'origin'
    ]

def get_document_count(country: str, format_type: str = None, country_filter_type: str = 'primary', 
                      date_from: str = None, date_to: str = None) -> Dict[str, Any]:
    """
    Get total document count for a specific country and format without downloading data
    
    Args:
        country: Country name (e.g., 'Sudan')
        format_type: Format name (e.g., 'Assessment') - optional
        country_filter_type: 'primary', 'associated', or 'all'
        date_from: Start date (YYYY-MM-DD) - optional
        date_to: End date (YYYY-MM-DD) - optional
    
    Returns:
        Dict with count information and breakdown
    """
    try:
        logger.info(f"🔢 Checking document count for: Country='{country}', Format='{format_type}', Type='{country_filter_type}'")
        
        # Build conditions for count query
        conditions = []
        
        # Country filter
        if country:
            if country_filter_type == 'primary':
                conditions.append({
                    "field": "primary_country.name",
                    "value": country
                })
            elif country_filter_type == 'associated':
                conditions.append({
                    "operator": "AND",
                    "conditions": [
                        {"field": "country.name", "value": country},
                        {"field": "primary_country.name", "value": country, "negate": True}
                    ]
                })
            else:  # 'all'
                conditions.append({
                    "field": "country.name",
                    "value": country
                })
        
        # Format filter
        if format_type:
            conditions.append({
                "field": "format.name",
                "value": format_type
            })
        
        # Date range filter
        if date_from or date_to:
            date_condition = {"field": "date.created"}
            
            if date_from and date_to:
                date_condition["value"] = {
                    "from": f"{date_from}T00:00:00+00:00",
                    "to": f"{date_to}T23:59:59+00:00"
                }
            elif date_from:
                date_condition["value"] = {"from": f"{date_from}T00:00:00+00:00"}
            elif date_to:
                date_condition["value"] = {"to": f"{date_to}T23:59:59+00:00"}
                
            conditions.append(date_condition)
        
        # Build filter
        if len(conditions) == 0:
            main_filter = None
        elif len(conditions) == 1:
            main_filter = conditions[0]
        else:
            main_filter = {
                "operator": "AND",
                "conditions": conditions
            }
        
        # Build payload for count-only query
        payload = {
            "preset": "minimal",
            "limit": 0,  # We only want the count, not the actual documents
            "facets": [
                {"field": "format.name", "limit": 50, "sort": "value:asc"},
                {"field": "source.name", "limit": 20, "sort": "count:desc"},
                {"field": "theme.name", "limit": 20, "sort": "count:desc"}
            ]
        }
        
        # Add filter if we have conditions
        if main_filter:
            payload["filter"] = main_filter
        
        logger.info(f"📡 Sending count query with payload: {json.dumps(payload, indent=2)}")
        
        # Make the API request
        url = f"{reliefweb_api.BASE_URL}/reports"
        params = {"appname": reliefweb_api.APP_NAME}
        
        response = reliefweb_api.session.post(url, json=payload, params=params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"API Error ({response.status_code}). Response: {response.text}")
            response.raise_for_status()
        
        data = response.json()
        
        # Extract count and facet information
        total_count = data.get('totalCount', 0)
        
        # Get format breakdown
        format_facets = data.get('facets', {}).get('format.name', {}).get('data', [])
        format_breakdown = {item['value']: item['count'] for item in format_facets}
        
        # Get source breakdown
        source_facets = data.get('facets', {}).get('source.name', {}).get('data', [])
        source_breakdown = {item['value']: item['count'] for item in source_facets}
        
        # Get theme breakdown
        theme_facets = data.get('facets', {}).get('theme.name', {}).get('data', [])
        theme_breakdown = {item['value']: item['count'] for item in theme_facets}
        
        result = {
            'total_count': total_count,
            'query_parameters': {
                'country': country,
                'format': format_type,
                'country_filter_type': country_filter_type,
                'date_from': date_from,
                'date_to': date_to
            },
            'breakdown': {
                'by_format': format_breakdown,
                'by_source': source_breakdown,
                'by_theme': theme_breakdown
            }
        }
        
        logger.info(f"📊 Found {total_count} documents matching criteria")
        logger.info(f"🎯 Format breakdown: {format_breakdown}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting document count: {e}")
        raise Exception(f"Failed to get document count: {e}")

def get_all_format_counts_for_country(country: str, country_filter_type: str = 'primary') -> Dict[str, int]:
    """
    Get document counts for all formats for a specific country
    
    Args:
        country: Country name (e.g., 'Sudan')
        country_filter_type: 'primary', 'associated', or 'all'
    
    Returns:
        Dict with format names as keys and counts as values
    """
    try:
        logger.info(f"📋 Getting all format counts for '{country}' ({country_filter_type})")
        
        # Get count with format facets
        result = get_document_count(country, None, country_filter_type)
        
        format_counts = result['breakdown']['by_format']
        total = result['total_count']
        
        logger.info(f"📊 Total documents for {country}: {total}")
        for format_name, count in sorted(format_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  📄 {format_name}: {count}")
        
        return format_counts
        
    except Exception as e:
        logger.error(f"Error getting format counts: {e}")
        raise

# Test the imports by creating a simple validation function
def validate_api_functions():
    """Validate that all required functions are available"""
    try:
        # Test that all functions can be called
        fields = get_available_fields()
        options = get_filter_options()
        
        print(f"✅ API functions validated successfully")
        print(f"   - Available fields: {len(fields)}")
        print(f"   - Filter options: {len(options)} categories")
        return True
    except Exception as e:
        print(f"❌ API function validation failed: {e}")
        return False

# Run validation if module is imported
if __name__ != "__main__":
    logger.info("ReliefWeb API module loaded successfully")

def analyze_country_data_before_filtering(metadata_list: List[Dict], target_country: str) -> Dict[str, Any]:
    """
    Analyze country data before filtering to identify potential issues
    """
    analysis = {
        'total_records': len(metadata_list),
        'target_country': target_country,
        'country_field_analysis': {},
        'primary_country_analysis': {},
        'title_mentions': {},
        'potential_valid_records': [],
        'suspicious_exclusions': [],
        'data_quality_issues': []
    }
    
    target_lower = target_country.lower()
    
    for i, record in enumerate(metadata_list):
        record_id = record.get('report_id', f'record_{i}')
        title = record.get('title', '').strip()
        primary_country = record.get('primary_country', '').strip()
        all_countries = record.get('country', '').strip()
        
        # Analyze country field patterns
        if all_countries:
            analysis['country_field_analysis'][record_id] = all_countries
            
        # Analyze primary country patterns
        if primary_country:
            analysis['primary_country_analysis'][record_id] = primary_country
        else:
            analysis['data_quality_issues'].append({
                'record_id': record_id,
                'issue': 'missing_primary_country',
                'title': title[:100],
                'all_countries': all_countries
            })
        
        # Check title mentions
        if target_lower in title.lower():
            analysis['title_mentions'][record_id] = title
            
        # Identify potential valid records that might be excluded
        title_has_target = target_lower in title.lower()
        countries_has_target = target_lower in all_countries.lower() if all_countries else False
        primary_has_target = target_lower in primary_country.lower() if primary_country else False
        
        # Special case for Sudan vs South Sudan
        if target_lower == 'sudan':
            title_has_south_sudan = contains_south_sudan(title)
            countries_has_south_sudan = contains_south_sudan(all_countries)
            primary_has_south_sudan = contains_south_sudan(primary_country)
            
            if (title_has_target or countries_has_target or primary_has_target) and not (title_has_south_sudan or countries_has_south_sudan or primary_has_south_sudan):
                analysis['potential_valid_records'].append({
                    'record_id': record_id,
                    'title': title[:100],
                    'primary_country': primary_country,
                    'all_countries': all_countries,
                    'reasons': {
                        'title_match': title_has_target,
                        'countries_match': countries_has_target,
                        'primary_match': primary_has_target,
                        'no_south_sudan': True
                    }
                })
        else:
            if title_has_target or countries_has_target or primary_has_target:
                analysis['potential_valid_records'].append({
                    'record_id': record_id,
                    'title': title[:100],
                    'primary_country': primary_country,
                    'all_countries': all_countries,
                    'reasons': {
                        'title_match': title_has_target,
                        'countries_match': countries_has_target,
                        'primary_match': primary_has_target
                    }
                })
    
    return analysis

def post_filtering_validation(original_list: List[Dict], filtered_list: List[Dict], 
                            excluded_list: List[Dict], target_country: str, filter_type: str) -> Dict[str, Any]:
    """
    Validate filtering results and identify potential false negatives
    """
    validation = {
        'original_count': len(original_list),
        'filtered_count': len(filtered_list),
        'excluded_count': len(excluded_list),
        'target_country': target_country,
        'filter_type': filter_type,
        'false_negatives': [],
        'suspicious_exclusions': [],
        'quality_issues': [],
        'recommendations': []
    }
    
    target_lower = target_country.lower()
    
    # Check excluded records for potential false negatives
    for record in excluded_list:
        record_id = record.get('report_id', 'unknown')
        title = record.get('title', '').strip()
        primary_country = record.get('primary_country', '').strip()
        all_countries = record.get('country', '').strip()
        
        # Check if this looks like it should have been included
        suspicious_reasons = []
        
        # Title contains target country
        if target_lower in title.lower():
            if target_lower == 'sudan' and not contains_south_sudan(title):
                suspicious_reasons.append(f"Title contains '{target_country}' without South Sudan")
            elif target_lower != 'sudan':
                suspicious_reasons.append(f"Title contains '{target_country}'")
        
        # Check for data quality issues
        if not primary_country and target_lower in all_countries.lower():
            suspicious_reasons.append("Missing primary country but target in all countries")
            validation['quality_issues'].append({
                'record_id': record_id,
                'issue': 'missing_primary_country_field',
                'title': title[:100],
                'all_countries': all_countries
            })
        
        # Check for exact country name patterns
        if filter_type == 'primary':
            # Look for records that should match primary filter
            country_patterns = [
                f'{target_country},',
                f'{target_country} ',
                f'{target_country}.',
                f'{target_country};'
            ]
            
            for pattern in country_patterns:
                if pattern.lower() in all_countries.lower() and pattern.lower() not in primary_country.lower():
                    suspicious_reasons.append(f"Pattern '{pattern}' in all countries but not primary")
        
        if suspicious_reasons:
            validation['suspicious_exclusions'].append({
                'record_id': record_id,
                'title': title[:100],
                'primary_country': primary_country,
                'all_countries': all_countries,
                'reasons': suspicious_reasons
            })
    
    # Generate recommendations
    if validation['quality_issues']:
        validation['recommendations'].append("Consider using 'all' filter type due to missing primary country data")
    
    if validation['suspicious_exclusions']:
        validation['recommendations'].append("Review suspicious exclusions for potential false negatives")
    
    if len(filtered_list) == 0 and len(validation['suspicious_exclusions']) > 0:
        validation['recommendations'].append("CRITICAL: No results but suspicious exclusions found - check filtering logic")
    
    return validation

def manual_validation_check(country: str, filter_type: str = 'primary', limit: int = 100):
    """
    Manual validation function to check filtering behavior
    """
    logger.info(f"🔍 MANUAL VALIDATION CHECK: {country} ({filter_type})")
    
    # Fetch sample data
    params = {
        'country': country,
        'country_filter_type': filter_type,
        'format': 'Assessment',
        'limit': str(limit)
    }
    
    try:
        api_response = reliefweb_api.fetch_reports(params)
        
        if not api_response.get('data'):
            logger.info("No data returned from API")
            return
        
        logger.info(f"📊 Analyzing {len(api_response['data'])} records...")
        
        # Check each record manually
        for i, item in enumerate(api_response['data'][:10]):  # Check first 10
            fields = item.get('fields', {})
            
            title = fields.get('title', '')
            primary_countries = fields.get('primary_country', [])
            all_countries = fields.get('country', [])
            
            # Extract country names
            primary_names = []
            if isinstance(primary_countries, list):
                primary_names = [pc.get('name', '') for pc in primary_countries if isinstance(pc, dict)]
            
            all_names = []
            if isinstance(all_countries, list):
                all_names = [c.get('name', '') for c in all_countries if isinstance(c, dict)]
            
            primary_str = ', '.join(primary_names)
            all_str = ', '.join(all_names)
            
            logger.info(f"Record {i+1}:")
            logger.info(f"  Title: {title[:100]}...")
            logger.info(f"  Primary: '{primary_str}'")
            logger.info(f"  All: '{all_str}'")
            logger.info(f"  Should include? {is_exact_sudan_match(primary_str, country)}")
            logger.info(f"  Contains South Sudan? {contains_south_sudan(title) or contains_south_sudan(primary_str) or contains_south_sudan(all_str)}")
            logger.info("---")
            
    except Exception as e:
        logger.error(f"Manual validation failed: {e}")

def apply_strict_country_filter_with_validation(metadata_list: List[Dict], target_country: str, filter_type: str) -> Tuple[List[Dict], int, Dict[str, Any]]:
    """
    Apply filtering with comprehensive validation and analysis
    Updated logic: Include records where Sudan appears anywhere, even with other countries,
    but exclude records that only contain South Sudan (with or without other countries)
    """
    if not target_country:
        return metadata_list, 0, {}
    
    logger.info(f"🔍 STARTING FILTERING WITH VALIDATION: Target='{target_country}', Type='{filter_type}', Input Records={len(metadata_list)}")
    
    # STEP 1: Pre-filtering analysis
    pre_analysis = analyze_country_data_before_filtering(metadata_list, target_country)
    logger.info(f"📊 PRE-ANALYSIS: Found {len(pre_analysis['potential_valid_records'])} potentially valid records")
    
    if pre_analysis['data_quality_issues']:
        logger.warning(f"⚠️ DATA QUALITY ISSUES: {len(pre_analysis['data_quality_issues'])} records with issues")
        for issue in pre_analysis['data_quality_issues'][:3]:  # Log first 3 issues
            logger.warning(f"   - Record {issue['record_id']}: {issue['issue']}")
    
    # STEP 2: Apply filtering
    filtered_list = []
    excluded_list = []
    filtered_out_count = 0
    
    for i, record in enumerate(metadata_list):
        should_include = False
        filter_reason = ""
        
        # Get country data from the record
        primary_country = record.get('primary_country', '').strip()
        all_countries = record.get('country', '').strip()
        title = record.get('title', '').strip()
        
        # Debug logging for first 5 records
        if i < 5:
            logger.info(f"🔍 Record {i+1}: Primary='{primary_country}', All='{all_countries}', Title='{title[:100]}...'")
        
        # NEW LOGIC: Check if Sudan appears anywhere (primary or all countries)
        sudan_in_primary = is_exact_sudan_match(primary_country, target_country)
        sudan_in_all = is_exact_sudan_match(all_countries, target_country)
        sudan_appears_somewhere = sudan_in_primary or sudan_in_all
        
        # Check for South Sudan contamination
        south_sudan_in_primary = contains_south_sudan(primary_country)
        south_sudan_in_all = contains_south_sudan(all_countries)
        south_sudan_in_title = contains_south_sudan(title)
        
        if target_country.lower() == 'sudan':
            if sudan_appears_somewhere:
                # Sudan is mentioned - this is potentially valid
                # But check if it's contaminated with South Sudan references
                if south_sudan_in_primary or south_sudan_in_all or south_sudan_in_title:
                    # Special case: If Sudan is primary but South Sudan is only in "all countries", 
                    # we might still want to include it (regional reports)
                    if sudan_in_primary and not south_sudan_in_primary and not south_sudan_in_title:
                        should_include = True
                        filter_reason = "Sudan primary with regional context (includes South Sudan)"
                    else:
                        should_include = False
                        filter_reason = "Contains South Sudan indicators that could cause confusion"
                else:
                    # Clean Sudan mention without South Sudan
                    should_include = True
                    filter_reason = "Clean Sudan mention"
            else:
                # Sudan is not mentioned at all
                should_include = False
                filter_reason = f"No mention of Sudan"
        else:
            # For non-Sudan countries, apply standard filtering
            if filter_type == 'primary':
                should_include = is_exact_sudan_match(primary_country, target_country)
                filter_reason = "Primary country match" if should_include else f"Primary country '{primary_country}' doesn't match '{target_country}'"
                
            elif filter_type == 'associated':
                in_all = is_exact_sudan_match(all_countries, target_country)
                in_primary = is_exact_sudan_match(primary_country, target_country)
                should_include = in_all and not in_primary
                filter_reason = "Associated match" if should_include else f"Not associated: in_all={in_all}, in_primary={in_primary}"
                
            else:  # 'all'
                should_include = is_exact_sudan_match(all_countries, target_country) or is_exact_sudan_match(primary_country, target_country)
                filter_reason = "Country mentioned" if should_include else f"No mention of '{target_country}'"
        
        if should_include:
            filtered_list.append(record)
            if i < 3:  # Log first few included records
                logger.info(f"✅ INCLUDED Record {i+1}: {filter_reason}")
        else:
            excluded_list.append(record)
            filtered_out_count += 1
            if i < 10:  # Log first few filtered records
                logger.info(f"❌ FILTERED Record {i+1}: {filter_reason}")
    
    # STEP 3: Post-filtering validation
    validation = post_filtering_validation(metadata_list, filtered_list, excluded_list, target_country, filter_type)
    
    # STEP 4: Report results
    logger.info(f"🎯 FILTERING COMPLETE: {len(metadata_list)} → {len(filtered_list)} records (filtered out {filtered_out_count})")
    
    if validation['suspicious_exclusions']:
        logger.warning(f"⚠️ SUSPICIOUS EXCLUSIONS: {len(validation['suspicious_exclusions'])} records may have been incorrectly excluded")
        for exclusion in validation['suspicious_exclusions'][:3]:  # Log first 3
            logger.warning(f"   - Record {exclusion['record_id']}: {', '.join(exclusion['reasons'])}")
    
    if validation['recommendations']:
        logger.info("💡 RECOMMENDATIONS:")
        for rec in validation['recommendations']:
            logger.info(f"   - {rec}")
    
    # STEP 5: Final validation for Sudan searches
    if target_country.lower() == 'sudan' and filtered_list:
        regional_reports = 0
        clean_sudan_only = 0
        
        for record in filtered_list:
            primary = record.get('primary_country', '')
            all_countries = record.get('country', '')
            
            if is_exact_sudan_match(primary, 'Sudan'):
                if contains_south_sudan(all_countries):
                    regional_reports += 1
                else:
                    clean_sudan_only += 1
            elif is_exact_sudan_match(all_countries, 'Sudan'):
                regional_reports += 1
        
        logger.info(f"✅ FINAL VALIDATION: {len(filtered_list)} Sudan records ({clean_sudan_only} Sudan-only, {regional_reports} regional)")
    
    return filtered_list, filtered_out_count, validation

def build_filters(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build API filters based on parameters"""
    filters = []
    
    country = params.get('country', '').strip()
    country_filter_type = params.get('country_filter_type', 'primary')
    
    if country:
        if country_filter_type == 'primary':
            filters.append({
                'field': 'primary_country.name',
                'value': country
            })
            logger.info(f"Using primary country filter: primary_country.name = '{country}'")
            
        elif country_filter_type == 'associated':
            # For Sudan, we want to be more inclusive to capture regional reports
            if country.lower() == 'sudan':
                # Get records where Sudan is mentioned but might not be primary
                filters.append({
                    'field': 'country.name',
                    'value': country
                })
                logger.info(f"Using inclusive Sudan filter: country.name = '{country}'")
            else:
                # Standard associated filter for other countries
                filters.append({
                    'operator': 'AND',
                    'conditions': [
                        {
                            'field': 'country.name',
                            'value': country
                        },
                        {
                            'field': 'primary_country.name',
                            'value': country,
                            'negate': True
                        }
                    ]
                })
                logger.info(f"Using associated country filter: '{country}'")
                
        else:  # 'all'
            filters.append({
                'field': 'country.name',
                'value': country
            })
            logger.info(f"Using country filter (all mentions): country.name = '{country}'")
    
    # Rest of the filtering logic remains the same...
    format_type = params.get('format', '').strip()
    if format_type:
        filters.append({
            'field': 'format.name',
            'value': format_type
        })
        logger.info(f"Using format filter: format.name = '{format_type}'")
    
    theme = params.get('theme', '').strip()
    if theme:
        filters.append({
            'field': 'theme.name',
            'value': theme
        })
        logger.info(f"Using theme filter: theme.name = '{theme}'")
    
    source = params.get('source', '').strip()
    if source:
        filters.append({
            'field': 'source.name',
            'value': source
        })
        logger.info(f"Using source filter: source.name = '{source}'")
    
    language = params.get('language', '').strip()
    if language:
        filters.append({
            'field': 'language.name',
            'value': language
        })
        logger.info(f"Using language filter: language.name = '{language}'")
    
    # Date filters
    date_from = params.get('date_from', '').strip()
    date_to = params.get('date_to', '').strip()
    
    if date_from or date_to:
        date_filter = {'field': 'date.created', 'value': {}}
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                date_filter['value']['from'] = from_date.strftime('%Y-%m-%dT00:00:00+00:00')
            except ValueError:
                logger.warning(f"Invalid date_from format: {date_from}")
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d')
                date_filter['value']['to'] = to_date.strftime('%Y-%m-%dT23:59:59+00:00')
            except ValueError:
                logger.warning(f"Invalid date_to format: {date_to}")
        
        if date_filter['value']:
            filters.append(date_filter)
            logger.info(f"Using date filter: {date_filter}")
    
    return filters

def apply_inclusive_sudan_filtering(metadata_list: List[Dict], target_country: str, filter_type: str) -> Tuple[List[Dict], int, Dict[str, Any]]:
    """
    Apply inclusive filtering that includes regional reports where Sudan appears with other countries
    Key principle: Include if Sudan is mentioned, exclude only if it's ONLY South Sudan (no Sudan mention)
    """
    if not target_country:
        return metadata_list, 0, {}
    
    logger.info(f"🔍 STARTING INCLUSIVE FILTERING: Target='{target_country}', Type='{filter_type}', Input Records={len(metadata_list)}")
    
    filtered_list = []
    excluded_list = []
    filtered_out_count = 0
    
    for i, record in enumerate(metadata_list):
        should_include = False
        filter_reason = ""
        
        # Get country data from the record
        primary_country = record.get('primary_country', '').strip()
        all_countries = record.get('country', '').strip()
        title = record.get('title', '').strip()
        
        # Debug logging for first 5 records
        if i < 5:
            logger.info(f"🔍 Record {i+1}: Primary='{primary_country}', All='{all_countries}', Title='{title[:100]}...'")
        
        if target_country.lower() == 'sudan':
            # NEW INCLUSIVE LOGIC FOR SUDAN
            
            # Check if Sudan is mentioned anywhere
            sudan_in_primary = is_exact_sudan_match(primary_country, target_country)
            sudan_in_all = is_exact_sudan_match(all_countries, target_country)
            sudan_mentioned = sudan_in_primary or sudan_in_all
            
            # Check if ONLY South Sudan is mentioned (without Sudan)
            south_sudan_in_primary = contains_south_sudan(primary_country)
            south_sudan_in_all = contains_south_sudan(all_countries)
            south_sudan_in_title = contains_south_sudan(title)
            
            if sudan_mentioned:
                # Sudan is mentioned - this is potentially valid
                # Apply filter type logic but be inclusive
                
                if filter_type == 'primary':
                    # Must have Sudan as primary country
                    if sudan_in_primary:
                        should_include = True
                        if south_sudan_in_all:
                            filter_reason = "Sudan primary with regional context (includes South Sudan)"
                        else:
                            filter_reason = "Clean Sudan primary country"
                    else:
                        should_include = False
                        filter_reason = f"Sudan not in primary country (primary='{primary_country}')"
                        
                elif filter_type == 'associated':
                    # Sudan mentioned but not primary
                    if sudan_in_all and not sudan_in_primary:
                        should_include = True
                        filter_reason = "Sudan in associated countries"
                    else:
                        should_include = False
                        filter_reason = f"Not associated: sudan_in_all={sudan_in_all}, sudan_in_primary={sudan_in_primary}"
                        
                else:  # 'all' - most inclusive
                    # Sudan mentioned anywhere
                    should_include = True
                    if sudan_in_primary and south_sudan_in_all:
                        filter_reason = "Sudan primary with regional mentions"
                    elif sudan_in_primary:
                        filter_reason = "Sudan primary country"
                    elif sudan_in_all:
                        filter_reason = "Sudan in associated countries"
                    else:
                        filter_reason = "Sudan mentioned"
                        
            else:
                # Sudan is NOT mentioned
                if south_sudan_in_primary or south_sudan_in_all or south_sudan_in_title:
                    # Only South Sudan mentioned, no Sudan
                    should_include = False
                    filter_reason = "Only South Sudan mentioned (no Sudan)"
                else:
                    # Neither Sudan nor South Sudan mentioned
                    should_include = False
                    filter_reason = "No Sudan mention found"
                    
        else:
            # For non-Sudan countries, apply standard filtering
            if filter_type == 'primary':
                should_include = is_exact_sudan_match(primary_country, target_country)
                filter_reason = "Primary country match" if should_include else f"Primary country '{primary_country}' doesn't match '{target_country}'"
                
            elif filter_type == 'associated':
                in_all = is_exact_sudan_match(all_countries, target_country)
                in_primary = is_exact_sudan_match(primary_country, target_country)
                should_include = in_all and not in_primary
                filter_reason = "Associated match" if should_include else f"Not associated: in_all={in_all}, in_primary={in_primary}"
                
            else:  # 'all'
                should_include = is_exact_sudan_match(all_countries, target_country) or is_exact_sudan_match(primary_country, target_country)
                filter_reason = "Country mentioned" if should_include else f"No mention of '{target_country}'"
        
        if should_include:
            filtered_list.append(record)
            if i < 5:  # Log first few included records
                logger.info(f"✅ INCLUDED Record {i+1}: {filter_reason}")
        else:
            excluded_list.append(record)
            filtered_out_count += 1
            if i < 10:  # Log first few filtered records
                logger.info(f"❌ FILTERED Record {i+1}: {filter_reason}")
    
    # Report results with breakdown
    logger.info(f"🎯 INCLUSIVE FILTERING COMPLETE: {len(metadata_list)} → {len(filtered_list)} records (filtered out {filtered_out_count})")
    
    # Analyze final results for Sudan
    if target_country.lower() == 'sudan' and filtered_list:
        pure_sudan = 0
        regional_sudan = 0
        
        for record in filtered_list:
            primary = record.get('primary_country', '')
            all_countries = record.get('country', '')
            
            if is_exact_sudan_match(primary, 'Sudan'):
                if contains_south_sudan(all_countries):
                    regional_sudan += 1
                else:
                    pure_sudan += 1
            else:
                regional_sudan += 1
        
        logger.info(f"✅ FINAL BREAKDOWN: {pure_sudan} pure Sudan + {regional_sudan} regional Sudan = {len(filtered_list)} total")
    
    # Create validation report
    validation = {
        'original_count': len(metadata_list),
        'filtered_count': len(filtered_list),
        'excluded_count': filtered_out_count,
        'target_country': target_country,
        'filter_type': filter_type,
        'inclusive_filtering': True
    }
    
    return filtered_list, filtered_out_count, validation