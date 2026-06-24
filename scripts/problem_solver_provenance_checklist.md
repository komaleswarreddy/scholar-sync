# Problem Solver Agents 17-22 — Provenance Checklist

## 1. Source PDF catalog

- [ ] All 9 PDFs present under `Problem solver_Questions/`
- [x] `Biology_Testing_Question_Bank_Updated.pdf` (cbse_biology)
- [x] `Mathematics_Testing_Question_Bank.pdf` (cbse_mathematics)
- [x] `Physics_testing_Question_Bank.pdf` (cbse_physics)
- [x] `Mains 2026 April.pdf` (jee_april_2026)
- [x] `Mains 2026 Jan.pdf` (jee_jan_2026)
- [x] `Botany.pdf` (neet_botany)
- [x] `Chemistry.pdf` (neet_chemistry)
- [x] `Physics.pdf` (neet_physics)
- [x] `Zoology.pdf` (neet_zoology)

## 2. Eval pool (165) vs question bank

- [x] 165/165 pool items traceable to bank (165/165)

## 3. source_key → PDF mapping

- [x] All source_key maps to correct PDF filename

## 4. Production LLM gold

- [x] 165/165 examples have `production_llm` gold (165/165)

## 5. Complete_Agent_DataSet.md vs eval pool

- [x] 165 examples in markdown
- [x] Unique problem texts in markdown
- [x] Markdown matches eval pool texts

## 6. Per-source PDF coverage in eval pool

- [x] `cbse_biology`: 23 (min 12)
- [x] `cbse_mathematics`: 10 (min 10)
- [x] `cbse_physics`: 24 (min 12)
- [x] `jee_april_2026`: 18 (min 18)
- [x] `jee_jan_2026`: 18 (min 18)
- [x] `neet_botany`: 18 (min 18)
- [x] `neet_chemistry`: 18 (min 18)
- [x] `neet_physics`: 18 (min 18)
- [x] `neet_zoology`: 18 (min 18)

## 7. Diagram / vision extraction quality

- [x] verify_diagram_extraction_quality.py passes

## Summary

- **Failures:** 0
- **Warnings:** 0
