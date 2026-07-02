# ScholarSync — Security Issues Found & Fixed (Beginner-Friendly Guide)

**Date:** 2026-06-30
**Audited by:** End-to-end code review of the FastAPI backend, Next.js frontend, dependencies, and configuration.
**Companion doc:** [PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md) (Section 7 — Security Measures)

---

## How to read this document

This guide is written so that **anyone** — even if you have never done security work — can understand:

1. **What was wrong** (the problem, in plain English)
2. **Why it was dangerous** (what a bad person could do)
3. **How we fixed it** (what code changed)
4. **A tiny example** (before vs after)

> Think of the app like a **school building**. Security issues are like **unlocked doors, master keys taped to the wall, or signs that reveal where the safe is**. We went around and locked every door, hid the keys, and removed the signs.

---

## Malware / virus check — result: CLEAN ✅

We scanned all dependencies (`requirements.txt`, every `package.json`, `pnpm-lock.yaml`) and the source code for:

- Typo-squatted or fake packages (e.g. a package pretending to be a real one)
- Hidden install scripts (`postinstall`, `preinstall`) that run code when you install
- `curl | bash`, `eval()`, or base64-decoded code that secretly executes
- Suspicious package registries

**Nothing malicious was found.** All libraries are well-known and legitimate (Clerk, Next.js, FastAPI, etc.). The only base64 in the repo is inside **test fixtures**, which is normal and harmless.

So this document is about **security weaknesses we fixed**, not malware.

---

## Summary table of everything we fixed

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Login tokens were accepted **without checking the signature** | 🔴 Critical | ✅ Fixed |
| 2 | Admin password & secret key were **hardcoded defaults** (`admin123`) | 🔴 Critical | ✅ Fixed |
| 3 | Admin login had **no brute-force protection** + plaintext password compare | 🔴 Critical | ✅ Fixed |
| 4 | Teacher login password was **inside the browser code** + fake token | 🔴 Critical | ✅ Fixed |
| 5 | Error messages **leaked internal details** (API keys, database structure) | 🟠 High | ✅ Fixed |
| 6 | No **security headers** (clickjacking, HTTPS, sniffing protection) | 🟠 High | ✅ Fixed |
| 7 | A health endpoint **leaked internal configuration** to the public | 🟡 Medium | ✅ Fixed |
| 8 | Logs printed user IDs and raw errors (**no redaction**) | 🟡 Medium | ✅ Fixed |
| 9 | Some dependencies had **known security bugs (CVEs)** | 🟠 High | ✅ Fixed |
| 10 | A leftover secrets file (`.env.bak`) and `.env.example` exposed defaults | 🟠 High | ✅ Fixed |
| 11 | No **startup safety check** to block insecure production launches | 🟠 High | ✅ Added |

---

# The details

---

## 🔴 Issue #1 — Login tokens were accepted without verifying the signature

**File:** `apps/api/middleware/auth.py`

### What was wrong (plain English)
When a student logs in, the app gives them a **token** — like a wristband at an event that proves "I paid to get in." Every time they ask the server for something, they show the wristband.

The old code had a rule like this:

> "If we have the official stamp machine configured, check that the wristband is real. **Otherwise, just trust whatever wristband they show.**"

And the stamp machine (`CLERK_JWT_PUBLIC_KEY`) was **empty**. So the app trusted **any** wristband — even a fake one drawn with a marker.

### Why it was dangerous
A hacker could **make their own token** that says *"I am the admin"* and the server would believe them. That is a full **login bypass + admin takeover**.

### How we fixed it
We made verification **fail-closed**, meaning: *if we cannot verify a token, we reject it* (never "just trust it"). We now verify tokens using Clerk's **JWKS** (an online list of official stamp patterns), which is the modern, recommended way.

The "trust without checking" path now **only** exists on a developer's local laptop when nothing is configured, and it prints a loud warning. In production it is **impossible**.

### Tiny example

**Before (dangerous):**
```python
if require_verification and settings.CLERK_JWT_PUBLIC_KEY:
    payload = jwt.decode(token, key, options={"verify_signature": True})
else:
    # ⚠️ Trust ANY token, no checking
    payload = jwt.decode(token, key="", options={"verify_signature": False})
```

**After (safe):**
```python
# Verify against Clerk's JWKS or public key. Expiry is always checked.
if settings.CLERK_JWKS_URL:
    key = find_matching_key(token)           # official stamp
    return jwt.decode(token, key, algorithms=["RS256"], options={"verify_signature": True})

# No key configured? Refuse in production / when verification is required.
if require_verification or settings.ENVIRONMENT == "production":
    raise HTTPException(status_code=401, detail="Authentication is not configured")
```

---

## 🔴 Issue #2 — Admin password and secret key were hardcoded defaults

**Files:** `config/settings.py`, `.env.example`

### What was wrong
The admin password was set to `admin123`, and the secret used to **sign admin tokens** was `dev-admin-portal-secret-change-in-production`. These values were written **right in the code** and in the example config.

### Why it was dangerous
Two problems:
1. `admin123` is one of the **first passwords** any attacker tries.
2. Because the **signing secret** was publicly known, a hacker could **forge a valid admin token at home** without ever logging in — like printing your own VIP wristband because everyone knows the stamp.

### How we fixed it
- The defaults are now clearly marked **"development only."**
- We added a **startup check** (Issue #11) that **refuses to start** the production server if these default values are still used.
- We removed the real default values from `.env.example` and replaced them with safe placeholders plus instructions on how to generate strong ones.

### Tiny example
**Generate a strong secret and password hash:**
```bash
# Strong random secret (48 chars)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Bcrypt hash of your real password (store this, NOT the plaintext)
python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt()).decode())"
```
Then in production you set `ADMIN_PORTAL_PASSWORD_HASH=<the hash>` and `ADMIN_PORTAL_JWT_SECRET=<the random secret>`.

---

## 🔴 Issue #3 — Admin login had no brute-force protection + plaintext compare

**Files:** `apps/api/routes/admin.py`, `apps/api/middleware/login_guard.py` (new)

### What was wrong
1. The login compared passwords like `if password != settings.ADMIN_PORTAL_PASSWORD`. This is **plaintext** (the real password sits in memory) and the comparison speed can secretly leak hints about the password (a "timing attack").
2. There was **no limit** on login attempts. A hacker could try **millions of passwords** as fast as the server allows.

### Why it was dangerous
Unlimited guessing = the attacker eventually guesses the password. This is called a **brute-force attack**.

### How we fixed it
- **Constant-time comparison:** we use `hmac.compare_digest` and **bcrypt** (a one-way password hash), so the comparison reveals nothing and the real password is never stored.
- **Rate limiting + lockout:** we created a small guard (`login_guard.py`). After **7 failed attempts** from the same IP+email within 5 minutes, that person is **locked out for 15 minutes** and gets HTTP `429 Too Many Requests`.

### Tiny example
**Before:**
```python
if email != expected_email or password != settings.ADMIN_PORTAL_PASSWORD:
    raise HTTPException(401, "Invalid email or password")
```

**After:**
```python
check_login_allowed("admin", request, email)        # 429 if locked out
email_ok = hmac.compare_digest(email, expected_email)
password_ok = verify_portal_password(password, ADMIN_PORTAL_PASSWORD, ADMIN_PORTAL_PASSWORD_HASH)
if not (email_ok and password_ok):
    record_failure("admin", request, email)          # count the failure
    raise HTTPException(401, "Invalid email or password")
record_success("admin", request, email)              # clear the counter
```

> **Real-world analogy:** like a phone that locks for a while after too many wrong passcodes.

---

## 🔴 Issue #4 — Teacher login password lived in the browser + fake token

**Files:** `apps/web/src/lib/teacher-auth.ts`, `apps/web/src/app/teacher/login/page.tsx`, `apps/api/routes/teacher_auth.py` (new)

### What was wrong
The teacher password (`admin123`) was written **inside the website's JavaScript**, which **every visitor can read** (right-click → View Source). Worse, after "logging in," the app stored a fixed text `"teacher-portal-session"` as the session. Anyone could open browser DevTools and type one line to **fake being a teacher** — no password needed.

### Why it was dangerous
The teacher portal had **no real lock at all**. The password was public, and the "key" was a word anyone could copy.

### How we fixed it
- We moved the password check to the **backend** (server side), where visitors **cannot see it**, in a new endpoint `POST /api/v1/teacher/auth/login`.
- The server now returns a **real signed token** (a JWT, like the student tokens) instead of a fixed word.
- We **deleted the password** from the browser code entirely.
- The login uses the **same rate limiting and bcrypt** protections as the admin portal.

### Tiny example
**Before (in browser code, visible to everyone):**
```typescript
export const TEACHER_PORTAL_PASSWORD = 'admin123';   // ⚠️ public!
function validateTeacherLogin(email, password) {
  return password === TEACHER_PORTAL_PASSWORD;        // checked in the browser
}
// ...later: setTeacherToken('teacher-portal-session'); // ⚠️ fake, guessable
```

**After (browser asks the server):**
```typescript
// No password in the browser anymore. The server checks it.
const token = await apiClient.teacherLogin(email, password); // real signed JWT
setTeacherToken(token);
```

> **Note (honest limitation):** the teacher *page* still checks "do I have a token?" in the browser. This is a known, accepted MVP trade-off documented in the deployment guide. The big wins — no public password and a real signed token — are done. A full server-side gate on every teacher API call is the recommended next step.

---

## 🟠 Issue #5 — Error messages leaked internal secrets

**Files:** `apps/api/routes/*.py`, `apps/api/utils/safe_errors.py` (new), `apps/api/main.py`, `apps/api/middleware/tenant.py`

### What was wrong
When something broke, the server often sent the **raw error text** back to the user. Those messages sometimes contained:

- Hints about **API keys** ("Please check your API keys in the backend .env file")
- **Database structure** ("the `feedback` column is missing... run: ALTER TABLE messages...")
- Internal file paths and library details

### Why it was dangerous
Error messages are like a **map for attackers**. Telling them your database table names, or that an API key is misconfigured, helps them plan an attack. This is called **information disclosure**.

### How we fixed it
We created one helper, `safe_detail()`. It does two things:
1. **Always logs the full error on the server** (so developers can still debug).
2. **Only shows a generic message to the user in production** (e.g., "Failed to load chat"), while still showing detail on a developer's laptop.

We applied this to the risky spots in chat, studio, notes, sources, tutor, problem-solver, admin routes, the global error handler, and the tenant middleware.

### Tiny example
**Before:**
```python
raise HTTPException(500, detail=f"Failed to get chat: {str(e)}")
# user might see: "...column messages.feedback does not exist..."
```

**After:**
```python
raise HTTPException(500, detail=safe_detail(e, "Failed to get chat"))
# production user sees: "Failed to get chat"
# server log still has the full error + traceback
```

---

## 🟠 Issue #6 — Missing security headers

**Files:** `apps/api/middleware/security_headers.py` (new), `apps/api/main.py`, `apps/web/next.config.js`

### What was wrong
The app sent no **security headers**. Headers are little instructions the server gives the browser, like "don't let other sites put my page inside theirs."

### Why it was dangerous
Without them, the app was open to:
- **Clickjacking** — an attacker hides your page inside an invisible frame and tricks users into clicking things.
- **MIME sniffing** — the browser guessing file types in unsafe ways.
- **Downgrade to HTTP** — using insecure connections.

### How we fixed it
We now send these headers on **both** the API and the website:

| Header | What it does (simple) |
|--------|------------------------|
| `X-Frame-Options: DENY` | "No one can put my page in a frame" (stops clickjacking) |
| `X-Content-Type-Options: nosniff` | "Don't guess file types" |
| `Referrer-Policy` | "Don't leak the full URL to other sites" |
| `Permissions-Policy` | "Block camera, microphone, location" |
| `Content-Security-Policy: frame-ancestors 'none'` | Extra anti-framing protection |
| `Strict-Transport-Security` (production) | "Always use HTTPS" |

We also turned off `X-Powered-By` so the site no longer advertises which framework it uses.

> We intentionally kept the Content-Security-Policy **minimal (anti-framing only)** for now, because a stricter CSP can accidentally break Clerk login widgets and math rendering. Tightening it further is a safe follow-up once every allowed source is listed.

---

## 🟡 Issue #7 — A health endpoint leaked internal configuration

**File:** `apps/api/routes/health.py`

### What was wrong
The endpoint `/health/langsmith` was **public** (no login needed) and returned internal details: the project name, the monitoring endpoint, connectivity status, and even **raw error text** if something failed.

### Why it was dangerous
It quietly told strangers about your internal tooling and configuration — more **free reconnaissance** for attackers.

### How we fixed it
- In **production**, this endpoint now returns **404 Not Found** (it simply doesn't exist to the public).
- It still works on a developer's machine for debugging.
- The raw error text is no longer returned; it is logged on the server instead.
- The basic `/health` (which just says `{"status": "ok"}`) stays public so load balancers can check the app is alive — that one reveals nothing sensitive.

---

## 🟡 Issue #8 — Logs printed user IDs and raw errors

**File:** `apps/api/middleware/tenant.py`

### What was wrong
The middleware used `print()` everywhere, dumping full **user IDs** and raw error messages into the logs on every request.

### Why it was dangerous
Logs are often stored and shared. Putting personal identifiers and internal errors in them is a **privacy and information-leak** risk.

### How we fixed it
- Switched from `print()` to proper **structured logging**.
- Added a `_redact()` helper so user IDs appear like `user…`**`a9`** instead of the full value.
- Stopped returning raw errors to clients from the middleware (returns a generic "Internal Server Error").

### Tiny example
**Before:**
```python
print(f"[SUCCESS] Authenticated user: {user_id}")   # full ID in logs
```
**After:**
```python
logger.info("Authenticated user: %s", _redact(user_id))  # e.g. "user…a9"
```

---

## 🟠 Issue #9 — Dependencies with known security bugs (CVEs)

**File:** `requirements.txt`

### What was wrong
Some Python libraries were old versions with publicly known security bugs (called **CVEs** — like a recall notice for software).

### Why it was dangerous
Attackers actively scan for apps using vulnerable library versions, because the exploit is already public.

### How we fixed it
We upgraded to patched versions:

| Library | Old | New | Why |
|---------|-----|-----|-----|
| `python-multipart` | 0.0.6 | **0.0.18** | Fixes CVE-2024-24762 (a denial-of-service via malformed upload headers) |
| `python-jose` | 3.3.0 | **3.4.0** | Fixes CVE-2024-33663 / CVE-2024-33664 (token algorithm confusion & DoS) |
| `jinja2` | 3.1.3 | **3.1.6** | Fixes template sandbox CVEs |
| `bcrypt` | (implicit) | **>=4.1,<5** | Pinned for reliable password hashing |

> **Recommended follow-up (not auto-applied to avoid breaking the build):** upgrade the frontend `next` from `14.1.0` to the latest patched `14.2.x` to pick up Next.js security advisories (including the middleware-bypass fix). Do this with `pnpm up next@14.2.x` and re-run the build.

---

## 🟠 Issue #10 — Leftover secrets file and exposed example defaults

**Files:** `.env.bak` (deleted), `.env.example`

### What was wrong
- A backup file `.env.bak` existed on disk containing **real API keys and database passwords**.
- `.env.example` showed real-looking default credentials (`admin123`, the dev secret).

### Why it was dangerous
Backup files are easy to forget and accidentally share. Example files that contain real defaults encourage people to ship those weak values to production.

### How we fixed it
- **Deleted `.env.bak`.**
- **Rewrote `.env.example`** to use safe placeholders and added commands showing how to generate strong secrets.

### ✅ Good news from our git history check
We verified that **`.env`, `.env.bak`, and `apps/web/.env.local` were never committed to git** (only the safe `.env.example` is tracked, and `.gitignore` already blocks the secret files). So the live keys are not in your repository history.

### ⚠️ Action still required from you
The real keys **were sitting on disk in `.env` / `.env.bak`**. To be safe you should **rotate (regenerate) them**, because they may have been copied or shared at some point:
- OpenAI, Anthropic, DeepSeek, Gemini, Cohere keys
- Pinecone key
- Supabase database password + service-role key
- Clerk secret key
- LangSmith key

Rotating a key means: create a new one in the provider's dashboard, paste it into your secret manager, and delete the old one.

---

## 🟠 Issue #11 — No startup safety check (NEW protection added)

**File:** `config/settings.py` → `validate_production_security()`, called from `apps/api/main.py`

### What we added
A **safety inspector** that runs the moment the production server starts. If anything insecure is detected, the server **refuses to start** and prints exactly what to fix. It checks:

1. Student token verification is configured (`CLERK_JWKS_URL` or `CLERK_JWT_PUBLIC_KEY`).
2. Admin secret is strong and not the default.
3. Admin password is strong or a bcrypt hash is set.
4. Teacher secret is strong and not the default.
5. Teacher password is strong or a bcrypt hash is set.
6. `CORS_ORIGINS` is an explicit list (no `*`).

### Why this matters
It makes it **impossible to accidentally launch with insecure settings**. Like a car that won't start until everyone's seatbelt is on.

### Proof it works
When we tested it with the old default values and `ENVIRONMENT=production`, the server correctly refused to start with:
```
Insecure production configuration detected. Fix these before launch:
  - ADMIN_PORTAL_JWT_SECRET must be a strong, non-default value (>= 32 chars).
  - Set ADMIN_PORTAL_PASSWORD_HASH (bcrypt) or a strong ADMIN_PORTAL_PASSWORD (>= 10 chars).
  - TEACHER_PORTAL_JWT_SECRET must be a strong, non-default value (>= 32 chars).
  - ...
```
With strong values, it started normally. ✅

---

# Files we created or changed

### New files
| File | Purpose |
|------|---------|
| `apps/api/middleware/login_guard.py` | Brute-force protection (rate limit + lockout) for logins |
| `apps/api/middleware/security_headers.py` | Adds security headers to every API response |
| `apps/api/routes/teacher_auth.py` | Server-side teacher login (replaces the browser password) |
| `apps/api/utils/safe_errors.py` | Returns generic errors to users, full detail to logs |
| `docs/SECURITY_FIXES.md` | This document |

### Changed files
| File | What changed |
|------|--------------|
| `apps/api/middleware/auth.py` | Fail-closed JWT verification (JWKS), bcrypt password helpers, teacher tokens |
| `apps/api/middleware/tenant.py` | Recognizes teacher token, redacted logging, no error leaks |
| `apps/api/routes/admin.py` | Rate-limited login + constant-time bcrypt compare; safe errors |
| `apps/api/routes/chat.py` | Sanitized error messages (HTTP + streaming) |
| `apps/api/routes/studio.py` | Stopped leaking API-key/config text in errors |
| `apps/api/routes/notes.py` `sources.py` `tutor.py` `problem_solver.py` | Sanitized error messages |
| `apps/api/routes/health.py` | `/health/langsmith` disabled in production; no raw errors |
| `apps/api/main.py` | Startup security validation, security headers, safe global errors |
| `config/settings.py` | New secure settings + `validate_production_security()` |
| `apps/web/next.config.js` | Security headers + removed `X-Powered-By` |
| `apps/web/src/lib/teacher-auth.ts` | Removed the hardcoded password |
| `apps/web/src/app/teacher/login/page.tsx` | Logs in via the backend |
| `apps/web/src/lib/api-client.ts` | Added `teacherLogin()` |
| `requirements.txt` | Upgraded vulnerable libraries |
| `.env.example` | Removed weak defaults; added secret-generation instructions |
| `.env.bak` | **Deleted** (contained live secrets) |

---

# Your action checklist before production

- [ ] **Rotate every API key / password** that was in `.env` and `.env.bak` (see Issue #10).
- [ ] Set a strong `ADMIN_PORTAL_JWT_SECRET` and `TEACHER_PORTAL_JWT_SECRET` (48-char random).
- [ ] Set `ADMIN_PORTAL_PASSWORD_HASH` and `TEACHER_PORTAL_PASSWORD_HASH` (bcrypt), or strong plaintext passwords.
- [ ] Set `CLERK_JWKS_URL` (or `CLERK_JWT_PUBLIC_KEY`) so student tokens are verified.
- [ ] Set `ENVIRONMENT=production` and an explicit `CORS_ORIGINS` (no `*`).
- [ ] Run `pip install -r requirements.txt` to pick up the security upgrades.
- [ ] (Recommended) Upgrade `next` to the latest `14.2.x` and re-run the build.
- [ ] Start the API once — the new startup check will confirm your config is safe.

---

# What was verified

- ✅ All changed Python files **compile** cleanly.
- ✅ The security modules **import and run** (password hashing, verification, login guard).
- ✅ The startup validator **rejects** insecure defaults and **accepts** strong config (tested both).
- ✅ Changed frontend files have **no linter errors**.
- ✅ Dev login still works (defaults are allowed in development only).

Nothing in the normal app flow was broken: development still uses friendly defaults, while production is now locked down and fails safely if misconfigured.

---

# Appendix — How rate limiting was implemented (honest end-to-end analysis)

> **Short answer:** Rate limiting is implemented and **works correctly for a single-instance MVP** (which is exactly the deployment described in the production guide: one Render instance). It is **NOT yet "perfect end-to-end"** for a large, multi-server deployment. Below is a complete, honest breakdown of what exists, what is solid, and what is still missing.

## 1. What "rate limiting" means here

Rate limiting = **putting a speed limit on how often someone can call an endpoint**. We use it for two different purposes in this app:

| Purpose | Where | Why |
|---------|-------|-----|
| **Brute-force protection** on logins | `apps/api/middleware/login_guard.py` (new) | Stop attackers guessing passwords millions of times |
| **Abuse/cost protection** on chat | `packages/core/memory/rate_limiter.py` (pre-existing) | Stop one user spamming the expensive LLM |

## 2. How the login guard works (step by step)

**File:** `apps/api/middleware/login_guard.py`

Imagine a **bouncer with a notepad**. For every failed login he writes down *"this IP + this email failed at this time."* The logic:

1. **Before checking the password** → `check_login_allowed()` asks: *"Is this person currently locked out?"* If yes → reply `429 Too Many Requests` with a `Retry-After` header.
2. **On a wrong password** → `record_failure()` adds a timestamp. It only keeps timestamps from the last **5 minutes** (a "sliding window"). If there are **7 or more** failures in that window → **lock the person out for 15 minutes.**
3. **On a correct password** → `record_success()` tears the page out of the notepad (clears the counter).

The "who" is identified by a **key = `scope : IP : email`** (e.g. `admin:203.0.113.4:ops@school.com`). The numbers are configurable in `config/settings.py`:

```python
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 7        # failures allowed
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 300    # within 5 minutes
LOGIN_RATE_LIMIT_LOCKOUT_SECONDS = 900   # then locked for 15 minutes
```

A `threading.Lock` makes the notepad safe when many requests arrive at once.

### Tiny example of the flow
```
Attacker tries admin login with wrong password...
  attempt 1..6  → 401 "Invalid email or password"
  attempt 7     → now locked
  attempt 8     → 429 "Too many failed login attempts. Please try again later." (Retry-After: 900)
...15 minutes later → can try again
```

## 3. Where it is applied (coverage)

| Endpoint | Brute-force / abuse limit? | How |
|----------|----------------------------|-----|
| `POST /api/v1/admin/auth/login` | ✅ Yes | `login_guard` |
| `POST /api/v1/teacher/auth/login` | ✅ Yes | `login_guard` |
| `POST /api/v1/chat/...` (LLM stream) | ✅ Yes | existing in-memory `rate_limiter` (30 req/min/user) |
| `POST /api/v1/ingest/upload` (file upload) | ❌ No | — |
| `POST /api/v1/admin/ncert-global/...` (NCERT upload) | ❌ No | — |
| `POST /api/v1/problem-solver/...` | ❌ No | — |

So the **most critical** path (login password guessing) and the **most expensive** path (chat) are covered. Bulk-upload endpoints are **not** yet rate limited.

## 4. Is it "done end-to-end perfectly"? — No. Here is the honest verdict.

✅ **What is genuinely solid:**
- Correct sliding-window + lockout logic, thread-safe.
- Generic 401 message (doesn't reveal which field was wrong) + proper `429` + `Retry-After`.
- Configurable thresholds; clears on success.
- Verified to import and run.

⚠️ **What is NOT perfect (real limitations):**

1. **In-memory / per-process (biggest gap).** The notepad lives inside one Python process. If you run **multiple workers or multiple servers** (e.g. `uvicorn --workers 4`, or 2+ Render instances), **each one has its own separate notepad.** An attacker spread across them effectively multiplies the allowed attempts. → **Fix: store counters in Redis/Upstash** so all instances share one notepad. This is already noted in `PRODUCTION_DEPLOYMENT_GUIDE.md` §7.2.
2. **Resets on restart.** A deploy or crash wipes the counters and any active lockout.
3. **IP can be spoofed if not behind a trusted proxy.** We read the first IP in `X-Forwarded-For`. Behind Render/Vercel/Cloudflare this is fine, but if the app is ever exposed directly, a client could fake this header. → **Fix: only trust `X-Forwarded-For` from known proxy IPs.**
4. **Distributed attacks aren't stopped.** The key includes the IP, so an attacker using **thousands of different IPs** (a botnet) gets 7 tries *per IP*. → **Fix: add a second, account-only limit (per email regardless of IP) and/or a global limit; a WAF/Cloudflare rule helps too.**
5. **Coverage gaps.** Upload endpoints have no per-user limit, so a logged-in user could spam uploads. → **Fix: add `login_guard`-style or Redis limits there.**
6. **Unbounded memory (minor).** Old entries are never garbage-collected, so the dictionary slowly grows. Not dangerous at MVP scale, but a cleanup/expiry pass (or Redis TTLs) would be cleaner.
7. **Two separate systems.** Logins use `login_guard`; chat uses the older `rate_limiter`. They work, but a single shared limiter would be tidier.

## 5. Verdict & recommendation

- **For the current MVP (one always-on Render instance, 150–300 students):** the implementation is **appropriate and effective** — login brute-force and chat abuse are both blocked.
- **To call it "perfect end-to-end" / production-grade at scale:** move both limiters to **Redis (Upstash)**, trust `X-Forwarded-For` only from your proxy, add account-level + global limits, and extend coverage to upload endpoints. None of these are blockers for the closed beta; they are the clear next step before a wider rollout.

In one line: **the speed limit is installed and works on this one road; to police a whole highway network you need the shared (Redis) version.**
