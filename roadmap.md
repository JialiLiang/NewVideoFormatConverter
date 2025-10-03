# Development Roadmap

## Overview

This roadmap tracks the implementation of the **hybrid architecture** migration from a monolithic Flask + Jinja template app to a modern React frontend with Flask API backend.

## Architecture Vision

**Target State:**
- **Frontend**: React + Vite + TypeScript + Chakra UI
- **Backend**: Flask REST API
- **Authentication**: Google OAuth 2.0 with session-based auth
- **Migration Strategy**: Gradual feature migration, maintaining backward compatibility

**Key Principles:**
1. Same-domain deployment to avoid CORS complexity
2. Session-based auth with httpOnly cookies
3. Progressive migration of features from Jinja to React
4. Maintain legacy routes during transition period

---

## Milestones & Implementation Status

### ✅ M1: OAuth Minimum Viable Product (COMPLETED)

**Goal**: Implement secure Google OAuth authentication flow

**Tasks:**
- [x] Set up Authlib with Google OAuth credentials
- [x] Implement `/api/auth/google/login` endpoint
- [x] Implement `/api/auth/google/callback` handler
- [x] Create `/api/me` endpoint for user profile
- [x] Configure session management (httpOnly, SameSite=Lax, Secure)
- [x] Test end-to-end login flow locally

**Outcome**: Users can authenticate with Google and maintain secure sessions.

---

### ✅ M2: React App Shell (COMPLETED)

**Goal**: Build the foundational React application structure

**Tasks:**
- [x] Set up Vite + React + TypeScript project in `/web`
- [x] Configure Chakra UI theme
- [x] Implement `/login` page with Google OAuth button
- [x] Create protected route guards (`ProtectedRoute.tsx`)
- [x] Build app layout with navigation (`AppLayout.tsx`)
- [x] Implement `/app` dashboard landing page
- [x] Create `/app/profile` page displaying user info from `/api/me`
- [x] Set up API client with Axios (withCredentials: true)
- [x] Configure Vite dev server proxy to Flask backend

**Outcome**: Users can log in, access protected routes, and see their profile.

---

### ✅ M3: Feature Migration - Phase 1 (COMPLETED)

**Goal**: Migrate initial features to React interface

**Phase 1 Features:**
- [x] **Name Generator**
  - [x] Extract backend API endpoints (if needed)
  - [x] Build React form component
  - [x] Implement filename generation logic
  - [x] Add validation and AI correction features
  - [x] Test parity with legacy Jinja version

- [x] **Video Converter**
  - [x] Create React upload interface with drag-and-drop
  - [x] Implement format selection UI
  - [x] Add real-time progress tracking
  - [x] Build download interface for completed conversions
  - [x] Test with various video formats and sizes

- [x] **AdLocalizer** (Partial)
  - [x] Build React interface for multi-step workflow
  - [x] Implement transcription step
  - [x] Add translation and language selection
  - [x] Integrate voice generation
  - [x] Complete video mixing flow

**Outcome**: Core features available in both React and legacy UIs.

---

### 🔄 M4: Security & Observability (IN PROGRESS)

**Goal**: Harden production readiness with security and monitoring

**Tasks:**
- [ ] Implement rate limiting on sensitive endpoints
- [ ] Add CSRF protection for state-changing operations
- [ ] Create unified error pages (404, 500, 403)
- [ ] Implement empty state components for all features
- [ ] Set up structured logging with log levels
- [ ] Add health check endpoint with detailed status
- [ ] Configure monitoring and alerting
- [x] Document environment variables and configuration
- [ ] Add input validation and sanitization
- [ ] Implement request size limits

**Target**: Production-ready application with proper security controls.

---

### 📋 M5: Feature Migration - Phase 2 (PLANNED)

**Goal**: Migrate remaining features to React

**Phase 2 Features:**
- [ ] **YouTube Playlist Creator**
  - [ ] Build React interface for batch playlist creation
  - [ ] Implement preview and confirmation flow
  - [ ] Add language selection interface

- [ ] **YouTube Bulk Uploader**
  - [ ] Create drag-and-drop upload interface
  - [ ] Implement progress tracking for uploads
  - [ ] Add results download and history view

- [ ] **Language Mapping Tool**
  - [ ] Create reference table component
  - [ ] Add search and filter functionality
  - [ ] Implement inline documentation

---

### 📋 M6: Enhanced Features (PLANNED)

**Goal**: Add new capabilities and improvements

**Features:**
- [ ] **User Dashboard**
  - [ ] Job history tracking
  - [ ] Usage statistics
  - [ ] Favorite presets and templates

- [ ] **Collaboration**
  - [ ] Share generated content with team members
  - [ ] Comments and feedback on conversions
  - [ ] Role-based access control

- [ ] **Advanced Video Features**
  - [ ] Batch watermarking
  - [ ] Custom aspect ratio support
  - [ ] Video trimming and editing

- [ ] **API Documentation**
  - [ ] Interactive API docs with Swagger/OpenAPI
  - [ ] API key management for programmatic access
  - [ ] Webhooks for job completion

---

### 📋 M7: Performance & Scaling (FUTURE)

**Goal**: Optimize for high-traffic production use

**Tasks:**
- [ ] Implement Redis for session storage
- [ ] Add background job queue (Celery/RQ)
- [ ] Optimize video processing pipeline
- [ ] Implement caching strategy
- [ ] Add CDN for static assets
- [ ] Database integration for persistent data
- [ ] Horizontal scaling setup
- [ ] Load testing and optimization

---

## Technical Decisions

### Authentication
- **Choice**: Session-based auth with httpOnly cookies
- **Rationale**: Simple, secure, works seamlessly with same-domain deployment
- **Alternative Considered**: JWT tokens (added complexity for refresh)

### Frontend Framework
- **Choice**: React + Vite + TypeScript
- **Rationale**: Fast dev experience, strong typing, modern tooling
- **Alternative Considered**: Vue, Svelte (team familiarity favored React)

### UI Library
- **Choice**: Chakra UI
- **Rationale**: Lightweight, good theming, accessible components
- **Alternative Considered**: Material-UI (heavier), Tailwind (more manual)

### API Client
- **Choice**: Axios with withCredentials
- **Rationale**: Automatic cookie handling, good error handling
- **Alternative Considered**: Fetch API (requires more boilerplate)

### Deployment Strategy
- **Choice**: Same-domain deployment (Flask serves React build)
- **Rationale**: Avoids CORS, simpler configuration, cookie handling
- **Alternative Considered**: Separate deployments (more complex)

---

## Risk Mitigation

### Risk: OAuth redirect_uri mismatch
- **Mitigation**: Maintain comprehensive env var documentation
- **Fallback**: Keep legacy login available during transition

### Risk: Session cookie issues in production
- **Mitigation**: Test cookie settings early in staging
- **Fallback**: Implement JWT fallback if needed

### Risk: Name Generator API not ready
- **Mitigation**: Keep Jinja version available until API stable
- **Timeline**: Only migrate after thorough testing

### Risk: Rate limiting causes false positives
- **Mitigation**: Implement feature flags for gradual rollout
- **Monitoring**: Track rate limit hits in logs

### Risk: OAuth clock skew
- **Mitigation**: Ensure server time synchronization
- **Configuration**: Allow configurable clock_skew parameter

---

## Environment & Deployment

### Directory Structure
```
NewVideoFormatConverter/
├── app.py                  # Flask backend + legacy routes
├── oauth_routes.py         # Google OAuth implementation
├── *_app.py                # Feature modules
├── templates/              # Legacy Jinja templates
├── static/                 # Legacy static assets
├── web/                    # React frontend
│   ├── src/
│   ├── dist/              # Built React app (production)
│   └── package.json
└── requirements.txt
```

### Environment Variables

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete list.

**Critical:**
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- `SECRET_KEY`, `FRONTEND_URL`
- `SESSION_COOKIE_SECURE` (true in production)

### Local Development

**Terminal 1 (Backend):**
```bash
python3 app.py --port 5000
```

**Terminal 2 (Frontend):**
```bash
cd web && npm run dev  # http://localhost:5173
```

### Production Deployment

**Monolithic (Recommended):**
1. Build React: `cd web && npm run build`
2. Flask serves from `web/dist/`
3. Single deployment to Render/Heroku

**Separate Services:**
1. Backend: Deploy Flask API
2. Frontend: Deploy to Vercel/Netlify
3. Configure CORS and cookie settings

---

## Current Focus (October 2025)

**Immediate Priorities:**
1. Complete security hardening (rate limiting, CSRF)
2. Implement comprehensive error handling
3. Add monitoring and observability
4. Complete YouTube tools migration to React
5. Performance optimization and load testing

**Next Quarter:**
- User dashboard with job history
- API documentation and public API
- Advanced video editing features
- Team collaboration features

---

## Success Metrics

**Phase 1 (Completed):**
- ✅ OAuth login working end-to-end
- ✅ React app shell with protected routes
- ✅ 3+ features migrated to React
- ✅ Zero breaking changes to legacy features

**Phase 2 (In Progress):**
- [ ] All features available in React UI
- [ ] < 2s page load time
- [ ] 99.5% uptime
- [ ] Zero critical security vulnerabilities

**Phase 3 (Future):**
- [ ] 100+ active users
- [ ] < 500ms API response time (p95)
- [ ] 10,000+ video conversions/month
- [ ] Public API with external integrations

---

## References

- [README.md](README.md) - Project overview and usage
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [web/README.md](web/README.md) - React frontend docs

---

**Last Updated**: October 3, 2025  
**Status**: Phase 1 Complete, Phase 2 In Progress  
**Next Review**: December 2025
