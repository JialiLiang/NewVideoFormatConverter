"""Google API client wrapper for YouTube uploads and playlist management."""
from __future__ import annotations

import datetime as dt
import logging
import pathlib
import re
import time
from typing import Dict, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

TOKEN_FILENAME = "token.json"
CLIENT_SECRET_FILENAME = "client_secret.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB
MAX_RETRIES = 5
PLAYLIST_PATTERN = re.compile(r"^\[(?P<tag>[^\]]+)\]_\[(?P<lang>[^\]]+)\]_(?P<date>\d{8})$")

logger = logging.getLogger("youtube_upload")
logger.setLevel(logging.INFO)


class CredentialSetupError(RuntimeError):
    """Raised when OAuth credentials cannot be prepared."""


class YoutubeUploadClient:
    """Handle YouTube video uploads and playlist management."""

    def __init__(self, *, workdir: Optional[pathlib.Path] = None, allow_browser: bool = True) -> None:
        self.workdir = workdir or pathlib.Path(__file__).resolve().parent.parent
        self.allow_browser = allow_browser
        self.creds = self._ensure_credentials()
        self.service = build("youtube", "v3", credentials=self.creds, cache_discovery=False)
        self._playlist_cache: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Credential helpers
    # ------------------------------------------------------------------
    def _ensure_credentials(self) -> Credentials:
        token_path = self.workdir / TOKEN_FILENAME
        client_secret_path = self.workdir / CLIENT_SECRET_FILENAME

        if not client_secret_path.exists():
            raise FileNotFoundError(
                f"Missing {CLIENT_SECRET_FILENAME}. Download it from Google Cloud Console and place it next to the script."
            )

        creds: Optional[Credentials] = None
        if token_path.exists():
            logger.info("Using cached OAuth token at %s", token_path)
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to refresh cached credentials: %s", exc)
                if not self.allow_browser:
                    raise CredentialSetupError(
                        "Cached credentials expired and could not be refreshed automatically. Re-run authentication."
                    ) from exc
                creds = None

        if not creds or not creds.valid:
            if not self.allow_browser:
                raise CredentialSetupError("No valid cached credentials available. Run the CLI locally to authenticate.")
            logger.info("Launching OAuth browser flow for YouTube upload scope")
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json())
        logger.info("OAuth token updated at %s", token_path)
        return creds

    # ------------------------------------------------------------------
    # Playlist management
    # ------------------------------------------------------------------
    def refresh_playlist_cache(self) -> None:
        logger.debug("Refreshing playlist cache")
        cache: Dict[str, str] = {}
        request = self.service.playlists().list(part="snippet", mine=True, maxResults=50)
        while request is not None:
            response = request.execute()
            for item in response.get("items", []):
                title = item["snippet"].get("title")
                if title:
                    cache[title] = item["id"]
            request = self.service.playlists().list_next(request, response)
        self._playlist_cache = cache

    def ensure_playlist(self, name: str, description: str | None = None) -> str:
        if not name:
            raise ValueError("Playlist name is required")

        if name not in self._playlist_cache:
            self.refresh_playlist_cache()

        if name in self._playlist_cache:
            return self._playlist_cache[name]

        body = {
            "snippet": {
                "title": name,
                "description": description or "Generated via bulk uploader",
            },
            "status": {"privacyStatus": "unlisted"},
        }
        response = self.service.playlists().insert(part="snippet,status", body=body).execute()
        playlist_id = response.get("id")
        if not playlist_id:
            raise RuntimeError("Failed to create playlist; no ID returned")
        self._playlist_cache[name] = playlist_id
        logger.info("Created playlist %s (%s)", name, playlist_id)
        return playlist_id

    # ------------------------------------------------------------------
    # Video upload helpers
    # ------------------------------------------------------------------
    def upload_video(
        self,
        file_path: pathlib.Path,
        *,
        title: str,
        description: str | None = None,
        privacy_status: str = "unlisted",
        made_for_kids: bool = False,
    ) -> str:
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        body = {
            "snippet": {
                "title": title,
                "description": description or "Say goodbye to bad photos",
            },
            "status": {
                "privacyStatus": privacy_status,
                "madeForKids": False,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(str(file_path), chunksize=CHUNK_SIZE, resumable=True)
        request = self.service.videos().insert(part="snippet,status", body=body, media_body=media)

        attempts = 0
        while True:
            try:
                status, response = request.next_chunk()
                if status:
                    logger.debug("Upload progress %.2f%% for %s", status.progress() * 100, file_path.name)
                if response and response.get("id"):
                    video_id = response["id"]
                    logger.info("Uploaded %s (videoId=%s)", file_path.name, video_id)
                    return video_id
            except HttpError as exc:
                attempts += 1
                logger.warning("YouTube API error on attempt %s/%s: %s", attempts, MAX_RETRIES, exc)
                if attempts >= MAX_RETRIES:
                    raise
                wait_for = min(2 ** attempts, 60)
                time.sleep(wait_for)
            except Exception as exc:  # noqa: BLE001
                attempts += 1
                logger.warning("Unexpected error on attempt %s/%s: %s", attempts, MAX_RETRIES, exc)
                if attempts >= MAX_RETRIES:
                    raise
                wait_for = min(2 ** attempts, 60)
                time.sleep(wait_for)

    def add_video_to_playlist(self, video_id: str, playlist_id: str) -> None:
        body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }
        self.service.playlistItems().insert(part="snippet", body=body).execute()
        logger.info("Added video %s to playlist %s", video_id, playlist_id)

    # ------------------------------------------------------------------
    # Playlist suggestion helpers
    # ------------------------------------------------------------------
    def find_closest_playlist(
        self,
        base_tag: str,
        language: str,
        date_code: str,
        *,
        threshold_days: int = 7,
    ) -> Optional[Dict[str, str]]:
        """Return the closest existing playlist within *threshold_days* or None."""

        if not base_tag or not language or not date_code:
            return None

        target_date = _parse_date_code(date_code)
        if target_date is None:
            return None

        if not self._playlist_cache:
            self.refresh_playlist_cache()

        best: Optional[Dict[str, str]] = None
        base_tag = base_tag.upper()
        language = language.lower()

        for title, playlist_id in self._playlist_cache.items():
            match = PLAYLIST_PATTERN.match(title)
            if not match:
                continue
            if match.group('tag').upper() != base_tag:
                continue
            if match.group('lang').lower() != language:
                continue

            playlist_date = _parse_date_code(match.group('date'))
            if playlist_date is None:
                continue

            delta = abs((playlist_date - target_date).days)
            if delta > threshold_days:
                continue

            if best is None or delta < best['delta_days']:
                best = {
                    'name': title,
                    'id': playlist_id,
                    'date': playlist_date.strftime('%d%m%Y'),
                    'delta_days': delta,
                }
        return best


def _parse_date_code(value: str) -> Optional[dt.date]:
    try:
        return dt.datetime.strptime(value, "%d%m%Y").date()
    except (ValueError, TypeError):
        return None
