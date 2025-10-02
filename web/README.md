# Creative Tools Web Shell

React + Vite frontend for the Creative Tools Console. Provides the Google login view, protected app shell, and profile page while Flask continues to serve legacy Jinja screens.

## Prerequisites
- Node.js 18+
- Copy `.env.example` to `.env` and adjust `VITE_API_BASE_URL` (defaults to `http://localhost:5000`).

## Scripts
- `npm run dev` — start Vite dev server (proxies `/api` to the Flask backend).
- `npm run build` — type-check and build production assets into `dist/`.
- `npm run lint` — run ESLint across the project.

## Development Flow
1. Ensure the Flask backend is running locally on port 5000.
2. Run `npm run dev` and open the printed URL (defaults to `http://localhost:5173`).
3. Visit `/login` to trigger Google OAuth and return to the protected `/app` routes.
4. Use `/app/profile` to verify `/api/me` responses render correctly.

Legacy pages remain available under their existing routes (e.g., `/adlocalizer`). As features migrate, expose new React views by extending `src/pages` and wiring them in `src/routes/AppRoutes.tsx`.
