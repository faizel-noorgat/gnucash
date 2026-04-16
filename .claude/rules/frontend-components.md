---
glob: "{frontend,admin}/src/components/**/*.{ts,tsx}"
---

# Frontend — React Component Rules

## Component Design
- One concern per component — a component handles either layout, data display, or user interaction, not multiple concerns
- No business logic in UI components — business logic lives in custom hooks or service functions in `lib/`
- Prefer function components — no class components
- Components must be self-contained — importing a component should not have side effects

## Props
- All props must be typed via TypeScript interfaces or types — no `any` or `unknown` without explicit handling
- Props use destructuring with default values in the function signature
- Use `children` prop for composition — do not use render props unless the pattern is required by a library
- Boolean props must default to `false` — never default to `true`

## State Management
- Local UI state (open/closed, input values, visibility) uses `useState` or `useReducer`
- Server state (API data, caching, background sync) uses React Query — never `useState` for server data
- Global client state (sidebar state, theme, offline queue) uses Zustand — not React Context
- Do not pass server state through props — use React Query hooks directly in components

## Event Handlers
- Event handlers named `handle<Event>` (e.g., `handleClick`, `handleSubmit`)
- Event handlers defined outside JSX via `const` declarations, not inline arrow functions where avoidable
- Form submissions use React Hook Form `handleSubmit` — never manual `onChange` state management

## Accessibility
- All interactive elements must be keyboard-accessible (Tab, Enter, Escape)
- Form inputs must have associated `<label>` elements or `aria-label` attributes
- Use shadcn/ui base components for accessibility — do not build custom dialogs, dropdowns, or modals from scratch
- Color contrast must meet WCAG AA minimum — do not rely on color alone for information

## shadcn/ui Usage
- Use shadcn/ui as the base component library — installed via CLI into `src/components/ui/`
- Do not modify shadcn/ui source files directly — wrap or extend via composition
- Radix UI primitives for complex interactions (ComboBox, DatePicker) — accessed via shadcn or directly

## Custom Accounting Components
- `SplitInput`, `AccountPicker`, `TransactionForm` are custom components — build these from shadcn primitives
- Custom components follow the same accessibility rules as shadcn components

## Sources
# Principles: [SRP (one component = one concern), Re-render Isolation (state changes must not cascade), Separation of Concerns]
# Web: https://react.dev/reference/react
# Web: https://ui.shadcn.com/docs
# Date: 2026-04-16