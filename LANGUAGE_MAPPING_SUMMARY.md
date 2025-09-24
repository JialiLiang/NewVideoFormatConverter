# Language Code Standardization - ISO 639-1 Implementation

## Overview
Successfully implemented ISO 639-1 language code standardization across Ad Localizer and Name Generator tools.

## Key Changes

### 1. Centralized Configuration
- **New file:** `language_config.py`
- Contains complete mapping between old codes and ISO 639-1 standard
- Provides utilities for validation and conversion
- Maintains backward compatibility

### 2. Updated Language Codes

| Old Code | New ISO 639-1 | Language | Status |
|----------|---------------|----------|---------|
| EN | en | English | ✅ Updated |
| JP | ja | Japanese | ✅ Updated |
| KR | ko | Korean | ✅ Updated |
| BR | pt | Portuguese (Brazilian) | ✅ Updated |
| SA | ar | Arabic | ✅ Updated |
| IN | hi | Hindi | ✅ Updated |
| VN | vi | Vietnamese | ✅ Updated |
| PH | tl | Filipino | ✅ Updated |
| MY | ms | Malay | ✅ Updated |
| CN | zh | Chinese | ✅ Updated |
| DE | de | German | ⚪ No change |
| FR | fr | French | ⚪ No change |
| IT | it | Italian | ⚪ No change |
| ES | es | Spanish | ⚪ No change |
| ID | id | Indonesian | ⚪ No change |
| TR | tr | Turkish | ⚪ No change |
| PL | pl | Polish | ⚪ No change |
| TH | th | Thai | ⚪ No change |
| NL | nl | Dutch | ⚪ No change |

### 3. Files Updated
- `adlocalizer_app.py` - Updated to use centralized language mapping
- `app.py` - Updated to use centralized language mapping  
- `templates/name_generator.html` - Updated all language codes and examples
- `templates/language_mapping.html` - New reference page created

### 4. New Features
- **Reference Page:** `/language-mapping` - View complete mapping table
- **Backward Compatibility:** Both old and new codes work during transition
- **Validation:** Built-in functions to validate language codes
- **Utilities:** Helper functions for code conversion
- **Inline Help:** Quick language code helper in Name Generator with key changes highlighted
- **Documentation:** Enhanced documentation showing old → new code transitions

## Benefits
1. **Industry Standard:** Follows ISO 639-1 international standard
2. **Consistency:** Same codes across all tools
3. **Integration Ready:** Works with external APIs and systems
4. **Future Proof:** Standard format for new features
5. **Reference:** Dedicated page to view all mappings

## Accessing the Reference Page
Visit: `http://localhost:8000/language-mapping` (when app is running)

## Usage Examples

### Name Generator (New Format)
```
internal_RedBottle_-_-_-_-_AIBG_en
freelancer-artlina333_Kitchen_ANIM_fr  
internal_Coffee-2_IGSTORY_ja
```

### Ad Localizer API (New Format)
```json
{
  "languages": ["en", "es", "pt", "fr"],
  "text": "Your video content"
}
```

## Backward Compatibility
- Old codes (EN, JP, KR, etc.) still work during transition
- **Full Migration Complete:** All tools now use ISO 639-1 codes internally
- **External APIs:** Conversion to legacy codes handled automatically when needed (e.g., ElevenLabs)
- No breaking changes for existing workflows

## Recent Updates
- **Complete Migration:** All tools now use ISO 639-1 codes natively (no more legacy codes except for external APIs)
- **Removed HK/Cantonese:** Simplified to use only `zh` for Chinese (including Traditional Chinese)
- **Enhanced Documentation:** Added key changes highlight (JP→ja, KR→ko, etc.)
- **Inline Helper:** Added collapsible language code helper in Name Generator
- **AdLocalizer Updated:** Frontend and backend now use lowercase ISO codes (en, ja, ko, pt, etc.)
- **Full Testing:** All configurations tested and working

## Next Steps
1. ✅ Test both tools with new language codes
2. ✅ Update documentation
3. ✅ Remove HK/Cantonese mapping
4. ✅ Add inline helper in Name Generator
5. ✅ Complete migration to ISO 639-1 codes across all tools
6. 🔄 Consider updating existing saved preferences (future)
7. 🔄 Migrate external integrations to new codes (future)

---
*Implementation completed: September 19, 2025*
