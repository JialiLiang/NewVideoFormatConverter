"""YouTube Playlist Batch Creator.

Create multiple unlisted YouTube playlists in one run using the YouTube Data API v3.
"""
from __future__ import annotations

import json
import logging
import pathlib
import sys
import time
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
DEFAULT_LANGUAGES: Sequence[str] = (
    "fr",
    "ja",
    "en",
    "de",
    "es",
    "it",
    "pt",
    "ko",
    "zh",
    "hi",
    "id",
    "tr",
    "tl",
    "pl",
    "ar",
    "ms",
    "vi",
    "th",
    "nl",
)
DEFAULT_PRIVACY = "unlisted"
TOKEN_FILENAME = "token.json"
CLIENT_SECRET_FILENAME = "client_secret.json"

logger = logging.getLogger("playlist_batch_creator")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class CredentialSetupError(RuntimeError):
    """Raised when OAuth credentials cannot be prepared programmatically."""


def ensure_credentials(directory: pathlib.Path, *, allow_browser: bool = True) -> Credentials:
    """Load cached credentials or run the OAuth flow to create them."""
    token_path = directory / TOKEN_FILENAME
    client_secret_path = directory / CLIENT_SECRET_FILENAME

    if not client_secret_path.exists():
        raise FileNotFoundError(
            f"Missing {CLIENT_SECRET_FILENAME}. Download it from Google Cloud Console and place it next to this script."
        )

    creds: Credentials | None = None
    if token_path.exists():
        logger.info("Using cached OAuth token at %s", token_path)
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing expired credentials")
            creds.refresh(Request())
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to refresh cached credentials: %s", exc)
            if not allow_browser:
                raise CredentialSetupError(
                    "Cached credentials expired and could not be refreshed automatically. "
                    "Re-run the CLI script locally to complete OAuth."
                ) from exc
            creds = None

    if not creds or not creds.valid:
        if not allow_browser:
            raise CredentialSetupError(
                "No valid cached credentials available. Run `python make_playlists.py` locally to authenticate"
            )
        logger.info("No valid credentials found. Launching OAuth browser flow...")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json())
    logger.info("OAuth token updated at %s", token_path)
    return creds


def build_service(creds: Credentials):
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def generate_playlist_names(
    base_tags: Iterable[str],
    date_code: str,
    languages: Iterable[str],
) -> List[str]:
    names: List[str] = []
    for raw_tag in base_tags:
        base_tag = str(raw_tag).strip()
        if not base_tag:
            continue
        for raw_lang in languages:
            lang = str(raw_lang).strip()
            if not lang:
                continue
            names.append(f"[{base_tag}]_[{lang}]_{date_code}")
    return names


def prompt_language_list(default_languages: Sequence[str]) -> List[str]:
    default_hint = ",".join(default_languages)
    while True:
        response = input(
            "Language codes (comma separated, e.g. fr,ja,en)"
            f" [{default_hint}]: "
        ).strip()
        if not response:
            return list(default_languages)

        languages = [item.strip() for item in response.split(",") if item.strip()]
        if languages:
            return languages

        print("Please enter at least one language code.")


def parse_error_reason(error: HttpError) -> str:
    try:
        data = json.loads(error.content.decode("utf-8"))
        return data["error"]["errors"][0].get("reason", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def should_retry(error: HttpError) -> bool:
    if error.resp.status in {500, 503}:
        return True
    return parse_error_reason(error) in {"quotaExceeded", "userRateLimitExceeded"}


def create_playlist_with_retry(service, name: str, description: str | None = None, *, max_attempts: int = 5) -> str:
    for attempt in range(1, max_attempts + 1):
        try:
            request = service.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": name,
                        "description": description or "Generated via playlist batch creator",
                    },
                    "status": {"privacyStatus": DEFAULT_PRIVACY},
                },
            )
            response = request.execute()
            playlist_id = response.get("id")
            if not playlist_id:
                raise ValueError("Playlist created without ID in response")
            return playlist_id
        except HttpError as error:
            reason = parse_error_reason(error)
            logger.warning("YouTube API error on attempt %s/%s: %s", attempt, max_attempts, reason)
            if attempt == max_attempts or not should_retry(error):
                raise
            sleep_for = min(2 ** attempt, 60)
            logger.info("Retrying in %s seconds", sleep_for)
            time.sleep(sleep_for)

    raise RuntimeError("Exceeded retry attempts without creating playlist")


def prompt(message: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{message}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        print("Value required. Please try again.")


def confirm(playlists: Sequence[str]) -> bool:
    print("\nPlaylists to create (privacy: unlisted):")
    for item in playlists:
        print(f"  - {item}")
    print()
    choice = input("Proceed with creation? [y/N]: ").strip().lower()
    return choice in {"y", "yes"}


def run_batch_creation(
    base_tags: Sequence[str] | str,
    date_code: str,
    languages: Sequence[str],
    *,
    allow_browser: bool,
    workdir: pathlib.Path | None = None,
) -> Dict[str, List[Dict[str, str]]]:
    """Programmatically create YouTube playlists and return structured results."""
    if isinstance(base_tags, str):
        base_tags_list = [base_tags]
    else:
        base_tags_list = list(base_tags)

    base_tags_clean = [tag.strip() for tag in base_tags_list if str(tag).strip()]
    if not base_tags_clean:
        raise ValueError("At least one base tag is required")

    if not date_code.strip():
        raise ValueError("Date code is required")

    clean_languages = [lang.strip() for lang in languages if lang.strip()]
    if not clean_languages:
        raise ValueError("At least one language code is required")

    workdir = workdir or pathlib.Path(__file__).resolve().parent

    playlists = generate_playlist_names(base_tags_clean, date_code.strip(), clean_languages)
    if not playlists:
        return {"requested": [], "created": [], "failed": []}

    creds = ensure_credentials(workdir, allow_browser=allow_browser)
    service = build_service(creds)

    created: List[Dict[str, str]] = []
    failed: List[Dict[str, str]] = []

    for name in playlists:
        try:
            playlist_id = create_playlist_with_retry(service, name)
            created.append(
                {
                    "name": name,
                    "playlist_id": playlist_id,
                    "url": f"https://www.youtube.com/playlist?list={playlist_id}",
                }
            )
        except HttpError as error:
            reason = parse_error_reason(error)
            logger.error("Failed to create playlist %s: %s", name, reason)
            failed.append({"name": name, "error": reason})
        except Exception as error:  # noqa: BLE001
            logger.error("Unexpected error for playlist %s: %s", name, error)
            failed.append({"name": name, "error": str(error)})

    return {
        "requested": playlists,
        "created": created,
        "failed": failed,
    }


def main():
    workdir = pathlib.Path(__file__).resolve().parent
    today_default = datetime.utcnow().strftime("%d%m%Y")

    base_tag_input = prompt("Base tag(s) (comma separated, e.g. AIBG,ANIM)")
    base_tags = [tag.strip() for tag in base_tag_input.split(',') if tag.strip()]
    if not base_tags:
        print("No base tags provided. Exiting.")
        return 1
    date_code = prompt("Date code (DDMMYYYY)", today_default)

    languages = prompt_language_list(DEFAULT_LANGUAGES)
    playlists = generate_playlist_names(base_tags, date_code, languages)
    if not playlists:
        print("No playlists to create. Exiting.")
        return 0

    if not confirm(playlists):
        print("Aborted by user.")
        return 0

    try:
        result = run_batch_creation(
            base_tags,
            date_code,
            languages,
            allow_browser=True,
            workdir=workdir,
        )
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 1
    except CredentialSetupError as exc:
        logger.error("%s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error: %s", exc)
        return 1

    created = result["created"]
    failed = result["failed"]
    playlists = result["requested"]

    print("\nBatch complete.")
    if created:
        print("Created playlists:")
        for item in created:
            print(f"  - {item['name']} (ID: {item['playlist_id']})")
    if failed:
        print("Failed playlists:")
        for item in failed:
            print(f"  - {item['name']}: {item['error']}")

    print("\nYou can find the cached credentials in token.json. Delete it to re-authenticate.")
    return 0 if len(failed) == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
