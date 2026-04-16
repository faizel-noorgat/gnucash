---
glob: "{frontend,admin}/src/**/{page,layout,route}*.{ts,tsx}"
---

# Frontend — Page & Route Rules

## Routing
- Use React Router v6 for client-side routing — file-based route configuration in `src/App.tsx`
- Route paths match the design spec exactly (e.g., `/accounts/:id`, `/transactions/new`)
- Route component files named `src/routes/<route-name>.tsx` — one file per route
- Protected routes (all tenant routes) must check authentication before rendering — redirect to `/login` if unauthenticated

## Data Fetching
- All data fetching via React Query `useQuery` hooks — no `fetch` or `axios` calls in page components
- `useQuery` hooks called at the top level of page components — not inside conditionals
- Loading states rendered via a page-level skeleton or spinner — not per-component
- Error states rendered via a page-level error boundary or `useQuery` error state

## Page Composition
- Pages compose feature components from `src/features/` — pages are thin wrappers that pass props
- Pages do not contain business logic — they wire queries to components
- Shared layout (navigation, sidebar) is defined in a root layout component — not duplicated per page

## Admin Hub Pages
- Admin pages follow the same structure under `admin/src/routes/`
- Admin routes prefixed with `/admin/` — protected by admin-only authentication
- Admin pages use the same React Query client setup but with separate API base URL if needed

## Loading & Error States
- Every page must handle three states: loading, error, and success — no page renders only success
- Loading uses a skeleton matching the page layout — not a full-screen spinner for content pages
- Error displays a retry option — not just a static message

## PWA
- Service worker registered in `frontend/src/` — configured via Vite PWA plugin
- App shell (navigation, layout) cached via service worker — API responses are NOT cached by service worker
- Offline page rendered when network is unavailable — uses IndexedDB data via Zustand store

## Sources
# Principles: [Separation of Concerns (data fetching vs layout vs interaction), Dependency Direction (pages compose components, never the reverse)]
# Web: https://reactrouter.com/en/main
# Date: 2026-04-16