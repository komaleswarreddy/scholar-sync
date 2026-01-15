# Authentication Details Documentation

**Project:** ScholarSync  
**Last Updated:** 2024  
**Version:** 2.0

---

## Overview

ScholarSync uses **Clerk** as the primary authentication provider for user management, session handling, and multi-tenancy support. The system implements a multi-tenant architecture where authentication is combined with tenant identification via subdomains.

---

## 1. Authentication Provider: Clerk

### 1.1. What is Clerk?
- **Purpose:** User authentication, session management, and multi-tenancy support
- **Type:** Third-party authentication service (SaaS)
- **Free Tier:** Up to 10,000 monthly active users
- **Documentation:** https://clerk.com/docs

### 1.2. Clerk Configuration

#### Frontend Configuration
- **Package:** `@clerk/nextjs` (version 5.0.0)
- **Environment Variables:**
  - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Public key for frontend (starts with `pk_test_` or `pk_live_`)
  - `CLERK_SECRET_KEY` - Secret key for backend verification (starts with `sk_test_` or `sk_live_`)

#### Backend Configuration
- **Environment Variable:**
  - `CLERK_SECRET_KEY` - Used for JWT token verification (starts with `sk_test_` or `sk_live_`)

### 1.3. Current Implementation Status

**Status:** ⚠️ **Partially Implemented / Development Mode**

- Authentication is **temporarily disabled** in development mode
- Clerk integration is set up but not fully enforced
- Frontend has Clerk components (`SignIn`, `SignUp`) ready
- Backend expects Clerk JWT tokens but has fallback for development

---

## 2. Frontend Authentication

### 2.1. Authentication Pages

#### Sign In Page
- **Location:** `apps/web/src/app/(auth)/sign-in/[[...sign-in]]/page.tsx`
- **Component:** Uses `<SignIn />` from `@clerk/nextjs`
- **Route:** `/sign-in`

#### Sign Up Page
- **Location:** `apps/web/src/app/(auth)/sign-up/[[...sign-up]]/page.tsx`
- **Component:** Uses `<SignUp />` from `@clerk/nextjs`
- **Route:** `/sign-up`

### 2.2. ClerkProvider Setup

**Location:** `apps/web/src/app/layout.tsx`

```typescript
const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
const isClerkConfigured = clerkKey && !clerkKey.includes('...');

if (isClerkConfigured) {
  return <ClerkProvider>{content}</ClerkProvider>;
}
```

**Behavior:**
- Only wraps app with `ClerkProvider` if Clerk keys are properly configured
- Falls back to non-authenticated mode if keys are missing or placeholder values

### 2.3. Home Page Authentication Check

**Location:** `apps/web/src/app/page.tsx`

**Current Status:** Authentication check is **commented out** for development:

```typescript
// Temporarily allow access without Clerk for development
// TODO: Re-enable authentication once Clerk keys are configured
// const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
// if (clerkKey && !clerkKey.includes('...')) {
//   const user = await currentUser();
//   if (!user) {
//     redirect('/sign-in');
//   }
// }
```

**Current Behavior:** Redirects directly to `/dashboard` without authentication check.

---

## 3. Backend Authentication

### 3.1. API Authentication Requirements

According to the API Specification (`4_API_Specification.md`):

**Required Headers:**
- `Authorization`: Bearer Token from Clerk (JWT)
  - Format: `Bearer <jwt_token>`
  - Used to identify the user (`user_id`)
- `X-Tenant-ID`: The subdomain string (e.g., `greenwood`)
  - Used to route to the correct DB schema/namespace

### 3.2. Current Backend Implementation

**Status:** ⚠️ **Development Mode with Fallback**

#### Token Extraction
- **Location:** `backend/app/api/v1/endpoints/chat.py`
- **Current Implementation:**
  ```python
  user_id = request.headers.get("X-User-ID")  # From Clerk JWT
  
  # For development: use default user if not provided
  if not user_id:
      if settings.ENVIRONMENT == "development":
          user_id = "dev-user-123"
      else:
          raise HTTPException(status_code=401, detail="User ID required")
  ```

**Note:** The backend currently expects `X-User-ID` header rather than extracting it from the JWT token. This is a **temporary development implementation**.

#### Expected Production Implementation
- Backend should verify Clerk JWT tokens using `CLERK_SECRET_KEY`
- Extract `user_id` from the verified JWT token payload
- Reject requests with invalid or missing tokens

### 3.3. API Client Authentication

**Location:** `packages/api/src/index.ts`

**Current Implementation:**
```typescript
setAuthToken(token: string) {
  this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}
```

**Status:** Method exists but is not automatically called. Frontend needs to:
1. Get token from Clerk session
2. Call `apiClient.setAuthToken(token)` after authentication

**Development Fallback:**
- Notes API uses hardcoded `'dev-user-123'` in `X-User-ID` header
- TODO comments indicate this should be replaced with actual Clerk user ID

---

## 4. Multi-Tenancy & Tenant Identification

### 4.1. Tenant Middleware

**Location:** `backend/app/core/middleware.py`

**How it Works:**
1. Extracts subdomain from `Host` header
2. Pattern: `{subdomain}.scholarsync.com` or `{subdomain}.localhost:3000`
3. Looks up tenant in database using subdomain
4. Injects `tenant_id` into `request.state` for all subsequent operations
5. For localhost (development), uses "default" tenant

**Development Behavior:**
- If no subdomain match and host is `localhost` or `127.0.0.1`:
  - Creates or uses "default" tenant
  - Sets `request.state.tenant_id` and `request.state.subdomain = "default"`

**Production Behavior:**
- Requires valid subdomain format
- Returns 404 if tenant not found for subdomain
- Returns 400 if subdomain format is invalid

### 4.2. Tenant Scoping

All database operations and vector searches are scoped to the tenant:
- Sources are tenant-specific
- Chats are tenant-specific
- Notes are tenant-specific
- Vector searches use tenant namespace in Pinecone

---

## 5. API Response Codes

### Authentication-Related Status Codes

- **200 OK**: Success (authenticated and authorized)
- **401 Unauthorized**: Missing or invalid Bearer token
- **403 Forbidden**: User does not belong to the Tenant specified in `X-Tenant-ID`
- **422 Validation Error**: Malformed JSON body (Pydantic validation failed)
- **429 Too Many Requests**: Rate limit exceeded per school/tenant

---

## 6. Environment Variables Summary

### Frontend (`.env.local`)
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...  # Optional for frontend
```

### Backend (`.env`)
```bash
CLERK_SECRET_KEY=sk_test_...
ENVIRONMENT=development  # or "production"
```

---

## 7. Security Considerations

### Current Security Status

⚠️ **Development Mode - Not Production Ready**

1. **Authentication Bypass:** Frontend authentication check is disabled
2. **Hardcoded User IDs:** Backend uses `"dev-user-123"` as fallback
3. **No JWT Verification:** Backend doesn't verify Clerk JWT tokens
4. **Missing Token Extraction:** Backend expects `X-User-ID` header instead of extracting from JWT

### Production Requirements

Before deploying to production:

1. ✅ **Enable Frontend Authentication:**
   - Uncomment authentication check in `page.tsx`
   - Ensure Clerk keys are properly configured

2. ✅ **Implement JWT Verification:**
   - Add Clerk JWT verification in backend middleware
   - Extract `user_id` from verified JWT token
   - Remove development fallbacks

3. ✅ **Update API Client:**
   - Automatically get token from Clerk session
   - Set token in API client after authentication
   - Remove hardcoded user IDs

4. ✅ **Add Authorization Checks:**
   - Verify user belongs to tenant
   - Implement role-based access control if needed

---

## 8. Getting Started with Clerk

### Setup Steps

1. **Create Clerk Account:**
   - Go to https://clerk.com
   - Sign up (free tier available)

2. **Create Application:**
   - Create a new application in Clerk dashboard
   - Choose authentication methods (email, OAuth, etc.)

3. **Get API Keys:**
   - Go to **API Keys** section
   - Copy **Publishable Key** (starts with `pk_test_`)
   - Copy **Secret Key** (starts with `sk_test_`)

4. **Configure Allowed Origins:**
   - Go to **Settings** → **Allowed Origins**
   - Add: `http://localhost:3000` (for development)
   - Add production domain when ready

5. **Add Keys to Environment:**
   - Frontend: Add to `.env.local`
   - Backend: Add to `.env`

6. **Test Authentication:**
   - Start the application
   - Navigate to `/sign-in` or `/sign-up`
   - Verify Clerk components render correctly

---

## 9. API Client Usage

### Setting Authentication Token

```typescript
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@scholarsync/api';

function MyComponent() {
  const { getToken } = useAuth();
  
  useEffect(() => {
    const setToken = async () => {
      const token = await getToken();
      if (token) {
        apiClient.setAuthToken(token);
      }
    };
    setToken();
  }, [getToken]);
  
  // ... rest of component
}
```

### Making Authenticated Requests

Once token is set, all API requests will include:
```
Authorization: Bearer <jwt_token>
```

---

## 10. Troubleshooting

### Common Issues

1. **Clerk Components Not Rendering:**
   - Check `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is set
   - Verify key doesn't contain placeholder values (`...`)
   - Check browser console for errors

2. **401 Unauthorized Errors:**
   - Verify `CLERK_SECRET_KEY` is set in backend
   - Check token is being sent in `Authorization` header
   - Ensure token hasn't expired

3. **403 Forbidden Errors:**
   - Verify user belongs to the tenant
   - Check `X-Tenant-ID` header matches user's tenant
   - Verify tenant exists in database

4. **Development Mode Issues:**
   - If using localhost, ensure "default" tenant exists
   - Check `ENVIRONMENT=development` is set in backend
   - Verify fallback user ID logic is working

---

## 11. Future Improvements

### Planned Enhancements

1. **Complete JWT Verification:**
   - Implement proper Clerk JWT verification in backend
   - Remove development fallbacks

2. **Automatic Token Management:**
   - Auto-refresh tokens when expired
   - Handle token refresh in API client

3. **Role-Based Access Control:**
   - Add user roles (admin, teacher, student)
   - Implement role-based permissions

4. **Multi-Factor Authentication:**
   - Enable MFA via Clerk
   - Support for various MFA methods

5. **Session Management:**
   - Implement proper session handling
   - Add session timeout and refresh logic

---

## 12. References

- **Clerk Documentation:** https://clerk.com/docs
- **API Specification:** `NotebookLM/4_API_Specification.md`
- **API Keys Guide:** `NotebookLM/API_KEYS_EXPLAINED.md`
- **Tech Stack:** `NotebookLM/3_Tech_Stack_Architecture.md`

---

**Note:** This documentation reflects the current state of the authentication implementation. As the system evolves, this document should be updated to reflect changes in authentication flow, security measures, and implementation details.
