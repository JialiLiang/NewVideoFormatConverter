from flask import Flask, render_template, request, jsonify
import logging
import subprocess
import json
import re
import os

# Set up logging
app_logger = logging.getLogger('youtube_playlist')
app_logger.setLevel(logging.INFO)

def extract_video_ids_from_playlist(playlist_url):
    """
    Extract video IDs from a YouTube playlist URL using yt-dlp
    
    Args:
        playlist_url (str): YouTube playlist URL
        
    Returns:
        dict: Result containing video IDs, titles, and metadata
    """
    try:
        # Validate URL format
        if not playlist_url or not isinstance(playlist_url, str):
            return {
                'success': False,
                'error': 'Invalid playlist URL provided'
            }
        
        # Check if it's a valid YouTube playlist URL
        playlist_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
        match = re.search(playlist_pattern, playlist_url)
        
        if not match:
            return {
                'success': False,
                'error': 'Invalid YouTube playlist URL format. Please provide a valid YouTube playlist URL.'
            }
        
        app_logger.info(f"Processing playlist URL with yt-dlp: {playlist_url}")
        
        # Use yt-dlp to extract playlist information
        try:
            # Command to get playlist info as JSON
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--no-warnings',
                '--quiet',
                playlist_url
            ]
            
            app_logger.info(f"Running command: {' '.join(cmd)}")
            
            # Run yt-dlp command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
                cwd=os.getcwd()
            )
            
            if result.returncode != 0:
                app_logger.error(f"yt-dlp failed with return code {result.returncode}")
                app_logger.error(f"stderr: {result.stderr}")
                return {
                    'success': False,
                    'error': f'Failed to access playlist: {result.stderr.strip() or "Unknown error"}'
                }
            
            # Parse the JSON output
            playlist_data = []
            playlist_title = "Unknown Playlist"
            
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    try:
                        data = json.loads(line)
                        playlist_data.append(data)
                        
                        # Get playlist title from the first entry
                        if playlist_title == "Unknown Playlist" and 'playlist_title' in data:
                            playlist_title = data['playlist_title']
                            
                    except json.JSONDecodeError as e:
                        app_logger.warning(f"Failed to parse JSON line: {line[:100]}... Error: {e}")
                        continue
            
            app_logger.info(f"Found {len(playlist_data)} videos in playlist: {playlist_title}")
            
            if not playlist_data:
                return {
                    'success': False,
                    'error': f'No videos found in the playlist "{playlist_title}" or playlist is empty',
                    'playlist_title': playlist_title,
                    'playlist_url': playlist_url
                }
            
            # Extract video information
            videos = []
            for item in playlist_data:
                try:
                    # Extract video ID from URL or id field
                    video_id = None
                    if 'id' in item:
                        video_id = item['id']
                    elif 'url' in item:
                        # Extract ID from URL
                        url_match = re.search(r'[?&]v=([a-zA-Z0-9_-]+)', item['url'])
                        if url_match:
                            video_id = url_match.group(1)
                    
                    if not video_id:
                        app_logger.warning(f"No video ID found for item: {item.get('title', 'Unknown')}")
                        continue
                    
                    video_info = {
                        'video_id': video_id,
                        'title': item.get('title', 'Unknown Title'),
                        'url': item.get('url', f'https://www.youtube.com/watch?v={video_id}'),
                        'duration': item.get('duration'),
                        'views': item.get('view_count'),
                        'author': item.get('uploader', item.get('channel', 'Unknown'))
                    }
                    videos.append(video_info)
                    
                except Exception as e:
                    app_logger.warning(f"Error processing video item: {str(e)}")
                    continue
            
            if not videos:
                return {
                    'success': False,
                    'error': f'No valid videos found in the playlist "{playlist_title}"',
                    'playlist_title': playlist_title,
                    'playlist_url': playlist_url
                }
            
            # Extract just the video IDs for easy copying
            video_ids = [video['video_id'] for video in videos]
            
            app_logger.info(f"Successfully extracted {len(videos)} videos from playlist")
            
            return {
                'success': True,
                'playlist_url': playlist_url,
                'playlist_title': playlist_title,
                'total_videos': len(videos),
                'video_ids': video_ids,
                'videos': videos,
                'video_ids_text': '\n'.join(video_ids)  # For easy copying
            }
            
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
        except Exception as e:
            app_logger.error(f"Error running yt-dlp: {str(e)}")
            return {
                'success': False,
                'error': f'Error running yt-dlp: {str(e)}'
            }
        
    except Exception as e:
        app_logger.error(f"Error processing playlist: {str(e)}")
        return {
            'success': False,
            'error': f'Error processing playlist: {str(e)}'
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
