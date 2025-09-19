"""
Language Configuration for Photoroom UA Video Tools
Centralized language code mapping to ISO 639-1 standard

This module provides a standardized mapping between our current language codes 
and ISO 639-1 two-letter codes for consistent use across Ad Localizer and Name Generator.
"""

# ISO 639-1 Language Mapping
# Maps our current codes to standardized ISO 639-1 two-letter codes
LANGUAGE_CODE_MAPPING = {
    # Current Code -> ISO 639-1 Code mapping
    "EN": "en",  # English
    "JP": "ja",  # Japanese (ja is the correct ISO 639-1 code)
    "CN": "zh",  # Chinese Traditional (zh covers Chinese)
    "DE": "de",  # German
    "IN": "hi",  # Hindi (hi is the correct ISO 639-1 code for Hindi)
    "FR": "fr",  # French
    "KR": "ko",  # Korean (ko is the correct ISO 639-1 code)
    "BR": "pt",  # Portuguese (Brazilian) - pt is the ISO code for Portuguese
    "IT": "it",  # Italian
    "ES": "es",  # Spanish
    "ID": "id",  # Indonesian
    "TR": "tr",  # Turkish
    "PH": "tl",  # Filipino (tl is the ISO code for Tagalog/Filipino)
    "PL": "pl",  # Polish
    "SA": "ar",  # Arabic (ar is the correct ISO 639-1 code)
    "MY": "ms",  # Malay (ms is the correct ISO 639-1 code)
    "VN": "vi",  # Vietnamese (vi is the correct ISO 639-1 code)
    "TH": "th",  # Thai
     # Additional codes from Name Generator
     "NL": "nl",  # Dutch
}

# Complete language definitions with both old and new codes
LANGUAGES = {
    "en": {
        "name": "English",
        "old_code": "EN",
        "iso_639_1": "en",
        "region": "Global"
    },
    "ja": {
        "name": "Japanese", 
        "old_code": "JP",
        "iso_639_1": "ja",
        "region": "Japan"
    },
    "zh": {
        "name": "Chinese",
        "old_code": "CN",
        "iso_639_1": "zh",
        "region": "China/Taiwan"
    },
    "de": {
        "name": "German",
        "old_code": "DE", 
        "iso_639_1": "de",
        "region": "Germany"
    },
    "hi": {
        "name": "Hindi",
        "old_code": "IN",
        "iso_639_1": "hi", 
        "region": "India"
    },
    "fr": {
        "name": "French",
        "old_code": "FR",
        "iso_639_1": "fr",
        "region": "France"
    },
    "ko": {
        "name": "Korean",
        "old_code": "KR",
        "iso_639_1": "ko",
        "region": "Korea"
    },
    "pt": {
        "name": "Portuguese (Brazilian)",
        "old_code": "BR",
        "iso_639_1": "pt",
        "region": "Brazil"
    },
    "it": {
        "name": "Italian",
        "old_code": "IT",
        "iso_639_1": "it",
        "region": "Italy"
    },
    "es": {
        "name": "Spanish", 
        "old_code": "ES",
        "iso_639_1": "es",
        "region": "Spain"
    },
    "id": {
        "name": "Indonesian",
        "old_code": "ID",
        "iso_639_1": "id",
        "region": "Indonesia"
    },
    "tr": {
        "name": "Turkish",
        "old_code": "TR",
        "iso_639_1": "tr", 
        "region": "Turkey"
    },
    "tl": {
        "name": "Filipino",
        "old_code": "PH",
        "iso_639_1": "tl",
        "region": "Philippines"
    },
    "pl": {
        "name": "Polish",
        "old_code": "PL",
        "iso_639_1": "pl",
        "region": "Poland"
    },
    "ar": {
        "name": "Arabic",
        "old_code": "SA",
        "iso_639_1": "ar",
        "region": "Saudi Arabia/Middle East"
    },
    "ms": {
        "name": "Malay",
        "old_code": "MY",
        "iso_639_1": "ms",
        "region": "Malaysia"
    },
    "vi": {
        "name": "Vietnamese", 
        "old_code": "VN",
        "iso_639_1": "vi",
        "region": "Vietnam"
    },
    "th": {
        "name": "Thai",
        "old_code": "TH",
        "iso_639_1": "th",
        "region": "Thailand"
    },
    "nl": {
        "name": "Dutch",
        "old_code": "NL", 
        "iso_639_1": "nl",
        "region": "Netherlands"
    }
}

def get_iso_code_from_old(old_code):
    """Convert old language code to ISO 639-1 code"""
    return LANGUAGE_CODE_MAPPING.get(old_code.upper(), old_code.lower())

def get_old_code_from_iso(iso_code):
    """Convert ISO 639-1 code to old language code"""
    for old_code, mapped_iso in LANGUAGE_CODE_MAPPING.items():
        if mapped_iso == iso_code.lower():
            return old_code
    return iso_code.upper()

def get_language_name(code):
    """Get language name from either old or ISO code"""
    # First try as ISO code
    if code.lower() in LANGUAGES:
        return LANGUAGES[code.lower()]["name"]
    
    # Then try to convert from old code
    iso_code = get_iso_code_from_old(code)
    if iso_code in LANGUAGES:
        return LANGUAGES[iso_code]["name"]
    
    return code

def get_all_languages_for_display():
    """Get all languages formatted for dropdown display"""
    return {
        iso_code: f"{info['iso_639_1'].upper()} - {info['name']}"
        for iso_code, info in LANGUAGES.items()
    }

def get_legacy_language_dict():
    """Get languages in the old format for backward compatibility"""
    legacy_dict = {}
    for iso_code, info in LANGUAGES.items():
        old_code = info["old_code"]
        legacy_dict[old_code] = info["name"]
    return legacy_dict

def validate_language_code(code):
    """Validate if a language code exists (either old or new format)"""
    # Check if it's a valid ISO code
    if code.lower() in LANGUAGES:
        return True
    
    # Check if it's a valid old code
    if code.upper() in LANGUAGE_CODE_MAPPING:
        return True
    
    return False

# Priority languages for the name generator (most commonly used)
PRIORITY_LANGUAGES = ["en", "fr", "pt", "es", "ja", "ko"]

def get_priority_languages():
    """Get priority languages for UI display"""
    return {
        iso_code: LANGUAGES[iso_code]
        for iso_code in PRIORITY_LANGUAGES
        if iso_code in LANGUAGES
    }

def get_other_languages():
    """Get non-priority languages for UI display"""
    return {
        iso_code: info
        for iso_code, info in LANGUAGES.items() 
        if iso_code not in PRIORITY_LANGUAGES
    }
