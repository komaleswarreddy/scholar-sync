# ScholarSync — Beginner UI Testing Checklist

**Purpose:** Test the product **only at the UI level**. Check that screens open, labels show, buttons work, and data **populates** (or correctly shows empty states). You do **not** need to read code or call APIs.

**Related guide:** [ScholarSync_IIL_Implementation_Guide.html](./ScholarSync_IIL_Implementation_Guide.html) (feedback tiers + IIL flywheel).

**How to use this file**

1. Start the app (`localhost:3000`) and API (`localhost:8000`).
2. Use one **school admin** account and at least one **student** account (created from admin).
3. For IIL feedback, also use accounts with expertise tier **teacher**, **tutor**, or **sme** (set in Admin → Roles & Permissions).
4. For every row, mark:
   - **Pass** — UI looks correct and data populates (or empty state is clear)
   - **Fail** — blank, wrong name, spinner forever, missing buttons, crash
   - **N/A** — feature not available for this role / not set up yet
5. In the **Populates?** column write: `Yes` / `No` / `Empty OK` (empty is fine when there is no data yet).

---

## Before you start

| Check | What you should see | Pass? | Populates? |
|-------|---------------------|-------|------------|
| Open `http://localhost:3000` | App loads (not a blank white page) | ☐ | |
| Open `http://localhost:8000/health` | Health OK (or API docs at `/api/docs`) | ☐ | |
| Sign-in page loads | ScholarSync branding, username, password, **Sign in** button | ☐ | |

**Accounts you need**

| Role | How to get it | Used for |
|------|---------------|----------|
| School admin | Bootstrap admin or account with role `schooladmin` | Admin portal, create users, curation |
| Student | Created in Admin → Roles & Permissions, tier `student` | Home, chat, basic feedback |
| Teacher (tier) | Same create form, expertise tier `teacher` | Extra feedback options |
| Tutor / SME (tier) | Expertise tier `tutor` or `sme` | Expert feedback options |

---

# Part A — Login, logout, and identity (all roles)

## A1. Sign in

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| A1.1 | Open `/sign-in` | Left hero text, feature list, form on the right | ☐ | |
| A1.2 | Wrong password | Red error message (not a blank hang) | ☐ | |
| A1.3 | Student login | Redirect to `/home` within a few seconds | ☐ | |
| A1.4 | Admin login | Redirect to `/admin/users` (or admin area) | ☐ | |
| A1.5 | After student login | Top-right avatar shows **initials** (not stuck on `U`) | ☐ | |
| A1.6 | After student login | Greeting uses **real name** (not only “Welcome back, there”) | ☐ | |
| A1.7 | Open profile menu once | Name + email/username visible **without** clicking Profile twice | ☐ | |

## A2. Sign out

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| A2.1 | Profile menu → Sign out | Lands on `/sign-in` | ☐ | |
| A2.2 | After sign out, open `/home` | Redirected to sign-in (cannot stay on home) | ☐ | |
| A2.3 | Sign in again | Identity and home load correctly again | ☐ | |

---

# Part B — Student portal (top navigation)

Test as a **student**. Click every top nav item. Navigation should feel quick; sidebar/header should not freeze.

## B1. Home (`/home`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B1.1 | Date line | e.g. day + week label | ☐ | |
| B1.2 | Welcome line | “Welcome back, **[First name]** …” | ☐ | |
| B1.3 | Continue card | Title “Continue”; subtitle notebook name **or** “No recent notebook yet” | ☐ | |
| B1.4 | Create Notebook | Opens create flow / popover | ☐ | |
| B1.5 | Focus this week | Focus topic **or** “Study a notebook to see your focus…” | ☐ | |
| B1.6 | Focus starter prompts (IIL Part 3) | If templates exist: prompt chips under focus; if not: empty is OK | ☐ | |
| B1.7 | Overview of learning | Four cards: Syllabus %, Tests, Strong concepts, Need attention (numbers can be 0) | ☐ | |
| B1.8 | Continue learning | Cards for notebooks **or** “Create new” empty state | ☐ | |
| B1.9 | View all library | Goes to Library | ☐ | |
| B1.10 | Class pill (top right) | Shows class (e.g. Class 12); click switches class if enabled | ☐ | |
| B1.11 | Notifications bell | Opens dropdown (may show sample/static items) | ☐ | |

## B2. Library (`/library`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B2.1 | Page header | Title + notebook counts (can be 0) | ☐ | |
| B2.2 | Search / filters | Controls visible and usable | ☐ | |
| B2.3 | Notebook grid | Cards with title/subject **or** “No notebooks yet” | ☐ | |
| B2.4 | Open a notebook card | Opens notebook workspace | ☐ | |
| B2.5 | New notebook action | Starts create flow | ☐ | |

## B3. Problem Solver (`/problem-solver`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B3.1 | Landing page | Loads without crash | ☐ | |
| B3.2 | Start / open a PS session | Chat or steps UI appears | ☐ | |
| B3.3 | Assistant messages | Text and layout readable | ☐ | |
| B3.4 | Feedback bar on PS assistant messages | Same feedback controls as chat (see Part D) | ☐ | |

## B4. Study Plan (`/study-planner`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B4.1 | Study plan list / calendar | Page loads | ☐ | |
| B4.2 | Plans list | Plans populate **or** clear empty state | ☐ | |
| B4.3 | Open a plan (`/study-planner/[planId]`) | Plan detail loads | ☐ | |

## B5. Analytics (`/analytics`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B5.1 | Analytics page | Loads | ☐ | |
| B5.2 | Charts / metrics | Numbers or empty placeholders (not infinite spinner) | ☐ | |

## B6. Assets (`/assets`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B6.1 | Assets page | Loads | ☐ | |
| B6.2 | Asset list | Items populate **or** empty state | ☐ | |

## B7. Notes (`/notes`) and Studios (`/studios`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B7.1 | Notes list | Notes populate **or** empty state | ☐ | |
| B7.2 | Studios list | Studio outputs populate **or** empty state | ☐ | |

## B8. Tutor entry (`/tutor`, `/tutor-mode`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| B8.1 | Tutor landing | Class / subject / chapter selectors populate | ☐ | |
| B8.2 | Start tutor notebook | Notebook opens in tutor mode | ☐ | |

## B9. Profile (`/profile/...`)

Open profile from the avatar menu. Check **every** section in the left menu:

| # | Section URL | What should populate / show | Pass? | Populates? |
|---|-------------|-----------------------------|-------|------------|
| B9.1 | `/profile/student-info` | Name, contact fields (saved values if set) | ☐ | |
| B9.2 | `/profile/academic-profile` | Class / board / stream fields | ☐ | |
| B9.3 | `/profile/exam-goals` | Goals form / content | ☐ | |
| B9.4 | `/profile/institute-info` | Institute fields | ☐ | |
| B9.5 | `/profile/current-plan` | Plan info or placeholder | ☐ | |
| B9.6 | `/profile/learning-preferences` | Preference controls | ☐ | |
| B9.7 | `/profile/notifications` | Notification toggles | ☐ | |
| B9.8 | `/profile/account-security` | Security / account controls | ☐ | |
| B9.9 | Save a field on student-info | Value still there after refresh | ☐ | |

---

# Part C — Notebook workspace (core study UI)

Create or open any notebook from Home or Library (`/notebook/[slug]`).

## C1. Layout and sources

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| C1.1 | Notebook title | Correct title in header | ☐ | |
| C1.2 | Sources panel | Upload / list sources | ☐ | |
| C1.3 | Upload a PDF/text | Source appears in list (status may show processing) | ☐ | |
| C1.4 | Source status | Indexed / processing / error is visible | ☐ | |

## C2. Chat (RAG / exploratory)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| C2.1 | Chat list | Chats populate **or** empty “new chat” | ☐ | |
| C2.2 | Send a question | User message appears immediately | ☐ | |
| C2.3 | Assistant reply | Reply streams or appears (not forever loading) | ☐ | |
| C2.4 | Citations / sources in reply | Shown if design includes them | ☐ | |
| C2.5 | Feedback bar under assistant message | Icons visible (see Part D) | ☐ | |

## C3. Studio (quiz, flashcards, mind map, slides)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| C3.1 | Studio entry in notebook | Studio panel / suite opens | ☐ | |
| C3.2 | Generate quiz | Quiz items populate | ☐ | |
| C3.3 | Generate flashcards | Cards populate | ☐ | |
| C3.4 | Generate mind map | Map / nodes populate | ☐ | |
| C3.5 | Generate slide deck | Slides populate | ☐ | |
| C3.6 | Saved studio outputs | Appear in list / assets | ☐ | |

## C4. Notes inside notebook

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| C4.1 | Notes sidebar / panel | Opens | ☐ | |
| C4.2 | Create note | Note appears in list | ☐ | |
| C4.3 | Edit note | Content saves and shows again | ☐ | |

## C5. Tutor mode notebook (if used)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| C5.1 | Curriculum scope | Class / subject / chapter shown | ☐ | |
| C5.2 | Bootstrap / starter content | Content or prompts populate | ☐ | |
| C5.3 | Follow-up questions | Suggestions populate if enabled | ☐ | |
| C5.4 | Feedback on tutor replies | Feedback bar present | ☐ | |

---

# Part D — Rich feedback UI (IIL) — must test per tier

Feedback appears **under every assistant message** in notebook chat and problem-solver chat.

**Rule:** Options depend on **expertise tier** (set by admin), not only role label.

## D1. Student tier

Login as user with expertise tier **student**.

| # | Control | Expected UI | Pass? | Populates? |
|---|---------|-------------|-------|------------|
| D1.1 | Helpful (thumb up) | Clickable; stays highlighted after submit | ☐ | |
| D1.2 | Not helpful (thumb down) | Opens text modal “What went wrong?”; submit works | ☐ | |
| D1.3 | Confusing | Clickable; highlights | ☐ | |
| D1.4 | Incomplete | Clickable; highlights | ☐ | |
| D1.5 | “More feedback” | **Must NOT** appear for student | ☐ | |
| D1.6 | “Expert feedback” | **Must NOT** appear for student | ☐ | |
| D1.7 | Refresh page | Previously submitted signal still shown as active | ☐ | |

## D2. Teacher tier

Login as user with expertise tier **teacher**.

| # | Control | Expected UI | Pass? | Populates? |
|---|---------|-------------|-------|------------|
| D2.1 | All student options | Helpful / Not helpful / Confusing / Incomplete | ☐ | |
| D2.2 | “More feedback” link | Visible; expands extra row | ☐ | |
| D2.3 | Inaccurate | Opens modal “What was incorrect?” (**note required**) | ☐ | |
| D2.4 | Off syllabus | Clickable | ☐ | |
| D2.5 | “Expert feedback” | **Must NOT** appear for teacher-only tier | ☐ | |

## D3. Tutor / SME tier

Login as user with expertise tier **tutor** or **sme**.

| # | Control | Expected UI | Pass? | Populates? |
|---|---------|-------------|-------|------------|
| D3.1 | All teacher options | Student + More feedback | ☐ | |
| D3.2 | “Expert feedback” | Opens purple expert panel | ☐ | |
| D3.3 | Expert validated | Clickable award control | ☐ | |
| D3.4 | Expert note | Opens modal for required text | ☐ | |
| D3.5 | Missing dimension | Dimension dropdown + “Tag missing dimension” | ☐ | |
| D3.6 | Dimension list | Options like definition, intuition, misconceptions, applications, exam traps, etc. | ☐ | |

## D4. Feedback on Problem Solver

| # | Step | Expected UI | Pass? | Populates? |
|---|------|-------------|-------|------------|
| D4.1 | Get an assistant reply in PS | Feedback bar under message | ☐ | |
| D4.2 | Submit helpful | Highlight persists | ☐ | |

---

# Part E — Admin portal (school admin only)

Login as **schooladmin**. Sidebar should switch pages **quickly** (no full-page freeze).

## E1. Sidebar navigation (click every item)

| # | Menu label | URL | Page title / content loads | Pass? | Populates? |
|---|------------|-----|----------------------------|-------|------------|
| E1.1 | Overview / Users | `/admin/users` | Users table / analytics | ☐ | |
| E1.2 | Roles & Permissions | `/admin/roles-permissions` | Create account form + account list | ☐ | |
| E1.3 | Documents | `/admin/documents` | Sources list / stats | ☐ | |
| E1.4 | NCERT Global | `/admin/ncert-global` | NCERT admin UI | ☐ | |
| E1.5 | Queries | `/admin/queries` | Query metrics | ☐ | |
| E1.6 | RAG Metrics | `/admin/rag-metrics` | Charts / quality metrics | ☐ | |
| E1.7 | Curation | `/admin/curation/candidates` | Candidate list or “No pending candidates” | ☐ | |
| E1.8 | Coverage Map | `/admin/curation/coverage` | Table: Concept, Class, Subject, Artifacts | ☐ | |
| E1.9 | Agents | `/admin/agents` | Agent metrics | ☐ | |
| E1.10 | Guardrails | `/admin/guardrails` | Guardrail metrics | ☐ | |
| E1.11 | Endpoints | `/admin/endpoints` | Endpoint list / metrics | ☐ | |
| E1.12 | Cost & Tokens | `/admin/cost-tokens` | Cost / token charts | ☐ | |
| E1.13 | Alerts | `/admin/alerts` | Alerts list or empty | ☐ | |
| E1.14 | Logs | `/admin/logs` | Log rows or empty | ☐ | |
| E1.15 | Pipeline | `/admin/pipeline` | Pipeline UI | ☐ | |

## E2. Roles & Permissions (accounts + expertise tier)

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| E2.1 | Account list | Users with username, role badges | ☐ | |
| E2.2 | Search / role filter | List filters | ☐ | |
| E2.3 | Create account form | Username, password, role, names, email, class, **Expertise tier (IIL)** | ☐ | |
| E2.4 | Create student | Appears in list; can sign in on student portal | ☐ | |
| E2.5 | Set expertise tier to `teacher` / `tutor` / `sme` | Saved on create/edit | ☐ | |
| E2.6 | Edit account | Fields pre-filled including expertise tier | ☐ | |
| E2.7 | Deactivate / delete (if shown) | List updates | ☐ | |

## E3. Users analytics (`/admin/users`)

| # | UI area | What should populate / show | Pass? | Populates? |
|---|---------|-----------------------------|-------|------------|
| E3.1 | User table | Rows with email/name | ☐ | |
| E3.2 | Metrics columns | Tokens, cost, queries (can be 0) | ☐ | |
| E3.3 | Search / sort / filters | Work without crash | ☐ | |
| E3.4 | Open user detail | Detail panel populates | ☐ | |

## E4. Curation candidates (IIL Part 2) — UI

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| E4.1 | Open Curation | List of pending candidates **or** “No pending candidates.” | ☐ | |
| E4.2 | If candidates exist | Score shown; **Review** link works | ☐ | |
| E4.3 | Candidate detail | JSON/detail block loads (not stuck on Loading) | ☐ | |
| E4.4 | Review notes field | Editable | ☐ | |
| E4.5 | Confidence 1–5 | Editable on approve path | ☐ | |
| E4.6 | Approve button | Returns to candidates list | ☐ | |
| E4.7 | Reject button | Returns to candidates list | ☐ | |

> **Note for testers:** Candidates only appear after enough chat + feedback (especially expert signals). Empty list is OK early in testing.

## E5. Coverage map (IIL Part 3 visibility)

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| E5.1 | Open Coverage Map | Table headers: Concept, Class, Subject, Artifacts | ☐ | |
| E5.2 | Rows | Concept names and artifact counts **or** empty table body | ☐ | |

## E6. RAG Metrics / IIL-related admin metrics

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| E6.1 | RAG Metrics page | Charts or metric cards load | ☐ | |
| E6.2 | Numbers | Show 0 or real values (not NaN / blank forever) | ☐ | |

## E7. Other admin pages (quick populate check)

For each page: **loads**, **shows numbers or empty**, **no endless skeleton**.

| Page | Pass? | Populates? | Notes |
|------|-------|------------|-------|
| Documents | ☐ | | Sources list |
| Queries | ☐ | | Aggregate metrics |
| Agents | ☐ | | Agent rows / charts |
| Guardrails | ☐ | | Safety metrics |
| Cost & Tokens | ☐ | | Cost + token breakdown |
| Alerts | ☐ | | Alert list (auto-refresh OK) |
| Logs | ☐ | | Log lines |
| Pipeline | ☐ | | Pipeline view |
| NCERT Global | ☐ | | Global NCERT admin |
| Endpoints | ☐ | | Endpoint metrics |

---

# Part F — Teacher portal (if enabled)

| # | Step | What should populate / show | Pass? | Populates? |
|---|------|-----------------------------|-------|------------|
| F1 | `/teacher` or `/teacher/login` | Login / dashboard loads | ☐ | |
| F2 | Exams list `/teacher/exams` | Exams populate **or** empty | ☐ | |
| F3 | New exam `/teacher/exams/new` | Wizard / form loads | ☐ | |
| F4 | Exam analytics | Charts / scores populate | ☐ | |

Mark **N/A** if your school build does not use the teacher portal.

---

# Part G — End-to-end UI flywheel (IIL) — beginner path

This section is **only** about walking the full IIL loop in the UI: expert chats and gives rich feedback → admin may see a curation candidate → approve → student later benefits (richer replies / focus prompts). You do **not** need to open the database or APIs.

Use **one concrete example** below. Stick to the same topic the whole way so the flywheel has something to connect.

---

## Example story (use these names)

Imagine your school is testing ScholarSync on **Class 12 Physics — Newton’s Third Law**.

You will use **three logins**:

1. **Admin** — school admin (you already have this).
2. **Dr. Mehta (SME)** — an expert account you create. Expertise tier must be **`sme`** (or **`tutor`**).
3. **Ananya (Student)** — a normal student account. Expertise tier **`student`**.

**Topic to chat about (copy-paste these questions):**

- “What is Newton’s Third Law in simple words?”
- “What mistakes do Class 12 students usually make with action-reaction pairs?”
- “How does this connect to conservation of momentum?”
- “What exam traps appear on this topic?”

That chain is intentional: one concept, several angles (definition → misconceptions → cross-concept → exam traps). That is what IIL is designed to capture.

---

## Step 1 — Admin creates the expert and the student

Sign in as **admin**. Open the sidebar and go to **Roles & Permissions**.

Create **Dr. Mehta**:

- Username: e.g. `mehta.sme`
- Password: anything valid (8+ characters)
- Role: can be `teacher` or `expert` (role is for access; tier drives feedback)
- **Expertise tier (IIL):** choose **`sme`** (or **`tutor`**)
- Fill first name / last name so the UI shows a real name

Create **Ananya**:

- Username: e.g. `ananya.student`
- **Expertise tier (IIL):** **`student`**
- First name: Ananya

**Pass when:** both users appear in the accounts list, and you can see the expertise tier you set.

☐ Pass — accounts created with correct tiers

---

## Step 2 — Expert signs in and deep-dives the topic

Sign **out** of admin. Sign in as **Dr. Mehta**.

You should land on the student-style home (or library). Check:

- Top-right avatar shows initials (e.g. **DM**), not stuck on **U**
- Greeting uses the expert’s name, not only “Welcome back, there”

Open **Library** (or Home → **Create Notebook**). Create or open a notebook, e.g. title **“Physics – Newton’s Laws”**. Upload a source if you have one (optional for this UI test; chat may still answer from NCERT/global knowledge depending on setup).

Open **Chat** and send the four questions above, one after another, waiting for each assistant reply.

**Pass when:** each question gets an assistant reply on screen (streaming or full text). You are not checking scientific perfection here — only that replies **populate**.

☐ Pass — expert chat replies populate for the full chain

---

## Step 3 — Expert gives rich feedback (this is the IIL signal)

Still as **Dr. Mehta**, scroll to a **good** assistant message.

Under the message you should see feedback icons (thumbs, etc.) **and** a link like **Expert feedback** (students will not see this).

Click **Expert feedback**. A purple panel opens.

On that good reply:

1. Click **Expert validated** (award icon).  
   **Pass when:** the control stays highlighted after click.

On another reply (for example the misconceptions answer):

2. In the dimension dropdown, pick something like **`misconceptions`** (or **`exam_traps`**).
3. Click **Tag missing dimension**.

Optional but useful: on a weak reply, use **More feedback** → **Inaccurate** and type a short note (required), or **Expert note** with a correction.

**Pass when:** expert-only controls appear, submit works, and highlights/tags stick if you refresh the page.

☐ Pass — expert feedback UI works (validated + missing dimension)

---

## Step 4 — Student signs in and uses the same topic

Sign **out**. Sign in as **Ananya**.

On **Home**:

- Greeting should say something like **“Welcome back, Ananya”** (or her first name)
- Overview cards may all be **0** — that is fine for a new student (**Empty OK**)
- **Focus this week** may still say “Study a notebook to see your focus…” — also **Empty OK** early

Open or create a notebook and ask a simple question on the **same topic**, e.g.:

> “Explain Newton’s Third Law for Class 12.”

**Pass when:**

- Reply populates
- Under the reply she only sees **student** feedback: Helpful, Not helpful, Confusing, Incomplete
- She does **not** see **Expert feedback** or **More feedback** (those are for teacher/tutor/sme tiers)

Have her tap **Helpful** once.

☐ Pass — student identity + chat + student-only feedback

---

## Step 5 — Admin checks the flywheel surfaces

Sign **out**. Sign in as **admin** again.

### 5a. Curation (sidebar → **Curation**)

Open **Curation** (`/admin/curation/candidates`).

**What you might see:**

- **“No pending candidates.”** — common on day one. Scoring runs on a schedule (not instantly). Mark **Empty OK**, not Fail.
- **A list with scores and a Review link** — good; the flywheel UI is alive.

If a candidate exists, click **Review**. You should see candidate detail (JSON/text block), a notes box, confidence (1–5), and **Approve** / **Reject**.

Click **Approve** (add a short note like “Good SME chain on Newton 3”). You should return to the candidates list.

☐ Pass — curation page loads; review works **or** empty list is acceptable early

### 5b. Coverage map (sidebar → **Coverage Map**)

Open **Coverage Map**.

You should see a table with headers: **Concept**, **Class**, **Subject**, **Artifacts**.

Rows may be empty until artifacts exist after approve + processing. Empty table body = **Empty OK**. If a row for a Newton-related concept shows an artifact count &gt; 0 after approve, that is a strong Pass.

☐ Pass — coverage map UI loads (rows optional early)

### 5c. RAG Metrics (sidebar → **RAG Metrics**)

Open **RAG Metrics**.

After feedback from Mehta and Ananya, **Total Feedback** should be **greater than 0** (not forever stuck at zero if they submitted feedback). Charts may show helpful / negative signals.

☐ Pass — feedback numbers move after real feedback (or note if still 0 and why)

---

## Step 6 — What “success” looks like in plain words

Think of the flywheel as a story:

1. **Expert explores** Newton’s Third Law from many angles in chat.  
2. **Expert stamps quality** with Expert validated / missing dimension (and optionally notes).  
3. **System logs** those interactions in the background (you do not see logs in the UI).  
4. **Admin may later see** a curation candidate and can **Approve**.  
5. **Coverage map** may show that concept has derived knowledge.  
6. **Students** keep chatting; over time they may get richer answers and, on Home, **starter prompts** under Focus (those can take longer — Empty OK at first).

You are only checking that **each screen opens, shows the right controls for each person, and data populates when it should**. You are not failing the test because curation is still empty five minutes after one chat.

---

## Quick checklist for this example only

Copy this into your notes:

- ☐ Admin created `mehta.sme` with tier **sme** (or tutor)  
- ☐ Admin created `ananya.student` with tier **student**  
- ☐ Mehta chat: 4 replies on Newton’s Third Law populate  
- ☐ Mehta: Expert validated works  
- ☐ Mehta: Missing dimension tag works  
- ☐ Ananya: name on Home is correct  
- ☐ Ananya: only student feedback options  
- ☐ Ananya: Helpful submits  
- ☐ Admin: Curation page loads (list or “No pending candidates”)  
- ☐ Admin: If candidate exists, Approve works  
- ☐ Admin: Coverage Map loads  
- ☐ Admin: RAG Metrics reflects feedback (or documented Empty OK)

**Overall for Part G:** ☐ Pass / ☐ Pass with Empty OK notes / ☐ Fail  

**Notes (what was empty vs broken):**

---


# Part H — Empty states vs broken UI (how to judge “Populates?”)

| Situation | Mark Populates? | Is it a Fail? |
|-----------|-----------------|---------------|
| New student, all metrics `0`, “No recent notebook yet” | **Empty OK** | No — correct empty state |
| Name shows “User” / “there” after login with full profile | **No** | **Yes** — identity not syncing |
| Spinner / skeleton never ends (>15s) | **No** | **Yes** |
| Page is blank white | **No** | **Yes** |
| Feedback icons missing on assistant message | **No** | **Yes** |
| Admin curation says “No pending candidates” in week 1 | **Empty OK** | No — not enough data yet |
| Coverage table has headers but no rows | **Empty OK** | No — until artifacts exist |

---

# Part I — Quick smoke (15 minutes)

If you only have a short window, run this minimum set:

1. Admin login → Roles → create student with tier student  
2. Student login → name + home populate  
3. Create notebook → upload source → ask chat question → reply populates  
4. Submit Helpful feedback → stays highlighted  
5. Admin sidebar: Users, Roles, Curation, Coverage Map all open  
6. Logout / login again — identity still correct  

---

# Sign-off

| Field | Value |
|-------|-------|
| Tester name | |
| Date | |
| Build / branch | |
| Browser | |
| Overall result | ☐ Pass / ☐ Fail / ☐ Pass with notes |
| Blocking UI bugs (list) | |
| Non-blocking notes | |

---

## Coverage map (what this checklist includes)

| Area | Covered |
|------|---------|
| Sign-in / sign-out / identity sync | Yes |
| Student nav: Home, Library, Problem Solver, Study Plan, Analytics, Assets | Yes |
| Notes, Studios, Tutor entry | Yes |
| Full profile sections (8) | Yes |
| Notebook: sources, chat, studio, notes, tutor mode | Yes |
| Feedback bar all tiers (student / teacher / tutor-sme) | Yes |
| Problem Solver feedback | Yes |
| Admin sidebar all pages | Yes |
| Roles + expertise tier (IIL) | Yes |
| Curation candidates + review approve/reject | Yes |
| Coverage map | Yes |
| RAG metrics and other admin metrics pages | Yes |
| Teacher portal (optional) | Yes |
| IIL flywheel UI path | Yes |

This document is **UI-only**. Backend log tables, Pinecone namespaces, and scoring jobs are out of scope here; use the IIL Implementation Guide for product meaning of each signal.
