"""
Administrative Geography utilities for extracting and managing geo districts
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AdminDistrict:
    """Administrative district data structure"""
    name: str
    level: int  # 0=country, 1=admin1, 2=admin2, etc.
    parent_code: Optional[str] = None
    iso_code: Optional[str] = None
    confidence: float = 0.0
    extraction_method: str = ""

class AdminGeoExtractor:
    """Extract administrative geographic information from text"""
    
    def __init__(self):
        self.country_patterns = self._load_country_patterns()
        self.admin_patterns = self._load_admin_patterns()
    
    def _load_country_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load country patterns and ISO codes"""
        return {
            'sudan': {
                'names': ['sudan', 'republic of sudan', 'republic of the sudan'],
                'iso2': 'SD',
                'iso3': 'SDN',
                'variants': ['sudanese']
            },
            'south_sudan': {
                'names': ['south sudan', 'republic of south sudan'],
                'iso2': 'SS',
                'iso3': 'SSD',
                'variants': ['south sudanese']
            },
            'chad': {
                'names': ['chad', 'republic of chad'],
                'iso2': 'TD',
                'iso3': 'TCD',
                'variants': ['chadian']
            },
            'ethiopia': {
                'names': ['ethiopia', 'federal democratic republic of ethiopia'],
                'iso2': 'ET',
                'iso3': 'ETH',
                'variants': ['ethiopian']
            },
            'eritrea': {
                'names': ['eritrea', 'state of eritrea'],
                'iso2': 'ER',
                'iso3': 'ERI',
                'variants': ['eritrean']
            },
            'libya': {
                'names': ['libya', 'state of libya'],
                'iso2': 'LY',
                'iso3': 'LBY',
                'variants': ['libyan']
            },
            'egypt': {
                'names': ['egypt', 'arab republic of egypt'],
                'iso2': 'EG',
                'iso3': 'EGY',
                'variants': ['egyptian']
            },
            'central_african_republic': {
                'names': ['central african republic', 'car'],
                'iso2': 'CF',
                'iso3': 'CAF',
                'variants': ['central african']
            }
        }
    
    def _load_admin_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Load administrative division patterns by country"""
        return {
            'sudan': {
                'states': [
                    # Current 18 states of Sudan
                    'blue nile', 'central darfur', 'east darfur', 'gedaref', 'gezira',
                    'kassala', 'khartoum', 'north darfur', 'north kordofan', 'northern',
                    'red sea', 'river nile', 'sennar', 'south darfur', 'south kordofan',
                    'west darfur', 'west kordofan', 'white nile'
                ],
                'localities': [
                    # Major localities/cities
                    'khartoum north', 'omdurman', 'bahri', 'port sudan', 'kassala city',
                    'el fasher', 'nyala', 'el obeid', 'wad medani', 'gedaref city',
                    'dongola', 'atbara', 'sennar city', 'ed dueim', 'kadugli'
                ]
            },
            'south_sudan': {
                'states': [
                    'central equatoria', 'eastern equatoria', 'western equatoria',
                    'jonglei', 'lakes', 'northern bahr el ghazal', 'unity',
                    'upper nile', 'warrap', 'western bahr el ghazal'
                ],
                'counties': [
                    'juba', 'torit', 'yambio', 'bor', 'rumbek', 'aweil',
                    'bentiu', 'malakal', 'kuajok', 'wau'
                ]
            }
        }
    
    def extract_primary_country(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract primary country from text content"""
        if not text:
            return None
        
        text_lower = text.lower()
        country_matches = []
        
        for country_key, country_data in self.country_patterns.items():
            confidence = 0.0
            matches = 0
            
            # Check main country names
            for name in country_data['names']:
                pattern = r'\b' + re.escape(name) + r'\b'
                if re.search(pattern, text_lower):
                    matches += len(re.findall(pattern, text_lower))
                    confidence += 0.8
            
            # Check variants
            for variant in country_data.get('variants', []):
                pattern = r'\b' + re.escape(variant) + r'\b'
                if re.search(pattern, text_lower):
                    matches += len(re.findall(pattern, text_lower))
                    confidence += 0.6
            
            # Check ISO codes
            iso2_pattern = r'\b' + re.escape(country_data['iso2']) + r'\b'
            iso3_pattern = r'\b' + re.escape(country_data['iso3']) + r'\b'
            
            if re.search(iso2_pattern, text_lower):
                matches += len(re.findall(iso2_pattern, text_lower))
                confidence += 0.9
            
            if re.search(iso3_pattern, text_lower):
                matches += len(re.findall(iso3_pattern, text_lower))
                confidence += 0.9
            
            if matches > 0:
                country_matches.append({
                    'country': country_key,
                    'matches': matches,
                    'confidence': min(confidence, 1.0),
                    'iso2': country_data['iso2'],
                    'iso3': country_data['iso3']
                })
        
        if not country_matches:
            return None
        
        # Return country with highest confidence
        primary_country = max(country_matches, key=lambda x: (x['confidence'], x['matches']))
        
        return {
            'country': primary_country['country'],
            'iso2': primary_country['iso2'],
            'iso3': primary_country['iso3'],
            'confidence': primary_country['confidence'],
            'extraction_method': 'pattern_matching'
        }
    
    def extract_admin_districts(self, text: str, primary_country: Optional[str] = None) -> List[AdminDistrict]:
        """Extract administrative districts from text"""
        if not text:
            return []
        
        districts = []
        text_lower = text.lower()
        
        # If no primary country provided, try to extract it
        if not primary_country:
            country_info = self.extract_primary_country(text)
            if country_info:
                primary_country = country_info['country']
        
        if not primary_country or primary_country not in self.admin_patterns:
            logger.warning(f"No admin patterns available for country: {primary_country}")
            return districts
        
        country_patterns = self.admin_patterns[primary_country]
        
        # Extract Admin Level 1 (states/provinces)
        for level_name, places in country_patterns.items():
            admin_level = 1 if level_name in ['states', 'provinces', 'regions'] else 2
            
            for place in places:
                pattern = r'\b' + re.escape(place) + r'\b'
                matches = re.findall(pattern, text_lower)
                
                if matches:
                    confidence = min(len(matches) * 0.3 + 0.4, 1.0)
                    
                    districts.append(AdminDistrict(
                        name=place.title(),
                        level=admin_level,
                        parent_code=primary_country,
                        confidence=confidence,
                        extraction_method='pattern_matching'
                    ))
        
        # Remove duplicates and sort by confidence
        unique_districts = {}
        for district in districts:
            key = f"{district.name}_{district.level}"
            if key not in unique_districts or district.confidence > unique_districts[key].confidence:
                unique_districts[key] = district
        
        result = list(unique_districts.values())
        result.sort(key=lambda x: x.confidence, reverse=True)
        
        return result
    
    def extract_geo_context(self, text: str) -> Dict[str, Any]:
        """Extract comprehensive geographic context from text"""
        geo_context = {
            'primary_country': None,
            'admin_districts': [],
            'geographic_features': [],
            'coordinates': [],
            'confidence_score': 0.0
        }
        
        # Extract primary country
        primary_country_info = self.extract_primary_country(text)
        if primary_country_info:
            geo_context['primary_country'] = primary_country_info
            geo_context['confidence_score'] += primary_country_info['confidence'] * 0.4
        
        # Extract admin districts
        primary_country = primary_country_info['country'] if primary_country_info else None
        admin_districts = self.extract_admin_districts(text, primary_country)
        
        if admin_districts:
            geo_context['admin_districts'] = [
                {
                    'name': d.name,
                    'level': d.level,
                    'parent_code': d.parent_code,
                    'confidence': d.confidence,
                    'extraction_method': d.extraction_method
                }
                for d in admin_districts[:10]  # Limit to top 10
            ]
            
            # Add to confidence score
            avg_district_confidence = sum(d.confidence for d in admin_districts[:5]) / min(5, len(admin_districts))
            geo_context['confidence_score'] += avg_district_confidence * 0.3
        
        # Extract coordinates (basic pattern matching)
        coord_patterns = [
            r'(\d{1,2}[.,]\d+)[°]?\s*[NS]\s*[,]?\s*(\d{1,3}[.,]\d+)[°]?\s*[EW]',
            r'(-?\d{1,2}[.,]\d+)\s*[,]\s*(-?\d{1,3}[.,]\d+)',
        ]
        
        coordinates = []
        for pattern in coord_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    lat = float(match[0].replace(',', '.'))
                    lon = float(match[1].replace(',', '.'))
                    
                    # Basic validation for reasonable coordinates
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        coordinates.append({
                            'latitude': lat,
                            'longitude': lon,
                            'extraction_method': 'regex_pattern'
                        })
                except ValueError:
                    continue
        
        geo_context['coordinates'] = coordinates[:5]  # Limit to 5 coordinates
        
        if coordinates:
            geo_context['confidence_score'] += min(len(coordinates) * 0.1, 0.3)
        
        # Normalize confidence score
        geo_context['confidence_score'] = min(geo_context['confidence_score'], 1.0)
        
        return geo_context

def extract_admin_geo_from_content(text: str) -> Dict[str, Any]:
    """Main function to extract administrative geographic information from content"""
    extractor = AdminGeoExtractor()
    return extractor.extract_geo_context(text)

def get_country_admin_hierarchy(country_iso: str) -> Dict[str, Any]:
    """Get administrative hierarchy for a specific country"""
    extractor = AdminGeoExtractor()
    
    # Find country by ISO code
    country_key = None
    for key, data in extractor.country_patterns.items():
        if data['iso2'] == country_iso.upper() or data['iso3'] == country_iso.upper():
            country_key = key
            break
    
    if not country_key:
        return {}
    
    country_data = extractor.country_patterns[country_key]
    admin_data = extractor.admin_patterns.get(country_key, {})
    
    return {
        'country': {
            'key': country_key,
            'names': country_data['names'],
            'iso2': country_data['iso2'],
            'iso3': country_data['iso3']
        },
        'administrative_divisions': admin_data
    }
