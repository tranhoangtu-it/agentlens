# Phase 4 — Dashboard Auth UI

## Context Links
- [App.tsx](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/dashboard/src/App.tsx) — hash router, sidebar layout
- [api-client.ts](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/dashboard/src/lib/api-client.ts) — fetch wrappers, BASE url
- [alert-api-client.ts](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/dashboard/src/lib/alert-api-client.ts) — second API client pattern
- [package.json](/Users/tranhoangtu/Desktop/PET/my-project/agentlens/dashboard/package.json) — current deps (no auth libs)
- [Phase 2](phase-02-auth-middleware.md) — login/register endpoints

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: Login page, auth context/state management, protected route wrapper, token-attached fetches, logout, API key management page

## Key Insights
- App uses hash-based routing (`#/traces/...`), no react-router
- All fetch calls go through `api-client.ts` and `alert-api-client.ts` — single place to attach `Authorization` header
- No state management lib — React useState/useContext is sufficient
- Lucide icons already available (use `LogIn`, `LogOut`, `Key`, `User` icons)
- Radix UI primitives available for dialogs/inputs
- Zero new npm dependencies needed — JWT decode not required client-side (server validates)

## Architecture

### Auth State Flow
```
App mount
  → check localStorage for token
    → if token: GET /api/auth/me
      → success: set user state, render app
      → 401: clear token, show login
    → if no token: show login page

Login
  → POST /api/auth/login { email, password }
  → store token in localStorage
  → set user state
  → redirect to #/

Logout
  → clear localStorage token
  → clear user state
  → show login page
```

### Component Tree
```
App.tsx
├── AuthProvider (context)
│   ├── LoginPage (no auth required)
│   └── AuthenticatedApp (requires auth)
│       ├── Sidebar (with user menu + logout)
│       ├── TracesListPage
│       ├── TraceDetailPage
│       ├── ...existing pages...
│       └── ApiKeysPage (new)
```

### Token Storage
- `localStorage.setItem("agentlens_token", token)`
- Cleared on logout or 401 response
- Attached to every fetch via `Authorization: Bearer <token>`

## Related Code Files

### Files to Create
1. `dashboard/src/lib/auth-context.tsx` — AuthContext, AuthProvider, useAuth hook (~80 lines)
2. `dashboard/src/lib/auth-api-client.ts` — login, register, me, api-keys fetch wrappers (~70 lines)
3. `dashboard/src/pages/login-page.tsx` — email/password form (~100 lines)
4. `dashboard/src/pages/api-keys-page.tsx` — list/create/delete API keys (~120 lines)
5. `dashboard/src/lib/fetch-with-auth.ts` — wrapper that attaches Bearer token + handles 401 (~40 lines)

### Files to Modify
1. `dashboard/src/App.tsx` — wrap in AuthProvider, add login route, add API Keys nav item, add user menu in sidebar footer
2. `dashboard/src/lib/api-client.ts` — use `fetchWithAuth` instead of raw `fetch`
3. `dashboard/src/lib/alert-api-client.ts` — use `fetchWithAuth` instead of raw `fetch`

## Implementation Steps

1. **Create `dashboard/src/lib/fetch-with-auth.ts`**
   ```typescript
   const TOKEN_KEY = "agentlens_token"

   export function getToken(): string | null {
     return localStorage.getItem(TOKEN_KEY)
   }

   export function setToken(token: string): void {
     localStorage.setItem(TOKEN_KEY, token)
   }

   export function clearToken(): void {
     localStorage.removeItem(TOKEN_KEY)
   }

   export async function fetchWithAuth(url: string, init?: RequestInit): Promise<Response> {
     const token = getToken()
     const headers = new Headers(init?.headers)
     if (token) headers.set("Authorization", `Bearer ${token}`)
     const res = await fetch(url, { ...init, headers })
     if (res.status === 401) {
       clearToken()
       window.location.hash = "#/login"
     }
     return res
   }
   ```

2. **Create `dashboard/src/lib/auth-api-client.ts`**
   - `login(email, password)` → POST /api/auth/login → returns `{ access_token, user }`
   - `register(email, password, display_name)` → POST /api/auth/register
   - `fetchMe()` → GET /api/auth/me → returns user
   - `createApiKey(name)` → POST /api/auth/api-keys
   - `fetchApiKeys()` → GET /api/auth/api-keys
   - `deleteApiKey(id)` → DELETE /api/auth/api-keys/{id}

3. **Create `dashboard/src/lib/auth-context.tsx`**
   ```typescript
   interface AuthState {
     user: User | null
     loading: boolean
     login: (email: string, password: string) => Promise<void>
     logout: () => void
   }

   const AuthContext = createContext<AuthState>(...)

   export function AuthProvider({ children }) {
     // On mount: check token, call fetchMe()
     // Expose: user, loading, login, logout
   }

   export function useAuth() { return useContext(AuthContext) }
   ```

4. **Create `dashboard/src/pages/login-page.tsx`**
   - Centered card with AgentLens logo
   - Email + password inputs (use existing `<Input>` component)
   - "Sign In" button
   - Error message display
   - Clean, minimal design matching existing dark theme

5. **Create `dashboard/src/pages/api-keys-page.tsx`**
   - List existing keys (prefix, name, created_at, last_used_at)
   - "Create Key" button → name input → shows full key once with copy button
   - Delete key with confirmation
   - Route: `#/api-keys`

6. **Update `dashboard/src/App.tsx`**
   - Wrap root in `<AuthProvider>`
   - Add route: `{ name: 'login' }` and `{ name: 'api-keys' }`
   - If `!user && !loading` → render `<LoginPage />`
   - Add `Key` icon nav item for API Keys
   - Replace footer version with user email + logout button

7. **Update `dashboard/src/lib/api-client.ts`**
   - Replace `fetch(url)` with `fetchWithAuth(url)` in all functions
   - Import from `./fetch-with-auth`

8. **Update `dashboard/src/lib/alert-api-client.ts`**
   - Same: replace `fetch` with `fetchWithAuth`

## Todo List
- [ ] Create fetch-with-auth.ts utility
- [ ] Create auth-api-client.ts with login/register/me/api-keys
- [ ] Create auth-context.tsx with AuthProvider + useAuth
- [ ] Create login-page.tsx with form UI
- [ ] Create api-keys-page.tsx with list/create/delete
- [ ] Update App.tsx with AuthProvider, login route, api-keys nav
- [ ] Update api-client.ts to use fetchWithAuth
- [ ] Update alert-api-client.ts to use fetchWithAuth
- [ ] Test: login → see traces → logout → redirected to login

## Success Criteria
- Unauthenticated users see only the login page
- Login with valid credentials shows dashboard
- Invalid credentials show error message
- Token persists across page reloads (localStorage)
- 401 response auto-redirects to login
- API keys page: create shows full key once, list shows prefixes
- Logout clears token and returns to login

## Risk Assessment
- **Token in localStorage**: vulnerable to XSS. Acceptable for self-hosted v1. CSP headers can mitigate.
- **No token refresh**: user must re-login after 24h. Document in UI ("Session expires in 24h").
- **Backward compat**: if server has no auth (old version), fetchWithAuth still works (no token sent, server ignores header).

## Security Considerations
- Never display full API key after creation — show once, then only prefix
- Clear token from localStorage on logout
- Auto-redirect on 401 prevents stale token usage
- HTTPS recommended for production (document in deployment guide)
