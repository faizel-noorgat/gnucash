---
glob: "{frontend,admin}/src/{stores,hooks}/**/*.{ts,tsx}"
---

# Frontend — State Management Rules

## React Query (Server State)
- All API interactions use React Query `useQuery` for reads, `useMutation` for writes
- Query keys follow the pattern: `['<resource>', <id>]` — e.g., `['account', accountId]`, `['transactions', { page: 1 }]`
- Mutation `onSuccess` callbacks must invalidate related queries via `queryClient.invalidateQueries` — never manually update cache unless for optimistic updates
- Mutations that create/update/delete a resource must invalidate the list and detail query keys for that resource
- Use `staleTime` to control refetch frequency — default `staleTime: 1000 * 60 * 5` (5 minutes) for list queries
- Paginated queries use `useInfiniteQuery` with `getNextPageParam` — not manual page tracking in state

## Zustand (Client State)
- Zustand stores live in `src/stores/` — one store per domain (e.g., `useOfflineStore`, `useUIStore`)
- Use the slices pattern for complex stores — each slice is a `StateCreator` function
- Selectors use `useShallow` for multi-property selection to prevent unnecessary re-renders
- Do not store server state in Zustand — use React Query for all API data
- Persist middleware only for offline queue and user preferences — not for session or auth state

## React Hook Form (Form State)
- All forms use React Hook Form — no manual `useState` for form field values
- Form validation via Zod schema passed to `useForm({ resolver: zodResolver(schema) })`
- Form submission via `handleSubmit` callback — never manual `onSubmit` with `preventDefault`
- Form state is local to the form component — do not lift form state to Zustand or React Query

## Offline Queue
- Offline mutations are queued in a Zustand store with `persist` middleware
- Each queued mutation stores the mutation function name, arguments, and timestamp
- On reconnect, mutations are replayed in order — conflicts prompt user resolution
- The sync queue is cleared only after server confirms all mutations

## Sources
# Principles: [Separation of Concerns (global server state vs local UI state), Cohesion (related state lives together)]
# Web: https://tanstack.com/query/latest/docs/framework/react/overview
# Web: https://zustand.docs.pmnd.rs/getting-started/introduction
# Web: https://react-hook-form.com/docs
# Date: 2026-04-16