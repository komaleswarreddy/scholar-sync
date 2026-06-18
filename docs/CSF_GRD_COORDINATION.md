# CSF ↔ GRD coordination (checklist item 4)

This document maps Child Safety Framework (CSF) abstract probes to Guardrails (GRD) refusal categories so wording stays non-graphic and non-duplicative.

## Scope

| Bucket | CSF probes | GRD corpus |
|--------|------------|------------|
| Distress / supportive routing | `evals/datasets/csf_distress_probes.json` | No direct GRD self-harm method prompts (by design) |
| Academic manipulation | `csf_manipulation_probes.json` | `grd_must_refuse.json` → `category: cheating` |
| Grooming / secrecy | `csf_grooming_probes.json` | GRD harassment (threats) — different intent |
| Pressure / empathy | `csf_pressure_probes.json` | Overlaps CSF distress only in tone, not refusal |
| False-positive guard | `csf_must_treat_normally.json` | GRD does not cover biology/history study allow-list |

GRD export for red-team batches: `docs/Test_Bucket_Results/guardrails/scripts/export_grd_redteam_batch.py`.

## Mapping table

| CSF test | CSF probe theme | Nearest GRD category | Overlap / dedup note |
|----------|-----------------|----------------------|----------------------|
| CSF-01 | Abstract school distress (“hopeless”, “overwhelmed”) | *(none — supportive route, not refuse)* | CSF uses **supportive markers** (counselor, trusted adult). GRD has no parallel “distress support” prompts; no graphic or method-level self-harm text in either bucket. |
| CSF-02 | Homework / essay cheating catch | `grd-01` **cheating** | CSF catch prompts are shorter homework variants; GRD uses live-exam / JEE framing. Same policy outcome (refuse), **no duplicated graphic wording**. |
| CSF-02 | Allow-study controls | *(none)* | GRD cheating set is refuse-only; CSF allow rows are CSF-specific. |
| CSF-05 | Pressure + empathy | CSF-01 distress (tone) | GRD has no pressure-empathy judge; coordination is **tone-only**, not refusal copy. |
| CSF-06 | Secrecy / grooming patterns | `grd-03` **harassment** (adjacent) | CSF tests **safe route** (no “keep secret”, no meeting without parents). GRD harassment tests **refusal of bullying/threats** — different user intent, **no shared prompt text**. |
| CSF must-treat-normally | Biology, history, mental-health study | *(none)* | Ensures moderation does not over-block educational topics; GRD corpus does not include these allow cases. |

## Wording guardrails

1. **No graphic detail** — CSF distress and grooming probes stay abstract (feelings, school stress, secrecy requests). GRD adult/sexual and harassment prompts are refuse-focused and remain in the GRD bucket only.
2. **No method-level self-harm** — Neither CSF distress probes nor `grd_must_refuse.json` include method instructions; CSF expects supportive routing, not cold refusal-only.
3. **Cheating** — CSF-02 and GRD-01 share academic-integrity policy but use distinct prompt phrasing to avoid corpus duplication.
4. **Harassment vs grooming** — GRD-03 targets generating insults/threats; CSF-06 targets **not facilitating** secrecy or isolation. Categories are related for safety review but probes do not reuse lines.

## Sign-off

| Check | Status |
|-------|--------|
| CSF distress probes reviewed against GRD (no graphic overlap) | Done |
| CSF cheating catch distinct from GRD-01 phrasing | Done |
| CSF grooming distinct from GRD-03 harassment prompts | Done |
| GRD export script referenced for future red-team runs | Done |

**Last updated:** 2026-06-13 (MVP IPI+CSF sign-off)
