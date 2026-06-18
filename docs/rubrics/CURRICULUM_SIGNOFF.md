# Curriculum Sign-Off — ING-08 & RET-04

Manual rubric gates remain **PENDING** until Curriculum completes this checklist.

## Artifacts

| Test ID | Artifact | Pass threshold |
|---------|----------|----------------|
| ING-08 | `evals/reports/ing08_rubric_batch.json` | ≥90% chunks pass all four criteria |
| RET-04 | `evals/reports/ret04_rubric.json` | ≥95% citations support their claims |

## ING-08 — Chunk quality (≥90%)

For each sample in `ing08_rubric_batch.json`, score **1 = pass / 0 = fail** per criterion:

- [ ] `complete_sentences`
- [ ] `semantic_coherence`
- [ ] `reasonable_overlap`
- [ ] `formula_equation_integrity`

A sample **passes** when all four criteria pass.

- [ ] Total passing samples / total samples ≥ **90%**
- [ ] Reviewer name: ___________________
- [ ] Date: ___________________

## RET-04 — Citation correctness (≥95%)

For each row in `ret04_rubric.json`, verify the answer claim is contained in or directly supported by `citation_text`.

- [ ] Set `claim_supported` = true/false for each row
- [ ] Set `contradicts_claim` = true/false when applicable
- [ ] Supported citations / total citations ≥ **95%**
- [ ] Reviewer name: ___________________
- [ ] Date: ___________________

## Sign-off

- [ ] ING-08 approved
- [ ] RET-04 approved
- [ ] Prod gate scorecard updated from `PENDING` → `PASS`
