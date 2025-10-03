from flask import request, jsonify
import logging
import subprocess
import json
import re
import os
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from yt_dlp.utils import DownloadError

from make_playlists import (
    DEFAULT_LANGUAGES,
    CredentialSetupError,
    run_batch_creation,
)

# Set up logging
app_logger = logging.getLogger('youtube_playlist')
app_logger.setLevel(logging.INFO)

def _build_playlist_result(playlist_data: Dict[str, Any], playlist_url: str):
    playlist_title = (
        playlist_data.get('title')
        or playlist_data.get('playlist_title')
        or 'Unknown Playlist'
    )
    entries: List[Dict[str, Any]] = playlist_data.get('entries') or []

    videos = []
    for item in entries:
        try:
            video_id = item.get('id')
            if not video_id:
                continue

            raw_url = item.get('url') or item.get('webpage_url')
            if raw_url and 'watch?v=' in raw_url:
                video_url = raw_url
            else:
                video_url = f'https://www.youtube.com/watch?v={video_id}'

            video_info = {
                'video_id': video_id,
                'title': item.get('title') or 'Unknown Title',
                'url': video_url,
                'duration': item.get('duration'),
                'views': item.get('view_count') or item.get('view_count_text'),
                'author': item.get('uploader') or item.get('channel'),
            }
            videos.append(video_info)
        except Exception as exc:
            app_logger.warning(f"Error processing video item: {exc}")
            continue

    if not videos:
        return {
            'success': False,
            'error': f'No valid videos found in the playlist "{playlist_title}"',
            'playlist_title': playlist_title,
            'playlist_url': playlist_url
        }

    video_ids = [video['video_id'] for video in videos]

    return {
        'success': True,
        'playlist_url': playlist_url,
        'playlist_title': playlist_title,
        'total_videos': len(videos),
        'video_ids': video_ids,
        'videos': videos,
        'video_ids_text': '\n'.join(video_ids)
    }


def extract_video_ids_from_playlist(playlist_url):
    """Extract video IDs from a YouTube playlist URL using yt-dlp."""
    try:
        if not playlist_url or not isinstance(playlist_url, str):
            return {'success': False, 'error': 'Invalid playlist URL provided'}

        playlist_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
        match = re.search(playlist_pattern, playlist_url)
        if not match:
            return {
                'success': False,
                'error': 'Invalid YouTube playlist URL format. Please provide a valid YouTube playlist URL.'
            }

        app_logger.info(f"Processing playlist URL with yt-dlp: {playlist_url}")

        try:
            socket_timeout = float(os.getenv('YT_DLP_SOCKET_TIMEOUT', '15'))
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'extract_flat': True,
                'socket_timeout': socket_timeout,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_data = ydl.extract_info(playlist_url, download=False)

            app_logger.info(
                "yt-dlp API returned %s entries",
                len(playlist_data.get('entries', []) if playlist_data else [])
            )

            api_result = _build_playlist_result(playlist_data, playlist_url)
            if api_result['success']:
                return api_result
        except DownloadError as exc:
            app_logger.error(f"yt-dlp API error: {exc}")
        except Exception as exc:
            app_logger.error(f"yt-dlp API unexpected error: {exc}")

        app_logger.info("Falling back to yt-dlp subprocess execution")

        try:
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--no-warnings',
                '--quiet',
                playlist_url
            ]

            command_timeout = int(os.getenv('YT_DLP_TIMEOUT', '180'))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=command_timeout,
                cwd=os.getcwd()
            )

            if result.returncode != 0:
                app_logger.error(f"yt-dlp failed with return code {result.returncode}")
                app_logger.error(f"stderr: {result.stderr}")
                return {
                    'success': False,
                    'error': f'Failed to access playlist: {result.stderr.strip() or "Unknown error"}'
                }

            playlist_data = {'entries': [], 'title': 'Unknown Playlist'}
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    try:
                        data = json.loads(line)
                        if playlist_data['title'] == 'Unknown Playlist' and 'playlist_title' in data:
                            playlist_data['title'] = data['playlist_title']
                        playlist_data['entries'].append(data)
                    except json.JSONDecodeError as exc:
                        app_logger.warning(f"Failed to parse JSON line: {line[:100]}... Error: {exc}")
                        continue

            return _build_playlist_result(playlist_data, playlist_url)

        except subprocess.TimeoutExpired:
            app_logger.error("yt-dlp command timed out")
            return {
                'success': False,
                'error': 'Request timed out. The playlist might be very large or there might be network issues.'
            }
        except FileNotFoundError:
            app_logger.error("yt-dlp not found")
            return {
                'success': False,
                'error': 'yt-dlp is not installed or not found in PATH. Please install yt-dlp.'
            }
        except Exception as exc:
            app_logger.error(f"Error running yt-dlp: {exc}")
            return {
                'success': False,
                'error': f'Error running yt-dlp: {exc}'
            }

    except Exception as exc:
        app_logger.error(f"Error processing playlist: {exc}")
        return {
            'success': False,
            'error': f'Error processing playlist: {str(exc)}'
        }

def process_playlist():
    """Handle playlist processing request"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        playlist_url = data.get('playlist_url', '').strip()
        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400
        
        app_logger.info(f"Processing playlist request for URL: {playlist_url}")
        
        # Extract video information
        result = extract_video_ids_from_playlist(playlist_url)
        
        if result['success']:
            app_logger.info(f"Successfully processed playlist with {result['total_videos']} videos")
            return jsonify(result)
        else:
            app_logger.warning(f"Failed to process playlist: {result['error']}")
            return jsonify(result), 400
            
    except Exception as e:
        app_logger.error(f"Error in process_playlist: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500

def validate_playlist_url():
    """Validate a playlist URL without processing it"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        playlist_url = data.get('playlist_url', '').strip()
        if not playlist_url:
            return jsonify({'error': 'Playlist URL is required'}), 400
        
        # Check URL format
        playlist_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
        match = re.search(playlist_pattern, playlist_url)
        
        if not match:
            return jsonify({
                'valid': False,
                'error': 'Invalid YouTube playlist URL format'
            }), 400
        
        return jsonify({
            'valid': True,
            'playlist_id': match.group(1),
            'message': 'Valid YouTube playlist URL'
        })
        
    except Exception as e:
        app_logger.error(f"Error validating playlist URL: {str(e)}")
        return jsonify({
            'valid': False,
            'error': f'Validation error: {str(e)}'
        }), 500


def create_playlists():
    """Create YouTube playlists based on the provided naming pattern."""
    try:
        data = request.get_json() or {}

        base_tags_raw = data.get('base_tags')
        date_code = (data.get('date_code') or '').strip()
        languages_raw = data.get('languages')

        if isinstance(base_tags_raw, str):
            base_tags = [item.strip() for item in base_tags_raw.split(',') if item.strip()]
        elif isinstance(base_tags_raw, list):
            base_tags = [str(item).strip() for item in base_tags_raw if str(item).strip()]
        else:
            base_tags = []

        if not base_tags:
            return jsonify({'success': False, 'error': 'At least one base tag is required'}), 400

        if not date_code:
            return jsonify({'success': False, 'error': 'Date code is required'}), 400

        if isinstance(languages_raw, str):
            languages = [item.strip() for item in languages_raw.split(',') if item.strip()]
        elif isinstance(languages_raw, list):
            languages = [str(item).strip() for item in languages_raw if str(item).strip()]
        else:
            languages = []

        if not languages:
            languages = list(DEFAULT_LANGUAGES)

        result = run_batch_creation(
            base_tags,
            date_code,
            languages,
            allow_browser=False,
            workdir=pathlib.Path(__file__).resolve().parent,
        )

        return jsonify({
            'success': True,
            'base_tags': base_tags,
            'requested': result['requested'],
            'created': result['created'],
            'failed': result['failed'],
        })
    except FileNotFoundError as exc:
        app_logger.error("Client secret missing: %s", exc)
        return jsonify({'success': False, 'error': str(exc)}), 500
    except CredentialSetupError as exc:
        app_logger.error("Credential setup error: %s", exc)
        return jsonify({'success': False, 'error': str(exc)}), 500
    except ValueError as exc:
        app_logger.error("Validation error: %s", exc)
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        app_logger.error("Unexpected error creating playlists: %s", exc)
        return jsonify({'success': False, 'error': f'Unexpected error: {exc}'}), 500
