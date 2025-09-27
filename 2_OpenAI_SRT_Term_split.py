import os
import json
from pathlib import Path
from openai import OpenAI
import shutil
import re
import importlib.util
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check if language processing libraries are installed
has_fugashi = importlib.util.find_spec("fugashi") is not None
has_opencc = importlib.util.find_spec("opencc") is not None

# Check for Java runtime (needed for Korean text processing)
has_java = False
try:
    import subprocess
    result = subprocess.run(['java', '-version'], capture_output=True, text=True)
    has_java = result.returncode == 0
except:
    has_java = False

# Language code mapping
LANGUAGE_CODES = {
    'EN': 'en',
    'FR': 'fr',
    'ES': 'es',
    'DE': 'de',
    'IT': 'it',
    'JP': 'ja',
    'CN': 'zh',
    'KR': 'ko',
    'HK': 'zh',  # Cantonese uses same code as Chinese
    'BR': 'pt',
    'ID': 'id',
    'MY': 'ms',
    'PH': 'tl',
    'IN': 'hi',
    'TR': 'tr',
    'PL': 'pl',
    'SA': 'ar',
    'VN': 'vi',
    'TH': 'th',
    'th-TH': 'th',  # Add locale format for Thai
    'es-ES': 'es',  # Add locale format for Spanish
    'it-IT': 'it',  # Add locale format for Italian
    'de-DE': 'de',  # Add locale format for German
    'fr-FR': 'fr',  # Add locale format for French
    'en-US': 'en',  # Add locale format for English
    'ja-JP': 'ja',  # Add locale format for Japanese
    'ko-KR': 'ko',  # Add locale format for Korean
    'zh-CN': 'zh',  # Add locale format for Simplified Chinese
    'zh-TW': 'zh',  # Add locale format for Traditional Chinese
    'pt-BR': 'pt',  # Add locale format for Brazilian Portuguese
    'ar-SA': 'ar',  # Add locale format for Arabic
    'hi-IN': 'hi',  # Add locale format for Hindi
    'tr-TR': 'tr',  # Add locale format for Turkish
    'pl-PL': 'pl',  # Add locale format for Polish
    'vi-VN': 'vi',  # Add locale format for Vietnamese
    'ms-MY': 'ms',  # Add locale format for Malay
    'tl-PH': 'tl'   # Add locale format for Tagalog
}

# RTL languages
RTL_LANGUAGES = {'SA'}  # Add more RTL languages as needed

# Maximum lengths dictionary for CJK languages - Move this to the top
max_lengths = {'CN': 16, 'JP': 16, 'KR': 16, 'HK': 16}

# Chinese punctuation that should not be at the start of a line
CHINESE_PUNCTUATION = "，。！？、；：""''「」【】《》（）…~～"
ALL_PUNCTUATION = CHINESE_PUNCTUATION + ",.!?;:\"'()[]{}<>…-"

# Words that should never be split
PRESERVED_TERMS = ["Photoroom", "AI", "App"]

def parse_timecode(timecode):
    """Convert timecode string to milliseconds."""
    try:
        # Handle different timecode formats
        if ' --> ' in timecode:
            timecode = timecode.split(' --> ')[0]  # Take only the start time
        
        # Try different separators
        if ':' in timecode and ',' in timecode:
            hours, minutes, seconds_ms = timecode.split(':')
            seconds, milliseconds = seconds_ms.split(',')
        elif ':' in timecode and '.' in timecode:
            hours, minutes, seconds_ms = timecode.split(':')
            seconds, milliseconds = seconds_ms.split('.')
        else:
            raise ValueError(f"Invalid timecode format: {timecode}")
            
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        milliseconds = int(milliseconds)
        
        return (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
    except Exception as e:
        print(f"Error parsing timecode '{timecode}': {e}")
        return 0  # Return 0 as fallback

def format_timecode(milliseconds):
    """Convert milliseconds to a timecode string."""
    total_seconds = milliseconds / 1000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    millisec = int(milliseconds % 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millisec:03}"

def convert_to_traditional_chinese(text):
    """Convert simplified Chinese to traditional Chinese if opencc is available."""
    if has_opencc:
        try:
            import opencc
            converter = opencc.OpenCC('s2t')  # Simplified to Traditional
            return converter.convert(text)
        except Exception as e:
            print(f"Error converting to traditional Chinese: {e}")
            return text
    return text

def is_punctuation(char):
    """Check if a character is punctuation."""
    return char in ALL_PUNCTUATION

def clean_text(text):
    """Clean text by removing extra spaces and normalizing punctuation."""
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Ensure space after western punctuation if followed by non-punctuation
    text = re.sub(r'([,.!?;:])([\w])', r'\1 \2', text)
    
    return text

def split_chinese_text(text, max_length, is_traditional=False):
    """Split Chinese text using character-based approach."""
    # Convert to traditional Chinese if needed and opencc is available
    original_text = text
    if is_traditional and has_opencc:
        try:
            import opencc
            converter = opencc.OpenCC('s2t')  # Simplified to Traditional
            text = converter.convert(text)
            print(f"Converted to traditional Chinese: {text}")
        except Exception as e:
            print(f"Error converting to traditional Chinese: {e}")
    
    # Clean and prepare text
    text = clean_text(text)
    
    # Manual character-based splitting for Chinese with attention to punctuation
    lines = []
    current_line = ""
    i = 0
    
    while i < len(text):
        # Skip adding punctuation at the beginning of a new line
        if current_line == "" and i < len(text) and is_punctuation(text[i]):
            if lines and len(lines[-1]) + 1 <= max_length:
                lines[-1] += text[i]
            else:
                # Skip this punctuation
                pass
            i += 1
            continue
        
        # Check for preserved terms
        preserved_term_found = False
        for term in PRESERVED_TERMS:
            if text[i:].startswith(term):
                preserved_term_found = True
                if len(current_line) + len(term) <= max_length:
                    current_line += term
                    i += len(term)
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = term
                    i += len(term)
                break
        
        if preserved_term_found:
            continue
        
        # Regular character
        if len(current_line) + 1 <= max_length:
            # Look ahead for punctuation to keep together with the current character
            if i+1 < len(text) and is_punctuation(text[i+1]):
                if len(current_line) + 2 <= max_length:
                    current_line += text[i] + text[i+1]
                    i += 2
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = text[i] + text[i+1]
                    i += 2
            else:
                current_line += text[i]
                i += 1
        else:
            if current_line:
                lines.append(current_line)
            current_line = text[i]
            i += 1
        
        # Check if we're at a sentence end to break naturally
        if current_line and any(current_line.endswith(end) for end in "。！？!?"):
            lines.append(current_line)
            current_line = ""
    
    if current_line:
        lines.append(current_line)
    
    # Post-process lines to ensure no line starts with punctuation
    processed_lines = []
    for i, line in enumerate(lines):
        if i > 0 and line and is_punctuation(line[0]):
            # If previous line exists and has room, add the punctuation there
            if processed_lines and len(processed_lines[-1]) + 1 <= max_length:
                processed_lines[-1] += line[0]
                if len(line) > 1:
                    processed_lines.append(line[1:])
            else:
                # Otherwise just keep it with this line
                processed_lines.append(line)
        else:
            processed_lines.append(line)
    
    # Filter out empty lines
    result = [line for line in processed_lines if line.strip()]
    print(f"Split result: {result}")
    return result

def split_japanese_text(text, max_length):
    """Split Japanese text respecting word boundaries using fugashi if available."""
    if has_fugashi:
        try:
            import fugashi
            tagger = fugashi.Tagger()
            words = [word.surface for word in tagger(text)]
            
            lines = []
            current_line = ""
            
            for word in words:
                # Check if preserved term
                is_preserved = False
                for term in PRESERVED_TERMS:
                    if term in word and not word.isspace():
                        is_preserved = True
                        break
                
                if is_preserved or len(current_line) + len(word) <= max_length:
                    current_line += word
                else:
                    if current_line:  # Only append if not empty
                        lines.append(current_line)
                    current_line = word
            
            if current_line:  # Add the last line
                lines.append(current_line)
                
            return lines
        except Exception as e:
            print(f"Error using fugashi for Japanese segmentation: {e}")
            # Fall back to character-based splitting
            return split_cjk_text_improved(text, max_length)
    else:
        # Fall back to character-based splitting
        print("Fugashi not found, falling back to character-based splitting for Japanese")
        return split_cjk_text_improved(text, max_length)

def split_korean_text(text, max_length):
    """Split Korean text using character-based approach."""
    return split_cjk_text_improved(text, max_length)

def split_cjk_text_improved(text, max_length, is_traditional=False):
    """Improved split CJK text by character, handling punctuation better."""
    # Convert to traditional Chinese if needed
    if is_traditional and has_opencc:
        text = convert_to_traditional_chinese(text)
    
    lines = []
    current_line = ""
    
    i = 0
    while i < len(text):
        # Skip adding punctuation at the beginning of a new line
        if current_line == "" and i < len(text) and is_punctuation(text[i]):
            if lines and len(lines[-1]) + 1 <= max_length:
                lines[-1] += text[i]
            else:
                # Skip this punctuation or wait for next character
                pass
            i += 1
            continue
        
        # Check for preserved terms
        preserved_term_found = False
        for term in PRESERVED_TERMS:
            if text[i:].startswith(term):
                preserved_term_found = True
                if len(current_line) + len(term) <= max_length:
                    current_line += term
                    i += len(term)
                else:
                    lines.append(current_line)
                    current_line = term
                    i += len(term)
                break
        
        if preserved_term_found:
            continue
        
        # Check for English words (assuming they're space-separated)
        if i < len(text) and text[i].isascii() and text[i].isalnum():
            word_end = text.find(' ', i)
            if word_end == -1:
                word_end = len(text)
            word = text[i:word_end]
            if len(current_line) + len(word) <= max_length:
                current_line += word
                i = word_end
            else:
                lines.append(current_line)
                current_line = word
                i = word_end
        else:
            # Look ahead for punctuation - keep it with the character before it
            if i+1 < len(text) and is_punctuation(text[i+1]):
                if len(current_line) + 2 <= max_length:  # Current char + punctuation
                    current_line += text[i] + text[i+1]
                    i += 2
                else:
                    lines.append(current_line)
                    current_line = text[i] + text[i+1]
                    i += 2
            else:
                # Regular CJK character
                if len(current_line) + 1 <= max_length:
                    current_line += text[i]
                else:
                    lines.append(current_line)
                    current_line = text[i]
                i += 1
        
        # Move to next character if it's a space
        if i < len(text) and text[i] == ' ':
            i += 1
        
        # Check if we're at a sentence end
        if current_line and any(current_line.endswith(end) for end in "。！？!?"):
            lines.append(current_line)
            current_line = ""

    if current_line:
        lines.append(current_line)
    
    # Filter out empty lines
    return [line for line in lines if line.strip()]

# Update the original split_cjk_text to call the improved version
def split_cjk_text(text, max_length, is_traditional=False):
    """Split CJK text by character, preserving specific terms and English words."""
    return split_cjk_text_improved(text, max_length, is_traditional)

def split_lines(text, max_length, is_cjk, language=None):
    """Split text into lines respecting word boundaries and preserving specific terms and English words."""
    lines = []
    
    # Use language-specific tokenizers
    if language == 'JP':
        return split_japanese_text(text, max_length)
    elif language == 'CN':
        return split_chinese_text(text, max_length, is_traditional=False)
    elif language == 'HK':
        return split_chinese_text(text, max_length, is_traditional=True)
    elif language == 'KR':
        return split_korean_text(text, max_length)
    elif language in RTL_LANGUAGES:
        # Handle RTL languages (like Arabic)
        words = text.split()
        current_line = ""
        for word in words:
            if len(current_line) + (len(word) + 1) <= max_length:  # +1 for space
                current_line = word + (' ' + current_line if current_line else '')
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
    elif is_cjk:  # Fallback for other CJK languages
        return split_cjk_text(text, max_length)
    else:  # For non-CJK languages, respect word boundaries
        words = text.split()
        current_line = ""
        for word in words:
            if len(current_line) + (len(word) + 1) <= max_length:  # +1 for space
                current_line += (' ' + word if current_line else word)
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

    return lines

def process_srt(file_path, max_lengths, backup_original=True):
    language = 'EN'  # Default to English
    is_cjk = False
    is_traditional = False
    
    filename = Path(file_path).name
    for lang_code in LANGUAGE_CODES.keys():
        if f'_{lang_code}_' in filename:
            language = lang_code
            break
    
    if language in ['JP', 'CN', 'KR', 'HK']:
        is_cjk = True
        if language == 'HK':
            is_traditional = True
        elif language == 'CN' and has_opencc:
            is_traditional = True

    max_length = max_lengths.get(language, 24)
    
    print(f"Processing subtitles for {language}...")

    try:
        if backup_original:
            backup_path = file_path + '.original'
            shutil.copy2(file_path, backup_path)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        content = content.replace('\r\n', '\n')
        entries = []
        current_entry = []
        
        for line in content.split('\n'):
            if line.strip() == '' and current_entry:
                entries.append('\n'.join(current_entry))
                current_entry = []
            elif line.strip() != '' or current_entry:
                current_entry.append(line)
        
        if current_entry:
            entries.append('\n'.join(current_entry))
        
        if language == 'CN' and has_opencc:
            process_entries(entries, file_path, max_length, is_cjk, language, False)
            process_entries(entries, file_path, max_length, is_cjk, language, True)
        else:
            process_entries(entries, file_path, max_length, is_cjk, language, is_traditional)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        print(f"✗ Error processing file: {str(e)}")
        if backup_original and os.path.exists(backup_path):
            shutil.copy2(backup_path, file_path)
        raise

def process_entries(entries, file_path, max_length, is_cjk, language, is_traditional):
    new_entries = []
    
    suffix = "_traditional" if is_traditional and language == 'CN' else ""
    new_file_path = file_path.replace('.srt', f'{suffix}_split.srt')
    
    subtitle_index = 1
    
    earliest_start = float('inf')
    for entry in entries:
        if entry.strip() == '':
            continue
            
        parts = entry.split('\n')
        if len(parts) < 2:
            continue
            
        timecode_line = -1
        for i, part in enumerate(parts):
            if ' --> ' in part:
                timecode_line = i
                break
                
        if timecode_line == -1:
            continue
            
        times = parts[timecode_line]
        if ' --> ' not in times:
            continue
            
        start_time, _ = times.split(' --> ')
        try:
            start_ms = parse_timecode(start_time)
            earliest_start = min(earliest_start, start_ms)
        except:
            continue
    
    if earliest_start == float('inf'):
        earliest_start = 0
    
    for entry_index, entry in enumerate(entries):
        if entry.strip() == '':
            continue
        
        parts = entry.split('\n')
        if len(parts) < 2:
            continue
        
        index_line = -1
        timecode_line = -1
        
        for i, part in enumerate(parts):
            if part.strip().isdigit():
                index_line = i
            elif ' --> ' in part:
                timecode_line = i
                break
        
        if timecode_line == -1:
            continue
            
        if index_line == -1 or index_line == timecode_line:
            index = subtitle_index
            times = parts[timecode_line]
            text_parts = parts[timecode_line+1:]
        else:
            index = parts[index_line]
            times = parts[timecode_line]
            text_parts = parts[timecode_line+1:]
        
        try:
            if ' --> ' not in times:
                continue
                
            start_time, end_time = times.split(' --> ')
            start_ms = parse_timecode(start_time)
            end_ms = parse_timecode(end_time)
            
            start_ms = max(0, start_ms - earliest_start)
            end_ms = max(0, end_ms - earliest_start)
            
            if start_ms == 0 and end_ms == 0:
                continue
                
        except ValueError:
            continue
            
        text = ' '.join(text_parts)
        
        if not text.strip():
            continue
        
        text = re.sub(r'[.,。!?！？]$', '', text.strip())
        
        if language in ['CN', 'HK']:
            lines = split_chinese_text(text, max_length, is_traditional)
        else:
            lines = split_lines(text, max_length, is_cjk, language)
            
        num_lines = len(lines)
        
        if num_lines == 0:
            continue
            
        increment = (end_ms - start_ms) // max(1, num_lines)

        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            new_start_time = format_timecode(start_ms + i * increment)
            new_end_time = format_timecode(start_ms + (i + 1) * increment)
            new_entries.append(f"{subtitle_index}\n{new_start_time} --> {new_end_time}\n{line}")
            subtitle_index += 1

    with open(new_file_path, 'w', encoding='utf-8') as new_file:
        new_file.write('\n\n'.join(new_entries))
    print(f"✓ Processed {len(new_entries)} subtitles")

def fix_malformed_srt(file_path):
    """Attempt to fix a malformed SRT file by rebuilding it properly."""
    print(f"Attempting to fix malformed SRT file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with a different encoding if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Normalize line endings
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Try to extract all subtitles using regex
    subtitle_pattern = r'(\d+)[\s\n]+(\d{2}:\d{2}:\d{2}[,\.]\d{3})[\s\n]*-->[\s\n]*(\d{2}:\d{2}:\d{2}[,\.]\d{3})[\s\n]+(.*?)(?=[\n\s]*\d+[\s\n]+\d{2}:\d{2}:\d{2}[,\.]\d{3}[\s\n]*-->|\Z)'
    subtitles = re.findall(subtitle_pattern, content, re.DOTALL)
    
    if not subtitles:
        print(f"No subtitles could be extracted from {file_path}")
        return False
    
    print(f"Extracted {len(subtitles)} subtitles from {file_path}")
    
    # Rebuild the SRT file
    rebuilt_content = ""
    index = 1  # Start with index 1
    
    for _, start_time, end_time, text in subtitles:
        # Normalize the time format (replace . with , for milliseconds)
        start_time = start_time.replace('.', ',')
        end_time = end_time.replace('.', ',')
        
        # Clean up text (remove extra newlines, spaces)
        text = re.sub(r'\n+', '\n', text.strip())
        
        # Add to the rebuilt content
        rebuilt_content += f"{index}\n{start_time} --> {end_time}\n{text}\n\n"
        index += 1
    
    # Save the fixed file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(rebuilt_content)
    
    print(f"Fixed SRT file saved with {index-1} entries")
    return True

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Function to format time for SRT files
def format_time(seconds):
    """Convert seconds to a timecode string."""
    milliseconds = int((seconds - int(seconds)) * 1000)
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

# Custom JSON encoder subclass to handle non-serializable objects
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)  # Last resort

# Function to extract language code from filename
def extract_language_code(file_path):
    """Extract language code from filename, handling both simple codes and locale formats."""
    filename = Path(file_path).name
    
    # First try matching pattern like _xx-XX_ (locale format)
    match = re.search(r'_([a-z]{2}-[A-Z]{2})_', filename)
    if match:
        locale_code = match.group(1)
        # Check if we have a direct mapping for the locale
        if locale_code in LANGUAGE_CODES:
            return locale_code
        # Otherwise return just the language part
        return locale_code.split('-')[0].upper()
    
    # Then try matching pattern like _XX_ (two-letter code)
    match = re.search(r'_([A-Z]{2})_', filename)
    if match:
        code = match.group(1)
        # Skip if the code is 'AI' as it's likely part of the filename, not a language code
        if code != 'AI':
            return code
    
    # Check for GoogleTTS pattern
    match = re.search(r'GoogleTTS_([a-z]{2}-[A-Z]{2})_', filename)
    if match:
        locale_code = match.group(1)
        # Check if we have a direct mapping for the locale
        if locale_code in LANGUAGE_CODES:
            return locale_code
        # Otherwise return just the language part
        return locale_code.split('-')[0].upper()
    
    # Default to English if no match found
    return 'EN'

def transcribe_with_prompt(audio_file_path):
    specific_terms = f"{background_terms}"  # Merge with previously defined AI Backgrounds terms
    
    # Extract language code from filename
    lang_code = extract_language_code(audio_file_path)
    language = LANGUAGE_CODES.get(lang_code, 'english')  # Default to English if not found
    
    print(f"\nProcessing {Path(audio_file_path).name} ({language})...")
    
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                prompt=specific_terms,
                language=language
            )
        
        # Ensure the transcription object is in a serializable format
        if hasattr(transcription, 'model_dump'):
            result = transcription.model_dump()
        else:
            result = dict(transcription)
            
        if 'text' in result:
            print(f"✓ Transcription completed")
        else:
            print("✗ Transcription failed - no text generated")
            
        return result
        
    except Exception as e:
        print(f"✗ Transcription failed: {str(e)}")
        return {
            "text": f"Error transcribing file: {str(e)}",
            "segments": []
        }

def save_transcript_and_create_srt(transcript, base_path):
    text_file_path = base_path.with_suffix('.txt')
    srt_folder = Path("/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/SRT")
    srt_file_path = srt_folder / base_path.with_suffix('.srt').name

    # Save the transcript as JSON using the custom encoder
    with open(text_file_path, 'w') as text_file:
        json.dump(transcript, text_file, cls=JSONEncoder)

    # Extract the language code from the filename for the SRT
    lang_code = extract_language_code(str(base_path))
    
    # Generate and save the SRT file
    srt_content = ""
    subtitle_index = 1
    
    segments = transcript.get('segments', [])
    if not segments and transcript.get('text', ''):
        segments = [{
            'start': 0.0,
            'end': 10.0,
            'text': transcript.get('text', '')
        }]
    
    earliest_start = min((segment['start'] for segment in segments), default=0.0)
    
    for i, segment in enumerate(segments):
        start_time = format_time(max(0.0, segment['start'] - earliest_start))
        end_time = format_time(max(0.0, segment['end'] - earliest_start))
        text = segment['text'].strip()
        
        if not text:
            continue
            
        sentences = re.split(r'([.!?。！？])', text)
        sentence_pairs = []
        for j in range(0, len(sentences) - 1, 2):
            if j + 1 < len(sentences):
                combined = sentences[j] + sentences[j+1]
                if combined.strip():
                    sentence_pairs.append(combined.strip())
            elif sentences[j].strip():
                sentence_pairs.append(sentences[j].strip())
        
        if not sentence_pairs and text.strip():
            sentence_pairs = [text.strip()]
        
        if len(sentence_pairs) > 1:
            duration = segment['end'] - segment['start']
            time_per_sentence = duration / len(sentence_pairs)
            
            for j, sentence in enumerate(sentence_pairs):
                sent_start = segment['start'] - earliest_start + (j * time_per_sentence)
                sent_end = sent_start + time_per_sentence
                srt_content += f"{subtitle_index}\n{format_time(sent_start)} --> {format_time(sent_end)}\n{sentence}\n\n"
                subtitle_index += 1
        else:
            srt_content += f"{subtitle_index}\n{start_time} --> {end_time}\n{text}\n\n"
            subtitle_index += 1
    
    srt_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(srt_file_path, 'w', encoding='utf-8') as srt_file:
        srt_file.write(srt_content)
    
    print(f"✓ SRT file created with {subtitle_index-1} subtitles")
    return srt_file_path

background_terms = (
    "AI Backgrounds, "
    "Photoroom, "             # Added a space after Photoroom
    "خلفيات الذكاء الاصطناعي, "  # Arabic
    "AI 背景, "               # Chinese Simplified
    "AI 背景, "               # Chinese Traditional (unchanged)
    "AI-baggrunde, "          # Danish
    "AI-Achtergronden, "      # Dutch
    "AI-taustat, "            # Finnish
    "Fonds IA, "              # French
    "AI Backgrounds, "        # German
    "Φόντα ΤΝ, "              # Greek
    "רקעים ב-AI, "            # Hebrew
    "AI hátterek, "           # Hungarian
    "Latar Belakang AI, "     # Indonesian
    "Sfondi IA, "             # Italian
    "AI 背景生成, "            # Japanese
    "AI 배경, "               # Korean
    "Latar Belakang AI, "     # Malay
    "KI-bakgrunner, "         # Norwegian
    "AI Backgrounds, "        # Persian
    "AI Backgrounds, "        # Polish
    "Fundos IA, "             # Portuguese (Brazil)
    "Fundos IA, "             # Portuguese (Portugal)
    "Fundaluri IA, "          # Romanian
    "ИИ-фоны, "               # Russian
    "Fondos IA, "             # Spanish
    "AI-bakgrunder, "         # Swedish
    "พื้นหลัง AI, "            # Thai
    "YZ Arka Planlar, "       # Turkish
    "ШІ-фони, "               # Ukrainian
    "Hình nền AI, "           # Vietnamese
    "AI 背景 (繁體中文)"        # Explicitly mentioning Traditional Chinese
)

# Directory containing your audio files
audio_files_directory = "/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/audio"

# Main processing loop
print("\nStarting subtitle processing...")
for audio_file_path in Path(audio_files_directory).glob('*.mp3'):
    transcript = transcribe_with_prompt(audio_file_path)
    srt_file_path = save_transcript_and_create_srt(transcript, audio_file_path)
    text_file_path = audio_file_path.with_suffix('.txt')
    text_file_path.unlink(missing_ok=True)
    fix_malformed_srt(str(srt_file_path))
    process_srt(str(srt_file_path), max_lengths, backup_original=False)

# Call the processing function on the SRT files generated by the first script
srt_files_directory = "/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/SRT"

# Process all SRT files in the directory
for filename in os.listdir(srt_files_directory):
    # Only process original SRT files (not ones that already end with _split.srt)
    if filename.endswith(".srt") and not filename.endswith("_split.srt"):
        file_path = os.path.join(srt_files_directory, filename)
        
        # First try to fix the file if it's malformed
        fix_malformed_srt(file_path)
        
        # Then process it
        process_srt(file_path, max_lengths)

# Print instructions for installing missing packages if not available
missing_packages = []
if not has_fugashi:
    missing_packages.append("fugashi unidic-lite")
if not has_opencc:
    missing_packages.append("opencc")

if missing_packages:
    print("\nRecommended packages for better CJK support:")
    for package in missing_packages:
        print(f"pip install {package}")