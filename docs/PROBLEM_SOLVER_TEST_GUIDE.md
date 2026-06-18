# Guided Problem Solver — UI Test Guide

Use this guide to verify the **Guided Problem Solver** in the browser. Every step describes what you should see and click in the UI.

**Example problem (use throughout):**

```text
A car accelerates uniformly from rest to 72 km/h in 10 seconds.
Find (a) the acceleration in m/s² and (b) the distance covered in this time.
```

This is a **Class 10 Physics (Motion)** numerical. DNA should show **Physics**, not Mathematics.

**Correct answers (for checking modes that reveal):**

| Part | Answer |
|------|--------|
| (a) Acceleration | **2 m/s²** |
| (b) Distance | **100 m** |

---

## Before you start

1. Sign in at `http://localhost:3000`.
2. Confirm **Problem Solver** appears in the top navigation (after Library).
3. Open `http://localhost:3000/problem-solver`.

---

## Step 1 — Landing: pick subjects

| What to do | What you should see |
|------------|---------------------|
| On `/problem-solver`, select **Science** (and optionally **Mathematics**) | Selected cards show a checkmark |
| Read the summary line | Shows your class and selected subjects |
| Click **Open notebook** | Navigates to `/notebook/...` (no long tutor “preparing” overlay) |

**Tip:** For physics problems, include **Science** in your selection so NCERT context matches.

---

## Step 2 — Notebook layout

| What to do | What you should see |
|------------|---------------------|
| After the notebook opens | **Three columns**: Sources (left), Guided flow (center), Current attempt (right) |
| Check the center header | Title **Guided Problem Solver** and step **1 — Upload your problem** |
| Check the right panel | Hint: *Upload a problem in the center panel…* |

---

## Step 3 — Paste problem and analyze

| What to do | What you should see |
|------------|---------------------|
| Paste the car problem into the large text area | Text is accepted (at least 10 characters) |
| Click **Analyze problem** | Button shows **Analyzing…** with a spinner |
| Wait 30–90 seconds (first run) | Do not refresh; DNA step loads when ready |

**If it fails:** A red message appears under the buttons (e.g. auth error or server unavailable).

---

## Step 4 — Problem DNA (step 2)

| Field | Expected for the car problem |
|-------|------------------------------|
| **Subject** | **Physics** (not Mathematics) |
| **Chapter** | Motion / Laws of Motion (or similar) |
| **Difficulty** | Easy or Medium |
| **Est. time** | A number of minutes (e.g. 10–20) |
| **Confidence** | A value like 0.7–0.9 |
| **Key concepts** | Pills such as **Acceleration**, **Distance**, **Uniform motion** |

| What to do | What you should see |
|------------|---------------------|
| Scroll the center panel | Step badge **2 — Problem DNA** with cards above |
| Check the right panel | **Physics · Motion** (or similar) and a snippet of your problem |
| Confirm no final answer | DNA cards do **not** show “2 m/s²” or “100 m” |

---

## Step 5 — The four mode cards (step 3)

After DNA loads, scroll to **Choose how you want help**. You should see **exactly four** clickable cards in a grid:

| Card title | Subtitle on the card | Badge |
|------------|----------------------|-------|
| **Explain from the Basics** | Build understanding from first principles with NCERT-grounded steps. | — |
| **Help Me Solve It** | Guided hints with up to two quick checkpoints — no answer until you earn it. | **Recommended for learning** |
| **Show the Missing Idea** | Identify the one concept blocking you and how to apply it. | — |
| **Show the Best Approach** | See the efficient solution path with reasoning and takeaway. | — |

| What to do | What you should see |
|------------|---------------------|
| Hover / read each card | Titles and subtitles match the table above |
| Click one card | A small spinner on that card; other cards disable until streaming finishes |
| Right panel | Updates with **Mode:** … after selection |

**Important:** Test **each mode separately**. After finishing one mode, click **New problem**, paste the car problem again, click **Analyze problem**, wait for DNA, then pick the next mode.

---

## Mode A — Explain from the Basics

**Card text:** *Build understanding from first principles with NCERT-grounded steps.*

### What to do

1. Complete Steps 1–4 (DNA ready).
2. Click **Explain from the Basics**.
3. Wait for sections to stream in (step badge **4 — Guided response**).
4. Scroll through all sections.
5. Try a follow-up pill at the bottom (step badge **5 — What next?**).

### What you should see (sections)

Sections appear **in order** (wording may vary slightly; check the **idea**, not exact punctuation):

| # | Section heading | What it should cover for the car problem |
|---|-----------------|------------------------------------------|
| 1 | **Question Understanding** | Car starts from rest, speeds up uniformly, time is 10 s, final speed is 72 km/h; find acceleration and distance. |
| 2 | **Given Information** | \(u = 0\), \(v = 72\) km/h, \(t = 10\) s; uniform acceleration. |
| 3 | **What to Find** | (a) acceleration in m/s², (b) distance in metres. |
| 4 | **Concept Needed** | Uniform acceleration, equations of motion (NCERT Motion chapter). |
| 5 | **Formula/Principle** | \(v = u + at\) and \(s = ut + \frac{1}{2}at^2\) (or equivalent). |
| 6 | **Step-by-step Solution** | Convert 72 km/h → 20 m/s; \(a = (v-u)/t = 2\) m/s²; then \(s = 100\) m. |
| 7 | **Final Answer** | (a) 2 m/s², (b) 100 m. |
| 8 | **Key Learning** | Always convert km/h to m/s; pick the right equation for what is unknown. |

### Final answer box

Below the sections, a **Final answer** box should show something like:

```text
(a) 2 m/s²   (b) 100 m
```

### Follow-up pills (step 5)

After streaming completes, you should see pills such as:

- **Show shorter version**
- **Show best approach**
- **Give similar problem**
- **Explain concept again**
- **Start Tutor Session**

| Follow-up | What should happen |
|-----------|-------------------|
| **Show shorter version** | Shorter summary; page does not crash |
| **Start Tutor Session** | Browser goes to `/tutor?...` with class/subject/chapter from DNA |

### Pass / fail

| Pass | Fail |
|------|------|
| All 8 section types appear | Stuck on spinner forever |
| Full solution with **2 m/s²** and **100 m** | No final answer in this mode |
| Follow-up pills visible | Cards missing or wrong count |

---

## Mode B — Help Me Solve It *(recommended)*

**Card text:** *Guided hints with up to two quick checkpoints — no answer until you earn it.*  
**Badge:** *Recommended for learning*

### What to do

1. Click **New problem** → paste car problem → **Analyze problem** → wait for DNA.
2. Click **Help Me Solve It**.
3. Read hints **without** expecting the final numbers yet.
4. Complete **Quick checkpoint 1** (MCQ).
5. Complete **Quick checkpoint 2** if it appears.
6. Read the completed guided solution or use **Reveal solution** follow-up.

### Phase 1 — Hints only (no final answer)

After you click the mode, streamed sections should look like:

| Section heading | What it should cover |
|-----------------|----------------------|
| **Problem decode** | Rest → 72 km/h in 10 s; two parts (a) and (b). |
| **Hint 1** | Convert km/h to m/s before using equations. |
| **Hint 2** | Use \(v = u + at\) first because you know \(u\), \(v\), and \(t\). |

**Pass check:** There is **no** **Final answer** box yet, and the text must **not** plainly state “2 m/s²” or “100 m” as the solution.

### Phase 2 — Checkpoint 1

A **Quick checkpoint** block appears (step badge **1**):

| UI element | Expected |
|------------|----------|
| Title | **Quick checkpoint** |
| Prompt | A question like *Which idea should we use?* or *What should we find first?* |
| Options | **4** choices labelled **A**, **B**, **C**, **D** (e.g. convert units first, use \(v = u + at\), use area under graph, etc.) |
| **Continue** button | Disabled until you pick an option; then shows **Checking…** |

**What to do:** Pick the option that best matches converting units / using \(v = u + at\) → click **Continue**.

### Phase 3 — Checkpoint 2 (if shown)

After checkpoint 1, you may get:

- More hints or feedback, then
- **Quick checkpoint** with badge **2** (e.g. *Which equation gives distance?* with options about \(s = ut + \frac{1}{2}at^2\), etc.)

**What to do:** Pick an option → **Continue**.

### Phase 4 — Solution revealed

After up to **two** checkpoints, you should see:

- A fuller guided write-up, and/or
- A **Final answer** box with **2 m/s²** and **100 m**

Follow-up pills may include:

- **Show next hint**
- **Reveal solution**
- **Show best approach**
- **Give similar problem**

| Follow-up | What should happen |
|-----------|-------------------|
| **Reveal solution** | Full worked solution with final numbers |

### Pass / fail

| Pass | Fail |
|------|------|
| Hints first, answer later | Full answer in the first response |
| At least 1 MCQ checkpoint | No checkpoint UI |
| Max 2 checkpoints then solution | Third checkpoint appears |
| Final answer matches **2 m/s²** / **100 m** | Wrong subject or no solution after checkpoints |

---

## Mode C — Show the Missing Idea

**Card text:** *Identify the one concept blocking you and how to apply it.*

### What to do

1. **New problem** → paste car problem → analyze → DNA.
2. Click **Show the Missing Idea**.
3. Read all sections.
4. Click **Now show full solution** (follow-up).

### What you should see (sections)

| # | Section heading | What it should cover for the car problem |
|---|-----------------|------------------------------------------|
| 1 | **The Missing Idea** | The unlock is **uniform acceleration** + using **equations of motion**, and converting **km/h → m/s** before substituting. |
| 2 | **Why It Feels Tricky** | Mixed units (km/h vs m/s²); two parts; choosing which equation to use first. |
| 3 | **Correct Mental Model** | Constant acceleration from rest → speed grows linearly; distance grows with \(t^2\). |
| 4 | **How to Start** | List given values in SI units; find \(a\) first, then \(s\). |
| 5 | **Common Mistake** | Using 72 directly in m/s² formulas without converting to 20 m/s. |

### Final answer

**By default:** No **Final answer** box (this mode gives the *idea*, not the full exam write-up).

### Follow-up pills

- **Now show full solution** ← use this to test the reveal path
- **Show best approach**
- **Give one similar problem**
- **Explain this concept**
- **Start Tutor Session**

| Follow-up | What should happen |
|-----------|-------------------|
| **Now show full solution** | Worked solution appears with **2 m/s²** and **100 m** |

### Pass / fail

| Pass | Fail |
|------|------|
| Focus on *one missing idea* (units + equations of motion) | Full step-by-step solution in the first response |
| No final numbers in the initial response | Answer leaked immediately |
| **Now show full solution** works | Follow-up does nothing |

---

## Mode D — Show the Best Approach

**Card text:** *See the efficient solution path with reasoning and takeaway.*

### What to do

1. **New problem** → paste car problem → analyze → DNA.
2. Click **Show the Best Approach**.
3. Read all sections and the **Final answer** box.
4. Try **Compare with basic method** or **Give similar exam problem**.

### What you should see (sections)

| # | Section heading | What it should cover for the car problem |
|---|-----------------|------------------------------------------|
| 1 | **Problem Pattern** | “From rest to a speed in a fixed time” — classic uniform acceleration numerical. |
| 2 | **Best Method** | Convert \(v\) to m/s → \(a = (v-u)/t\) → \(s = ut + \frac{1}{2}at^2\) (or \(s = \frac{(u+v)t}{2}\)). |
| 3 | **Why This Fits** | You know \(u\), \(v\), \(t\); direct path, minimal steps. |
| 4 | **Efficient Setup** | \(u=0\), \(v=20\) m/s, \(t=10\) s on one line. |
| 5 | **Clean Solution** | \(a=2\) m/s²; \(s=100\) m with neat substitution. |
| 6 | **Exam Note** | Show units; box final answers as (a) and (b). |
| 7 | **When Not to Use** | If acceleration is not uniform, these equations do not apply. |

### Final answer box

Should show:

```text
(a) 2 m/s²   (b) 100 m
```

### Follow-up pills

- **Compare with basic method**
- **Explain why this works**
- **Give similar exam problem**
- **Show common mistakes**
- **Start Tutor Session**

| Follow-up | What should happen |
|-----------|-------------------|
| **Compare with basic method** | Alternative method (e.g. graph area) without crash |
| **Give similar exam problem** | New practice question (train/bus/object from rest) |

### Pass / fail

| Pass | Fail |
|------|------|
| Exam-style efficient method | Only vague hints |
| Clear **2 m/s²** and **100 m** | Wrong numbers |
| **Exam Note** / **When Not to Use** present | Missing structured sections |

---

## Step 6 — Shared UI after any mode

These apply no matter which mode you picked:

| UI area | What you should see |
|---------|---------------------|
| **Step 4 — Guided response** | Title at top; sections stream in; spinner while loading |
| **Final answer** box | Only when the mode allows reveal (not in Help Me Solve It phase 1, not in Missing Idea until follow-up) |
| **Step 5 — What next?** | Row of follow-up pills + optional text input *Optional: add a follow-up question…* |
| **Right panel** | Subject · chapter, mode name, problem snippet |
| **New problem** | Resets to step 1 intake |

---

## Step 7 — New problem (reset)

| What to do | What you should see |
|------------|---------------------|
| Click **New problem** (center header or right panel) | Returns to step **1 — Upload your problem** |
| Right panel | Empty hint again until you analyze a new problem |

Use this between testing each of the four modes.

---

## Step 8 — Optional: image / PDF upload

| What to do | What you should see |
|------------|---------------------|
| Click **Image / PDF** and upload a one-page file with the car problem | **Extracting text…** / analyzing state |
| Wait for processing | Same DNA → mode → response flow as text paste |
| Left **Sources** column | Uploaded file listed after ingest |

---

## Full test checklist (car problem)

Run in order. Use **New problem** + re-analyze between modes.

| # | Mode | Click | Must see | Must NOT see (initially) |
|---|------|-------|----------|--------------------------|
| 1 | — | Analyze | DNA: **Physics**, Motion, concept pills | Final answer in DNA |
| 2 | Explain from the Basics | Card #1 | 8 sections + final **2 m/s²**, **100 m** | — |
| 3 | Help Me Solve It | Card #2 (recommended) | Hints + checkpoint MCQ(s) | Final answer before checkpoints |
| 4 | Help Me Solve It | Continue ×1–2 | Solution with **2 m/s²**, **100 m** | Third checkpoint |
| 5 | Show the Missing Idea | Card #3 | 5 “missing idea” sections | Full numeric solution |
| 6 | Show the Missing Idea | **Now show full solution** | Full solution | — |
| 7 | Show the Best Approach | Card #4 | 7 exam-method sections + final answer | — |

---

## Quick pass / fail (whole feature)

| Area | Pass if |
|------|---------|
| Landing + layout | 3 columns; Problem Solver nav works |
| Intake | Analyze advances to DNA |
| DNA | **Physics** + motion concepts for car problem |
| Mode cards | All 4 titles/subtitles match Step 5 table |
| Explain from the Basics | Full teaching path + final answer |
| Help Me Solve It | Hints → checkpoints → earned answer |
| Show the Missing Idea | Idea first; full solution only via follow-up |
| Show the Best Approach | Efficient exam solution + final answer |
| Reset | **New problem** clears session |

---

## URLs

| Screen | Path |
|--------|------|
| Landing | `/problem-solver` |
| Workspace | `/notebook/{slug}` |

---

*Last updated for V1 Guided Problem Solver — UI walkthrough with the car acceleration example and all four solving modes.*
