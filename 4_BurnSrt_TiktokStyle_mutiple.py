import logging
import re
from moviepy.editor import VideoFileClip, CompositeVideoClip, TextClip, ImageClip
from moviepy.video.tools.subtitles import SubtitlesClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import glob
from pathlib import Path

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ISO-639-1 language code mapping
LANGUAGE_CODE_MAPPING = {
    "EN": "en", "JP": "ja", "CN": "zh", "DE": "de", "IN": "hi", "FR": "fr",
    "KR": "ko", "BR": "pt", "IT": "it", "ES": "es", "ID": "id", "TR": "tr",
    "PH": "tl", "PL": "pl", "SA": "ar", "MY": "ms", "VN": "vi", "TH": "th", "NL": "nl",
    "HK": "zh"  # Hong Kong also uses Chinese
}

# Reverse mapping from ISO codes back to original codes (for SRT file matching)
# Handle cases where multiple original codes map to the same ISO code
ISO_TO_ORIGINAL_MAPPING = {
    "en": "EN", "ja": "JP", "zh": "CN", "de": "DE", "hi": "IN", "fr": "FR",
    "ko": "KR", "pt": "BR", "it": "IT", "es": "ES", "id": "ID", "tr": "TR",
    "tl": "PH", "pl": "PL", "ar": "SA", "ms": "MY", "vi": "VN", "th": "TH", "nl": "NL"
}

export_dir = Path('/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/export')
srt_dir = Path('/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/SRT')
exported_video_files = glob.glob(str(export_dir / '*.mp4'))
srt_files = glob.glob(str(srt_dir / '*_split.srt'))

# Define your font paths here
font_paths = {
    'CN': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/chinese.msyh.ttf',
    'HK': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/chinese.msyh.ttf',
    'KR': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Maplestory OTF Bold.otf',
    'JP': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Gen Jyuu Gothic Monospace Bold.ttf',
    'SA': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Noto Naskh Arabic-Bold.ttf',
    'TH': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Aksaramatee Bold.ttf',
    'IN': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/Mangal Regular.ttf',
    'default': '/Users/jiali/Documents/AdLocaliserV1/New clean ones 2025/font/ProximaNovaSemibold.ttf'  # Default font
}

def select_font(language_code):
    return font_paths.get(language_code, font_paths['default'])

def extract_language_code_for_srt_matching(video_filename):
    """Extract language code from video filename for SRT file matching"""
    # First, try to extract from bracketed format like [zh], [pt], etc.
    bracket_match = re.search(r'\[([a-z]{2})\](?:\.mp4)?$', video_filename)
    if bracket_match:
        iso_code = bracket_match.group(1)
        # Convert ISO code back to original code for SRT file matching
        original_code = ISO_TO_ORIGINAL_MAPPING.get(iso_code, iso_code.upper())
        return original_code
    
    # Fallback to old format: extract from underscore-separated parts
    parts = video_filename.split('_')
    if len(parts) > 1:
        last_part = parts[-1].split('.')[0]
        # If it's a 2-letter code, return it
        if len(last_part) == 2 and last_part.isalpha():
            return last_part.upper()
    
    return None

def apply_iso_lang_suffix(basename: str, language_code: str) -> str:
    """Apply ISO-639-1 language code mapping to replace [en] or other bracketed codes in filename"""
    # First, try to find and replace any existing bracketed language code
    # Look for patterns like [en], [EN], [XX] at the end or before file extension
    pattern = r"(.*)\[([^\]]+)\](\.\w+)?$"
    match = re.search(pattern, basename)
    
    if match:
        prefix = match.group(1)
        existing_code = match.group(2)
        extension = match.group(3) or ""
        
        # Map the language code to ISO format
        mapped_code = LANGUAGE_CODE_MAPPING.get(language_code.upper(), language_code.lower())
        
        new_filename = f"{prefix}[{mapped_code}]{extension}"
        
        logging.info(f"Filename transformation: {basename} → language: {language_code} → mapped: {mapped_code} → {new_filename}")
        
        return new_filename
    else:
        # No bracketed code found, add the language code at the end before extension
        if '.' in basename:
            name_part, ext_part = basename.rsplit('.', 1)
            mapped_code = LANGUAGE_CODE_MAPPING.get(language_code.upper(), language_code.lower())
            new_filename = f"{name_part}[{mapped_code}].{ext_part}"
        else:
            mapped_code = LANGUAGE_CODE_MAPPING.get(language_code.upper(), language_code.lower())
            new_filename = f"{basename}[{mapped_code}]"
        
        logging.info(f"Filename transformation: {basename} → language: {language_code} → mapped: {mapped_code} → {new_filename}")
        
        return new_filename

# Update languages_to_skip to only exclude 'IN' (Hindi)
languages_to_skip = ['IN']

def create_rounded_rectangle(size, radius, color):
    """Creates an image with a rounded rectangle."""
    mask = Image.new('L', size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), size], radius, fill=255)
    rounded_rect = Image.new('RGB', size, color)
    rounded_rect.putalpha(mask)
    return np.array(rounded_rect)

def create_text_clip_with_background(txt, fontsize, font_name, text_color):
    """Creates a text clip with a white rounded background."""
    # Special handling only for Arabic text
    if any('\u0600' <= char <= '\u06FF' for char in txt):
        fontsize = int(fontsize * 1.2)
        # Create PIL Image for Arabic text
        font = ImageFont.truetype(font_name, fontsize)
        temp_img = Image.new('RGBA', (1000, 200), (255, 255, 255, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), txt, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        h_padding = 70
        v_padding = 30
        img_width = text_width + h_padding
        img_height = text_height + v_padding
        
        # Create background with rounded corners
        bg = Image.new('RGBA', (img_width, img_height), (255, 255, 255, 0))
        bg_draw = ImageDraw.Draw(bg)
        bg_draw.rounded_rectangle([(0, 0), (img_width, img_height)], 15, fill=(255, 255, 255, 255))
        
        # Draw Arabic text from right to left
        bg_draw.text((img_width - text_width - h_padding//2, v_padding//2), 
                     txt, 
                     font=font, 
                     fill='black',
                     direction='rtl')
        
        return ImageClip(np.array(bg)).set_duration(1)
        
    else:
        # Original code for all other languages
        if any('\u0E00' <= char <= '\u0E7F' for char in txt):  # Thai
            fontsize = int(fontsize * 1.3)
        
        fontsize = max(40, min(fontsize, 80))
        
        text_clip = TextClip(
            txt, 
            fontsize=fontsize, 
            font=font_name, 
            color=text_color,
            kerning=-1,
            method='label'
        )
        
        text_width, text_height = text_clip.size
        
        # Use original padding logic
        if any('\u0E00' <= char <= '\u0E7F' for char in txt):  # Thai
            h_padding = 60
        else:
            h_padding = 50
            
        size = (text_width + h_padding, text_height + 30)
        bg_array = create_rounded_rectangle(size, radius=15, color=(255, 255, 255))
        bg_clip = ImageClip(bg_array)
        composite_clip = CompositeVideoClip([
            bg_clip.set_position(('center', 'center')), 
            text_clip.set_position(('center', 'center'))
        ], size=size)
        
        return composite_clip.set_duration(text_clip.duration)

def process_video(exported_video_file):
    video_clip = None
    try:
        video_file_name = Path(exported_video_file).name
        language_code = extract_language_code_for_srt_matching(video_file_name)
        if not language_code:
            logging.warning(f"Could not extract language code from {video_file_name}, skipping.")
            return
        if language_code in languages_to_skip:
            logging.info(f"Skipping language {language_code} as per configuration.")
            return

        matching_srt_file = next((srt for srt in srt_files if language_code in srt), None)
        if not matching_srt_file:
            logging.warning(f"No SRT file found for {language_code}, skipping video.")
            return
        
        # Check if SRT file is empty
        if Path(matching_srt_file).stat().st_size == 0:
            logging.warning(f"SRT file {Path(matching_srt_file).name} is empty, skipping video.")
            return
        
        logging.info(f"Found video: {video_file_name} and subtitles: {Path(matching_srt_file).name}")

        # Apply ISO language code mapping to the output filename
        base_output_name = video_file_name.replace('.mp4', '_Sub.mp4')
        normalized_output_name = apply_iso_lang_suffix(base_output_name, language_code)
        output_video_file = str(export_dir / normalized_output_name)
        video_clip = VideoFileClip(exported_video_file)
        
        # Trim the video slightly before the end to avoid last frame issues
        trim_duration = video_clip.duration - 0.1
        video_clip = video_clip.subclip(0, trim_duration)
        
        font_path = select_font(language_code)

        subtitles_generator = lambda txt: create_text_clip_with_background(txt, fontsize=60, font_name=font_path, text_color='black')
        subtitles_clip = SubtitlesClip(matching_srt_file, make_textclip=subtitles_generator)
        
        # Check if subtitles are empty using subtitle_clips.subtitles
        if not hasattr(subtitles_clip, 'subtitles') or not subtitles_clip.subtitles:
            logging.warning(f"No valid subtitles found in {Path(matching_srt_file).name}, skipping video.")
            if video_clip:
                video_clip.close()
            return
            
        pos_y = (2 * video_clip.size[1]) // 3
        
        # Calculate the end time for subtitles (1 second before video ends)
        subtitle_end_time = max(0, trim_duration - 1)
        
        # Trim the subtitles clip to end 1 second before the video ends
        subtitles_clip = subtitles_clip.subclip(0, subtitle_end_time)
        
        subtitles_clip = subtitles_clip.set_position(('center', pos_y))

        video_with_subs = CompositeVideoClip([video_clip, subtitles_clip])
        video_with_subs.write_videofile(output_video_file, codec='libx264', audio_codec='aac', 
                                      ffmpeg_params=['-max_muxing_queue_size', '1024'])

        logging.info(f"Subtitle burned into {output_video_file}")
    except Exception as e:
        logging.error(f"Failed to process video {video_file_name} due to {str(e)}")
    finally:
        if video_clip:
            video_clip.close()

if __name__ == '__main__':
    if not exported_video_files:
        logging.info("No video files found in the directory.")
    elif not srt_files:
        logging.info("No subtitle files found in the directory.")
    else:
        logging.info("OK, hold on, we are getting there! 小程序正在努力运转中～")
        for video_file in exported_video_files:
            process_video(video_file)
