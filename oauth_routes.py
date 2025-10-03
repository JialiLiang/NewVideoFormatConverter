from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, Response, current_app, jsonify, redirect, session, url_for

logger = logging.getLogger(__name__)

oauth = OAuth()
auth_bp = Blueprint('auth', __name__, url_prefix='/api')


def init_auth(app) -> None:
    oauth.init_app(app)

    client_id = app.config.get('GOOGLE_CLIENT_ID')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET')

    if client_id and client_secret:
        oauth.register(
            name='google',
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )
    else:
        logger.warning('Google OAuth is not fully configured; login will be unavailable until credentials are set.')

    app.register_blueprint(auth_bp)


def _is_oauth_configured() -> bool:
    return hasattr(oauth, 'google')


def _build_frontend_url(path_config_key: str, fallback_path: str, error: Optional[str] = None) -> str:
    base = current_app.config.get('FRONTEND_URL')
    path = current_app.config.get(path_config_key, fallback_path)
    target = f"{base.rstrip('/')}{path}" if base else path
    if error:
        separator = '&' if '?' in target else '?'
        return f"{target}{separator}{urlencode({'error': error})}"
    return target


def _frontdoor_path(error: Optional[str] = None) -> str:
    return _build_frontend_url('FRONTEND_APP_PATH', '/app', error)


def _login_path(error: Optional[str] = None) -> str:
    return _build_frontend_url('FRONTEND_LOGIN_PATH', '/login', error)


@auth_bp.get('/auth/google/login')
def auth_login() -> Response:
    if not _is_oauth_configured():
        return jsonify({'error': 'Google OAuth is not configured'}), 503

    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
    if not redirect_uri:
        redirect_uri = url_for('auth.auth_callback', _external=True)

    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.get('/auth/google/callback')
def auth_callback() -> Response:
    if not _is_oauth_configured():
        return redirect(_login_path('oauth_not_configured'))

    try:
        token: Dict[str, Any] = oauth.google.authorize_access_token()
    except Exception:  # pragma: no cover - Authlib raises dynamically
        logger.exception('Failed to complete Google OAuth handshake')
        return redirect(_login_path('oauth_failed'))

    userinfo = token.get('userinfo')
    if not userinfo:
        try:
            userinfo = oauth.google.parse_id_token(token)
        except Exception:  # pragma: no cover - Authlib raises dynamically
            logger.exception('Failed to parse Google user info from id_token')
            return redirect(_login_path('invalid_token'))

    if not userinfo:
        return redirect(_login_path('missing_userinfo'))

    normalized_user = {
        'id': userinfo.get('sub') or userinfo.get('id'),
        'email': userinfo.get('email'),
        'name': userinfo.get('name'),
        'given_name': userinfo.get('given_name'),
        'family_name': userinfo.get('family_name'),
        'picture': userinfo.get('picture'),
        'locale': userinfo.get('locale'),
        'login_at': datetime.utcnow().isoformat() + 'Z',
    }

    session['user'] = {k: v for k, v in normalized_user.items() if v is not None}
    session['token'] = {
        key: token.get(key)
        for key in ('access_token', 'expires_at', 'refresh_token', 'scope')
        if token.get(key) is not None
    }
    session.permanent = True

    return redirect(_frontdoor_path())


@auth_bp.post('/auth/logout')
def auth_logout() -> Response:
    session.clear()
    return jsonify({'success': True})


@auth_bp.get('/me')
def auth_me() -> Response:
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(user)
