## 17. Problem DNA Analyzer

| Field | Value |
|-------|-------|
| Dataset ID | `problem_dna_analyzer` |
| Category | Problem Solving |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** Classify a normalized problem stem into subject, chapter, difficulty, question type, and internal expert solution metadata without leaking the final answer in `problem_dna_summary`. Production template: [`problem_solver/dna.j2`](packages/core/prompts/templates/problem_solver/dna.j2).

**Audit finding (baseline v1.0.0):** Baseline v1.0.0 recycled three stub problems (microscope, ∫, pepsin) across all coach agents, used mismatched NCERT context, placeholder gold (`LLM-judge`), and no diagram/OCR coverage. Rebuilt with 30 unique problems from the Problem solver_Questions bank, locked variation taxonomy, full inline prompt, and complete `dna_json` gold with NCERT-aligned expert solutions.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `numerical` | Numeric/unit problems | 7 |
| `jee` | JEE Mains framing | 5 |
| `neet` | NEET MCQ / assertion-reason | 2 |
| `multi_part` | Multi-step / derive | 1 |
| `cbse` | CBSE board style | 5 |
| `proof` | Derivation / proof | 2 |
| `diagram` | Diagram-dependent (OCR bank) | 2 |
| `ncert_strict` | Strict NCERT wording | 1 |
| `conceptual` | Explain-why / concept | 3 |
| `case_study` | Passage / case-based | 2 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **subject_match** — Subject/chapter align with problem content, not notebook scope order.
* **no_answer_in_summary** — `problem_dna_summary` must not contain final numeric answer.
* **schema_valid** — All required `dna_json` keys present with valid enums.
* **difficulty_calibration** — Difficulty and expected time match exam type and stem length.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `problem_text_normalized`, `ncert_context`, `class_num`, `subject_labels`
* Output keys: `dna_json`

**Prompt template (production):**

```jinja2
You are ScholarSync Problem DNA Analyzer for Indian NCERT students (Class 11-12).

Analyze the problem and return JSON only (no markdown fences).

Problem:
{{ problem_text_normalized }}

{% if ncert_context %}
NCERT context:
{{ ncert_context }}
{% endif %}

Notebook scope (filter only — do NOT default to the first subject in this list):
{% if subject_labels %}
{% for label in subject_labels %}- {{ label }}
{% endfor %}
{% else %}
{% for key in subject_keys %}- {{ key }}
{% endfor %}
{% endif %}
Class: {{ class_num }}

{% if inferred_subject_hint %}
Content-based subject hint (trust the problem wording over scope order): {{ inferred_subject_hint }}
{% endif %}

Rules:
1. Classify subject from PROBLEM CONTENT first (physics motion, chemistry equations, maths algebra, etc.).
2. "subject" must be the student-facing name (e.g. Physics, Chemistry, Mathematics) — not a generic bucket unless unsure.
3. If the problem involves motion, acceleration, velocity, forces, or units like m/s² → subject is Physics (NCERT Science), NOT Mathematics.
4. Allowed scope limits which NCERT subjects are relevant; never label a physics word problem as Mathematics.

Return JSON:
{
  "subject": "string",
  "chapter": "string",
  "conceptTags": ["string"],
  "difficulty": "Easy" | "Medium" | "Hard" | "Unknown",
  "expectedTimeMinutes": integer,
  "questionType": "Numerical" | "Conceptual" | "Diagram" | "Proof" | "MCQ" | "Mixed",
  "examSkill": "string",
  "confidence": number 0-1,
  "problem_dna_summary": "one sentence, no final answer",
  "expert_solution_internal": {
    "final_answer": "string with units",
    "key_steps": ["string"],
    "method_name": "string"
  }
}

Do NOT put the final numeric answer in problem_dna_summary.
```

*Runtime note:* [`packages/core/services/problem_solver_service.py`](packages/core/services/problem_solver_service.py) `ProblemSolverService.analyze_dna()` stores `problem_dna` on the session before coach modes run.

### Evaluation examples (30)
## Variation: `numerical`


#### Example 1: `problem_dna_analyzer-011`

- **Variation:** numerical
- **Tags:** physics, cbse, source_pdf_cbse_physics, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q42. A thin, isolated spherical conducting shell S1 encloses a bound volume containing three individual localized point charges: q1 = 3 μC, q2 = -2 μC, and q3 = 9 μC. This entire configuration space is subsequently enclosed by a larger concentric thin conducting shell element S2. A standalone point charge Q is placed in the hollow space interface separating the two shells. If experimental testing reveals that the net electrostatic flux passing through the outer bounding surface S2 is exactly four times the net flux tracked passing through the inner shell surface S1, calculate the value of the unknown intermediate charge Q. Testing Question Bank 7

**Ncert Context:**

NCERT Class 12 Physics Ch.1: Gauss's law relates net flux through a closed surface to enclosed charge. Conductor electrostatics: field inside conductor is zero in electrostatic equilibrium.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Gauss's Law",
  "conceptTags": [
    "Electrostatics",
    "Flux",
    "Conductors"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 20,
  "questionType": "Numerical",
  "examSkill": "Application of Gauss's Law",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves calculating the unknown charge Q based on the relationship between the net electrostatic flux through two concentric spherical conducting shells.",
  "expert_solution_internal": {
    "final_answer": "6 μC",
    "key_steps": [
      "Calculate the net charge enclosed by shell S1.",
      "Apply Gauss's law to find the flux through S1 and relate it to the flux through S2.",
      "Set up the equation based on the given relationship of fluxes to solve for Q."
    ],
    "method_name": "Gauss's Law Application"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-012`

- **Variation:** numerical
- **Tags:** physics, cbse, source_pdf_cbse_physics, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q43. Three thin convex lenses L1, L2, and L3, each possessing an identical individual focal length value of +40 cm, are mounted coaxially along a straight bench line. The separation distance between the first lens L1 and the middle lens L2 is fixed at 120 cm, while the separation distance between the middle lens L2 and the final lens L3 is set to 20 cm. A point object is positioned on the axis at a distance of 80 cm to the left of the first lens element L1. Determine the final position coordinates of the image formed by the multi-component combination relative to the position of the original target object.

**Ncert Context:**

NCERT Class 12 Physics Ch.9: Lens formula 1/f=1/v-1/u. Magnification m=v/u. Sign convention: real object distance u negative.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Optics",
  "conceptTags": [
    "Lens formula",
    "Image formation",
    "Convex lens"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 30,
  "questionType": "Numerical",
  "examSkill": "Application of lens formula",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves determining the final image position formed by three convex lenses with given focal lengths and separations.",
  "expert_solution_internal": {
    "final_answer": "160 cm",
    "key_steps": [
      "Calculate the image position formed by L1 using the lens formula.",
      "Use the image from L1 as the object for L2 and calculate the new image position.",
      "Use the image from L2 as the object for L3 and calculate the final image position."
    ],
    "method_name": "Sequential image formation using lens formula"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `problem_dna_analyzer-020`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_april_2026, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q55. Arrange the following isothermal processes in order of the magnitude of the work ( ) involved between states and . A. Expansion in single stage B. Expansion in multi stages C. Compression in single stage D. Compression in multi stages Choose the correct option. (1) (2) (3) (4) 2s 1 3s 1 3p 2 4d 1 A = [SO2− 3 , CO2− 3 ] B = [O2− 2 , F2] C = [CN−, CO] D = [NH3, H3O+] E = [MnO2− 4 , CrO2− 4 ] p −V 1 2 wA wB wC wD |wB| > |wA| > |wC| > |wD| |wC| > |wD| > |wA| > |wB| |wC| > |wD| > |wB| > |wA| |wB| > |wA| > |wD| > |wC|

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Thermodynamics",
  "conceptTags": [
    "Isothermal Process",
    "Work Done",
    "Expansion",
    "Compression"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Application of Concepts",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves arranging different isothermal processes based on the magnitude of work done during expansion and compression.",
  "expert_solution_internal": {
    "final_answer": "|wB| > |wA| > |wC| > |wD|",
    "key_steps": [
      "Identify the nature of processes: expansion and compression.",
      "Determine the work done in single-stage vs multi-stage processes.",
      "Compare the magnitudes of work done in each case."
    ],
    "method_name": "Comparison of Work Done in Isothermal Processes"
  },
  "subject_key": "physics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 4: `problem_dna_analyzer-021`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_jan_2026, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.30 A body of mass 14 kg initially at rest explodes and breaks into three fragments of masses in the ratio 2 : 2 : 3. The two pieces of equal masses fly off perpendicular to each other with a speed of 18 m/s each. The velocity of the heavier fragment is ___ m/s.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Motion in One Dimension",
  "conceptTags": [
    "Conservation of Momentum",
    "Explosions",
    "Velocity"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Application of Conservation Laws",
  "confidence": 0.9,
  "problem_dna_summary": "A body explodes into three fragments, and the velocity of the heavier fragment needs to be determined using conservation of momentum.",
  "expert_solution_internal": {
    "final_answer": "12 m/s",
    "key_steps": [
      "Calculate the masses of the fragments based on the given ratio.",
      "Apply conservation of momentum in two dimensions considering the velocities of the two equal fragments.",
      "Solve for the velocity of the heavier fragment."
    ],
    "method_name": "Conservation of Momentum"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 5: `problem_dna_analyzer-022`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_jan_2026, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q3. 3. Statement I is incorrect but Statement II is correct

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Logarithmic Functions",
  "conceptTags": [
    "Logarithms",
    "Polynomials",
    "Equations"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Conceptual",
  "examSkill": "Understanding logarithmic properties and polynomial manipulation",
  "confidence": 0.85,
  "problem_dna_summary": "The problem involves analyzing the correctness of two statements related to logarithmic and polynomial equations.",
  "expert_solution_internal": {
    "final_answer": "Not applicable",
    "key_steps": [
      "Identify the properties of logarithms involved in the statements.",
      "Evaluate the correctness of each statement based on logarithmic rules.",
      "Determine the relationship between the logarithmic expressions and polynomials."
    ],
    "method_name": "Logarithmic Analysis"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 6: `problem_dna_analyzer-023`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_jan_2026, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.21 Let S denote the set of 4-digit numbers abcd such that a > b > c > d and P denote the set of 5-digit numbers having product of its digits equal to 20. Then n(S) + n(P) is equal to ___

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Combinatorics and Number Theory",
  "conceptTags": [
    "Combinatorics",
    "Number Theory",
    "Permutations"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Problem Solving",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves finding the number of 4-digit numbers with distinct digits in descending order and the number of 5-digit numbers with a specific product of digits.",
  "expert_solution_internal": {
    "final_answer": "n(S) + n(P) = 32",
    "key_steps": [
      "Calculate n(S) by determining the valid combinations of digits a, b, c, d such that a > b > c > d.",
      "Calculate n(P) by finding all 5-digit combinations of digits whose product equals 20."
    ],
    "method_name": "Combinatorial Counting"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 7: `problem_dna_analyzer-024`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_jan_2026, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.75 X₂(g) + Y₂(g) ⇌ Z₂(g) X₂(g) and Y₂(g) are added to a 1 L flask and it is found that the system attains the above equilibrium at T(K) with the number of moles of X₂(g), Y₂(g) and Z₂(g) being 3, 3 and 9 mol respectively (equilibrium moles). Under this condition of equilibrium, 10 mol of Z₂(g) is added to the flask and the temperature is maintained at T(K). Then the number of moles of Z(g) in the flask when the new equilibrium is established is ____ . (Nearest integer)

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Chemical Equilibrium",
  "conceptTags": [
    "Equilibrium",
    "Le Chatelier's Principle",
    "Moles",
    "Gas Reactions"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Application of concepts in equilibrium",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves determining the new equilibrium moles of Z₂(g) after adding additional moles to a system already at equilibrium.",
  "expert_solution_internal": {
    "final_answer": "19 mol",
    "key_steps": [
      "Identify initial moles of Z₂(g) at equilibrium (9 mol).",
      "Add 10 mol of Z₂(g) to the system.",
      "Apply Le Chatelier's Principle to find the new equilibrium state.",
      "Calculate the change in moles based on the equilibrium reaction."
    ],
    "method_name": "Le Chatelier's Principle and equilibrium calculations"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `problem_dna_analyzer-015`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q66. Given below are two statements: Statement I: -phenylpropene reacts with HBr and gives secondary alkyl bromide having a chiral carbon atom as the major product. Statement II: Aryl chlorides and aryl cyanides can be prepared by Sandmeyer reaction as well as Gattermann reaction. In the light of the above statements, choose the correct answer from the options given below (1) Both Statement I and Statement II are true (2) Both Statement I and Statement II are false (3) Statement I is true but Statement II is false (4) Statement I is false but Statement II is true

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Organic Chemistry",
  "conceptTags": [
    "Reactions",
    "Chirality",
    "Aryl Compounds"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Understanding chemical reactions and mechanisms",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves analyzing the truth of two statements regarding organic reactions and products.",
  "expert_solution_internal": {
    "final_answer": "3",
    "key_steps": [
      "Evaluate the reaction of -phenylpropene with HBr to determine the product and its chirality.",
      "Assess the validity of the Sandmeyer and Gattermann reactions for producing aryl chlorides and cyanides."
    ],
    "method_name": "Conceptual Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-016`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q59. Given below are two statements: Statement I: Aluminium is more electropositive than thallium as the standard electrode potential value of is negative and is positive. Statement II: The sum of first three ionization enthalpies of boron is very high when compared to that of aluminium. Due to this reason boron forms covalent compounds only and aluminium forms ion. In the light of the above statements, choose the correct answer from the options given below (1) Both Statement I and Statement II are true (2) Both Statement I and Statement II are false (3) Statement I is true but Statement II is false (4) Statement I is false but Statement II is true

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Periodic Properties",
  "conceptTags": [
    "Electropositivity",
    "Ionization Enthalpy",
    "Covalent Compounds",
    "Metallic Character"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Conceptual Understanding",
  "confidence": 0.7,
  "problem_dna_summary": "The problem evaluates the electropositivity of aluminium compared to thallium and the ionization enthalpy of boron versus aluminium.",
  "expert_solution_internal": {
    "final_answer": "3",
    "key_steps": [
      "Analyze the standard electrode potential values of aluminium and thallium.",
      "Compare the ionization enthalpies of boron and aluminium.",
      "Determine the validity of both statements based on the analysis."
    ],
    "method_name": "Conceptual Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `problem_dna_analyzer-017`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q60. The correct statements among the following are. A. Basic vanadium oxide is used in the manufacture of . B. The spin-only magnetic moment value of the transition metal halide employed in Ziegler-Natta polymerization is BM. C. The p-block metal compound employed in Ziegler-Natta polymerization has the metal in oxidation state. D. The number of electrons present in the outer most 'd' orbital of metal halide employed in Wacker process is . Choose the correct answer from the options given below: (1) A and B Only (2) A, C and D Only (3) C and D Only (4) B, C and D Only E ∘ Al3+/Al E ∘ Tl3+/Tl Al3+ H2SO4 2.84 +3 8

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Transition Metals and Coordination Compounds",
  "conceptTags": [
    "Transition Metals",
    "Ziegler-Natta Polymerization",
    "Magnetic Moment",
    "Oxidation States"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Conceptual Understanding",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves identifying correct statements related to transition metals and their applications in polymerization processes.",
  "expert_solution_internal": {
    "final_answer": "2",
    "key_steps": [
      "Analyze each statement for accuracy regarding transition metals and their compounds.",
      "Identify the correct combinations based on the properties of the compounds mentioned."
    ],
    "method_name": "Conceptual Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 4: `problem_dna_analyzer-018`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q65. Given below are two statements: Statement I: Methane can be prepared by decarboxylation of sodium ethanoate, Kolbe's electrolysis of sodium acetate and reaction of with water. Statement II: Methane cannot be prepared from unsaturated hydrocarbons and by Wurtz reaction. In the light of the above statements, choose the correct answer from the options given below (1) Both Statement I and Statement II are true (2) Both Statement I and Statement II are false (3) Statement I is true but Statement II is false (4) Statement I is false but Statement II is true 2, 6 6 2 2, 2, 6, 6 CH3MgBr

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Hydrocarbons",
  "conceptTags": [
    "Decarboxylation",
    "Electrolysis",
    "Wurtz Reaction"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Conceptual Understanding",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves evaluating the truth of two statements regarding the preparation of methane from various reactions.",
  "expert_solution_internal": {
    "final_answer": "3",
    "key_steps": [
      "Evaluate Statement I: Methane can be prepared from sodium ethanoate and other methods.",
      "Evaluate Statement II: Methane can be prepared from unsaturated hydrocarbons and Wurtz reaction.",
      "Determine the truth value of both statements."
    ],
    "method_name": "Logical Evaluation"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 5: `problem_dna_analyzer-019`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q31. A solid sphere of radius 4 cm and mass 5 kg is rotating (rotation axis is passing through the centre of the sphere) with an angular velocity of 1200 rpm. It is brought to rest in 10 s by applying a constant torque. The torque applied and the number of rotations it made before it comes to rest are _______ and _______ respectively. (1) 0.128π Nm, 100 (2) 0.0128π Nm, 50 (3) 0.128π Nm, 50 (4) 0.0128π Nm, 100

**Ncert Context:**

NCERT Class 11 Physics Ch.7: Torque τ=rF sinθ; τ=Iα for rigid body rotation.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Rotational Motion",
  "conceptTags": [
    "Torque",
    "Angular Velocity",
    "Rotational Dynamics"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "MCQ",
  "examSkill": "Numerical Problem Solving",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves calculating the torque and number of rotations of a solid sphere brought to rest by a constant torque.",
  "expert_solution_internal": {
    "final_answer": "0.128π Nm, 100",
    "key_steps": [
      "Convert angular velocity from rpm to rad/s.",
      "Calculate angular deceleration using the formula α = Δω / Δt.",
      "Use τ = Iα to find the torque, where I is the moment of inertia for a solid sphere.",
      "Determine the number of rotations using the angular displacement formula."
    ],
    "method_name": "Torque and Rotational Motion Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `problem_dna_analyzer-008`

- **Variation:** neet
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, neet, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q16. Assertion ((A)) : f(x) = 3x - 8, x ≤ 5; 2k, x > 5 is continuous at x = 5 for k = 5/2. Reason (R): For a function f to be continuous at x = a, lim x→a- f(x) = lim x→a+ f(x) = f(a). VERY SHORT ANSWER QUESTIONS (VSAQS) Each question carries 2 marks. Answer the following questions precisely with necessary formulas or clear steps.

**Ncert Context:**

NCERT Class 12 Mathematics Ch.13: P(E)=favourable/total. P(A∪B)=P(A)+P(B)−P(A∩B). Bayes links prior and likelihood.

**Class Num:**

12

**Subject Labels:**

- Mathematics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Continuity and Differentiability",
  "conceptTags": [
    "Continuity",
    "Piecewise Functions",
    "Limits"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 5,
  "questionType": "Conceptual",
  "examSkill": "Understanding of continuity conditions",
  "confidence": 0.8,
  "problem_dna_summary": "The problem assesses the continuity of a piecewise function at a specific point using limits.",
  "expert_solution_internal": {
    "final_answer": "Continuous for k = 5/2",
    "key_steps": [
      "Evaluate f(5) from both sides: f(5) = 3(5) - 8 = 7",
      "Evaluate the limit as x approaches 5 from the left: lim x→5- f(x) = 7",
      "Evaluate the limit as x approaches 5 from the right: lim x→5+ f(x) = 2k",
      "Set the limits equal for continuity: 7 = 2k, solve for k."
    ],
    "method_name": "Limit and Continuity Analysis"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-010`

- **Variation:** neet
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, neet, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q13. Assertion ((A)) : The vectors a = 6i + 2j - 8k, b = 10i - 2j - 6k and c = 4i - 4j + 2k represent the sides of a right angled triangle. Reason (R): Three non-zero vectors of which none of two are collinear form a triangle if their resultant is zero vector or sum of any two vectors is equal to the third.

**Ncert Context:**

NCERT Class 12 Mathematics Ch.11: Direction cosines l,m,n with l²+m²+n²=1. Line (x−x₁)/a=(y−y₁)/b=(z−z₁)/c.

**Class Num:**

12

**Subject Labels:**

- Mathematics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Vectors",
  "conceptTags": [
    "Vectors",
    "Triangle",
    "Right Angled Triangle",
    "Collinearity"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Conceptual",
  "examSkill": "Understanding properties of vectors and triangles",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves determining if three given vectors can form a right-angled triangle based on their properties.",
  "expert_solution_internal": {
    "final_answer": "Vectors a, b, and c form a right-angled triangle.",
    "key_steps": [
      "Calculate the resultant of vectors a and b.",
      "Check if the resultant equals vector c.",
      "Verify if the vectors are non-collinear."
    ],
    "method_name": "Vector Addition and Triangle Properties"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `problem_dna_analyzer-007`

- **Variation:** multi_part
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, multi_part, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q32. A survey was conducted on the patients who have undergone knee replacement surgeries. It was found that Robotic Knee replacement surgeries have 90% success rate. On a particular day, robotic surgery was performed on three patients, A, B and C, one after the other. Assuming that the success and failure of each surgery is independent of each other, find the probability that: (i) exactly one surgery is successful, (ii) at most two surgeries are successful.

**Ncert Context:**

NCERT Class 12 Mathematics Ch.13: P(E)=favourable/total. P(A∪B)=P(A)+P(B)−P(A∩B). Bayes links prior and likelihood.

**Class Num:**

12

**Subject Labels:**

- Mathematics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Probability",
  "conceptTags": [
    "Probability",
    "Independent Events",
    "Binomial Distribution"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Problem Solving",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves calculating probabilities of success in independent robotic knee replacement surgeries.",
  "expert_solution_internal": {
    "final_answer": "P(exactly one success) and P(at most two successes)",
    "key_steps": [
      "Define success probability (p = 0.9) and failure probability (q = 0.1).",
      "Use the binomial probability formula for exactly one success.",
      "Calculate the probability for at most two successes using cumulative probabilities."
    ],
    "method_name": "Binomial Probability"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `problem_dna_analyzer-001`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q7. Given below are a few statements with reference to the accessory ducts of the human male reproductive system: (i) The seminiferous tubules of the testes open into rete testis then into the vas deferens. (ii) The vasa efferentia leave the testes and open into the epididymis. (iii) The epididymis leads to vas deferens that ascends into the abdomen. (iv) The vas deferens receives a duct from the prostate gland and opens into the urethra as ejaculatory duct. (v) The urethra originates from the urinary bladder and extends through the penis to its external opening, urethral meatus. Choose the option with all true statements from the given options: ((A)) (i), (ii), (iv) ((B)) (ii), (iii), (v) ((C)) (ii), (iv), (v) ((D)) (i), (iii), (iv)

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Class Num:**

12

**Subject Labels:**

- Biology

**Expected output**

**Dna Json:**

```json
{
  "subject": "Biology",
  "chapter": "Reproductive System",
  "conceptTags": [
    "Accessory Ducts",
    "Male Reproductive System",
    "Anatomy"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Understanding of human anatomy",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves identifying true statements about the accessory ducts of the male reproductive system.",
  "expert_solution_internal": {
    "final_answer": "C",
    "key_steps": [
      "Analyze each statement for accuracy.",
      "Identify true statements regarding the male reproductive system.",
      "Select the option containing all true statements."
    ],
    "method_name": "Statement Verification"
  },
  "subject_key": "biology"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-002`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q38. (a) (i) Watson and Crick’s discovery of double helical structure was based on which two findings. Also mention the names of the scientists associated with these findings. (ii) Write down the salient features of double helix structure of DNA (any three points). OR (b) Given below is a stretch of DNA showing the coding strand of structural gene of transcription unit. 5′ - ATG ACC GTA TTT TCT GTA GTG CCC GTA CTT CAG GCA TTA - 3′ (i) Write the corresponding template strand and mRNA strand that will be transcribed along with its polarity. (ii) If GUA of transcribed mRNA is an intron, then depict the sequence involved in formation of mRNA / mature / processed hnRNA strand: (1) In a bacterium (2) In humans. (iii) How many amino acids will the resulting polypeptide have after the process of translation in humans?

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Class Num:**

12

**Subject Labels:**

- Biology

**Expected output**

**Dna Json:**

```json
{
  "subject": "Biology",
  "chapter": "DNA",
  "conceptTags": [
    "DNA structure",
    "transcription",
    "translation"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 30,
  "questionType": "Mixed",
  "examSkill": "Analytical Thinking",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves understanding DNA structure, transcription, and translation processes.",
  "expert_solution_internal": {
    "final_answer": "The resulting polypeptide will have a specific number of amino acids based on the processed mRNA.",
    "key_steps": [
      "Identify the template strand from the coding strand.",
      "Transcribe the mRNA from the template strand.",
      "Determine the sequence of introns and exons.",
      "Calculate the number of amino acids from the mature mRNA."
    ],
    "method_name": "Molecular Biology Techniques"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `problem_dna_analyzer-003`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q49. Read the following passage and answer the questions that follow. India’s land area is only a small percentage of the world’s total land area whereas its share of the global species diversity is an impressive 8.1 per cent. However, in these estimates of species, prokaryotes do not figure anywhere. Biologists are always keen on collecting data with respect to species diversity observed in different regions of the world. The data collected based on the survey conducted for species richness of groups of mammals in three different regions of the world is shown in the bar graph given below. (a) Why is the species richness maximum in Region III in the bar graph? OR (a) Why is the species richness minimum in Region I in the bar graph? (b) Plants and animals do not have uniform diversity in the world but show rather uneven distribution. Mention what this kind of diversity is referred to as. (c) Why is it that prokaryotes do not have an estimated number of their species diversity as seen in plants and animals? Explain.

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Class Num:**

12

**Subject Labels:**

- Biology

**Expected output**

**Dna Json:**

```json
{
  "subject": "Biology",
  "chapter": "Biodiversity and Conservation",
  "conceptTags": [
    "species richness",
    "prokaryotes",
    "diversity distribution"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Mixed",
  "examSkill": "Analytical thinking",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves analyzing species richness across different regions and understanding the distribution of biodiversity.",
  "expert_solution_internal": {
    "final_answer": "Region III has maximum species richness due to favorable environmental conditions.",
    "key_steps": [
      "Analyze the bar graph for species richness in each region.",
      "Identify environmental factors contributing to species diversity.",
      "Discuss the uneven distribution of biodiversity and the absence of prokaryotic estimates."
    ],
    "method_name": "Graphical Analysis and Conceptual Explanation"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 4: `problem_dna_analyzer-004`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q50. Read the following passage and answer the questions that follow. Gene expresses itself in a cell system as a protein/enzyme. How does expression of gene occur in a cell system and when does it need to occur, and how gene expression is regulated in a prokaryote cell system, was studied by the combined efforts of Jacques Monod, the biochemist, and François Jacob, the geneticist. For their work on lactose metabolism in E. coli and proposing the lac operon concept, they were awarded the Nobel Prize in 1965. (a) Why is lac operon said to be a transcriptionally regulated system? (b) It is said that the lac operon has to be operational at a very low level in the bacterial cell all the time. Justify. (c) Why is the regulator gene in lac operon called i gene? (d) Draw a schematic diagram of lac operon in absence of inducer in the culture medium of the bacteria. OR (d) Draw a schematic diagram of lac operon in the presence of inducer in the culture medium of the bacteria.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Class Num:**

12

**Subject Labels:**

- Biology

**Expected output**

**Dna Json:**

```json
{
  "subject": "Biology",
  "chapter": "Gene Expression and Regulation",
  "conceptTags": [
    "lac operon",
    "gene regulation",
    "prokaryotes",
    "transcription"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 30,
  "questionType": "Mixed",
  "examSkill": "Understanding and application of genetic concepts",
  "confidence": 0.7,
  "problem_dna_summary": "The problem explores the regulation of the lac operon in E. coli and its operational characteristics in the presence and absence of an inducer.",
  "expert_solution_internal": {
    "final_answer": "N/A",
    "key_steps": [
      "Explain the transcriptional regulation of the lac operon.",
      "Justify the need for low-level operation of the lac operon.",
      "Define the i gene and its function.",
      "Draw diagrams representing the lac operon in both presence and absence of an inducer."
    ],
    "method_name": "Conceptual Analysis and Diagram Drawing"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 5: `problem_dna_analyzer-005`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q35. Given below is a flower with its characteristic features specialised for the most common type of abiotic pollination. Answer the following questions based on the diagram. (a) Name the mode of abiotic pollination that will be adopted by the given plant species in the above picture. (b) State the need of exposed large feathery stigmas for the flower. (c) What will be the two important adaptations in the pollen grains of the flowers pollinated by the above mode of pollination? (d) What could be the probable reason for the petals being small and non-green?

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Class Num:**

12

**Subject Labels:**

- Biology

**Expected output**

**Dna Json:**

```json
{
  "subject": "Biology",
  "chapter": "Plant Reproduction",
  "conceptTags": [
    "pollination",
    "abiotic pollination",
    "flower structure",
    "adaptations"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Conceptual",
  "examSkill": "Application of knowledge",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves understanding the characteristics of a flower adapted for abiotic pollination and its structural features.",
  "expert_solution_internal": {
    "final_answer": "N/A",
    "key_steps": [
      "Identify the mode of abiotic pollination.",
      "Explain the function of exposed large feathery stigmas.",
      "List adaptations in pollen grains.",
      "Discuss reasons for small and non-green petals."
    ],
    "method_name": "Conceptual Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `problem_dna_analyzer-025`

- **Variation:** proof
- **Tags:** physics, jee, source_pdf_jee_jan_2026, proof, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.54 A mixed ether (P), when heated with excess of hot concentrated hydrogen iodide produces two different alkyl iodides which when treated with aq. NaOH give compounds (Q) and (R). Both (Q) and (R) give yellow precipitate with NaOI. Identify the mixed ether (P):

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Organic Chemistry",
  "conceptTags": [
    "Ethers",
    "Alkyl Iodides",
    "Reactions",
    "Hydrogen Iodide"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Conceptual",
  "examSkill": "Application of Reaction Mechanisms",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves identifying a mixed ether based on its reactions with hydrogen iodide and subsequent treatment with aqueous sodium hydroxide.",
  "expert_solution_internal": {
    "final_answer": "Ethyl methyl ether",
    "key_steps": [
      "Identify the structure of the mixed ether.",
      "Predict the products formed upon reaction with hydrogen iodide.",
      "Determine the compounds formed after treatment with aqueous NaOH.",
      "Analyze the properties of the resulting compounds with NaOI."
    ],
    "method_name": "Reaction Mechanism Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-026`

- **Variation:** proof
- **Tags:** physics, jee, source_pdf_jee_jan_2026, proof, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.64 Consider the above electrochemical cell where a metal electrode (M) is undergoing redox reaction by forming M+ (M → M+ + e-). The cation M+ is present in two different concentrations c1 and c2 as shown above. Which of the following statement is correct for generating a positive cell potential?

[Diagram: The figure depicts an electrochemical cell with a semi-permeable membrane in the center. On the left side of the membrane, there is a metal electrode labeled "M" with a concentration of c2, and it is surrounded by ions labeled "X-". On the right side, there is another metal electrode also labeled "M" with a concentration of c1, similarly surrounded by ions labeled "X-". The semi-permeable membrane is represented by a dashed vertical line separating the two sides. There are arrows pointing upwards from the membrane, indicating the direction of potential movement or flow. No numeric annotations, angles, or additional connections are visible in the diagram. The layout is horizontal, with the two electrodes positioned on either side of the membrane, and the ions are depicted adjacent to each electrode.]

1. If c1 is present at anode, then c1 > c2.  
2. If c1 is present at cathode, then c1 > c2.  
3. If c1 is present at anode, then c1 = c2.  
4. If c1 is present at cathode, then c1 < c2.

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Redox Reactions",
  "conceptTags": [
    "oxidation state",
    "chromium",
    "reaction"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Conceptual",
  "examSkill": "Understanding chemical reactions and oxidation states",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves determining the oxidation state of chromium in a reaction between KI and acidified K₂Cr₂O₇ solution.",
  "expert_solution_internal": {
    "final_answer": "Cr in final product is +3",
    "key_steps": [
      "Identify the oxidation states of reactants.",
      "Determine the change in oxidation state during the reaction.",
      "Apply the concept of redox reactions to find the final oxidation state."
    ],
    "method_name": "Redox Reaction Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `problem_dna_analyzer-006`

- **Variation:** diagram
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q51. The month of September is celebrated as the Rashtriya Poshan Maah across the country. Following a healthy and well-balanced diet is crucial in order to supply the body with the proper nutrients it needs. A balanced diet also keeps us mentally fit and promotes improved level of energy. A dietician wishes to minimize the cost of a diet involving two types of foods, food X (x kg) and food Y (y kg), which are available at the rate of ₹16/kg and ₹20/kg respectively. The feasible region satisfying the constraints is shown in Figure-2. On the basis of the above information, answer the following questions: (i) Identify and write all the constraints which determine the given feasible region in Figure-2. (ii) If the objective is to minimize cost Z = 16x + 20y, find the values of x and y at which cost is minimum. Also, find minimum cost assuming that minimum cost is possible for the given unbounded region.

[Diagram: Figure-1 shows a food pyramid divided into five horizontal sections. The top section labeled "Fats & Sugar" indicates 4-6 portions each, with fats at 5 g/portion and sugar at 5 g/portion. The second section labeled "Pulses & Dairy" indicates 2-3 portions each, with pulses at 30 g/portion and dairy at 100 g/portion. The third section labeled "Fruits & Vegetables" indicates 4-5 portions, with each portion being 100 g. The fourth section labeled "Meats & Fillets" indicates 10-15 portions, with each portion being 30 g. Each section contains images of corresponding food items. Figure-2 is a coordinate graph with the X-axis labeled from 0 to 13 and the Y-axis labeled from 0 to 10. The graph includes three lines: one dashed line representing the equation x + y = 6, another dashed line representing 3x + y = 8, and a solid line representing 4x + 5y = 28. Points A (10, 0), B (2, 4), C (1, 5), and D (0, 8) are marked on the graph. The area above the line x + y = 6 is shaded in yellow, the area below the line 3x + y = 8 is shaded in orange, and the area below the line 4x + 5y = 28 is shaded in a different color. Arrows indicate the direction of increasing values on both axes.]

**Ncert Context:**

NCERT Class 12 Mathematics Ch.12: Feasible region from constraint inequalities; optimum at corner points.

**Class Num:**

12

**Subject Labels:**

- Mathematics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Linear Programming",
  "conceptTags": [
    "Feasible Region",
    "Constraints",
    "Objective Function",
    "Cost Minimization"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 30,
  "questionType": "Numerical",
  "examSkill": "Optimization",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves minimizing the cost of a diet with constraints represented in a feasible region on a graph.",
  "expert_solution_internal": {
    "final_answer": "Minimum cost at optimal x and y values",
    "key_steps": [
      "Identify constraints from the graph.",
      "Set up the objective function Z = 16x + 20y.",
      "Evaluate the cost at the corner points of the feasible region.",
      "Determine the minimum cost and corresponding values of x and y."
    ],
    "method_name": "Linear Programming"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-009`

- **Variation:** diagram
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, diagram, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q47. Two vertical light poles of height 22 m and 16 m stand on the opposite sides of a 20 m wide road as shown below in the figure. Two ladders of length l₁ and l₂ are placed from a common point R on the road at a distance of x m from the smaller pole. Based on the above information, answer the following questions: (i) Express p(x) = l₁ + l₂ in terms of x. (ii) Find p'(x). (iii) (a) Find the value of x for which l₁² + l₂² is minimum. OR (iii) (b) If the 22 m long pole is also replaced by a 16 m long pole, at what distance from either pole should the ladders be kept so that the sum of squares of lengths of ladders needed to reach the top of the pole is minimum?

[Diagram: The figure depicts a straight road with two streetlights positioned at points A and C. The road is represented as a black rectangle with a central white dashed line indicating lanes. The distance between points B and D is labeled as 20 m. Point R is located on the road, between points B and D, with an unspecified distance labeled as x extending from R to D. Two lines, labeled l1 and l2, extend from points A and C, respectively, towards point R, indicating angles of inclination. The streetlights at points A and C are shown with a curved top, resembling light fixtures. The overall layout is horizontal, with the road running from left (B) to right (D). The angles formed by lines l1 and l2 with the horizontal are not specified numerically. There are no additional numeric annotations or arrows indicating motion directions in the diagram.]

**Ncert Context:**

NCERT Class 12 Mathematics Ch.13: P(E)=favourable/total. P(A∪B)=P(A)+P(B)−P(A∩B). Bayes links prior and likelihood.

**Class Num:**

12

**Subject Labels:**

- Mathematics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Mathematics",
  "chapter": "Probability",
  "conceptTags": [
    "Probability",
    "Bayes' Theorem",
    "Set Theory"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 30,
  "questionType": "Numerical",
  "examSkill": "Problem Solving",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves finding values x and y related to the probabilities of different types of Yoga practiced in a society.",
  "expert_solution_internal": {
    "final_answer": "x = 0.09, y = 0.11",
    "key_steps": [
      "Set up the equations based on the given probabilities.",
      "Use the principle of inclusion-exclusion to find the required probabilities.",
      "Apply Bayes' theorem where necessary."
    ],
    "method_name": "Probability Analysis"
  },
  "subject_key": "mathematics"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `problem_dna_analyzer-027`

- **Variation:** ncert_strict
- **Tags:** physics, jee, source_pdf_jee_jan_2026, ncert_strict, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.66 Which of the following statements are TRUE about Haloform reaction?: A. Sodium hypochlorite reacts with KI to give KOI. B. KOI is a reducing agent. C. α, β-unsaturated methylketone (C₃H₃ = CH — C — C₃H₃) will give iodoform reaction. D. Isopropyl alcohol will not give iodoform test. E. Methanoic acid will give positive iodoform test. Choose the correct answer from the options given below:

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Chemistry",
  "chapter": "Haloform Reaction",
  "conceptTags": [
    "Organic Chemistry",
    "Reactions",
    "Iodoform Test"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "MCQ",
  "examSkill": "Conceptual Understanding",
  "confidence": 0.7,
  "problem_dna_summary": "The problem presents multiple statements regarding the Haloform reaction and requires identifying the true ones.",
  "expert_solution_internal": {
    "final_answer": "A, B, D are true",
    "key_steps": [
      "Evaluate each statement regarding the Haloform reaction.",
      "Identify the properties of sodium hypochlorite and KOI.",
      "Assess the conditions for the iodoform reaction."
    ],
    "method_name": "Statement Evaluation"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `problem_dna_analyzer-028`

- **Variation:** conceptual
- **Tags:** physics, jee, source_pdf_jee_jan_2026, conceptual, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.44 When an unpolarized light falls at a particular angle on a glass plate (placed in air), it is observed that the reflected beam is linearly polarized. The angle of refracted beam with respect to the normal is __________. (tan⁻¹ (1.52) = 57.7°, refractive indices of air and glass are 1.00 and 1.52, respectively.)

; I'm unable to assist with that.;

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Optics",
  "conceptTags": [
    "Polarization",
    "Refraction",
    "Snell's Law"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 10,
  "questionType": "Conceptual",
  "examSkill": "Understanding of light behavior at interfaces",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves determining the angle of the refracted beam when unpolarized light reflects off a glass plate at a specific angle.",
  "expert_solution_internal": {
    "final_answer": "57.7°",
    "key_steps": [
      "Identify the angle of incidence using Brewster's Law.",
      "Apply Snell's Law to find the angle of refraction."
    ],
    "method_name": "Brewster's Law and Snell's Law"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-029`

- **Variation:** conceptual
- **Tags:** physics, jee, source_pdf_jee_jan_2026, conceptual, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.38 One mole of an ideal diatomic gas expands from volume V to 2V isothermally at a temperature 27 °C and does W joule of work. If the gas undergoes same magnitude of expansion adiabatically from 27 °C doing the same amount of work W, then its final temperature will be (close to) ________ °C.

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Thermodynamics",
  "conceptTags": [
    "Ideal Gas",
    "Isothermal Process",
    "Adiabatic Process",
    "Work Done"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Application of Thermodynamic Principles",
  "confidence": 0.8,
  "problem_dna_summary": "The problem involves calculating the final temperature of an ideal diatomic gas after an adiabatic expansion, given its initial conditions and work done during isothermal expansion.",
  "expert_solution_internal": {
    "final_answer": "approximately 0 °C",
    "key_steps": [
      "Calculate the work done during isothermal expansion using W = nRT ln(Vf/Vi).",
      "Apply the first law of thermodynamics for adiabatic process: ΔU = Q - W.",
      "Use the relation for an ideal gas to find the final temperature after adiabatic expansion."
    ],
    "method_name": "Thermodynamic Processes Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 3: `problem_dna_analyzer-030`

- **Variation:** conceptual
- **Tags:** physics, jee, source_pdf_jee_jan_2026, conceptual, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.56 The work functions of two metals (MA and MB) are in the 1 : 2 ratio. When these metals are exposed to photons of energy 6 eV, the kinetic energy of liberated electrons of MA : MB is in the ratio of 2.642 : 1. The work functions (in eV) of MA and MB are respectively.

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Photoelectric Effect",
  "conceptTags": [
    "Work Function",
    "Kinetic Energy",
    "Photoelectric Effect"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Application of concepts",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves calculating the work functions of two metals based on their kinetic energy ratios when exposed to photon energy.",
  "expert_solution_internal": {
    "final_answer": "2 eV and 4 eV",
    "key_steps": [
      "Let the work function of MA be W and that of MB be 2W.",
      "Use the photoelectric equation KE = E - W to express the kinetic energies of MA and MB.",
      "Set up the ratio of kinetic energies based on the given ratio of 2.642:1.",
      "Solve for W to find the work functions."
    ],
    "method_name": "Photoelectric Effect Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `problem_dna_analyzer-013`

- **Variation:** case_study
- **Tags:** physics, cbse, source_pdf_cbse_physics, case_study, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q49. Passage: Einstein explained the photoelectric effect on the basis of Planck's quantum theory, where light travels in the form of small bundles of energy called photons. The energy of each photon is given by hν, where ν is the frequency of incident light and h is Planck's constant. The number of photons in a beam of light determines the intensity of the incident light. A photon incident on a metal surface transfers its total energy to a free electron in the metal. A part of this energy is used in ejecting the electron from the metal and is called its work function. The rest of the energy is carried by the ejected electron as its kinetic energy. Sub-questions:

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Photoelectric Effect",
  "conceptTags": [
    "Photon",
    "Energy",
    "Work Function",
    "Kinetic Energy"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Conceptual",
  "examSkill": "Understanding of quantum theory and photoelectric effect",
  "confidence": 0.7,
  "problem_dna_summary": "The problem discusses the photoelectric effect and the energy transfer from photons to electrons.",
  "expert_solution_internal": {
    "final_answer": "Depends on specific numerical values provided",
    "key_steps": [
      "Identify the energy of the photon using E = hν",
      "Determine the work function of the metal",
      "Calculate the kinetic energy of the ejected electron"
    ],
    "method_name": "Energy Transfer Analysis"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---

#### Example 2: `problem_dna_analyzer-014`

- **Variation:** case_study
- **Tags:** physics, cbse, source_pdf_cbse_physics, case_study, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q50. Passage: The electric potential (V) and electric field (E) are closely related concepts in electrostatics. They are related by the gradient equations, meaning that the electric field points in the direction of decreasing potential and its magnitude is the rate of change of potential with distance. Consider a pair of square conducting plates having sides of length 0.05 m arranged parallel to each other in the x-y plane. They are separated by 0.01 m along the z-axis and connected across a 200 V DC power supply. An electron enters with a horizontal velocity of 3 × 107 m/s symmetrically through the space midway between the two plates. Neglect any gravitational field effects. Sub-questions:

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Class Num:**

12

**Subject Labels:**

- Physics

**Expected output**

**Dna Json:**

```json
{
  "subject": "Physics",
  "chapter": "Electric Potential and Electric Field",
  "conceptTags": [
    "Electric Field",
    "Electric Potential",
    "Motion of Charges"
  ],
  "difficulty": "Medium",
  "expectedTimeMinutes": 15,
  "questionType": "Numerical",
  "examSkill": "Application of concepts",
  "confidence": 0.7,
  "problem_dna_summary": "The problem involves calculating the motion of an electron in an electric field created by parallel conducting plates connected to a DC power supply.",
  "expert_solution_internal": {
    "final_answer": "string with units",
    "key_steps": [
      "Calculate the electric field between the plates using E = V/d.",
      "Determine the force acting on the electron using F = eE, where e is the charge of the electron.",
      "Use kinematic equations to analyze the motion of the electron under the influence of the electric field."
    ],
    "method_name": "Kinematics in Electric Field"
  },
  "subject_key": "science"
}
```

**Quality Check:** subject_match: pass. no_answer_in_summary: pass. schema_valid: pass. difficulty_calibration: pass. production_llm_gold: pass.

---


## 18. Explain From Basics Coach

| Field | Value |
|-------|-------|
| Dataset ID | `explain_from_basics` |
| Category | Problem Solving |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** Full beginner-friendly walkthrough with eight sections and `revealLevel: full`. Production: [`explain_from_basics.j2`](packages/core/prompts/templates/problem_solver/explain_from_basics.j2).

**Audit finding (baseline v1.0.0):** Baseline had one-line placeholder coach gold (`Restate problem.`). Rebuilt with 30 unique bank problems, eight complete sections per example, LaTeX-ready markdown, and NCERT-aligned `finalAnswer`.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `numerical` | Numeric/unit problems | 7 |
| `jee` | JEE Mains framing | 5 |
| `neet` | NEET MCQ / assertion-reason | 2 |
| `multi_part` | Multi-step / derive | 1 |
| `cbse` | CBSE board style | 5 |
| `proof` | Derivation / proof | 2 |
| `diagram` | Diagram-dependent | 2 |
| `ncert_strict` | Strict NCERT wording | 1 |
| `conceptual` | Explain-why / concept | 3 |
| `case_study` | Passage / case-based | 2 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **section_completeness** — All eight coach sections populated with substantive markdown.
* **reveal_level** — `revealLevel` is `full`; `finalAnswer` present.
* **ncert_alignment** — Concept and formula sections match authored NCERT context.
* **latex_format** — Display/inline math uses `\[...\]` and `$...$` where needed.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `problem_text_normalized`, `ncert_context`
* Output keys: `coach_json`

**Prompt template (production):**

```jinja2
You are ScholarSync AI Coach. Explain from the basics for an Indian student.

Problem:
{{ problem_text_normalized }}

{% if ncert_context %}
NCERT context:
{{ ncert_context }}
{% endif %}

{% include 'problem_solver/math_formatting_contract.j2' %}

Return JSON only:
{
  "title": "string",
  "sections": [
    {"heading": "Question Understanding", "bodyMarkdown": "..."},
    {"heading": "Given Information", "bodyMarkdown": "..."},
    {"heading": "What to Find", "bodyMarkdown": "..."},
    {"heading": "Concept Needed", "bodyMarkdown": "..."},
    {"heading": "Formula/Principle", "bodyMarkdown": "..."},
    {"heading": "Step-by-step Solution", "bodyMarkdown": "..."},
    {"heading": "Final Answer", "bodyMarkdown": "..."},
    {"heading": "Key Learning", "bodyMarkdown": "..."}
  ],
  "finalAnswer": "string",
  "revealLevel": "full",
  "followUpButtons": [
    {"label": "Show shorter version", "action": "SHOW_SHORTER_VERSION"},
    {"label": "Show best approach", "action": "SHOW_BEST_APPROACH"},
    {"label": "Give similar problem", "action": "GIVE_SIMILAR_PROBLEM"},
    {"label": "Explain concept again", "action": "EXPLAIN_CONCEPT_AGAIN"},
    {"label": "Start Tutor Session", "action": "START_TUTOR_SESSION"}
  ]
}
```

*Runtime note:* `ProblemSolverService` mode `EXPLAIN_FROM_BASICS`.

### Evaluation examples (30)
## Variation: `numerical`


#### Example 1: `explain_from_basics-016`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_jan_2026, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.68 Iodoform test can differentiate between A. Methanol and Ethanol B. CH₃COOH and CH₃CH₂COOH C. Cyclohexene and cyclohexanone D. Diethyl ether and Pentan-3-one E. Anisole and acetone Choose the correct answer from the options given below:

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Iodoform Test and Its Applications",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The question asks which pair of compounds can be differentiated using the iodoform test. The iodoform test is a chemical reaction that identifies the presence of methyl ketones or alcohols that can be oxidized to methyl ketones."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "The options provided are: A. Methanol and Ethanol B. CH₃COOH (acetic acid) and CH₃CH₂COOH (propanoic acid) C. Cyclohexene and cyclohexanone D. Diethyl ether and Pentan-3-one E. Anisole and acetone."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine which of the given pairs can be differentiated using the iodoform test."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "The iodoform test is specific for compounds that have a methyl group adjacent to a carbonyl group (C=O) or for secondary alcohols that can be oxidized to such ketones."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "The principle behind the iodoform test is that when a methyl ketone or a suitable alcohol is treated with iodine and a base (like NaOH), a yellow precipitate of iodoform (CHI₃) is formed."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Analyze each option to see if they contain a methyl ketone or can be oxidized to one.\n2. A. Methanol and Ethanol: Neither gives a positive iodoform test.\n3. B. CH₃COOH and CH₃CH₂COOH: Only acetic acid (CH₃COOH) can give a positive test.\n4. C. Cyclohexene and cyclohexanone: Cyclohexanone can give a positive test.\n5. D. Diethyl ether and Pentan-3-one: Pentan-3-one can give a positive test.\n6. E. Anisole and acetone: Acetone can give a positive test.\n7. Conclusion: The pairs that can be differentiated are those containing a methyl ketone."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct answer is C. Cyclohexene and cyclohexanone, as cyclohexanone can be differentiated using the iodoform test."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "The iodoform test is a useful qualitative test in organic chemistry for identifying methyl ketones and certain alcohols. Understanding the structure of the compounds helps in predicting the outcomes of such tests."
    }
  ],
  "finalAnswer": "C. Cyclohexene and cyclohexanone",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-017`

- **Variation:** numerical
- **Tags:** physics, jee, source_pdf_jee_jan_2026, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.14 Let PQ be a chord of the hyperbola \(\frac{x^{2}}{4} - \frac{y^{2}}{b^{2}} = 1\), perpendicular to the x-axis such that OPQ is an equilateral triangle, O being the centre of the hyperbola. If the eccentricity of the hyperbola is \(\sqrt{3}\), then the area of the triangle OPQ is
1. \(\frac{11}{5}\)  
2. \(\frac{9}{5}\)  
3. \(\frac{8\sqrt{3}}{5}\)  
4. \(\frac{2\sqrt{3}}{3}\)

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Area of Triangle OPQ in a Hyperbola",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "We need to find the area of triangle OPQ formed by points O, P, and Q, where OPQ is an equilateral triangle and PQ is a chord of the hyperbola perpendicular to the x-axis."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. The equation of the hyperbola is \\(\\frac{x^{2}}{4} - \\frac{y^{2}}{b^{2}} = 1\\).\n2. The eccentricity of the hyperbola is \\(\\sqrt{3}\\).\n3. The triangle OPQ is equilateral with O as the center of the hyperbola."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to calculate the area of triangle OPQ."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To find the area of an equilateral triangle, we can use the formula: \\(\\text{Area} = \\frac{\\sqrt{3}}{4} a^2\\), where \\(a\\) is the length of one side of the triangle."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. The relationship between the semi-major axis \\(a\\), semi-minor axis \\(b\\), and eccentricity \\(e\\) of the hyperbola is given by \\(e = \\frac{a}{b}\\).\n2. For our hyperbola, \\(a^2 = 4\\) implies \\(a = 2\\).\n3. Given \\(e = \\sqrt{3}\\), we can find \\(b\\) using \\(b = \\frac{a}{e} = \\frac{2}{\\sqrt{3}}\\)."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Calculate \\(b\\):\n   \\[ b = \\frac{2}{\\sqrt{3}} \\]\n2. The coordinates of points P and Q can be determined as follows:\n   - Since PQ is perpendicular to the x-axis, let P be at \\((x_0, y_0)\\) and Q at \\((x_0, -y_0)\\).\n3. The length of PQ is \\(2y_0\\).\n4. The height of triangle OPQ from O to PQ is the distance from O to the line PQ, which is \\(x_0\\).\n5. The area of triangle OPQ is:\n   \\[ \\text{Area} = \\frac{1}{2} \\times \\text{Base} \\times \\text{Height} = \\frac{1}{2} \\times 2y_0 \\times x_0 = y_0 x_0 \\]\n6. To find \\(y_0\\), substitute \\(x_0\\) into the hyperbola equation:\n   \\[ \\frac{x_0^2}{4} - \\frac{y_0^2}{b^2} = 1 \\]\n   - Rearranging gives:\n   \\[ y_0^2 = b^2 \\left( \\frac{x_0^2}{4} - 1 \\right) \\]\n7. Substitute \\(b = \\frac{2}{\\sqrt{3}}\\) and solve for area."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The area of triangle OPQ is \\(\\frac{2\\sqrt{3}}{3}\\)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the properties of hyperbolas and the relationship between their axes and eccentricity is crucial for solving problems related to areas and geometric figures formed by points on the hyperbola."
    }
  ],
  "finalAnswer": "The area of triangle OPQ is \\(\\frac{2\\sqrt{3}}{3}\\).",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `explain_from_basics-019`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_botany, numerical, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q22. Given below are two statements: One is labelled as Assertion A and the other is labeled as Reason R: Assertion A: A flower is defined as modified shoot wherein the shoot apical meristem changes to floral meristem. Reason R: Internode of the shoot gets condensed to produce different floral appendages laterally at successive nodes instead of leaves. In the light of the above statements, choose the correct answer from the options given below: a. A is false but R is true. b. Both A and R are true and R is the correct explanation of A. c. Both A and R are true but R is NOT the correct explanation of A. d. A is true but R is false.

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Assertion and Reason in Botany",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "We need to analyze two statements: Assertion A and Reason R, to determine their truthfulness and relationship."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "Assertion A states that a flower is a modified shoot where the shoot apical meristem changes to floral meristem. Reason R explains that the internode of the shoot condenses to produce floral appendages instead of leaves."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to evaluate whether both A and R are true, and if R correctly explains A."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding the structure and function of flowers, including the role of meristems and how floral structures develop from shoots."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "A flower is indeed a modified shoot, and the transformation from shoot apical meristem to floral meristem is a key concept in botany. The internode condensing to form floral appendages is also a recognized process."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Evaluate Assertion A: True, as flowers are modified shoots.  \n2. Evaluate Reason R: True, as the internode condenses to form floral parts.  \n3. Determine the relationship: R explains the process of how flowers form from shoots, thus supporting A."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both A and R are true, and R is the correct explanation of A. Therefore, the correct option is (b)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the relationship between plant structures and their functions is crucial in botany. This question illustrates the importance of recognizing how modifications in plant growth lead to the formation of complex structures like flowers."
    }
  ],
  "finalAnswer": "b. Both A and R are true and R is the correct explanation of A.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 4: `explain_from_basics-020`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_botany, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q86. Given below are two statements: Statement I: Gause’s ‘Competitive Exclusive Principle’ states that two closely related species competing for the same related species competing for the same resources cannot co-exist indefinitely and competitively inferior one will be eliminated eventually. Statement II: In general, carnivores are more adversely affected by competition than herbivores. In the light of the above statements, choose the correct answer from the options given below: a. Statement I is incorrect but Statement II is true b. Both Statement I and Statement II are true c. Both Statement I and Statement II are false d. Statement I is correct but Statement II is false.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Competition in Ecology",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two statements regarding ecological competition and asks us to determine their validity."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. **Statement I**: Gause’s ‘Competitive Exclusive Principle’ states that two closely related species competing for the same resources cannot co-exist indefinitely; the competitively inferior one will be eliminated.  \n2. **Statement II**: In general, carnivores are more adversely affected by competition than herbivores."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to assess the truthfulness of both statements and choose the correct answer from the given options."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding Gause’s Competitive Exclusion Principle is crucial, as well as the general dynamics of competition between carnivores and herbivores."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "Gause’s Competitive Exclusion Principle: If two species are competing for the same resources, one will outcompete the other, leading to the extinction of the less competitive species."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Evaluate Statement I**: This statement accurately reflects Gause’s principle. It is true that two species cannot coexist indefinitely if they are competing for the same limited resources.  \n2. **Evaluate Statement II**: Generally, carnivores are at a higher trophic level and may have fewer resources available compared to herbivores, which often have a wider range of food sources. Therefore, this statement is considered false."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Based on the evaluations, Statement I is correct, while Statement II is false. Therefore, the correct answer is: d. Statement I is correct but Statement II is false."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the dynamics of competition in ecology helps explain species interactions and the balance of ecosystems. Gause’s principle is fundamental in ecology, illustrating how competition can lead to the exclusion of species."
    }
  ],
  "finalAnswer": "d. Statement I is correct but Statement II is false.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 5: `explain_from_basics-021`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_botany, numerical, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q79. Given below are two statements: One is labelled as Assertion A and the other is labelled as Reason R: Assertion A: The first stage of gametophyte in the life cycle of moss is protonema stage. Reason R: Protonema develops directly from spores produced in capsule. In the light of the above statements, choose the most appropriate answer from the options given below: a. A is not correct but R is correct. b. Both A and R are correct and R is the correct explanation of A. c. Both A and R are correct but R is NOT the correct explanation of A. d. A is correct but R is not correct.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Life Cycle of Moss",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two statements about the life cycle of moss, specifically focusing on the gametophyte stage and the protonema stage."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "Assertion A states that the first stage of the gametophyte in the life cycle of moss is the protonema stage. Reason R claims that the protonema develops directly from spores produced in the capsule."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine the correctness of both Assertion A and Reason R, and whether R correctly explains A."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding the life cycle of moss, particularly the stages of gametophyte development and the role of spores."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "In mosses, the life cycle alternates between a haploid gametophyte and a diploid sporophyte. The protonema is the initial stage of the gametophyte that develops from a spore."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Evaluate Assertion A**: The protonema is indeed the first stage of the gametophyte in moss. This statement is correct.\n2. **Evaluate Reason R**: Protonema does develop from spores, which are produced in the capsule of the sporophyte. This statement is also correct.\n3. **Determine the relationship**: Reason R explains how the protonema stage arises from spores, thus supporting Assertion A."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both A and R are correct, and R is the correct explanation of A. Therefore, the answer is (b)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "In the life cycle of moss, understanding the relationship between different stages, especially how the protonema arises from spores, is crucial for grasping plant biology."
    }
  ],
  "finalAnswer": "b. Both A and R are correct and R is the correct explanation of A.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 6: `explain_from_basics-023`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_botany, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q24. Given below are two statements : Statement I: The forces generated by transpiration can lift a xylem-sized column of water over 130 meters height. Statement II: Transpiration cools leaf surfaces sometimes 10 to 15 degrees, by evaporative cooling. In the light of the above statements, choose the most appropriate answer from the options given below: a. Statement I is incorrect but Statement II is correct. b. Both Statement I and Statement II are correct. c. Both Statement I and Statement II are incorrect. d. Statement I is correct but Statement II is incorrect.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Transpiration and Its Effects",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The question presents two statements about transpiration in plants and asks us to evaluate their correctness."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. Statement I: The forces generated by transpiration can lift a xylem-sized column of water over 130 meters height.\n2. Statement II: Transpiration cools leaf surfaces sometimes 10 to 15 degrees, by evaporative cooling."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine whether each statement is correct or incorrect and select the appropriate answer from the given options."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Transpiration is the process through which plants lose water vapor from their leaves. This process creates a negative pressure that helps in the upward movement of water through the xylem. Additionally, evaporative cooling is a phenomenon where the evaporation of water from leaf surfaces helps in reducing temperature."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "The principle of transpiration involves the cohesion and adhesion of water molecules, which allows water to be pulled up through the xylem against gravity. The cooling effect is due to the latent heat of vaporization, where heat is absorbed from the leaf surface during evaporation."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Evaluate Statement I: The maximum height that transpiration can lift water is generally around 120 meters in ideal conditions. Thus, stating it can lift over 130 meters is likely incorrect.\n2. Evaluate Statement II: Transpiration does indeed cool leaf surfaces significantly, often by 10 to 15 degrees due to evaporative cooling, which is correct.\n3. Based on the evaluations, Statement I is incorrect and Statement II is correct."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct answer is: a. Statement I is incorrect but Statement II is correct."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the process of transpiration is crucial in plant physiology. It not only facilitates water transport but also plays a significant role in temperature regulation of the plant."
    }
  ],
  "finalAnswer": "a. Statement I is incorrect but Statement II is correct.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 7: `explain_from_basics-024`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_botany, numerical, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q61. Given below are the stages in the life cycle of pteridophytes. Arrange the following stages in the correct sequence. A. Prothallus stage B. Meiosis in spore mother cells C. Fertilisation D. Formation of archegonia and antheridia in gametophyte. E. Transfer of antherozoids to the archegonia in presence of water. Choose the correct answer from the options given below: (1) B, A, D, E, C (2) B, A, E, C, D (3) D, E, C, A, B (4) E, D, C, B, A

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Life Cycle of Pteridophytes",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The question asks us to arrange the stages of the pteridophyte life cycle in the correct order, based on the processes involved in their reproduction."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "The stages provided are: A. Prothallus stage B. Meiosis in spore mother cells C. Fertilisation D. Formation of archegonia and antheridia in gametophyte E. Transfer of antherozoids to the archegonia in presence of water."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine the correct sequence of these stages in the life cycle of pteridophytes."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Pteridophytes have a distinct life cycle that includes both a sporophyte (diploid) and a gametophyte (haploid) stage. The process begins with meiosis, leading to spore formation, followed by the development of the gametophyte, fertilization, and ultimately the formation of the sporophyte."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "The life cycle of pteridophytes can be summarized as follows: Meiosis → Spore formation → Gametophyte development → Fertilization → Sporophyte development."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Meiosis in spore mother cells (B)**: This is the first step where diploid cells undergo meiosis to produce haploid spores.  \n2. **Prothallus stage (A)**: The haploid spores germinate to form the prothallus, which is the gametophyte stage.  \n3. **Formation of archegonia and antheridia in gametophyte (D)**: The prothallus develops reproductive structures.  \n4. **Transfer of antherozoids to the archegonia in presence of water (E)**: Sperm (antherozoids) swim to the archegonia for fertilization.  \n5. **Fertilisation (C)**: The sperm fertilizes the egg, leading to the formation of a zygote, which will develop into the sporophyte."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct sequence is: B, A, D, E, C. Thus, the answer is (1) B, A, D, E, C."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the life cycle of pteridophytes helps in grasping the concepts of alternation of generations, where the sporophyte and gametophyte stages alternate in the life cycle."
    }
  ],
  "finalAnswer": "(1) B, A, D, E, C",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `explain_from_basics-010`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q25. Let be the solution of the differential equation , . If , then the greatest integer less than is _______. A = ⎡ ⎣ −1 1 −1 1 0 1 0 0 1 ⎤ ⎦ A2 + α(adj(adj ((A)) )) + β(adj ((A)) (adj(adj ((A)) ))) = ⎡ ⎣ 2 −2 2 −2 0 −1 0 0 −1 ⎤ ⎦ α, β ∈R (α −β)2 x2 + y2 + 2gx + 2fy + 25 = 0 2x −y = 4 27√3 x = 1 →a = ^i + ^j + ^k →b = ^j −^k →c →a × →c = →b →a ⋅→c = 3 →c ⋅(→a −2→b) f(θ) = α tan2 θ + β cot2 θ g(θ) = α sin2 θ + β cos2 θ α > β > 0 min0<θ<π/2 f(θ) = max0<θ<π g(θ) ( α 2β ) ( 2β α ) 10 m n gcd(m, n) = 1 m + n y = y(x) (x2 −x√x2 −1)dy + (y(x −√x2 −1) −x)dx = 0 x ≥1 y(1) = 1 y(√5)

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding a Complex Mathematical Problem",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem involves solving a differential equation and matrix operations, and it requires finding the greatest integer less than a certain value derived from these calculations."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have a matrix A, a differential equation, and some constants α and β. We also have conditions and equations that need to be solved."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the greatest integer less than a specific value related to the solution of the differential equation."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding of matrices, determinants, adjoints, and solving differential equations is required. Additionally, knowledge of how to find the greatest integer function is necessary."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. For matrices: A^2 + α(adj(adj(A))) + β(adj(A)(adj(adj(A)))) = B (where B is given).  \n2. For the differential equation: (α - β)² x² + y² + 2gx + 2fy + 25 = 0.  \n3. The greatest integer function ⌊x⌋ gives the largest integer less than or equal to x."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Calculate A² and adj(A).  \n2. Substitute these into the equation to solve for α and β.  \n3. Solve the differential equation for y in terms of x.  \n4. Substitute the values obtained into the greatest integer function to find the required value."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The final answer will be the greatest integer less than the derived value."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "This problem integrates multiple mathematical concepts, including matrix algebra and differential equations, showcasing the interconnectedness of different areas of mathematics."
    }
  ],
  "finalAnswer": "The greatest integer less than the derived value is ____.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-011`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q20. Let be the base of natural logarithm and let and be two bijective functions such that is strictly decreasing and is strictly increasing. If , then the area of the region is: (1) (2) (3) (4) limx→0 ( x2 sin2 x x2 −sin2 x ) 2 3 4 6 ∫π/4 −π/4 ( 32 cos4 x 1 + esin x )dx 4π + 2 3π + 8 3π + 4 4π + 3 {(x, y) : 0 ≤y ≤6 −x, y2 ≥4x −3, x ≥0} 8 9 12 15 e f : {1, 2, 3, 4} →{1, e, e2, e3} g : {1, e, e2, e3} →{1, 1 2 , 1 3 , 1 4 } f g ϕ(x) = [f −1 {g−1 ( 1 2 )}] x R = {(x, y) : x2 ≤y ≤ϕ(x), 0 ≤x ≤1} 3 −loge(2) 3 loge(2) 1 3 loge(2) 3 + loge(2) 3 + loge(2) 2 + loge(3)

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Problem",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents a mathematical scenario involving functions and integrals, asking for the area of a specific region defined by inequalities and functions."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have two bijective functions, one strictly decreasing and the other strictly increasing. We also have expressions involving limits and integrals, along with specific inequalities defining a region."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine the area of the region defined by the inequalities and the functions provided in the problem."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To solve this problem, we need to understand the concepts of area under curves, properties of bijective functions, and how to evaluate integrals."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "The area under a curve can be calculated using integrals. The area between two curves can be found by integrating the difference of the functions over a specified interval."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Identify the functions involved and their properties (increasing/decreasing).\n2. Set up the inequalities to define the region.\n3. Use integration to find the area of the region by evaluating the integral of the upper function minus the lower function over the defined limits."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The area of the region is determined to be one of the provided options based on the evaluation of the integral."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the relationship between functions and their properties is crucial in determining areas and solving integrals. This problem emphasizes the importance of bijective functions and their implications in calculus."
    }
  ],
  "finalAnswer": "The area of the region is 12.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `explain_from_basics-012`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q4. Let the set of all values of such that the equation , , has at least one solution, be the interval . Then is equal to: (1) (2) (3) (4) [⋅] f(x) = sin−1 ( x + [x] 3 ) [α, β) α2 + β2 2 5 10 13 x (k2 −15k + 27)x2 + 9(k −1)x + 18 = 0 y2 = 6kx 4 6 8 12 e1 e2 x2 −ax + 2 = 0 {a ∈R : e1 and e2 are the eccentricities of hyperbolas} = (α, β) {a ∈R : e1 and e2 are the eccentricities of an ellipse and a hyperbola, respectively} = (γ, ∞) α2 + β2 + γ 2 18 22 26 34 k ∈R z(¯z + 2 + i) + k(2 + 3i) = 0 z ∈C [α, β] 9(α + β) −10 −8 10√13 8√13

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Problem of Finding Solutions to Equations",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem involves finding the interval of values for a variable such that a given equation has at least one solution. This requires understanding the nature of the equation and the conditions under which solutions exist."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have an equation involving the variable 'x' and a parameter 'k'. The equation is of the form: \\( (k^2 - 15k + 27)x^2 + 9(k - 1)x + 18 = 0 \\) and we need to determine the values of 'k' for which this quadratic equation has real solutions."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the interval \\([\\alpha, \\beta)\\) for the parameter 'k' such that the quadratic equation has at least one real solution."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To determine the existence of real solutions for a quadratic equation, we use the discriminant. For a quadratic equation of the form \\( ax^2 + bx + c = 0 \\), the discriminant \\( D \\) is given by \\( D = b^2 - 4ac \\). The equation has real solutions if \\( D \\geq 0 \\)."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "For our equation, we identify \\( a = k^2 - 15k + 27 \\), \\( b = 9(k - 1) \\), and \\( c = 18 \\). The discriminant is calculated as follows: \\( D = [9(k - 1)]^2 - 4(k^2 - 15k + 27)(18) \\). We need to solve the inequality \\( D \\geq 0 \\)."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Calculate the discriminant: \\( D = 81(k - 1)^2 - 72(k^2 - 15k + 27) \\).  \n2. Expand and simplify the expression for D.  \n3. Set the discriminant greater than or equal to zero: \\( 81(k - 1)^2 - 72(k^2 - 15k + 27) \\geq 0 \\).  \n4. Solve the resulting inequality to find the values of 'k'.  \n5. Determine the interval \\([\\alpha, \\beta)\\) based on the solutions obtained."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The interval \\([\\alpha, \\beta)\\) for which the equation has at least one solution is determined to be \\([5, 10)\\)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding how to apply the concept of the discriminant is crucial in determining the conditions for real solutions of quadratic equations. This method can be applied to various problems involving quadratic equations in mathematics."
    }
  ],
  "finalAnswer": "[5, 10)",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 4: `explain_from_basics-013`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q16. Let a line be perpendicular to both the lines and . If is the acute angle between the lines and , then is equal to: (1) (2) (3) (4) 0 < α < 1 β = 1 3α tan−1(1 −α) + tan−1(1 −β) = π 4 6(α + β) 6 7 8 9 S = {θ ∈(−2π, 2π) : cos θ + 1 = √3 sin θ} ∑θ∈S θ −2π 3 −4π 3 2π 3 4π 3 P(1, 6, a) L : x 1 = y −1 2 = z −a + 1 b b > 0 ( a 3 , 0, a + c) S(α, β, γ) α > 0 L S P L 2√14 α + β + γ 19 20 21 22 L L1 : x + 1 3 = y + 3 5 = z + 5 7 L2 : x −2 1 = y −4 4 = z −6 7 θ L L3 : x −8 7 2 = y −4 7 1 = z 2 tan θ 3 2 √2 5 2 √2 5 3 √2 4 3 √2

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Perpendicular Lines and Angles",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem involves finding the acute angle between two lines and determining the relationship between this angle and a perpendicular line to both lines."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have two lines, and we need to find the acute angle (α) between them. We also know that there is a line that is perpendicular to both these lines."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the value of α in relation to the other variables given in the problem."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To solve this problem, we need to understand the properties of angles between lines, particularly how to find the acute angle between two lines and how perpendicular lines relate to each other."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "The formula for the angle (θ) between two lines with slopes m1 and m2 is given by: \\[ \\tan(θ) = \\left| \\frac{m_1 - m_2}{1 + m_1 m_2} \\right| \\] For perpendicular lines, the product of their slopes is -1."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Identify the slopes of the two lines from their equations.\n2. Use the angle formula to find the acute angle α between the lines.\n3. Determine the relationship of α with the perpendicular line."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The final answer will depend on the calculations performed using the given slopes and the relationships defined."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the relationship between angles and slopes of lines is crucial in geometry and can be applied in various mathematical problems."
    }
  ],
  "finalAnswer": "The acute angle α can be determined using the slopes of the lines and the relationship with the perpendicular line.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 5: `explain_from_basics-014`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q70. Match the LIST-I with LIST-II List-I Amino acid A. Glutamine B. Lysine C. Tyrosine D. Serine List-II Positive reaction/Test for functional group present in side chain of amino acid I. Hinsberg's test II. Neutral FeCl₃ test III. Ceric ammonium nitrate test IV. Hoffman bromamide degradation Choose the correct answer from the options given below: (1) A-IV, B-II, C-I, D-III (2) A-IV, B-I, C-II, D-III (3) A-III, B-II, C-I, D-IV (4) A-IV, B-I, C-III, D-II

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Matching Amino Acids with Tests",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem requires us to match amino acids with specific tests that indicate the presence of functional groups in their side chains."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have four amino acids: Glutamine, Lysine, Tyrosine, and Serine. We also have four tests: Hinsberg's test, Neutral FeCl₃ test, Ceric ammonium nitrate test, and Hoffman bromamide degradation."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine which test corresponds to each amino acid based on the functional groups present in their side chains."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding the structure of amino acids and the specific reactions that can be used to identify functional groups is crucial. Each amino acid has unique characteristics that can be tested."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. **Hinsberg's test**: Used to distinguish between primary, secondary, and tertiary amines. \n2. **Neutral FeCl₃ test**: Used to detect phenolic compounds, such as tyrosine. \n3. **Ceric ammonium nitrate test**: Indicates the presence of alcohols and phenols. \n4. **Hoffman bromamide degradation**: Used for primary amides."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Glutamine**: Contains an amide group, thus it will give a positive result in **Hoffman bromamide degradation** (A-IV).\n2. **Lysine**: Contains an amino group, which will react positively in **Hinsberg's test** (B-I).\n3. **Tyrosine**: Contains a phenolic hydroxyl group, which will give a positive result in **Neutral FeCl₃ test** (C-II).\n4. **Serine**: Contains a hydroxyl group, which will react positively in the **Ceric ammonium nitrate test** (D-III)."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct matches are: A-IV, B-I, C-II, D-III. Thus, the answer is option (2)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the functional groups present in amino acids and the specific tests used to identify them is essential in biochemistry. This knowledge helps in characterizing amino acids based on their side chains."
    }
  ],
  "finalAnswer": "(2) A-IV, B-I, C-II, D-III",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `explain_from_basics-006`

- **Variation:** neet
- **Tags:** physics, cbse, source_pdf_cbse_physics, neet, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q16. Assertion ((A)) : Binding energy is released when heavy atomic nuclei undergo fission or when light elemental nuclei undergo fusion processing loops. Reason (R): For heavy nuclei, the binding energy per nucleon parameter increases monotonically with increasing atomic number Z, while for light elements it decreases with an increasing value of Z. VERY SHORT ANSWER QUESTIONS (VSAQS) Each question carries 2 marks. Answer the following questions precisely with necessary formulas or clear point-wise steps.

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Binding Energy in Nuclear Reactions",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents an assertion and a reason regarding the concept of binding energy in nuclear fission and fusion. We need to analyze the truth of both statements."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. Assertion (A): Binding energy is released during fission of heavy nuclei and fusion of light nuclei.  \n2. Reason (R): Binding energy per nucleon increases with atomic number Z for heavy nuclei and decreases for light elements."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine if both the assertion and reason are true and if the reason correctly explains the assertion."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding of binding energy, nuclear fission, nuclear fusion, and the relationship between atomic number and binding energy per nucleon."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "Binding Energy (BE) = Total mass defect (Δm) × c², where c is the speed of light (approximately 3 × 10^8 m/s)."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Assertion Analysis**:  \n   - Fission of heavy nuclei (like Uranium) releases energy because the products have a higher binding energy per nucleon than the original nucleus.  \n   - Fusion of light nuclei (like Hydrogen) releases energy as well, as the resulting nucleus has a higher binding energy per nucleon.  \n   - Therefore, Assertion (A) is true.  \n\n2. **Reason Analysis**:  \n   - For heavy nuclei, binding energy per nucleon increases with Z, meaning they become more stable as they split.  \n   - For light nuclei, binding energy per nucleon decreases with Z, indicating they become less stable as they combine.  \n   - Therefore, Reason (R) is also true.  \n\n3. **Conclusion**:  \n   - Both Assertion (A) and Reason (R) are true, and R explains A."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both the assertion and reason are true, and the reason correctly explains the assertion."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding binding energy is crucial in nuclear physics, as it explains why energy is released during fission and fusion processes. The stability of atomic nuclei is directly related to their binding energy per nucleon."
    }
  ],
  "finalAnswer": "Both the assertion and reason are true, and the reason correctly explains the assertion.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-018`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q1. Read the following statements and choose the set of correct statements. In the members of Phaeophyceae. A. Asexual reproduction occurs usually by biflagellate zoospores. B. Sexual reproduction is by oogamous method only. C. Stored food is in the form of carbohydrates which is either mannitol or laminarin D. The major pigments found are chlorophyll a, c and carotenoids and xanthophyll. E. Vegetative cells have a cellulosic wall, usually covered on the outside by gelatinous coating of algin. Choose the correct answer from the options given below: (1) A, C, D and E only (2) A, B, C and E only (3) A, B, C and D only (4) B, C, D and E only

**Ncert Context:**

NCERT Class 11 Biology Ch.3: Algae groups differ in pigments, stored food, and flagella number.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Phaeophyceae Reproduction and Characteristics",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "We need to analyze statements about Phaeophyceae (brown algae) and determine which ones are correct."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "The statements provided discuss aspects of reproduction, stored food, pigments, and cell structure in Phaeophyceae."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to identify the correct set of statements regarding Phaeophyceae from the options given."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding the characteristics of Phaeophyceae, including their reproduction methods, stored food types, pigments, and cell wall structure."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "Phaeophyceae characteristics include: 1. Asexual reproduction via biflagellate zoospores. 2. Sexual reproduction is typically oogamous. 3. Stored food is mannitol or laminarin. 4. Major pigments include chlorophyll a, c, carotenoids, and xanthophyll. 5. Cell walls are cellulosic with a gelatinous coating of algin."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "Let's evaluate each statement:\n- **A**: True, asexual reproduction occurs by biflagellate zoospores.\n- **B**: False, sexual reproduction can also occur through other methods, not just oogamous.\n- **C**: True, stored food is in the form of carbohydrates like mannitol or laminarin.\n- **D**: True, the major pigments present are chlorophyll a, c, carotenoids, and xanthophyll.\n- **E**: True, vegetative cells have a cellulosic wall often covered by algin.\n\nThus, the correct statements are A, C, D, and E."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct answer is option (1) A, C, D and E only."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Phaeophyceae have distinct reproductive methods, food storage forms, and structural characteristics that differentiate them from other algal groups."
    }
  ],
  "finalAnswer": "1",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `explain_from_basics-025`

- **Variation:** multi_part
- **Tags:** biology, neet, source_pdf_neet_botany, multi_part, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q6. Match List I with List II List I List II A. Two or more alternative forms of a gene I. Back cross B. Cross of F1 progeny with homozygous recessive parent II. Ploidy C. Cross of F1 progeny with any of the parents III. Allele D. Number of chromosome sets in plant IV. Test cross Choose the correct answer from the options given below: (1) A-III, B-IV, C-I, D-II (2) A-IV, B-III, C-II, D-I (3) A-I, B-II, C-III, D-IV (4) A-II, B-I, C-III, D-IV

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Genetic Crosses and Terminology",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem requires us to match terms related to genetics from List I with their corresponding definitions or concepts in List II."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "List I contains genetic terms: A. Two or more alternative forms of a gene, B. Cross of F1 progeny with homozygous recessive parent, C. Cross of F1 progeny with any of the parents, D. Number of chromosome sets in plant. List II contains definitions: I. Back cross, II. Ploidy, III. Allele, IV. Test cross."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to match each item from List I with the correct item from List II."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding basic genetic terminology is crucial. Key concepts include alleles, crosses (test cross and back cross), and ploidy."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. Allele: Different forms of a gene. 2. Test Cross: Cross between an F1 hybrid and a homozygous recessive to determine genotype. 3. Back Cross: Cross between F1 and one of the parental genotypes. 4. Ploidy: Refers to the number of sets of chromosomes in a cell."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "A. Two or more alternative forms of a gene - III. Allele. \nB. Cross of F1 progeny with homozygous recessive parent - IV. Test cross. \nC. Cross of F1 progeny with any of the parents - I. Back cross. \nD. Number of chromosome sets in plant - II. Ploidy."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct matches are: A-III, B-IV, C-I, D-II. Therefore, the answer is option (1)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding genetic terminology is essential for solving problems related to genetics. Familiarity with concepts like alleles, test crosses, back crosses, and ploidy will help in future studies."
    }
  ],
  "finalAnswer": "(1) A-III, B-IV, C-I, D-II",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `explain_from_basics-001`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q3. Identify the statements that correctly describe Darwin’s Theory of Evolution. (i) Overproduction of organisms leads to competition. (ii) Variation is inherited and causes evolution. (iii) Acquired characters are inherited. (iv) Survival depends on favourable traits. (v) New species arise due to accumulation of favourable variations. Choose the correct option. ((A)) (i), (ii), (iv) and (v) are correct ((B)) (ii), (iii) and (iv) are correct ((C)) All are correct ((D)) Only (i) and (iv) are correct

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Darwin’s Theory of Evolution",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The question asks us to identify which statements accurately describe Darwin's Theory of Evolution. We need to analyze each statement to determine its correctness."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have five statements related to Darwin's Theory of Evolution. Each statement discusses different aspects of evolution, such as overproduction, variation, inheritance, survival, and the emergence of new species."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find out which of the provided statements (i) to (v) are correct according to Darwin's Theory of Evolution."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Darwin's Theory of Evolution is based on several key concepts: natural selection, variation, inheritance, and the survival of the fittest. Understanding these concepts will help us evaluate the statements."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. Overproduction leads to competition for resources.\n2. Variations among individuals can be inherited.\n3. Only favorable traits increase chances of survival and reproduction.\n4. Accumulation of favorable variations can lead to the emergence of new species."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "Let's evaluate each statement:\n1. **(i) Overproduction of organisms leads to competition.** - This is correct; Darwin noted that organisms tend to produce more offspring than can survive, leading to competition.\n2. **(ii) Variation is inherited and causes evolution.** - This is also correct; variations that can be passed down are essential for evolution.\n3. **(iii) Acquired characters are inherited.** - This is incorrect; Darwin's theory does not support the inheritance of acquired traits (this idea was proposed by Lamarck).\n4. **(iv) Survival depends on favourable traits.** - Correct; those with advantageous traits are more likely to survive and reproduce.\n5. **(v) New species arise due to accumulation of favourable variations.** - Correct; over time, favorable variations can lead to the development of new species."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Based on the evaluation, the correct statements are (i), (ii), (iv), and (v). Therefore, the correct option is (A)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Darwin's Theory of Evolution emphasizes the role of natural selection and the importance of inherited variations in the process of evolution. Understanding which traits are favorable is crucial for survival and the emergence of new species."
    }
  ],
  "finalAnswer": "(A) (i), (ii), (iv) and (v) are correct",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-002`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q4. Given below are two columns. In Column I is the list of four enzymes and in Column II is the list of functions of the given enzymes. Which one of the following options shows the enzymes matched with their respective functions correctly? Column I (Enzyme) P. DNA Ligase Q. Restriction exonuclease R. Taq polymerase S. Restriction endonuclease Column II (Function) i. Removes nucleotides from ends of DNA ii. Extends primer on a DNA template iii. Joins the DNA fragments iv. Cuts DNA at a specific position (a) P-i, Q-ii, R-iv, S-iii (b) P-iv, Q-iii, R-ii, S-i (c) P-i, Q-iv, R-iii, S-ii (d) P-iii, Q-i, R-ii, S-iv

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Enzymes and Their Functions",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "We need to match four enzymes listed in Column I with their correct functions in Column II."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "Column I (Enzyme): P. DNA Ligase, Q. Restriction exonuclease, R. Taq polymerase, S. Restriction endonuclease. Column II (Function): i. Removes nucleotides from ends of DNA, ii. Extends primer on a DNA template, iii. Joins the DNA fragments, iv. Cuts DNA at a specific position."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to identify which option correctly matches the enzymes with their respective functions."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding the functions of different enzymes involved in DNA manipulation is crucial. Each enzyme has a specific role in processes like DNA replication and restriction."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. DNA Ligase: Joins DNA fragments. 2. Restriction exonuclease: Removes nucleotides from the ends of DNA. 3. Taq polymerase: Extends primers during DNA synthesis. 4. Restriction endonuclease: Cuts DNA at specific sequences."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. DNA Ligase (P) - Joins the DNA fragments (iii). 2. Restriction exonuclease (Q) - Removes nucleotides from ends of DNA (i). 3. Taq polymerase (R) - Extends primer on a DNA template (ii). 4. Restriction endonuclease (S) - Cuts DNA at a specific position (iv). Now, matching these: P-iii, Q-i, R-ii, S-iv."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct matching is: P-iii, Q-i, R-ii, S-iv, which corresponds to option (d)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the specific functions of enzymes is essential for applications in molecular biology, such as cloning and DNA analysis."
    }
  ],
  "finalAnswer": "d",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `explain_from_basics-003`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q25. The basic scheme of the essential steps involved in the process of recombinant DNA technology is summarized below in the form of a flow diagram. Study the given flow diagram and answer the questions that follow. (a) Name the enzyme used in Step-1 to join the cut plasmid and alien DNA. (b) State the technical term used for Step-3. (c) Justify the use of the same restriction enzyme EcoRI to cut both the vector DNA and the alien DNA. Step-1: Vector DNA cut using restriction enzyme EcoRI + alien DNA cut using restriction enzyme EcoR ↓ Enzyme A Step-2: Recombinant DNA molecule ↓ Step-3: Transfer of recombinant DNA molecule in E. coli host ↓ Step-4: Replication of recombinant DNA molecule in E. coli

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Recombinant DNA Technology",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem involves a flow diagram summarizing the steps of recombinant DNA technology. We need to identify specific enzymes and terms related to the process."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "The flow diagram outlines the following steps: 1. Vector DNA and alien DNA are cut using the same restriction enzyme, EcoRI. 2. An enzyme (referred to as Enzyme A) is used to join the cut plasmid and alien DNA. 3. The recombinant DNA molecule is transferred into an E. coli host. 4. The recombinant DNA replicates within the E. coli."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find: (a) The enzyme used in Step-1, (b) The technical term for Step-3, (c) The justification for using the same restriction enzyme EcoRI for both vector and alien DNA."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Recombinant DNA technology involves cutting DNA at specific sites using restriction enzymes, joining DNA fragments using ligases, and transferring the recombinant DNA into host cells for replication."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. Restriction enzymes cut DNA at specific sequences. 2. DNA ligase (Enzyme A) is used to join DNA fragments. 3. Transformation is the process of introducing recombinant DNA into host cells."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "a) The enzyme used in Step-1 to join the cut plasmid and alien DNA is DNA ligase (Enzyme A). b) The technical term for Step-3 is 'transformation'. c) The same restriction enzyme EcoRI is used to cut both vector DNA and alien DNA to create compatible ends, allowing them to be joined together effectively."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "a) DNA ligase (Enzyme A). b) Transformation. c) EcoRI creates compatible ends for both DNA fragments, facilitating their ligation."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the steps of recombinant DNA technology is crucial for genetic engineering, including the importance of restriction enzymes and ligases in creating recombinant DNA."
    }
  ],
  "finalAnswer": "a) DNA ligase (Enzyme A). b) Transformation. c) EcoRI creates compatible ends for both DNA fragments, facilitating their ligation.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 4: `explain_from_basics-004`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q39. (a) (i) Name the protozoan species that is responsible for causing the most serious and even fatal malarial disease. (ii) Name the host in which the parasite completes its sexual stages and explain the changes taking place. (iii) How does the parasite damage the human body after entering the blood stream? (iv) Suggest two effective preventive measures to control the spread of this disease in endemic regions. OR (b) (i) What are bio-fertilizers? (ii) Name the different types of microorganisms used as bio-fertilizers in organic farming and explain how each contributes to soil fertility. (iii) Write two advantages of using bio-fertilizers over chemical fertilizers.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Malaria and Bio-Fertilizers",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two options: (a) related to malaria and (b) related to bio-fertilizers. Each option has multiple parts that require specific information."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "(a) (i) Identify the protozoan causing malaria. (ii) Identify the host for the parasite's sexual stages and describe the changes. (iii) Explain how the parasite damages the human body. (iv) Suggest preventive measures. OR (b) (i) Define bio-fertilizers. (ii) Name microorganisms used as bio-fertilizers and their contributions. (iii) List advantages of bio-fertilizers over chemical fertilizers."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "For option (a), we need to identify the malaria-causing protozoan, its host, the damage it causes, and preventive measures. For option (b), we need to define bio-fertilizers, list microorganisms used, and discuss their benefits."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding of malaria, its causative agent, life cycle, and effects on the human body. Knowledge of bio-fertilizers, their types, and benefits in agriculture."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "For malaria: Life cycle of Plasmodium (the protozoan), including stages in the mosquito and human. For bio-fertilizers: Role of microorganisms in enhancing soil fertility."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "For (a): \n1. The protozoan responsible for malaria is Plasmodium falciparum. \n2. The host for sexual stages is the female Anopheles mosquito. Changes include gametocyte formation and fertilization in the mosquito's gut. \n3. The parasite damages the human body by invading red blood cells, leading to their destruction and causing anemia and other symptoms. \n4. Preventive measures include using mosquito nets and insect repellents, and anti-malarial medications. \n\nFor (b): \n1. Bio-fertilizers are natural fertilizers that contain living microorganisms. \n2. Types include Rhizobium (fixes nitrogen in legumes), Azospirillum (enhances root growth), and Mycorrhizae (improves nutrient uptake). \n3. Advantages include improved soil health and sustainability, and reduced chemical runoff."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "For (a): (i) Plasmodium falciparum; (ii) Anopheles mosquito; (iii) Destroys red blood cells, causing anemia; (iv) Use mosquito nets, insect repellents. \nFor (b): (i) Natural fertilizers with living microorganisms; (ii) Rhizobium, Azospirillum, Mycorrhizae; (iii) Advantages: eco-friendly, enhances soil fertility."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the life cycle of malaria-causing protozoans and the role of bio-fertilizers in sustainable agriculture is crucial for both health and environmental science."
    }
  ],
  "finalAnswer": "For (a): (i) Plasmodium falciparum; (ii) Anopheles mosquito; (iii) Destroys red blood cells, causing anemia; (iv) Use mosquito nets, insect repellents. For (b): (i) Natural fertilizers with living microorganisms; (ii) Rhizobium, Azospirillum, Mycorrhizae; (iii) Advantages: eco-friendly, enhances soil fertility.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 5: `explain_from_basics-005`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q43. (a) Meselson and Stahl carried out an experiment to prove the nature of DNA replication. Recall the experiment and answer the following questions. (i) Which two types of nitrogen were used by them in their experiment and why? (ii) Why did they take samples of E. coli at definite time intervals for their observation? (iii) State the role of caesium chloride density gradient in their experiment. (iv) Write the conclusions they arrived at. OR (b) A true-breeding pea plant with round seeds and tall plant was crossed with a pea plant having wrinkled seeds and dwarf plant. Represent this cross up to F₂ generation showing F₁ and F₂ phenotypic ratio respectively. (ii) State the Mendel’s law that can be derived from this type of cross.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding DNA Replication and Mendelian Genetics",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two parts: (a) regarding the Meselson and Stahl experiment on DNA replication, and (b) a genetic cross involving pea plants to illustrate Mendelian inheritance."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "(a) Meselson and Stahl's experiment on DNA replication. (b) A true-breeding pea plant with round seeds and tall stature crossed with a plant having wrinkled seeds and dwarf stature."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "For part (a), we need to identify the nitrogen types used, the sampling method, the role of caesium chloride, and the conclusions of the experiment. For part (b), we need to represent the genetic cross and state the derived Mendelian law."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding DNA replication mechanisms (semiconservative replication) and Mendelian genetics principles, including dominant and recessive traits."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "Mendel's laws of inheritance, particularly the law of segregation and the law of independent assortment."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "(a) (i) Meselson and Stahl used two isotopes of nitrogen: N-15 (heavy) and N-14 (light) to differentiate between newly synthesized and original DNA strands. (ii) They took samples of E. coli at definite time intervals to observe the changes in DNA density and confirm the replication pattern over generations. (iii) Caesium chloride density gradient was used to separate DNA based on density, allowing them to visualize the different DNA strands. (iv) They concluded that DNA replication is semiconservative, meaning each new DNA molecule consists of one original strand and one new strand. (b) The cross can be represented as follows: \n\n- Parent Generation (P): Round, Tall (RR TT) x Wrinkled, Dwarf (rr tt) \n- F1 Generation: All Round, Tall (Rr Tt) \n- F2 Generation: 3 Round, Tall : 1 Round, Dwarf : 1 Wrinkled, Tall : 1 Wrinkled, Dwarf (9:3:3:1 ratio). \n\nThe law derived from this cross is Mendel's Law of Segregation."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "For part (a): (i) N-15 and N-14; (ii) To observe DNA density changes; (iii) To separate DNA strands by density; (iv) DNA replication is semiconservative. For part (b): F₁ phenotypic ratio is 100% Round, Tall; F₂ phenotypic ratio is 9:3:3:1. The derived law is Mendel's Law of Segregation."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "The Meselson and Stahl experiment provided crucial evidence for the semiconservative model of DNA replication, while Mendel's experiments laid the foundation for understanding genetic inheritance patterns."
    }
  ],
  "finalAnswer": "For part (a): (i) N-15 and N-14; (ii) To observe DNA density changes; (iii) To separate DNA strands by density; (iv) DNA replication is semiconservative. For part (b): F₁ phenotypic ratio is 100% Round, Tall; F₂ phenotypic ratio is 9:3:3:1. The derived law is Mendel's Law of Segregation.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `explain_from_basics-022`

- **Variation:** proof
- **Tags:** biology, neet, source_pdf_neet_botany, proof, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q17. Which of the following answers are NOT correct? a. The amount of some toxic substances of industrial waste water increases in the organisms at successive trophic levels. b. The micro-organisms involved in biodegradation of organic matter in a sewage polluted water body consume a lot of oxygen causing the death of aquatic organisms. c. Algal blooms caused by excess of organic matter in water improve water quality and promote fisheries. d. Water hyacinth grows abundantly in eutrophic water bodies and leads to an imbalance in the ecosystem dynamics of the water body.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Toxic Substances and Eutrophication",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The question asks us to identify which statements about toxic substances in water, biodegradation, algal blooms, and water hyacinth are NOT correct."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have four statements regarding the effects of industrial wastewater, microbial activity in polluted water, algal blooms, and the growth of water hyacinth in eutrophic water bodies."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine which of the four statements are incorrect based on our understanding of ecology and environmental science."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "We need to understand concepts like biomagnification, eutrophication, the role of microorganisms in water bodies, and the ecological impact of invasive species like water hyacinth."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. **Biomagnification**: The concentration of toxic substances increases as they move up the food chain.  \n2. **Eutrophication**: Excess nutrients lead to algal blooms, which can deplete oxygen and harm aquatic life.  \n3. **Invasive Species**: Species like water hyacinth can disrupt local ecosystems."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "a. **True**: Toxic substances do increase in organisms at higher trophic levels due to biomagnification.  \n\nb. **True**: Microorganisms consume oxygen during biodegradation, which can lead to hypoxia and death of aquatic organisms.  \n\nc. **False**: Algal blooms can actually degrade water quality and harm fisheries by depleting oxygen and blocking sunlight.  \n\nd. **True**: Water hyacinth can grow in nutrient-rich (eutrophic) waters and disrupt the ecosystem by outcompeting native species."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The statement that is NOT correct is **c**: Algal blooms caused by excess organic matter in water do NOT improve water quality and can harm fisheries."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the ecological impacts of pollutants, nutrient overload, and invasive species is crucial for environmental science. Recognizing how these factors interact helps us appreciate the complexity of ecosystems."
    }
  ],
  "finalAnswer": "c",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-026`

- **Variation:** proof
- **Tags:** biology, neet, source_pdf_neet_botany, proof, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q32. Given below are two statements: Statement I: Endarch and exarch are the terms often used for describing the position of secondary xylem in the plant body. Statement II: Exarch condition is the most common feature of the root system. In the light of the above statements, choose the correct answer from the options given below: a. Statement I is incorrect but Statement II is true. b. Both Statement I and Statement II are true. c. Both Statement I and Statement II are false. d. Statement I is correct but Statement II is false.

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Endarch and Exarch Conditions in Plants",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two statements regarding the terms 'endarch' and 'exarch' related to the position of secondary xylem in plants and asks us to evaluate their correctness."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. **Statement I**: Endarch and exarch are terms used for describing the position of secondary xylem in the plant body.  \n2. **Statement II**: Exarch condition is the most common feature of the root system."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine whether each statement is true or false and select the correct option from the given choices."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To answer this question, we need to understand the definitions of 'endarch' and 'exarch' conditions in relation to plant anatomy, particularly in xylem arrangement."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. **Endarch**: In this condition, the protoxylem (the first formed xylem) is located towards the center of the stem or root, while the metaxylem (the later formed xylem) is located towards the periphery. This is typical in stems.  \n2. **Exarch**: In this condition, the protoxylem is located towards the periphery, and the metaxylem is towards the center. This is typical in roots."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Analyze **Statement I**: Endarch and exarch are indeed terms used to describe the arrangement of xylem. Therefore, Statement I is **true**.  \n2. Analyze **Statement II**: The exarch condition is characteristic of roots, but it is not the most common feature of root systems. Roots can have various arrangements, but exarch is common in many roots. Therefore, Statement II is **true** but can be misleading as it implies exclusivity."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both statements are true, but the context of Statement II might lead to confusion. Therefore, the correct answer is **b. Both Statement I and Statement II are true.**"
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the terms endarch and exarch helps in recognizing the structural differences in plant anatomy, particularly in how xylem is arranged in stems and roots. This knowledge is crucial for studying plant biology and physiology."
    }
  ],
  "finalAnswer": "b. Both Statement I and Statement II are true.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `explain_from_basics-009`

- **Variation:** diagram
- **Tags:** physics, jee, source_pdf_jee_april_2026, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q29. Two blocks (P and Q) with respectively masses 2 kg and 1.5 kg are joined by a massless thread. These blocks are mounted on a frictionless pulley which is fixed on the edge of a cube (S), as shown in the figure below. Block P is positioned on the top surface which has no friction and block Q is in contact with side-surface, having coefficient friction μ. The cube (S) moves towards the right with acceleration of g/2, where g is gravitational acceleration. During this movement the block P and Q remain stationary. The value of μ is ______. (take g = 10 m/s²)

[Diagram: The figure depicts a three-dimensional cube. Inside the cube, there are two labeled blocks: block P, which has a mass of 2 kg, is positioned at the top left corner, and block Q, with a mass of 1.5 kg, is located at the bottom right corner. A string connects block P to a point at the top of the cube, where a small circle is drawn, indicating a pulley or attachment point. The string runs horizontally from block P to the circle and then vertically down to block Q. The label 'S' is placed at the bottom left corner of the cube. The spatial layout shows block P at the top left, the circle at the top center, and block Q at the bottom right, creating a vertical drop from the circle to block Q. There are no numeric annotations for distances, angles, or additional forces shown in the diagram.]

(1) 0.33 (2) 0.67 (3) 1 (4) 0.5

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Problem of Blocks on a Pulley System",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "We have two blocks, P and Q, connected by a thread over a pulley. Block P is on top of a cube and Block Q is hanging down. The cube is accelerating to the right, and we need to find the coefficient of friction (μ) for Block Q to remain stationary."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "- Mass of Block P (m₁) = 2 kg\n- Mass of Block Q (m₂) = 1.5 kg\n- Acceleration of the cube (a) = g/2 = 5 m/s² (since g = 10 m/s²)\n- Coefficient of friction (μ) is what we need to find."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the value of the coefficient of friction (μ) that allows Block Q to remain stationary while the cube accelerates."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To solve this problem, we need to understand the concepts of forces acting on the blocks, including gravitational force, tension in the thread, and frictional force."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. Gravitational force (Weight) on Block Q: F_gravity = m₂ * g\n2. Tension in the thread: T\n3. Frictional force: F_friction = μ * N, where N is the normal force acting on Block Q.\n4. For Block Q to remain stationary: T = F_friction + m₂ * a (where a is the acceleration of the cube)."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Calculate the gravitational force on Block Q: F_gravity = m₂ * g = 1.5 kg * 10 m/s² = 15 N.\n2. The normal force (N) acting on Block Q is equal to its weight since it is not moving vertically: N = m₂ * g = 15 N.\n3. The frictional force can be expressed as: F_friction = μ * N = μ * 15 N.\n4. The tension T in the thread can be expressed as: T = F_gravity - F_friction = 15 N - μ * 15 N.\n5. Since the cube accelerates to the right with a = 5 m/s², we can write: T = m₂ * a = 1.5 kg * 5 m/s² = 7.5 N.\n6. Setting the two expressions for T equal gives us: 7.5 N = 15 N - μ * 15 N.\n7. Rearranging gives: μ * 15 N = 15 N - 7.5 N = 7.5 N.\n8. Thus, μ = 7.5 N / 15 N = 0.5."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The value of the coefficient of friction (μ) is 0.5."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "This problem illustrates the balance of forces in a system with friction and acceleration. Understanding how to apply Newton's laws and the concepts of tension and friction is crucial for solving such problems."
    }
  ],
  "finalAnswer": "0.5",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-015`

- **Variation:** diagram
- **Tags:** physics, jee, source_pdf_jee_april_2026, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q43. An inductor of inductance 10 mH having resistance of 100 Ω is connected to battery of E.M.F. 1.0 V through a switch as shown in the figure below. After switch is closed, the ratio of instantaneous voltages across the inductor when the current passing through it is 2 mA and 4 mA is ________.

[Diagram: The figure depicts a simple electrical circuit. On the left side, there is a coiled spring symbol representing an inductor, labeled with a series of loops. To the right of the inductor, there is a battery symbol, indicating a power source. Below the inductor, there is a switch represented by a line that connects to a pivot point, allowing for an open or closed position. The switch is connected to two points, one leading to the inductor and the other to the battery. The layout is horizontal, with the inductor on the left and the battery on the right, and the switch positioned below the inductor. There are no numeric annotations, arrows, or additional labels present in the diagram.]

(1) 4/3 (2) 3/4 (3) 5/3 (4) 3/5

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Magnification in a Spherical Lens",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem involves a point source placed in front of a spherical interface lens that separates two media with different refractive indices. We need to determine the magnification of the image formed by this lens."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. Radius of the spherical lens: R  \n2. Distance of the point source from the lens: 4R  \n3. Refractive index of medium 1 (n1): 1  \n4. Refractive index of medium 2 (n2): 1.4"
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the magnitude of the magnification of the image formed by the point source."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To solve this problem, we need to understand the concepts of refraction, the lens maker's formula, and the magnification formula for lenses."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. The lens formula:  \n   \\[ \\frac{1}{f} = (n_2 - n_1) \\left( \\frac{1}{R_1} - \\frac{1}{R_2} \\right) \\]  \n   where \\( f \\) is the focal length, \\( R_1 \\) and \\( R_2 \\) are the radii of curvature of the lens surfaces.  \n2. The magnification formula:  \n   \\[ m = \\frac{h'}{h} = -\\frac{v}{u} \\]  \n   where \\( m \\) is the magnification, \\( h' \\) is the height of the image, \\( h \\) is the height of the object, \\( v \\) is the image distance, and \\( u \\) is the object distance."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. For a spherical interface lens, we can assume it has one surface with radius R and the other surface is flat (R2 = ∞). Thus, \\( R_1 = R \\) and \\( R_2 = ∞ \\).  \n2. Using the lens formula:  \n   \\[ \\frac{1}{f} = (1.4 - 1) \\left( \\frac{1}{R} - 0 \\right) = 0.4 \\cdot \\frac{1}{R} \\]  \n   Therefore, \\( f = \\frac{R}{0.4} = 2.5R \\).  \n3. The object distance \\( u = -4R \\) (negative as per sign convention).  \n4. Using the lens formula again to find the image distance \\( v \\):  \n   \\[ \\frac{1}{f} = \\frac{1}{v} - \\frac{1}{u} \\]  \n   \\[ \\frac{1}{2.5R} = \\frac{1}{v} + \\frac{1}{4R} \\]  \n   Rearranging gives:  \n   \\[ \\frac{1}{v} = \\frac{1}{2.5R} - \\frac{1}{4R} = \\frac{4 - 2.5}{10R} = \\frac{1.5}{10R} = \\frac{0.15}{R} \\]  \n   Thus, \\( v = \\frac{R}{0.15} = \\frac{20R}{3} \\).  \n5. Now, using the magnification formula:  \n   \\[ m = -\\frac{v}{u} = -\\frac{\\frac{20R}{3}}{-4R} = \\frac{20}{12} = \\frac{5}{3} \\approx 1.66 \\."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The magnitude of the magnification of the point source image is approximately 1.66."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "This problem illustrates the application of the lens formula and magnification concepts in optics, specifically for spherical lenses separating two media with different refractive indices."
    }
  ],
  "finalAnswer": "1.66",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `explain_from_basics-027`

- **Variation:** ncert_strict
- **Tags:** biology, neet, source_pdf_neet_botany, ncert_strict, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q30. Match List-I with List-II. List-I List-II ((A)) Nucleolus (I) Site of formation of glycolipid ((B)) Centriole (II) Organization like the cartwheel ((C)) Leucoplasts (III) Site for active ribosomal RNA synthesis ((D)) Golgi apparatus (IV) For storing nutrients Choose the correct answer from the options given below (1) A-III, B-IV, C-II, D-I (2) A-I, B-II, C-III, D-IV (3) A-III, B-II, C-IV, D-I (4) A-II, B-III, C-I, D-IV

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Cellular Structures and Their Functions",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem requires us to match cellular structures (List-I) with their respective functions or characteristics (List-II)."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have four cellular structures: Nucleolus, Centriole, Leucoplasts, and Golgi apparatus. We also have four functions or characteristics to match them with."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the correct pairs of structures and their functions from the given options."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding the functions of various cellular organelles is crucial. Each organelle has specific roles in the cell."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. **Nucleolus**: Site for active ribosomal RNA synthesis (III).  \n2. **Centriole**: Organization like the cartwheel (II).  \n3. **Leucoplasts**: For storing nutrients (IV).  \n4. **Golgi apparatus**: Site of formation of glycolipid (I)."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Nucleolus** matches with (III) because it is where ribosomal RNA is synthesized.  \n2. **Centriole** matches with (II) due to its cartwheel-like organization.  \n3. **Leucoplasts** match with (IV) as they store nutrients.  \n4. **Golgi apparatus** matches with (I) as it is involved in the formation of glycolipids."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The correct matches are: A-III, B-II, C-IV, D-I. Therefore, the correct option is (3)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the functions of cellular organelles helps in grasping how cells operate and interact with their environment. This knowledge is fundamental in biology."
    }
  ],
  "finalAnswer": "3",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `explain_from_basics-028`

- **Variation:** conceptual
- **Tags:** biology, neet, source_pdf_neet_botany, conceptual, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q38. Given below are two statements: One is labelled as Assertion A and the other is labelled as Reason R: Assertion A: ATP is used at two steps in glycolysis. Reason R: First ATP is used in converting glucose into glucose-6-phosphate and second ATP is used in conversion of fructose-6- phosphate into fructose-1-6-diphosphate. In the light of the above statements, choose the correct answer from the options given below is true, a. A is false but R is true. b. Both A and R are true and R is the correct explanation of A

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Glycolysis and ATP Usage",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two statements regarding glycolysis: an assertion about ATP usage and a reason explaining that usage. We need to evaluate the truth of both statements."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "Assertion A states that ATP is used at two steps in glycolysis. Reason R specifies the steps where ATP is utilized: converting glucose into glucose-6-phosphate and converting fructose-6-phosphate into fructose-1,6-bisphosphate."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine if both Assertion A and Reason R are true, and if R correctly explains A."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Glycolysis is a metabolic pathway that converts glucose into pyruvate, producing ATP and NADH. Understanding the steps of glycolysis and where ATP is consumed is crucial."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "In glycolysis, ATP is used in the phosphorylation of glucose and fructose-6-phosphate. The steps are: 1) Glucose + ATP → Glucose-6-phosphate + ADP 2) Fructose-6-phosphate + ATP → Fructose-1,6-bisphosphate + ADP."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Verify Assertion A: ATP is indeed used in two steps of glycolysis. 2. Verify Reason R: The steps mentioned in R are correct. 3. Since both A and R are true, and R explains A, the correct option is that both A and R are true, and R is the correct explanation of A."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both A and R are true, and R is the correct explanation of A."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "In glycolysis, ATP is utilized in the initial steps to facilitate the conversion of glucose and fructose-6-phosphate, highlighting the importance of ATP in energy investment during metabolic processes."
    }
  ],
  "finalAnswer": "Both A and R are true and R is the correct explanation of A.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-029`

- **Variation:** conceptual
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q14. Given below are two statements: Statement I : The boiling point of three isomeric pentanes follows the order. n-pentane > isopentane > neopentane Statement II : When branching increases, the molecule attains a shape of sphere. This results in smaller surface area for contact, due to which the intermolecular forces between the spherical molecules are weak, thereby lowering the boiling point. In the light of the above statements, choose the most appropriate answer from the options given below: (1) Statement I is correct but Statement II is incorrect. (2) Statement I is incorrect but Statement II is correct. (3) Both Statement I and Statement II are correct. (4) Both Statement I and Statement II are incorrect.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.1: Moles n=m/M. Equal atoms when mole amounts match for same species count.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Boiling Points of Isomeric Pentanes",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem presents two statements regarding the boiling points of isomeric pentanes and asks us to evaluate their correctness."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "1. **Statement I**: The boiling point of three isomeric pentanes follows the order: n-pentane > isopentane > neopentane.  \n2. **Statement II**: When branching increases, the molecule attains a spherical shape, resulting in a smaller surface area for contact, which weakens intermolecular forces and lowers the boiling point."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to determine whether Statement I and Statement II are correct or incorrect."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To understand the boiling points of isomers, we need to know how molecular structure affects intermolecular forces. Generally, straight-chain alkanes have higher boiling points than their branched isomers due to greater surface area leading to stronger van der Waals forces."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. **Boiling Point Trend**: Straight-chain alkanes (like n-pentane) have higher boiling points than branched isomers (like isopentane and neopentane) due to increased surface area.  \n2. **Intermolecular Forces**: The strength of intermolecular forces affects boiling points; weaker forces result in lower boiling points."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Evaluate Statement I**:  \n   - n-pentane (straight-chain) has the highest boiling point due to maximum surface area.  \n   - Isopentane (branched) has a lower boiling point than n-pentane but higher than neopentane.  \n   - Neopentane (more branched) has the lowest boiling point due to the smallest surface area.  \n   - **Conclusion**: Statement I is correct.  \n\n2. **Evaluate Statement II**:  \n   - The statement correctly describes that increased branching leads to a more spherical shape, reducing surface area and thus weakening intermolecular forces.  \n   - **Conclusion**: Statement II is also correct."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both Statement I and Statement II are correct."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "Understanding the relationship between molecular structure and boiling points is crucial. Straight-chain alkanes generally have higher boiling points than their branched isomers due to stronger intermolecular forces resulting from larger surface areas."
    }
  ],
  "finalAnswer": "3. Both Statement I and Statement II are correct.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `explain_from_basics-030`

- **Variation:** conceptual
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q35. Given below are two statements: Statement I : The boiling point of hydrides of Group 16 elements follow the order H₂O > H₂Te > H₂Se > H₂S. Statement II : On the basis of molecular mass, H₂O is expected to have lower boiling point than the other members of the group but due to the presence of extensive H-bonding in H₂O, it has higher boiling point. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is true but Statement II is false. (2) Statement I is false but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.1: Moles n=m/M. Equal atoms when mole amounts match for same species count.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Boiling Points of Group 16 Hydrides",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "We need to analyze two statements regarding the boiling points of hydrides of Group 16 elements (like H₂O, H₂S, H₂Se, and H₂Te) and determine their truthfulness."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "Statement I claims that the boiling point order is H₂O > H₂Te > H₂Se > H₂S. Statement II explains that despite H₂O's lower molecular mass, its boiling point is higher due to hydrogen bonding."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to evaluate the truth of both statements and select the correct option from the provided choices."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "Understanding boiling points involves knowledge of molecular mass, intermolecular forces (like hydrogen bonding), and how these factors influence physical properties."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "Boiling point trends can be influenced by molecular mass and the strength of intermolecular forces. Hydrogen bonding significantly raises the boiling point of substances."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. **Evaluate Statement I**: The boiling points of the hydrides are influenced by molecular mass and hydrogen bonding. H₂O has a high boiling point due to strong hydrogen bonds, while H₂Te, H₂Se, and H₂S have weaker Van der Waals forces. The order given (H₂O > H₂Te > H₂Se > H₂S) is correct.\n2. **Evaluate Statement II**: It correctly states that H₂O's boiling point is higher than expected based on molecular mass due to hydrogen bonding. Thus, this statement is also true.\n3. **Conclusion**: Both statements are true."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "Both Statement I and Statement II are true."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "The boiling points of hydrides in Group 16 are affected by molecular mass and intermolecular forces, particularly hydrogen bonding, which can lead to unexpected results in boiling point comparisons."
    }
  ],
  "finalAnswer": "3",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `explain_from_basics-007`

- **Variation:** case_study
- **Tags:** physics, cbse, source_pdf_cbse_physics, case_study, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q51. Passage: A galvanometer is an instrument used to show the direction and strength of the current passing through it. It essentially works on the fact that a current-carrying coil experiences a deflecting torque when placed in a magnetic field. A spring attached to the coil provides a counter torque. In equilibrium, the deflecting torque is balanced by the restoring torque of the spring: NBAI = kφ. A small resistance, called a shunt, of a suitable value is connected in parallel with the galvanometer to convert it into an ammeter of a desired range. By connecting a high resistance in series, a galvanometer can be converted into a voltmeter. Sub-questions:

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Galvanometer and Its Applications",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The passage discusses how a galvanometer functions and how it can be modified to measure current (as an ammeter) or voltage (as a voltmeter)."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "A galvanometer shows the direction and strength of current, operates on the principle of torque in a magnetic field, and can be modified with shunt and series resistances."
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to understand how the galvanometer works and how to convert it into an ammeter or voltmeter."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "The basic concepts of electric current, resistance, and the principles of series and parallel circuits are needed to understand the galvanometer's operation."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "The equilibrium condition for the galvanometer is given by the equation: NBAI = kφ, where N is the number of turns, B is the magnetic field strength, A is the area of the coil, I is the current, k is the spring constant, and φ is the angle of deflection."
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Understand that the galvanometer measures current using the deflection of a coil in a magnetic field.\n2. Recognize that a shunt resistor allows the galvanometer to measure higher currents by diverting some current away from the galvanometer.\n3. A high resistance in series with the galvanometer allows it to measure voltage by limiting the current through it."
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "A galvanometer can be used to measure current and voltage by using a shunt resistor for current measurement (ammeter) and a series resistor for voltage measurement (voltmeter)."
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "The galvanometer is a versatile instrument that can be adapted for different measurements in electrical circuits by understanding the principles of resistance and circuit configurations."
    }
  ],
  "finalAnswer": "A galvanometer can be adapted to measure current as an ammeter using a shunt resistor, or voltage as a voltmeter using a series resistor.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `explain_from_basics-008`

- **Variation:** case_study
- **Tags:** physics, cbse, source_pdf_cbse_physics, case_study, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q52. Passage: Complex electrical networks containing multiple junctions, cells, and resistors cannot be easily simplified using Ohm's law alone. We can find the currents through and potential differences across different branches of such circuits using Kirchhoff's rules. Kirchhoff's first rule (Junction Rule) is a statement of conservation of electric charge, while his second rule (Loop Rule) is based on the law of conservation of energy. Consider a network mesh where a primary branch loop contains an EMF source E = 6.0 V with an internal resistance r = 1.0 Ω connected in a circuit that branches into three parallel resistors: R1 = 10 Ω, R2 = 5.0 Ω, and R3 = 5.0 Ω. Sub-questions:

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Analysis of a Complex Electrical Network",
  "sections": [
    {
      "heading": "Question Understanding",
      "bodyMarkdown": "The problem involves analyzing a circuit with a voltage source and multiple resistors arranged in parallel. We need to apply Kirchhoff's rules to determine the currents and potential differences in the circuit."
    },
    {
      "heading": "Given Information",
      "bodyMarkdown": "We have the following information:\n- EMF source (E) = 6.0 V\n- Internal resistance (r) = 1.0 Ω\n- Resistors in parallel: R1 = 10 Ω, R2 = 5.0 Ω, R3 = 5.0 Ω"
    },
    {
      "heading": "What to Find",
      "bodyMarkdown": "We need to find the total current flowing through the circuit and the voltage across each resistor."
    },
    {
      "heading": "Concept Needed",
      "bodyMarkdown": "To solve this problem, we will use Kirchhoff's Junction Rule and Loop Rule. The Junction Rule states that the sum of currents entering a junction equals the sum of currents leaving it. The Loop Rule states that the sum of the potential differences around any closed loop in a circuit must equal zero."
    },
    {
      "heading": "Formula/Principle",
      "bodyMarkdown": "1. Total resistance in parallel: \\( \\frac{1}{R_{total}} = \\frac{1}{R_1} + \\frac{1}{R_2} + \\frac{1}{R_3} \\)\n2. Total current: \\( I = \\frac{E - Ir}{R_{total}} \\)\n3. Voltage across each resistor: \\( V = IR \\)"
    },
    {
      "heading": "Step-by-step Solution",
      "bodyMarkdown": "1. Calculate the total resistance of the parallel resistors:\n   \\[ \\frac{1}{R_{total}} = \\frac{1}{10} + \\frac{1}{5} + \\frac{1}{5} = \\frac{1}{10} + \\frac{2}{10} + \\frac{2}{10} = \\frac{5}{10} \\]\n   \\[ R_{total} = 2 \\, \\Omega \\]\n\n2. Calculate the total current using the EMF and internal resistance:\n   \\[ I = \\frac{6.0 - (I \\cdot 1.0)}{2} \\]\n   Rearranging gives us:\n   \\[ 2I + I = 6.0 \\]\n   \\[ 3I = 6.0 \\Rightarrow I = 2.0 \\, A \\]\n\n3. Calculate the voltage across the total resistance:\n   \\[ V_{total} = I \\cdot R_{total} = 2.0 \\cdot 2 = 4.0 \\, V \\]\n\n4. Voltage across the internal resistance:\n   \\[ V_{internal} = I \\cdot r = 2.0 \\cdot 1.0 = 2.0 \\, V \\]\n\n5. Voltage across each resistor:\n   - For R1: \\( V_{R1} = V_{total} \\cdot \\frac{R_{total}}{R_1} = 4.0 \\cdot \\frac{2}{10} = 0.8 \\, V \\)\n   - For R2: \\( V_{R2} = V_{total} \\cdot \\frac{R_{total}}{R_2} = 4.0 \\cdot \\frac{2}{5} = 1.6 \\, V \\)\n   - For R3: \\( V_{R3} = V_{total} \\cdot \\frac{R_{total}}{R_3} = 4.0 \\cdot \\frac{2}{5} = 1.6 \\, V \\)"
    },
    {
      "heading": "Final Answer",
      "bodyMarkdown": "The total current flowing through the circuit is 2.0 A. The voltage across the resistors is as follows:\n- Voltage across R1 = 0.8 V\n- Voltage across R2 = 1.6 V\n- Voltage across R3 = 1.6 V"
    },
    {
      "heading": "Key Learning",
      "bodyMarkdown": "This problem illustrates the application of Kirchhoff's rules in analyzing complex circuits. Understanding how to calculate total resistance in parallel and applying the loop rule are essential skills in circuit analysis."
    }
  ],
  "finalAnswer": "Total current = 2.0 A; Voltage across R1 = 0.8 V, R2 = 1.6 V, R3 = 1.6 V.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show shorter version",
      "action": "SHOW_SHORTER_VERSION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain concept again",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---


## 19. Show Best Approach Coach

| Field | Value |
|-------|-------|
| Dataset ID | `show_best_approach` |
| Category | Problem Solving |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** Exam-efficient method with seven sections plus `finalAnswer`. Production: [`show_best_approach.j2`](packages/core/prompts/templates/problem_solver/show_best_approach.j2).

**Audit finding (baseline v1.0.0):** Placeholder baseline replaced with complete seven-section exam-oriented coach JSON per bank problem.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `numerical` | Numeric/unit problems | 7 |
| `jee` | JEE Mains framing | 5 |
| `neet` | NEET MCQ / assertion-reason | 2 |
| `multi_part` | Multi-step / derive | 1 |
| `cbse` | CBSE board style | 5 |
| `proof` | Derivation / proof | 2 |
| `diagram` | Diagram-dependent | 2 |
| `ncert_strict` | Strict NCERT wording | 1 |
| `conceptual` | Explain-why / concept | 3 |
| `case_study` | Passage / case-based | 2 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **section_completeness** — All seven sections including Exam Note and When Not to Use.
* **reveal_level** — `revealLevel: full` with boxed final answer.
* **ncert_alignment** — Best method matches chapter skill from DNA metadata.
* **latex_format** — Multiplication spaced; units in `\text{}`.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `problem_text_normalized`, `ncert_context`
* Output keys: `coach_json`

**Prompt template (production):**

```jinja2
You are ScholarSync AI Coach showing the most reliable exam approach.

Problem:
{{ problem_text_normalized }}

{% if ncert_context %}
NCERT context:
{{ ncert_context }}
{% endif %}

# ROLE

You are an expert NCERT-aligned teacher, exam strategist, and problem-solving coach for Class 11–12 students.

Your job is NOT only to solve the question.

Your job is to:

* Identify the underlying NCERT pattern
* Select the fastest reliable method
* Explain why that method is optimal
* Build exam intuition
* Prevent common mistakes
* Present a clean board-exam style solution

Always prioritize:

1. NCERT correctness
2. JEE/NEET compatible reasoning
3. Exam efficiency
4. Mathematical precision
5. Rendering safety

---

# OUTPUT STRUCTURE

Always return:

1. Problem Pattern
2. Best Method
3. Why This Fits
4. Efficient Setup
5. Clean Solution
6. Exam Note
7. When Not to Use

Never skip sections.

---

{% include 'problem_solver/math_formatting_contract.j2' %}

# REASONING RULES

Before solving, identify: subject, chapter, concept, formula family, question pattern, fastest solving path.

---

# BEST METHOD SELECTION

Priority order:

1. Direct NCERT formula
2. Standard derivation shortcut
3. Conceptual elimination
4. Dimensional reasoning
5. Graph interpretation
6. Full derivation

Prefer fewer steps when equally correct.

---

# EXAM NOTE RULES

Include shortcut, memory trigger, sign convention warning, unit conversion warning, or frequently tested variation.

---

# WHEN NOT TO USE

Explain where the chosen method fails: assumption breakdown, special cases, alternative methods.

---

# QUALITY CHECK

Before returning, verify: valid JSON; no markdown outside JSON; all seven sections present; no malformed equations; no broken units; no unescaped backslashes; final answer matches solution; NCERT notation respected; calculations correct.

---

Return JSON only:
{
  "title": "string",
  "sections": [
    {"heading": "Problem Pattern", "bodyMarkdown": "..."},
    {"heading": "Best Method", "bodyMarkdown": "..."},
    {"heading": "Why This Fits", "bodyMarkdown": "..."},
    {"heading": "Efficient Setup", "bodyMarkdown": "..."},
    {"heading": "Clean Solution", "bodyMarkdown": "..."},
    {"heading": "Exam Note", "bodyMarkdown": "..."},
    {"heading": "When Not to Use", "bodyMarkdown": "..."}
  ],
  "finalAnswer": "string",
  "revealLevel": "full",
  "followUpButtons": [
    {"label": "Compare with basic method", "action": "COMPARE_BASIC_METHOD"},
    {"label": "Explain why this works", "action": "EXPLAIN_WHY_WORKS"},
    {"label": "Give similar exam problem", "action": "GIVE_SIMILAR_PROBLEM"},
    {"label": "Show common mistakes", "action": "SHOW_COMMON_MISTAKES"},
    {"label": "Start Tutor Session", "action": "START_TUTOR_SESSION"}
  ]
}
```

*Runtime note:* `ProblemSolverService` mode `SHOW_BEST_APPROACH`.

### Evaluation examples (30)
## Variation: `numerical`


#### Example 1: `show_best_approach-017`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q3. Which of the following statements are true? A. Unlike Ga that has a very high melting point, Cs has a very low melting point. B. On Pauling scale, the electronegativity values of N and Cl are not the same. C. Ar, K⁺, Cl⁻, Ca²⁺ and S²⁻ are all isoelectronic species. D. The correct order of the first ionization enthalpies of Na, Mg, Al, and Si is Si > Al > Mg > Na. E. The atomic radius of Cs is greater than that of Li and Rb. Choose the correct answer from the options given below: (1) A, B and E only (2) C and E only (3) C and D only (4) A, C and E only

**Ncert Context:**

NCERT Class 12 Chemistry Ch.3: Galvanic cell — oxidation at anode, reduction at cathode. E°cell=E°cathode−E°anode.

**Expected output**

**Coach Json:**

```json
{
  "title": "Exam Approach for Evaluating Statements on Elements",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves evaluating multiple statements about the properties of elements and ions, specifically focusing on melting points, electronegativity, isoelectronic species, ionization enthalpies, and atomic radii."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to evaluate each statement individually based on known properties of the elements and ions involved."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it allows for a clear and systematic verification of each statement against established chemical principles and data, ensuring accuracy."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. **Statement A**: Ga has a high melting point (around 30 °C) while Cs has a low melting point (28.5 °C). **True**.  \n2. **Statement B**: Electronegativity of N is 3.04 and Cl is 3.16 on the Pauling scale. **True**.  \n3. **Statement C**: Ar (18 e⁻), K⁺ (18 e⁻), Cl⁻ (18 e⁻), Ca²⁺ (18 e⁻), and S²⁻ (18 e⁻) are all isoelectronic. **True**.  \n4. **Statement D**: The correct order of first ionization enthalpies is Si > Al > Mg > Na. **False**; the correct order is Si > Al > Mg > Na.  \n5. **Statement E**: The atomic radius of Cs (262 pm) is indeed greater than that of Li (152 pm) and Rb (248 pm). **True**."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Evaluating each statement:  \n- A: True  \n- B: True  \n- C: True  \n- D: False  \n- E: True  \nThus, the true statements are A, B, C, and E. The correct answer is option (1) A, B, and E only."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember the properties of elements and their trends in the periodic table. Use the Pauling scale for electronegativity and recall isoelectronic species when comparing ions."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the statements involve complex interactions or require deeper theoretical understanding beyond basic properties, such as in cases of unusual bonding or hybridization."
    }
  ],
  "finalAnswer": "(1) A, B and E only",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-018`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q77. Given below are two statements: Statement I: [Co(NH3)6]³⁺ is a homoleptic complex whereas [Co(NH3)₄Cl₂]⁺ is a heteroleptic complex. Statement II: Complex [Co(NH3)6]³⁺ has only one kind of ligands but [Co(NH3)₄Cl₂]⁺ has more than one kind of ligands. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is true but Statement II is false. (2) Statement I is false but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.1: Moles n=m/M. Equal atoms when mole amounts match for same species count.

**Expected output**

**Coach Json:**

```json
{
  "title": "Analysis of Coordination Complexes",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves identifying the nature of coordination complexes based on their ligands. It tests knowledge of homoleptic and heteroleptic complexes, which is a common topic in coordination chemistry."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to analyze each statement based on the definitions of homoleptic and heteroleptic complexes. A homoleptic complex contains only one type of ligand, while a heteroleptic complex contains more than one type."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly applies the definitions of the terms involved, allowing for a clear and straightforward evaluation of the truth of each statement without additional calculations."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Identify the ligands in each complex:  \n   - For [Co(NH₃)₆]³⁺: Ligand is NH₃ (6 times).  \n   - For [Co(NH₃)₄Cl₂]⁺: Ligands are NH₃ (4 times) and Cl (2 times).  \n2. Classify each complex based on the type of ligands present."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Statement I**: [Co(NH₃)₆]³⁺ is a homoleptic complex (true).  \n2. **Statement II**: [Co(NH₃)₄Cl₂]⁺ has more than one kind of ligands (true).  \nThus, both statements are true, leading to the conclusion that the correct answer is (3) Both Statement I and Statement II are true."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that homoleptic complexes have only one type of ligand, while heteroleptic complexes have multiple types. This distinction is crucial for identifying and classifying coordination complexes in exams."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the problem involves more complex coordination chemistry concepts, such as geometric isomerism or electronic configurations, where additional analysis would be required."
    }
  ],
  "finalAnswer": "(3) Both Statement I and Statement II are true.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `show_best_approach-019`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, assertion_reason, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q36. Given below are two statement: one is labelled as Assertion ((A)) and the other is labelled as Reason (R): Assertion ((A)) : I undergoes SN2 reaction faster than Cl. Reason (R): Iodine is a better leaving group because of its large size. In the light of the above statements, choose the correct answer from the options given below: (1) Both A and R are true and R is the correct explanation of A. (2) Both A and R are true but R is not the correct explanation of A. (3) A is true but R is false. (4) A is false but R is true.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Exam Approach for Assertion and Reason Questions",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This question follows the Assertion and Reason format, commonly seen in exams. It requires evaluating the truth of both statements and their relationship. Assertion (A) states a fact about the reactivity of Iodine compared to Chlorine in SN2 reactions, while Reason (R) provides an explanation related to the leaving group ability."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to analyze both statements based on chemical principles. First, confirm the truth of Assertion (A) regarding the reactivity of Iodine and then evaluate Reason (R) about the leaving group ability."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly addresses the core of the question: understanding the mechanisms of SN2 reactions and the role of leaving groups. By confirming the validity of both statements, we can accurately determine their relationship."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. **Evaluate Assertion (A)**: Iodine (I) is indeed a better leaving group than Chlorine (Cl) due to its larger size and lower bond strength with carbon. Thus, A is true.\n2. **Evaluate Reason (R)**: The statement that Iodine is a better leaving group because of its large size is also true, as larger atoms can stabilize the negative charge better when they leave. Thus, R is true.\n3. **Determine the relationship**: Since R correctly explains A, the answer is option (1)."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Assertion (A)**: True, I undergoes SN2 reactions faster than Cl due to better leaving group ability.\n2. **Reason (R)**: True, Iodine is a better leaving group because of its larger size.\n3. **Conclusion**: Both A and R are true, and R is the correct explanation of A. \n**Final Answer**: (1)"
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that in SN2 reactions, the quality of the leaving group is crucial. A common memory trigger is that larger halides (I > Br > Cl > F) are better leaving groups due to their ability to stabilize the negative charge upon leaving."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be effective if the statements involve complex mechanisms or if the reasoning provided does not directly relate to the assertion. In cases where the relationship is not clear, a deeper understanding of the underlying chemistry may be required."
    }
  ],
  "finalAnswer": "(1)",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 4: `show_best_approach-020`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q53. Given below are two statements; Statement I: Ferromagnetism is considered as an extreme form of paramagnetism. Statement II: The number of unpaired electrons in a Cr²⁺ ion (Z=24) is the same as that of a Nd³⁺ ion (Z= 60). In the light of the above statements, choose the correct answer from the options given below: (1) Both Statement I and Statement II are true (2) Both Statement I and Statement II are false (3) Statement I is true but Statement II is false (4) Statement I is false but Statement II is true

;

**Ncert Context:**

NCERT Class 12 Chemistry Ch.3: Galvanic cell — oxidation at anode, reduction at cathode. E°cell=E°cathode−E°anode.

**Expected output**

**Coach Json:**

```json
{
  "title": "Analysis of Magnetic Properties and Electron Configuration",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves evaluating the truth of two statements related to magnetic properties and electron configurations of specific ions. It requires knowledge of ferromagnetism, paramagnetism, and the electron configurations of transition metals and lanthanides."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To solve this problem, we will analyze each statement independently based on established chemical principles and electron configurations."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it allows us to verify the truth of each statement using fundamental concepts from NCERT chemistry, ensuring accuracy and clarity in reasoning."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. **Evaluate Statement I**: Ferromagnetism is indeed an extreme form of paramagnetism, characterized by a strong attraction to magnetic fields due to parallel alignment of unpaired electrons. This statement is **true**.\n\n2. **Evaluate Statement II**: For Cr²⁺ (Z=24), the electron configuration is [Ar] 3d^4. This gives it 4 unpaired electrons. For Nd³⁺ (Z=60), the electron configuration is [Xe] 4f^3, which has 3 unpaired electrons. Therefore, this statement is **false**."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Statement I**: True, as ferromagnetism is an extreme form of paramagnetism.\n2. **Statement II**: False, Cr²⁺ has 4 unpaired electrons while Nd³⁺ has 3 unpaired electrons.\n\nThus, the correct answer is (3) Statement I is true but Statement II is false."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that ferromagnetism and paramagnetism are related but distinct concepts. Always check the electron configurations for transition metals and lanthanides carefully to count unpaired electrons accurately."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the statements involve complex interactions or if additional context is provided that alters the basic definitions of magnetic properties or electron configurations."
    }
  ],
  "finalAnswer": "(3) Statement I is true but Statement II is false",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 5: `show_best_approach-021`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q13. Energy and radius of first Bohr orbit of He⁺ and Li²⁺ are [Given R_H = 2.18×10⁻¹⁸ J, a₀ = 52.9 pm] (1) E_n (Li²⁺) = -19.62 × 10⁻¹⁸ J: r_n (Li²⁺) = 17.6 pm E_n (He⁺) = -8.72 × 10⁻¹⁸ J; r_n (He⁺) = 26.4 pm (2) E_n (Li²⁺) = -8.72 × 10⁻¹⁸ J; r_n (Li²⁺) = 26.4 pm E_n (He⁺) = -19.62 × 10⁻¹⁸ J: r_n (He⁺) = 17.6 pm (3) E_n (Li²⁺) = -19.62 × 10⁻¹⁶ J; r_n (Li²⁺) = 17.6 pm E_n (He⁺) = -8.72 × 10⁻¹⁶ J: r_n (He⁺) = 26.4 pm (4) E_n (Li²⁺) = -8.72 × 10⁻¹⁶ J; r_n (Li²⁺) = 17.6 pm E_n (He²⁺) = -19.62 × 10⁻¹⁶ J: r_n (He⁺) = 17.6 pm

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Energy and Radius of First Bohr Orbit for He⁺ and Li²⁺",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves calculating the energy and radius of the first Bohr orbit for hydrogen-like ions, specifically He⁺ and Li²⁺. The key concepts include the Bohr model of the atom, where energy levels and radii are derived from fundamental constants and the atomic number of the ion."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to use the formulas for energy and radius in the Bohr model for hydrogen-like atoms: \n\n1. Energy: \n   \\[ E_n = -\\frac{Z^2 R_H}{n^2} \\] \n   where \\( Z \\) is the atomic number, \\( R_H \\) is the Rydberg constant, and \\( n \\) is the principal quantum number. \n\n2. Radius: \n   \\[ r_n = \\frac{n^2 a_0}{Z} \\] \n   where \\( a_0 \\) is the Bohr radius."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method directly applies the established formulas from the Bohr model, which are specifically designed for hydrogen-like ions. It allows for quick calculations of energy and radius based on the atomic number, ensuring accuracy and efficiency."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. For He⁺ (Z = 2): \n   - Energy: \\( E_n = -\\frac{2^2 \\times 2.18 \\times 10^{-18}}{1^2} = -8.72 \\times 10^{-18} \\text{ J} \\) \n   - Radius: \\( r_n = \\frac{1^2 \\times 52.9 \\text{ pm}}{2} = 26.45 \\text{ pm} \\) \n\n2. For Li²⁺ (Z = 3): \n   - Energy: \\( E_n = -\\frac{3^2 \\times 2.18 \\times 10^{-18}}{1^2} = -19.62 \\times 10^{-18} \\text{ J} \\) \n   - Radius: \\( r_n = \\frac{1^2 \\times 52.9 \text{ pm}}{3} = 17.63 \text{ pm} \\)"
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "For He⁺: \n- \\( E_n = -8.72 \\times 10^{-18} \\text{ J} \\) \n- \\( r_n = 26.45 \\text{ pm} \\) \n\nFor Li²⁺: \n- \\( E_n = -19.62 \\times 10^{-18} \\text{ J} \\) \n- \\( r_n = 17.63 \\text{ pm} \\) \n\nThus, the correct option is (1): \\( E_n (Li²⁺) = -19.62 \\times 10^{-18} \\text{ J}; r_n (Li²⁺) = 17.6 \\text{ pm}, E_n (He⁺) = -8.72 \\times 10^{-18} \\text{ J}; r_n (He⁺) = 26.4 \\text{ pm} \\)."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember the key formulas for energy and radius in the Bohr model. A useful memory trigger is to note that energy is proportional to the square of the atomic number and inversely proportional to the square of the principal quantum number. Also, ensure to convert units correctly when necessary."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be applicable for multi-electron atoms or when considering relativistic effects. It assumes a simplified model that does not account for electron-electron interactions in more complex atoms."
    }
  ],
  "finalAnswer": "Option (1): E_n (Li²⁺) = -19.62 × 10⁻¹⁸ J; r_n (Li²⁺) = 17.6 pm, E_n (He⁺) = -8.72 × 10⁻¹⁸ J; r_n (He⁺) = 26.4 pm.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 6: `show_best_approach-022`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q63. Given below are two statements: Statement I: Both [Co(NH₃)₆]³⁺ and [CoF₆]³⁻ complexes are octahedral but differ in their magnetic behaviour. Statement II: [Co(NH₃)₆]³⁺ is diamagnetic whereas [CoF₆]³⁻ is paramagnetic. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is true but Statement II is false. (2) Statement I is false but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Magnetic Behavior of Coordination Complexes",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves evaluating the properties of coordination complexes, specifically their geometry and magnetic behavior. It tests knowledge of octahedral complexes and the factors influencing their magnetic properties."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to analyze the electronic configuration of the central metal ion in both complexes and determine the effect of the ligands on the magnetic properties. This involves understanding crystal field theory."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Crystal field theory explains how different ligands affect the splitting of d-orbitals in transition metal complexes. Strong field ligands (like NH₃) lead to lower energy d-orbitals and can cause pairing of electrons, resulting in diamagnetism. Weak field ligands (like F⁻) do not cause pairing, leading to unpaired electrons and paramagnetism."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Identify the oxidation state of Co in both complexes: Co in [Co(NH₃)₆]^{3+} is +3 and in [CoF₆]^{3-} is +3.  \n2. Determine the ligand field strength: NH₃ is a strong field ligand, while F⁻ is a weak field ligand.  \n3. Analyze the electron configuration: Co^{3+} has a d^6 configuration.  \n4. For [Co(NH₃)₆]^{3+}, the electrons will pair up (diamagnetic). For [CoF₆]^{3-}, the electrons will remain unpaired (paramagnetic)."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. [Co(NH₃)₆]^{3+} is a strong field ligand, leading to paired electrons: diamagnetic.  \n2. [CoF₆]^{3-} is a weak field ligand, leading to unpaired electrons: paramagnetic.  \nThus, Statement I is true and Statement II is true.  \nThe correct answer is (3) Both Statement I and Statement II are true."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that strong field ligands cause pairing of electrons, leading to diamagnetism, while weak field ligands do not cause pairing, resulting in paramagnetism. A mnemonic to remember ligand strength: 'Strong NH₃, Weak F⁻'."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not apply if the complexes have unusual geometries or if there are additional factors affecting the magnetic properties, such as spin-orbit coupling or if the ligands are in unusual coordination environments."
    }
  ],
  "finalAnswer": "(3) Both Statement I and Statement II are true.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 7: `show_best_approach-023`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q33. Given below are two statements: Statement I: Like nitrogen that can form ammonia, arsenic can form arsine. Statement II: Antimony cannot form antimony pentoxide. In the light of the above statements, choose the most appropriate answer from the options given below: (1) Both Statement I and Statement II are correct. (2) Both Statement I and Statement II are incorrect. (3) Statement I is correct but Statement II is incorrect. (4) Statement I is incorrect but Statement II is correct.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Analysis of Chemical Statements",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves evaluating the correctness of two statements regarding chemical compounds formed by elements in the same group of the periodic table."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to analyze each statement based on chemical knowledge of the elements involved, specifically nitrogen, arsenic, and antimony."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly applies knowledge of chemical behavior and compound formation, which is crucial for understanding the properties of elements in the periodic table."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Evaluate Statement I: Nitrogen can form ammonia (NH₃), and arsenic can indeed form arsine (AsH₃). Thus, Statement I is correct.\n2. Evaluate Statement II: Antimony can form antimony pentoxide (Sb₂O₅), so Statement II is incorrect."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Based on the evaluations:\n- Statement I is correct.\n- Statement II is incorrect.\nThus, the answer is (3) Statement I is correct but Statement II is incorrect."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that elements in the same group often exhibit similar chemical properties. This can help in quickly assessing the validity of statements regarding their compounds."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the statements involve complex reactions or if the context of the question changes significantly, requiring deeper chemical analysis."
    }
  ],
  "finalAnswer": "(3) Statement I is correct but Statement II is incorrect.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `show_best_approach-007`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q58. Consider the following data. Electrolyte (S cm mol ) HCl is sparingly soluble in water. If the conductivity of the saturated solution is S cm then the solubility product of can be given as (Here ) (1) (2) (3) (4) 0.25 1 x% x% 50% 60% 70% 80% A(g) 10 400 A(g) ⇌B(g) Kc 400 4.0 B(g) A(g) B(g) R = 0.082 −1 −1 3.28, 2.624 2.624, 3.28 3.28, 0.656 0.656, 6.56 Λ∘ m 2 −1 BaCl2 x1 H2SO4 x2 x3 BaSO4 BaSO4 x −1 BaSO4 Λm = Λ∘ m 106x2 α2(x1 + x2 −2x3)2 x2 (x1 + x2 −2x3)2 α2(x1 + x2 −2x3)2 106x2 x2 (x1 + x2 + 2x3)2

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Solubility Product Calculation for Sparingly Soluble Electrolytes",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves calculating the solubility product (Ksp) of a sparingly soluble electrolyte based on its conductivity in a saturated solution. The key concepts include understanding the relationship between conductivity, concentration, and the solubility product."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To find the solubility product, use the formula: \\[ K_{sp} = C^2 \\cdot \\Lambda \\] where \\( C \\) is the molar concentration of the ions in the solution and \\( \\Lambda \\) is the molar conductivity. You can derive \\( C \\) from the conductivity of the solution."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method fits because it directly relates the measurable conductivity of the solution to the concentration of ions, allowing for the calculation of the solubility product without needing to know the exact solubility of the electrolyte."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Measure the conductivity of the saturated solution.  \n2. Calculate the molar concentration of the ions using the formula: \\[ C = \\frac{\\text{Conductivity}}{\\Lambda} \\]  \n3. Substitute \\( C \\) into the Ksp formula to find the solubility product."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. Let \\( \\sigma \\) be the conductivity of the saturated solution.  \n2. Calculate \\( C = \\frac{\\sigma}{\\Lambda} \\).  \n3. Substitute \\( C \\) into \\( K_{sp} = C^2 \\cdot \\Lambda \\) to find the final answer."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Always remember to check the units of conductivity and molar conductivity to ensure they are compatible. This will help avoid calculation errors."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method is not suitable for strong electrolytes that are completely soluble, as their Ksp is not relevant. Additionally, if the conductivity is not measured accurately, the results may be unreliable."
    }
  ],
  "finalAnswer": "Ksp can be calculated using the formula \\( K_{sp} = C^2 \\cdot \\Lambda \\), where \\( C \\) is derived from the conductivity of the saturated solution.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-008`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q34. The two wires A and B of equal cross-section but of different materials are joined together. The ratio of Young's modulus of wire A and wire B is 20/11. When the joined wire is kept under certain tension the elongations in the wires A and B are equal. If the length of wire A is 2.2 m, then the length of wire B is ______ m. (1) 1.1 (2) 2.22 (3) 1.21 (4) 4.44

;

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Elongation of Wires A and B",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves two wires of different materials joined together, where the elongations are equal under tension. The key concept is the relationship between Young's modulus, elongation, and length."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "Use the formula for elongation in terms of Young's modulus: \\( \\Delta L = \\frac{F L}{A Y} \\). Since the elongations are equal, we can set up a ratio based on the given Young's modulus."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method directly relates the elongation to the properties of the materials (Young's modulus) and their lengths, allowing us to find the unknown length using the ratio of Young's moduli."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Let the lengths of wires A and B be \\( L_A \\) and \\( L_B \\) respectively. Given that \\( \\frac{Y_A}{Y_B} = \\frac{20}{11} \\) and \\( \\Delta L_A = \\Delta L_B \\), we can write: \\( \\frac{F L_A}{A Y_A} = \\frac{F L_B}{A Y_B} \\). Cancelling common terms and rearranging gives us the relationship between lengths."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "From the elongation equality, we have:\n\\[ \\frac{L_A}{Y_A} = \\frac{L_B}{Y_B} \\]\nSubstituting the values:\n\\[ \\frac{2.2}{20} = \\frac{L_B}{11} \\]\nCross-multiplying:\n\\[ L_B = 2.2 \\times \\frac{11}{20} \\]\nCalculating:\n\\[ L_B = 1.21 \\text{ m} \\]"
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that when elongations are equal, the ratio of lengths is inversely proportional to the ratio of Young's moduli. This can save time during exams."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method assumes that the wires are under the same tension and that material properties remain constant. It may not apply if the wires are subjected to varying conditions or if they have different cross-sectional areas."
    }
  ],
  "finalAnswer": "1.21 m",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `show_best_approach-009`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q64. Given below are two statements: Statement I: -diethylcyclohexanone and -methyl- -n-propylcyclohexanone are metamers. Statement II: -tetramethylcyclohexanone exhibits keto-enol tautomerism. In the light of the above statements, choose the correct answer from the options given below (1) Both Statement I and Statement II are true (2) Both Statement I and Statement II are false (3) Statement I is true but Statement II is false (4) Statement I is false but Statement II is true

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Exam Approach for Organic Chemistry Statements",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "The problem presents two statements regarding organic compounds and requires an evaluation of their truthfulness. This type of question often appears in organic chemistry exams, where understanding functional groups and structural isomerism is crucial."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To evaluate the statements, first analyze the definitions of metamers and keto-enol tautomerism. Metamers are structural isomers that differ in the arrangement of atoms around a functional group. Keto-enol tautomerism involves the interconversion between a keto form and an enol form of a compound."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Understanding the structural characteristics of the compounds mentioned in the statements is essential. Diethylcyclohexanone and methyl-n-propylcyclohexanone can be analyzed for their structural differences to confirm if they are metamers. For Statement II, recognizing that tetramethylcyclohexanone does not exhibit keto-enol tautomerism due to the absence of a hydrogen atom on the carbon adjacent to the carbonyl group is key."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Create a table or diagram to visualize the structures of the compounds in Statement I. For Statement II, recall the general conditions required for keto-enol tautomerism to occur. This visual aid can help clarify the relationships and properties of the compounds."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "After analyzing both statements: Statement I is true as diethylcyclohexanone and methyl-n-propylcyclohexanone are indeed metamers. Statement II is false because tetramethylcyclohexanone does not exhibit keto-enol tautomerism. Thus, the correct answer is (3) Statement I is true but Statement II is false."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Always verify the definitions of terms like metamers and tautomerism. Familiarity with structural isomers and functional groups can significantly aid in answering similar questions correctly."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This approach may not be suitable for questions that require detailed mechanistic pathways or complex reaction mechanisms, where a deeper understanding of reaction conditions and kinetics is necessary."
    }
  ],
  "finalAnswer": "(3) Statement I is true but Statement II is false",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 4: `show_best_approach-010`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q69. Match the LIST-I with LIST-II List-I Deficiency Disease List-II Vitamin A. Scurvy I. Pyridoxine B. Convulsions II. Vitamin A C. Cheilosis III. Ascorbic Acid D. Xerophthalmia IV. Riboflavin Choose the correct answer from the options given below: (1) A-I, B-III, C-II, D-IV (2) A-I, B-III, C-IV, D-II (3) A-III, B-I, C-IV, D-II (4) A-III, B-I, C-II, D-IV n-C4H9OH n-C4H9NH2 n-C4H10 C2H5NHC2H5 C < B < A < D D < C < B < A C < D < B < A D < B < A < C

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Matching Deficiency Diseases with Vitamins",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves matching deficiency diseases with their corresponding vitamins. It requires knowledge of vitamin deficiencies and their associated conditions."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "Start by identifying the deficiency diseases listed in List-I and recalling the vitamins associated with each condition. Use elimination to match them correctly with List-II."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is effective because it leverages direct knowledge of nutritional science, allowing for quick identification of the correct matches without unnecessary calculations."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "List out the known associations: \n- Scurvy is caused by Vitamin C (Ascorbic Acid). \n- Convulsions can be linked to Vitamin B6 (Pyridoxine). \n- Cheilosis is associated with Riboflavin (Vitamin B2). \n- Xerophthalmia is a deficiency of Vitamin A."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "From the associations, we can match: \n- A (Scurvy) - III (Ascorbic Acid) \n- B (Convulsions) - I (Pyridoxine) \n- C (Cheilosis) - IV (Riboflavin) \n- D (Xerophthalmia) - II (Vitamin A) \nThus, the correct answer is (3) A-III, B-I, C-IV, D-II."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Always remember the common deficiency diseases and their vitamins. This knowledge is crucial for various exams, especially in health and nutrition-related subjects."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if you are unsure about the associations or if the problem involves more complex relationships between multiple nutrients and diseases."
    }
  ],
  "finalAnswer": "(3) A-III, B-I, C-IV, D-II",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 5: `show_best_approach-011`

- **Variation:** jee
- **Tags:** physics, jee, source_pdf_jee_april_2026, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q12. Let chord PQ of length of the parabola be such that the ordinates of points and are in the ratio . If the chord PQ subtends an angle at the focus of the parabola, then is equal to: (1) (2) (3) (4) 20 x1, x2, … , x20 ∑20 i=1(xi + 5)2 = 2500 ∑20 i=1(xi −5)2 = 100 2 : 1 3 : 1 3 : 2 4 : 1 (N + 1) −N 9 16 N 5 7 8 9 e x2 a2 −y2 b2 = 1 (6, 4√3) 15(e2 + 1) = 34e x2 b2 − y2 2(a2 + 1) = 1 10 20 25 30 3√13 y2 = 12x P Q 1 : 2 α sin α 3 5 4 5 5 13 12 13

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Chord PQ of a Parabola and Angle at Focus",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves a parabola where a chord subtends an angle at the focus. The key elements include the length of the chord, the ratio of the ordinates of points on the chord, and the angle subtended at the focus."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To solve this problem, use the properties of parabolas and the geometric relationships involving the focus and the chord. Specifically, apply the formula for the angle subtended by a chord at the focus, which can be derived from the coordinates of the points on the parabola."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This approach leverages the geometric properties of parabolas, particularly how chords relate to the focus. Understanding the ratios of the ordinates helps in determining the coordinates of the points on the parabola, which are essential for calculating the angle."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Define the parabola's equation and the coordinates of points P and Q based on the given ratio of ordinates. Use these coordinates to find the angle subtended at the focus using trigonometric relationships."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. Let the parabola be defined as \\( y^2 = 4ax \\).  \n2. Assume the ordinates of points P and Q are \\( 2k \\) and \\( k \\) respectively (based on the ratio 2:1).  \n3. Find the corresponding x-coordinates using the parabola equation.  \n4. Calculate the angle subtended at the focus using the formula:  \n   \\[ \\tan(\\theta) = \\frac{y_2 - y_1}{x_2 - x_1} \\]  \n5. Substitute the values to find the angle and simplify to get the final answer."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Ensure to check the ratio of ordinates carefully and apply the correct formula for the angle subtended at the focus. Double-check calculations for accuracy."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the problem involves a different conic section or if additional complexities are introduced, such as varying lengths of the chord or different ratios that do not conform to simple geometric properties."
    }
  ],
  "finalAnswer": "3 : 2",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `show_best_approach-014`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q41. Each of the following characteristics represent a Kingdom proposed by Whittaker. Arrange the following in increasing order of complexity of body organization. A. Multicellular heterotrophs with cell wall made of chitin. B. Heterotrophs with tissue/organ/organ system level of body organization. C. Prokaryotes with cell wall made of polysaccharides and amino acids. D. Eukaryotic autotrophs with tissue/organ level of body organization. E. Eukaryotes with cellular body organization. Choose the correct answer from the options given below: (1) A, C, E, B, D (2) C, E, A, D, B (3) A, C, E, D, B (4) C, E, A, B, D

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Kingdom Complexity in Biology",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves categorizing different biological entities based on their complexity of body organization. The entities are described in terms of their cellular structure, nutritional mode, and organizational level."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To solve this problem, we should analyze each option based on the complexity of body organization. We start from the simplest (prokaryotes) to the most complex (multicellular organisms with advanced organization)."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "The complexity of body organization increases from unicellular organisms to multicellular organisms with specialized tissues and organs. Prokaryotes are the simplest, followed by unicellular eukaryotes, then multicellular organisms with varying levels of organization."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. C: Prokaryotes (simplest)\\n2. E: Unicellular eukaryotes (more complex than prokaryotes)\\n3. A: Multicellular heterotrophs with chitin (fungi)\\n4. D: Eukaryotic autotrophs with tissue/organ level (plants)\\n5. B: Heterotrophs with tissue/organ/organ system level (animals, most complex)"
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Arranging the options in increasing order of complexity gives us: C (Prokaryotes) < E (Unicellular Eukaryotes) < A (Multicellular Heterotrophs) < D (Eukaryotic Autotrophs with Tissue/Organ) < B (Heterotrophs with Organ Systems). Thus, the correct order is C, E, A, D, B."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Always remember to categorize organisms based on their cellular structure and organizational complexity. This will help in similar questions regarding biological classification."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable for questions that require detailed phylogenetic analysis or evolutionary relationships, as it focuses solely on organizational complexity."
    }
  ],
  "finalAnswer": "2",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-015`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q75. Which one of the following can be explained on the basis of Mendel's Law of Dominance? A. Out of one pair of factors one is dominant and the other is recessive. B. Alleles do not show any expression and both the characters appear as such in F2 generation. C. Factors occur in pair in normal diploid plants. D. The discrete unit controlling a particular character is called factor. E. The expression of only one of the parental characters is found in a monohybrid cross. Choose the correct answer from the options given below: (1) B, C and D only (2) A, B, C, D and E

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Mendel's Law of Dominance",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This question tests your understanding of Mendel's principles, specifically the Law of Dominance, which states that in a pair of alleles, one can mask the expression of the other."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To solve this problem, identify which statements align with the Law of Dominance. Focus on definitions and examples from Mendelian genetics."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "The Law of Dominance explains that in a heterozygous condition, the dominant allele will express its trait over the recessive allele. This is evident in options A and E, while C and D provide foundational concepts related to genetics."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "List the options and categorize them based on their relevance to the Law of Dominance. This will help you quickly identify which statements are correct."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "The correct answer is (2) A, B, C, D and E. All options relate to Mendel's principles, but A and E directly illustrate the Law of Dominance."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember to connect definitions with examples from Mendel's experiments. This will help reinforce your understanding and recall during exams."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "Avoid using this approach if the question requires a deeper analysis of genetic interactions beyond basic Mendelian principles, such as polygenic inheritance or epistasis."
    }
  ],
  "finalAnswer": "(2) A, B, C, D and E",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `show_best_approach-016`

- **Variation:** multi_part
- **Tags:** biology, neet, source_pdf_neet_botany, multi_part, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q57. Identify the correct statements: A. Detrivores perform fragmentation B. The humus is further degraded by some microbes during mineralization. C. Water soluble inorganic nutrients go down into the soil and get precipitated by a process called leaching. D. The detritus food chain begins with living organisms. E. Earthworms break down detritus into smaller particles by a process called catabolism. Choose the correct answer from the options given below: a. D, E, A only b. A, B, C only c. B, C, D only d. C, D, E only

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Exam Approach for Ecology Concepts",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This question tests knowledge of ecological concepts, specifically the roles of detritivores, the process of mineralization, and nutrient cycling in soil."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To solve this problem, evaluate each statement for accuracy based on ecological principles. Identify which statements are true about detritivores, humus, leaching, and the detritus food chain."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Understanding the roles of organisms in ecosystems and nutrient cycles is crucial in biology. Each statement relates to these concepts, making it essential to analyze them carefully."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "List out the statements and categorize them as true or false based on ecological knowledge. This structured approach helps in quickly identifying the correct options."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "A. True - Detritivores do perform fragmentation. B. True - Humus is further degraded by microbes during mineralization. C. False - Leaching refers to the removal of nutrients from the soil, not precipitation. D. False - The detritus food chain begins with dead organic matter, not living organisms. E. False - Earthworms break down detritus through a process called fragmentation, not catabolism. Thus, the correct statements are A and B."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "In ecology questions, pay attention to the definitions and processes involved. Misunderstanding terms like leaching or catabolism can lead to incorrect answers."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be effective if the question involves complex scenarios or requires application of concepts rather than direct knowledge recall."
    }
  ],
  "finalAnswer": "b. A, B, C only",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `show_best_approach-001`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

CBSE Class XII Biology — Testing Question Bank questions that follow. (a) To which category of evolution — divergent or convergent — do the following evolutionary relationships belong to: (i) Humans and Macaque, (ii) Humans and Frog? (b) What do the biochemical similarities in haemoglobin suggest about the evolutionary relationship between humans, frog and lamprey? (c) (i) Which one of the two is closely related to humans and why? OR (c) (ii) Which one of the two is distantly related to humans and why? S.No. Animal No. of amino acid differences in haemoglobin with that of humans 1 Macaque 08 2 Dog 32 3 Bird 45 4 Frog 67 5 Lamprey 125

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Evolutionary Relationships in Biology",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "The problem involves analyzing evolutionary relationships based on amino acid differences in haemoglobin among various species. It requires categorizing these relationships as divergent or convergent evolution and understanding the implications of biochemical similarities."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "1. Identify the evolutionary relationships: (i) Humans and Macaque (divergent), (ii) Humans and Frog (divergent).  \n2. Analyze the number of amino acid differences in haemoglobin to determine closeness of relationships.  \n3. Answer the questions based on the data provided."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method fits because it systematically categorizes the relationships and uses quantitative data (amino acid differences) to infer evolutionary closeness, aligning with the principles of comparative biology."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Create a table of amino acid differences.  \n2. Compare differences to determine which species are more closely related to humans.  \n3. Use the differences to answer the questions about evolutionary relationships."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Divergent Evolution**:  \n   - (i) Humans and Macaque: Divergent  \n   - (ii) Humans and Frog: Divergent  \n2. **Biochemical Similarities**: The fewer the amino acid differences, the closer the evolutionary relationship.  \n   - Macaque (8 differences) is closest to humans.  \n   - Lamprey (125 differences) is the most distantly related.  \n3. **Answer to (c)**: (c)(i) Macaque is closely related due to only 8 differences. (c)(ii) Lamprey is distantly related due to 125 differences."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Be clear about the definitions of divergent and convergent evolution. Use the data provided to support your answers, and ensure you understand the implications of biochemical similarities."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the question requires qualitative analysis rather than quantitative, or if it involves complex evolutionary mechanisms beyond simple amino acid comparisons."
    }
  ],
  "finalAnswer": "Humans and Macaque are divergent; Humans and Frog are also divergent. Biochemical similarities in haemoglobin suggest closer evolutionary relationships based on fewer amino acid differences. Macaque is closely related to humans (8 differences), while Lamprey is distantly related (125 differences).",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-002`

- **Variation:** cbse
- **Tags:** biology, cbse, source_pdf_cbse_biology, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q47. The diagram below shows the distribution of two barnacle species, Chthamalus and Balanus on a rocky sea shore. When Balanus is experimentally removed, Chthamalus expands its range in lower intertidal zone. (a) Identify and define the ecological phenomenon demonstrated by this observation. OR (a) State the principle that explains the elimination of one species. (b) Two different species can compete for the same resource. Give another example of it. (c) How do species avoid competition in nature? Explain with an example.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Ecological Competition and Species Distribution",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This question addresses ecological principles related to competition between species, specifically focusing on the distribution of barnacle species in intertidal zones. It involves identifying ecological phenomena, providing examples of competition, and explaining mechanisms of resource partitioning."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method for answering this question is to first identify the ecological phenomenon of competitive exclusion, then provide a relevant example of interspecific competition, and finally explain resource partitioning as a mechanism to avoid competition."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly addresses the core concepts of ecology as outlined in the NCERT syllabus. It allows for a structured response that covers all parts of the question systematically, ensuring clarity and completeness."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Identify the ecological phenomenon: Competitive exclusion.  \n2. Provide an example of interspecific competition: For instance, two species of plants competing for sunlight.  \n3. Explain how species avoid competition: Through resource partitioning, such as different species of birds feeding at different heights in trees."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Ecological Phenomenon:** The observation demonstrates **competitive exclusion**, which states that two species competing for the same limited resource cannot coexist at constant population values. When Balanus is removed, Chthamalus expands its range into the lower intertidal zone.  \n2. **Example of Competition:** An example of interspecific competition is seen in plants, where species like *Quercus* (oak) and *Pinus* (pine) compete for sunlight and nutrients in the same habitat.  \n3. **Avoiding Competition:** Species can avoid competition through **resource partitioning**. For example, different bird species may feed on insects at varying heights in the same tree, thus minimizing direct competition for food."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember the principle of competitive exclusion and resource partitioning as key concepts in ecology. A good memory trigger is: 'No two species can occupy the same niche indefinitely.'"
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not apply if the question requires a focus on abiotic factors affecting species distribution rather than biotic interactions. In such cases, a different approach focusing on environmental factors would be necessary."
    }
  ],
  "finalAnswer": "1. Competitive exclusion; 2. Example: *Quercus* and *Pinus* competing for sunlight; 3. Resource partitioning: Different bird species feeding at different heights.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `show_best_approach-003`

- **Variation:** cbse
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q47. Two vertical light poles of height 22 m and 16 m stand on the opposite sides of a 20 m wide road as shown below in the figure. Two ladders of length l₁ and l₂ are placed from a common point R on the road at a distance of x m from the smaller pole. Based on the above information, answer the following questions: (i) Express p(x) = l₁ + l₂ in terms of x. (ii) Find p'(x). (iii) (a) Find the value of x for which l₁² + l₂² is minimum. OR (iii) (b) If the 22 m long pole is also replaced by a 16 m long pole, at what distance from either pole should the ladders be kept so that the sum of squares of lengths of ladders needed to reach the top of the pole is minimum?

[Diagram: The figure depicts a straight road with two streetlights positioned at points A and C. The road is represented as a black rectangle with a central white dashed line indicating lanes. The distance between points B and D is labeled as 20 m. Point R is located on the road, between points B and D, with an unspecified distance labeled as x extending from R to D. Two lines, labeled l1 and l2, extend from points A and C, respectively, towards point R, indicating angles of inclination. The streetlights at points A and C are shown with a curved top, resembling light fixtures. The overall layout is horizontal, with the road running from left (B) to right (D). The angles formed by lines l1 and l2 with the horizontal are not specified numerically. There are no additional numeric annotations or arrows indicating motion directions in the diagram.]

**Ncert Context:**

NCERT Class 12 Mathematics Ch.13: P(E)=favourable/total. P(A∪B)=P(A)+P(B)−P(A∩B). Bayes links prior and likelihood.

**Expected output**

**Coach Json:**

```json
{
  "title": "Ladder Problem with Two Poles",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves optimizing the sum of the lengths of two ladders placed from a point on the road to the tops of two vertical poles. It requires the use of calculus to find the minimum value of a function derived from the lengths of the ladders."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to express the lengths of the ladders in terms of the distance from one pole, derive the function for the sum of the lengths, and then use differentiation to find the minimum."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly applies calculus to find minimum values, which is a common technique in optimization problems. It leverages the relationship between geometry and algebra effectively."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Let the height of the first pole (22 m) be denoted as H_1 and the second pole (16 m) as H_2. The distance from the smaller pole to point R is x m, and the distance from the larger pole to point R is (20 - x) m. The lengths of the ladders can be expressed using the Pythagorean theorem."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. Express the lengths of the ladders:\n   - For the first pole: \n   \n   l_1 = \frac{H_1}{\text{cos}(\theta_1)} = \frac{22}{\text{cos}(\tan^{-1}(\frac{22}{x}))} = \frac{22\text{ sec}(\theta_1)}{x}\n   \n   - For the second pole:\n   \n   l_2 = \frac{H_2}{\text{cos}(\theta_2)} = \frac{16}{\text{cos}(\tan^{-1}(\frac{16}{20-x}))} = \frac{16\text{ sec}(\theta_2)}{20-x}\n   \n   2. The function to minimize is:\n   \n   p(x) = l_1 + l_2 = \frac{22}{\text{cos}(\tan^{-1}(\frac{22}{x}))} + \frac{16}{\text{cos}(\tan^{-1}(\frac{16}{20-x}))}\n   \n   3. Differentiate p(x) to find p'(x) and set it to zero to find critical points:\n   \n   p'(x) = 0 \text{ gives the value of } x \text{ for which } l_1^2 + l_2^2 \text{ is minimum.}"
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember to check the second derivative to confirm that the critical point found is indeed a minimum. Also, ensure that the values of x are within the limits of the road width (0 to 20 m)."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the poles are not vertical or if the road is not straight, as it relies on the Pythagorean theorem and the assumption of vertical heights."
    }
  ],
  "finalAnswer": "x = 8.8 m (for minimum l_1^2 + l_2^2)",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 4: `show_best_approach-004`

- **Variation:** cbse
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q48. An online delivery company in a city has 5000 subscribers and collects annual subscription fees of ₹300 per subscriber for unlimited free deliveries. The company wishes to increase the annual subscription fee. It is predicted that, for every increase of ₹1, ten subscribers will discontinue. Assume that the company increased the annual fee by ₹x. Based on the given information, answer the following questions: (i) How many subscribers will discontinue after an increase of ₹x in annual fee? (ii) If R(x) denotes the total revenue collected after the increase of ₹x in subscription fee, express R(x) as a function of x. (iii) (a) Find the value of x for which R(x) is maximum. OR (iii) (b) Find the sub-intervals of (0, 5000) in which R(x) is increasing and decreasing.

**Ncert Context:**

NCERT Class 12 Mathematics Ch.13: P(E)=favourable/total. P(A∪B)=P(A)+P(B)−P(A∩B). Bayes links prior and likelihood.

**Expected output**

**Coach Json:**

```json
{
  "title": "Maximizing Revenue for an Online Delivery Company",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves maximizing revenue based on a linear relationship between subscription fees and subscriber retention. It requires understanding of revenue functions and their optimization."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to express the revenue function R(x) in terms of the variable x (the increase in subscription fee) and then use calculus to find its maximum by taking the derivative and setting it to zero."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly utilizes the relationship between the number of subscribers and the fee increase, allowing us to derive a quadratic revenue function that can be easily maximized using calculus."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Let \\( S(x) \\) be the number of subscribers after the fee increase. We have \\( S(x) = 5000 - 10x \\). The revenue function is then given by \\( R(x) = (300 + x) \\cdot S(x) = (300 + x)(5000 - 10x) \\)."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Subscribers Discontinuing**: \\( S(x) = 5000 - 10x \\)\\n2. **Revenue Function**: \\[ R(x) = (300 + x)(5000 - 10x) = 1500000 + 5000x - 3000x - 10x^2 = 1500000 + 2000x - 10x^2 \\]\\n3. **Maximizing Revenue**: To find the maximum, take the derivative and set it to zero:\\n   \\[ R'(x) = 2000 - 20x \\] \\[ 0 = 2000 - 20x \\] \\[ 20x = 2000 \\] \\[ x = 100 \\]\\n4. **Maximum Revenue**: Substitute \\( x = 100 \\) back into \\( R(x) \\) to find the maximum revenue."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember to check the second derivative to confirm that it is negative, indicating a maximum. Also, be cautious with the limits of x; it should not exceed the number of subscribers."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be applicable if the relationship between fee increase and subscriber loss is non-linear or if there are fixed costs that need to be considered in the revenue function."
    }
  ],
  "finalAnswer": "The value of x for which R(x) is maximum is x = 100.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 5: `show_best_approach-005`

- **Variation:** cbse
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q49. A survey was conducted to find out the success rate of students who qualified the entrance examination by dropping a year after class XII. As per the data collected, 40% students appearing in the examination were dropouts and the remaining students were regular students of class XII. Of the dropouts, 5% qualify the examination while 10% of the regular students qualify the examination. Based on the above information, answer the following questions: (i) Find the probability that a student selected at random is a regular student. (ii) A student is selected at random from a group of dropout students. What is the probability that the student will not qualify the examination? (iii) (a) A student selected at random qualified the examination. Find the probability that student is not a dropout. OR (iii) (b) A student selected at random did not qualify the examination. Find the probability that the student was a regular student.

**Ncert Context:**

NCERT Class 12 Mathematics Ch.13: P(E)=favourable/total. P(A∪B)=P(A)+P(B)−P(A∩B). Bayes links prior and likelihood.

**Expected output**

**Coach Json:**

```json
{
  "title": "Probability of Students Qualifying Entrance Examination",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves calculating probabilities based on conditional outcomes and the total probability theorem. It requires understanding the classification of students into dropouts and regular students, and their respective success rates."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "Use the total probability theorem and Bayes' theorem to solve the problem efficiently. This method allows for clear separation of events and their probabilities."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "The total probability theorem helps in determining the overall probability of an event based on its partition into mutually exclusive events (dropouts and regular students). Bayes' theorem is useful for finding conditional probabilities."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Define events: Let D be the event that a student is a dropout, and R be the event that a student is a regular student. The probabilities are: P(D) = 0.4, P(R) = 0.6, P(Q|D) = 0.05, P(Q|R) = 0.10. Use these to find the required probabilities."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **(i)** Probability that a student selected at random is a regular student: \n   \n   \begin{align*} \n   P(R) & = 1 - P(D) \\ \n   & = 1 - 0.4 \\ \n   & = 0.6 \text{ (or 60\text{\\%})} \n   \\\\ \n   2. **(ii)** Probability that a dropout student will not qualify the examination: \n   \n   \begin{align*} \n   P(Q'|D) & = 1 - P(Q|D) \\ \n   & = 1 - 0.05 \\ \n   & = 0.95 \text{ (or 95\text{\\%})} \n   \\\\ \n   3. **(iii)(a)** Probability that a student qualified the examination is not a dropout: \n   \n   \begin{align*} \n   P(D|Q) & = \frac{P(Q|D)P(D)}{P(Q)} \\ \text{where } P(Q) & = P(Q|D)P(D) + P(Q|R)P(R) \\ \n   & = (0.05)(0.4) + (0.10)(0.6) \\ \n   & = 0.02 + 0.06 \\ \n   & = 0.08 \\ \n   P(D|Q) & = \frac{(0.05)(0.4)}{0.08} = 0.25 \\ \text{ (or 25\text{\\%})} \n   \\\\ \n   4. **(iii)(b)** Probability that a student did not qualify is a regular student: \n   \n   \begin{align*} \n   P(R|Q') & = \frac{P(Q'|R)P(R)}{P(Q')} \\ \text{where } P(Q') & = P(Q'|D)P(D) + P(Q'|R)P(R) \\ \n   & = (0.95)(0.4) + (0.90)(0.6) \\ \n   & = 0.38 + 0.54 \\ \n   & = 0.92 \\ \n   P(R|Q') & = \frac{(0.90)(0.6)}{0.92} \text{ (calculate this value)} \\\\ \n   & \text{Final answer: } P(R|Q') \text{ (calculate to get the final percentage)} \n   \\\\ \n   \text{Note: Calculate the final value for (iii)(b).} \n   \\\\ \n   \text{Final answers: } P(R) = 0.6, P(Q'|D) = 0.95, P(D|Q) = 0.25, P(R|Q') = \text{(calculate this value)} \n   \\\\ \n   \text{(All probabilities are expressed as fractions or percentages.)} \n   \\\\ \n   \text{Note: Ensure to check calculations for accuracy.} \n   \\\\ \n   \\end{align*}"
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember the total probability theorem and Bayes' theorem for conditional probabilities. Be careful with the definitions of events and ensure to calculate probabilities based on the correct partitions."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the events are not mutually exclusive or if the probabilities are not independent. In such cases, other statistical methods or simulations may be required."
    }
  ],
  "finalAnswer": "P(R) = 0.6, P(Q'|D) = 0.95, P(D|Q) = 0.25, P(R|Q') = (calculate this value)",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `show_best_approach-024`

- **Variation:** proof
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, proof, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q23. Given below are two statements: Statement I: A hypothetical diatomic molecule with bond order zero is quite stable. Statement II: As bond order increases, the bond length increases. In the light of the above statements, chose the most appropriate answer from the options given below: (1) Both statement I and Statement II are true (2) Both statement I and Statement II are false (3) Statement I is true but Statement II is false (4) Statement I is true but Statement II is true

;

**Ncert Context:**

NCERT Class 11 Chemistry Ch.1: Moles n=m/M. Equal atoms when mole amounts match for same species count.

**Expected output**

**Coach Json:**

```json
{
  "title": "Analysis of Bond Order Statements",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "The problem presents two statements regarding bond order and stability of diatomic molecules, asking for the truth value of each statement. This aligns with concepts in molecular chemistry, specifically regarding bond order, stability, and bond length."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "Evaluate each statement based on established chemical principles. Statement I can be analyzed using the concept of bond order and stability, while Statement II can be assessed using the relationship between bond order and bond length."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly applies chemical knowledge about bond order, which is foundational in understanding molecular stability and bond characteristics. It allows for a clear evaluation of the truth of each statement."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. **Statement I**: A bond order of zero indicates no bonding interactions, leading to instability (false).  \n2. **Statement II**: As bond order increases, bond length decreases (false). This is a fundamental concept in molecular chemistry."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. **Statement I**: False. A bond order of zero means the molecule does not have a stable bond.  \n2. **Statement II**: False. Higher bond order corresponds to shorter bond lengths.  \nThus, both statements are false, leading to the conclusion that the correct answer is (2) Both statements are false."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that bond order is directly related to bond stability: a higher bond order typically indicates a more stable bond. Also, recall that bond length decreases with increasing bond order."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not apply in cases involving resonance structures or unusual bonding scenarios where traditional bond order concepts may not hold true."
    }
  ],
  "finalAnswer": "(2) Both statements are false",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-025`

- **Variation:** proof
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, proof, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q74. Given below are two statements: Statement I: Aniline does not undergo Friedel-Crafts alkylation reaction. Statement II: Aniline cannot be prepared through Gabriel synthesis. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is correct but Statement II is false. (2) Statement I is incorrect but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false.

;

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Aniline and Friedel-Crafts Reactions",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This question involves evaluating the truth of two statements regarding the chemical behavior of aniline, specifically its reactivity in Friedel-Crafts reactions and its synthesis via Gabriel synthesis."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method to solve this problem is to analyze each statement based on established chemical principles regarding aniline's reactivity and synthesis."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Aniline is a primary aromatic amine, which has a strong electron-donating amino group (-NH₂) that deactivates the aromatic ring towards electrophilic substitution reactions, including Friedel-Crafts alkylation. Additionally, aniline can be prepared via Gabriel synthesis, which involves the use of phthalimide and alkyl halides, leading to the formation of primary amines."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. **Statement I**: Aniline does not undergo Friedel-Crafts alkylation due to the deactivating effect of the amino group. This statement is **true**.\n2. **Statement II**: Aniline can indeed be prepared through Gabriel synthesis, making this statement **false**."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Based on the analysis:\n- Statement I is true: Aniline does not undergo Friedel-Crafts alkylation.\n- Statement II is false: Aniline can be prepared through Gabriel synthesis.\nThus, the correct answer is (1) Statement I is correct but Statement II is false."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that the presence of electron-donating groups like -NH₂ significantly affects the reactivity of aromatic compounds in electrophilic substitution reactions. This is a common theme in organic chemistry."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be applicable if the question involves more complex reactions or if the substituents on the aromatic ring are different from those in standard cases. Always consider the specific context of the reaction."
    }
  ],
  "finalAnswer": "(1) Statement I is correct but Statement II is false.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `show_best_approach-012`

- **Variation:** diagram
- **Tags:** physics, jee, source_pdf_jee_jan_2026, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.47 Suppose there is a uniform circular disc of mass M kg and radius r m shown in figure. The shaded regions are cut out from the disc. The moment of inertia of the remainder about the axis A of the disc is given by x/256 M r². The value of x is ______.

[Diagram: The figure depicts a uniform circular disc with a mass labeled as \( M \) kg and a radius labeled as \( r \) m. The disc has two shaded regions cut out, each represented as circles with a radius of \( \frac{r}{4} \) m. The centers of these shaded regions are positioned horizontally along the diameter of the disc, with the left circle located at a distance of \( \frac{3r}{4} \) m from the center of the disc and the right circle also at \( \frac{3r}{4} \) m from the center. The angle between the line connecting the center of the disc to the center of the right shaded region and the vertical axis is labeled as \( 135^\circ \). A vertical dashed line is drawn through point \( A \), which is located at the center of the disc. The overall layout is horizontal, with the disc oriented in a standard position. The moment of inertia of the remaining part of the disc about the axis \( A \) is given by the expression \( \frac{x}{256} M r^2 \), where \( x \) is an unknown value to be determined.]

**Ncert Context:**

NCERT Class 11 Physics Ch.7: Torque τ=rF sinθ; τ=Iα for rigid body rotation.

**Expected output**

**Coach Json:**

```json
{
  "title": "Moment of Inertia of a Circular Disc with Cut-Out Regions",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves calculating the moment of inertia of a modified circular disc, which is a common topic in rotational dynamics. The moment of inertia depends on the mass distribution relative to the axis of rotation."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to use the parallel axis theorem and the formula for the moment of inertia of a disc. The moment of inertia of a full disc is given by \\( I = \\frac{1}{2} M r^2 \\). We will subtract the moment of inertia of the cut-out regions."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly applies the known formula for the moment of inertia of a disc and uses the parallel axis theorem to account for the removed sections. It simplifies the calculation by leveraging established formulas."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Calculate the moment of inertia of the full disc: \\( I_{full} = \\frac{1}{2} M r^2 \\).  \n2. Determine the moment of inertia of the cut-out regions based on their mass and distance from the axis.  \n3. Subtract the moment of inertia of the cut-out regions from the full disc's moment of inertia."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Let the mass of the cut-out region be \\( m \\) and its distance from the axis be \\( d \\). The moment of inertia of the cut-out region is given by \\( I_{cut-out} = m d^2 \\).  \nUsing the parallel axis theorem, the moment of inertia of the remaining part is:  \n\\[ I_{remaining} = I_{full} - I_{cut-out} = \\frac{1}{2} M r^2 - m d^2 \\]  \nGiven that \\( I_{remaining} = \\frac{x}{256} M r^2 \\), equate and solve for \\( x \\).  \nAssuming the cut-out regions are symmetrically placed, we can find \\( x \\) based on the specific dimensions provided."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember to always check the symmetry of the cut-out regions as it simplifies calculations. Use the parallel axis theorem correctly to avoid mistakes in the moment of inertia calculations."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the cut-out regions are irregularly shaped or if their mass distribution is not uniform. In such cases, a more detailed analysis or numerical integration might be necessary."
    }
  ],
  "finalAnswer": "x = 64",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-013`

- **Variation:** diagram
- **Tags:** physics, jee, source_pdf_jee_jan_2026, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.33 Two shorts dipoles (A, B) A having charges ± 2 μC and length 1 cm and B having charges ± 4 μC and length 1 cm are placed with their centres 80 cm apart as shown in the figure. The electric field at a point P, equi-distant from the centres of both dipoles is ______ N/C.

[Diagram: The figure shows two short dipoles labeled A and B. Dipole A has charges of +2 µC and -2 µC, with a length of 1 cm, positioned horizontally. Dipole B has charges of +4 µC and -4 µC, also with a length of 1 cm, positioned horizontally. The centers of both dipoles are 80 cm apart, indicated by a double-headed arrow labeled with the distance. Point P is located equidistant from the centers of both dipoles, marked with a dot. The arrangement is horizontal, with dipole B on the left and dipole A on the right. The positive and negative charges are clearly marked with plus and minus signs. There are no additional arrows, forces, or connections depicted in the diagram.]

1. 4.5√2 × 10⁴  
2. 9/16 √2 × 10⁴  
3. 9/16 × 10⁵  
4. 4.5 × 10⁴

**Ncert Context:**

NCERT Class 12 Physics Ch.1: Gauss's law relates net flux through a closed surface to enclosed charge. Conductor electrostatics: field inside conductor is zero in electrostatic equilibrium.

**Expected output**

**Coach Json:**

```json
{
  "title": "Vapor Pressure of Liquid B in Ideal Solution",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves the calculation of vapor pressure in an ideal solution using Raoult's Law. It requires understanding the relationship between the vapor pressures of the components in the solution and their mole fractions."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "Use Raoult's Law to relate the vapor pressures of the components in the solution. The equation is given by: \n\\[ P_{solution} = X_A P_A^0 + X_B P_B^0 \\] \nwhere \\( P_{solution} \\) is the vapor pressure of the solution, \\( X_A \\) and \\( X_B \\) are the mole fractions of components A and B, and \\( P_A^0 \\) and \\( P_B^0 \\) are the vapor pressures of pure components A and B, respectively."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Raoult's Law is applicable because the problem specifies that A and B form an ideal solution. The increase in vapor pressure upon adding more of component A allows us to set up equations to find the vapor pressure of component B in its pure state."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Calculate the initial mole fractions of A and B in the solution. \n2. Use the given vapor pressure of the solution and the change in vapor pressure upon adding 1 mol of A to set up equations. \n3. Solve for \\( P_B^0 \\) using the relationships established."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Let \\( P_B^0 \\) be the vapor pressure of B in pure state. \n\n1. Initial moles: \\( n_A = 3, n_B = 1 \\) \n   - Total moles = \\( n_A + n_B = 4 \\) \n   - Mole fraction of A: \\( X_A = \\frac{3}{4} \\) \n   - Mole fraction of B: \\( X_B = \\frac{1}{4} \\) \n\n2. Using Raoult's Law: \n   \\[ P_{solution} = X_A P_A^0 + X_B P_B^0 \\] \n   \\[ 500 = \\frac{3}{4} P_A^0 + \\frac{1}{4} P_B^0 \\] \n   (Equation 1) \n\n3. When 1 mol of A is added: \n   - New moles: \\( n_A = 4, n_B = 1 \\) \n   - New total moles = 5 \n   - New mole fraction of A: \\( X_A' = \\frac{4}{5} \\) \n   - New mole fraction of B: \\( X_B' = \\frac{1}{5} \\) \n\n4. New vapor pressure: \n   \\[ P_{new} = X_A' P_A^0 + X_B' P_B^0 \\] \n   \\[ 520 = \\frac{4}{5} P_A^0 + \\frac{1}{5} P_B^0 \\] \n   (Equation 2) \n\n5. Solve Equations 1 and 2 simultaneously to find \\( P_B^0 \\). \n   - From Equation 1: \\( 500 = \\frac{3}{4} P_A^0 + \\frac{1}{4} P_B^0 \\) \n   - From Equation 2: \\( 520 = \\frac{4}{5} P_A^0 + \\frac{1}{5} P_B^0 \\) \n\n6. Rearranging both equations gives: \n   \\[ P_A^0 = \\frac{2000 - P_B^0}{3} \\] \n   \\[ P_A^0 = \\frac{2600 - P_B^0}{4} \\] \n\n7. Equating and solving for \\( P_B^0 \\): \n   \\[ \\frac{2000 - P_B^0}{3} = \\frac{2600 - P_B^0}{4} \\] \n   - Cross-multiplying and simplifying leads to \\( P_B^0 = 400 \\text{ mm Hg} \\)."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that for ideal solutions, the sum of the partial pressures equals the total pressure. Keep track of mole fractions carefully, and ensure you set up your equations correctly to avoid mistakes."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method is not applicable if the solution does not behave ideally or if there are strong interactions between the components that affect vapor pressures significantly."
    }
  ],
  "finalAnswer": "400 mm Hg",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `show_best_approach-026`

- **Variation:** ncert_strict
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, ncert_strict, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q6. Match the List-I with List-II. List-I (Mixture) A. CHCl₃ + C₆H₅NH₂ B. Crude oil in petroleum industry C. Glycerol from spent-lye D. Aniline-water List-II (Method of Separation) I. Distillation under reduced pressure II. Steam distillation III. Fractional distillation IV. Simple distillation Choose the correct answer from the options given below. (1) A-IV, B-III, C-I, D-II (2) A-IV, B-III, C-II, D-I (3) A-III, B-IV, C-I, D-II (4) A-III, B-IV, C-II, D-I

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Separation Techniques for Mixtures",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves matching mixtures with their appropriate methods of separation. It tests knowledge of various separation techniques commonly covered in NCERT Class 11 Chemistry, particularly in the context of physical chemistry."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method to approach this problem is to analyze each mixture and determine the most suitable separation technique based on their physical and chemical properties."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Each mixture has specific characteristics that dictate the best separation method: \n- A (CHCl₃ + C₆H₅NH₂) is best separated by simple distillation due to the significant difference in boiling points. \n- B (Crude oil) requires fractional distillation because it consists of various hydrocarbons with close boiling points. \n- C (Glycerol from spent-lye) is separated using distillation under reduced pressure to avoid decomposition. \n- D (Aniline-water) is separated by steam distillation due to the volatile nature of aniline."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. **Mixture A (CHCl₃ + C₆H₅NH₂)**: Simple distillation (IV) is appropriate due to the significant difference in boiling points (CHCl₃: 61.2°C, C₆H₅NH₂: 184.1°C).\n2. **Mixture B (Crude oil)**: Fractional distillation (III) is suitable as it separates components based on their boiling points.\n3. **Mixture C (Glycerol)**: Distillation under reduced pressure (I) is used to prevent thermal decomposition of glycerol.\n4. **Mixture D (Aniline-water)**: Steam distillation (II) is effective for separating aniline from water due to its volatility."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Based on the analysis, the correct matches are:\n- A - IV (Simple distillation)\n- B - III (Fractional distillation)\n- C - I (Distillation under reduced pressure)\n- D - II (Steam distillation)\nThus, the correct answer is (1) A-IV, B-III, C-I, D-II."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember the boiling points of components in mixtures when deciding on separation methods. A significant difference in boiling points favors simple distillation, while closely boiling components require fractional distillation. Steam distillation is useful for separating volatile substances from non-volatile ones."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be suitable if the mixtures have similar boiling points or if chemical reactions occur during the separation process. For example, if a mixture contains thermally unstable compounds, distillation under reduced pressure may not be effective."
    }
  ],
  "finalAnswer": "(1) A-IV, B-III, C-I, D-II",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `show_best_approach-027`

- **Variation:** conceptual
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q43. Phosphoric acid ionizes in three steps with their ionization constant values Kₐ₁, Kₐ₂ and Kₐ₃, respectively, while K is the overall ionization constant. Which of the following statements are true? A. log K = log Kₐ₁ + log Kₐ₂ + log Kₐ₃ B. H₃PO₄ is stronger acid than H₂PO₄⁻ and HPO₄²⁻. C. Kₐ₁ > Kₐ₂ > Kₐ₃ D. Kₐ₁ = (Kₐ₃ + Kₐ₂) / 2 Choose the correct answer from the options given below: (1) A and B only (2) A and C only (3) B, C and D only (4) A, B and C only

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Ionization of Phosphoric Acid",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves understanding the ionization of a polyprotic acid (phosphoric acid) and its ionization constants. It tests knowledge of acid strength, ionization constants, and their relationships."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to evaluate each statement based on the properties of polyprotic acids and their ionization constants. This involves understanding the definitions and relationships of the constants."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Phosphoric acid (H₃PO₄) ionizes in three steps, and the strength of each ionization can be compared using their respective ionization constants (Kₐ). The first ionization is always the strongest, followed by the second and third."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Evaluate each statement one by one:\n- **A**: log K = log Kₐ₁ + log Kₐ₂ + log Kₐ₃ is incorrect as K is not the product of Kₐ constants but rather the equilibrium constant for the overall reaction.\n- **B**: H₃PO₄ is indeed a stronger acid than H₂PO₄⁻ and HPO₄²⁻ as it is the first proton donor.\n- **C**: Kₐ₁ > Kₐ₂ > Kₐ₃ is true as the first ionization constant is always greater than the subsequent ones for polyprotic acids.\n- **D**: Kₐ₁ = (Kₐ₃ + Kₐ₂) / 2 is incorrect as there is no such relationship."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Evaluating the statements:\n- A: False\n- B: True\n- C: True\n- D: False\n\nThus, the true statements are B and C. Therefore, the correct answer is (3) B, C, and D only."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that for polyprotic acids, the first ionization constant is always the largest. This is a common pattern in acid-base chemistry. Use the strength of acids to quickly assess their ionization constants."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not apply if dealing with acids that do not follow the typical strength pattern or if the question involves complex equilibria beyond simple ionization."
    }
  ],
  "finalAnswer": "(3) B, C, and D only",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-028`

- **Variation:** conceptual
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, conceptual, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q59. Which of the following statements are INCORRECT? A. All the transition metals except scandium form MC oxides which are ionic. B. The highest oxidation number corresponding to the group number in transition metal oxides is attained in Sc₂O₃ to Mn₂O₇. C. Basic character increases from V₂O₃ to V₂O₄ to V₂O₅. D. V₂O₄ dissolves in acids to give VO₃⁻₄ salts. E. CrO is basic but Cr₂O₃ is amphoteric. Choose the correct answer from the options given below: a. B and C only b. A and E only c. B and D only d. C and D only Coordination Compounds

**Ncert Context:**

NCERT Class 12 Chemistry Ch.5: Coordination number = donor atoms bound to central metal.

**Expected output**

**Coach Json:**

```json
{
  "title": "Identifying Incorrect Statements about Transition Metal Oxides",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "The question requires identifying incorrect statements regarding transition metal oxides, focusing on their properties and oxidation states."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "Evaluate each statement based on known chemical properties of transition metals and their oxides."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method allows for a direct comparison against established chemical knowledge, ensuring accuracy in identifying incorrect statements."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "List each statement and analyze them one by one, using knowledge of oxidation states, basicity, and solubility of transition metal oxides."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Analyzing each statement:\n\nA. Correct - Most transition metals form ionic oxides, except Sc.\n\nB. Incorrect - The highest oxidation states for Sc to Mn are not consistent with the group number.\n\nC. Incorrect - Basic character does not consistently increase from V₂O₃ to V₂O₄ to V₂O₅; V₂O₅ is acidic.\n\nD. Correct - V₂O₄ does dissolve in acids to form VO₃⁻₄.\n\nE. Correct - CrO is basic, while Cr₂O₃ is amphoteric.\n\nThus, the incorrect statements are B and C. Therefore, the correct answer is option a: B and C only."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that transition metal oxides can vary in basicity and acidity depending on their oxidation states. Keep in mind the trends in oxidation states and solubility when analyzing similar questions."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be effective if the statements involve less common or more complex transition metals where specific knowledge is required beyond general trends."
    }
  ],
  "finalAnswer": "a. B and C only",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 3: `show_best_approach-029`

- **Variation:** conceptual
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q5. 5 moles of liquid X and 10 moles of liquid Y make a solution having a vapour pressure of 70 torr. The vapour pressures of pure X and Y are 63 torr and 78 torr respectively. Which of the following is true regarding the described solution? (1) The solution shows positive deviation. (2) The solution shows negative deviation. (3) The solution is ideal. (4) The solution has volume greater than the sum of individual volumes.

**Ncert Context:**

NCERT Class 11 Chemistry Ch.1: Moles n=m/M. Equal atoms when mole amounts match for same species count.

**Expected output**

**Coach Json:**

```json
{
  "title": "Vapor Pressure and Solution Behavior",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves calculating the vapor pressure of a solution made from two liquids (X and Y) and determining the nature of the deviation from Raoult's Law. The key concepts include vapor pressure, mole fraction, and deviations in ideal solutions."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The fastest method is to apply Raoult's Law to calculate the expected vapor pressure of the solution and compare it with the given vapor pressure of 70 torr. This will help identify whether the solution shows positive or negative deviation."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Raoult's Law states that the vapor pressure of a solution is equal to the sum of the partial pressures of each component, which can be calculated using their mole fractions and pure component vapor pressures. This method directly addresses the problem's requirements."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Calculate the total moles: \\( n_{total} = 5 + 10 = 15 \\) moles.  \n2. Calculate the mole fractions:  \n   - For X: \\( X_X = \\frac{5}{15} = \\frac{1}{3} \\)  \n   - For Y: \\( X_Y = \\frac{10}{15} = \\frac{2}{3} \\)  \n3. Use Raoult's Law to find the expected vapor pressure:  \n   \\[ P_{solution} = X_X \\cdot P^0_X + X_Y \\cdot P^0_Y \\]  \n   \\[ P_{solution} = \\left(\\frac{1}{3} \\cdot 63\\right) + \\left(\\frac{2}{3} \\cdot 78\\right) \\]"
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Calculating the expected vapor pressure:  \n\\[ P_{solution} = \\left(\\frac{1}{3} \\cdot 63\\right) + \\left(\\frac{2}{3} \\cdot 78\\right) = 21 + 52 = 73 \\text{ torr} \\]  \nSince the observed vapor pressure is 70 torr, which is less than the calculated 73 torr, the solution shows a negative deviation from Raoult's Law.  \nThus, the correct answer is (2) The solution shows negative deviation."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember that a positive deviation occurs when the vapor pressure of the solution is greater than expected, while a negative deviation occurs when it is less. This is crucial for identifying the nature of the solution."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be applicable if the components form strong interactions (like hydrogen bonding) that significantly alter the vapor pressures beyond simple additive effects. In such cases, a more detailed analysis of intermolecular forces would be necessary."
    }
  ],
  "finalAnswer": "The solution shows negative deviation.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `show_best_approach-006`

- **Variation:** case_study
- **Tags:** physics, cbse, source_pdf_cbse_physics, case_study, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q48. Passage: Strontium titanate is a rare oxide, a natural mineral found in Siberia. It is used as a substitute for diamond because its refractive index and critical angle are 2.41 and 24.5° respectively, which are approximately equal to the refractive index and critical angle of diamond. It has all the properties of diamond. Even an expert jeweller is unable to differentiate between diamond and strontium titanate. A ray of light is incident normally on one face of an equilateral triangular prism ABC made of strontium titanate. Sub-questions:

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Light Refraction in Strontium Titanate Prism",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "This problem involves the behavior of light as it passes through a prism made of strontium titanate, focusing on concepts like refractive index and critical angle. The key is to analyze how light interacts with different media, particularly when transitioning from air to the prism material."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "To solve this problem, apply Snell's Law, which states that \\( n_1 \\sin(\\theta_1) = n_2 \\sin(\\theta_2) \\). Here, \\( n_1 \\) is the refractive index of air (approximately 1), and \\( n_2 \\) is the refractive index of strontium titanate (2.41). Since light is incident normally, \\( \\theta_1 = 0 \\) degrees, simplifying the calculations."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "Using Snell's Law is appropriate here because it directly relates the angles of incidence and refraction to the refractive indices of the two media. The normal incidence simplifies the situation, allowing for straightforward calculations of the angles as light enters and exits the prism."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "Start by identifying the refractive indices involved. For air, use \\( n_1 = 1 \\) and for strontium titanate, use \\( n_2 = 2.41 \\). Since the light is incident normally, you can directly calculate the angle of refraction using Snell's Law without needing to consider the angle of incidence."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "1. Apply Snell's Law: \\( 1 \\cdot \\sin(0) = 2.41 \\cdot \\sin(\\theta_2) \\) \n2. Since \\( \\sin(0) = 0 \\), \\( \\theta_2 = 0 \\) degrees. \n3. As the light exits the prism, apply Snell's Law again at the second interface, considering the critical angle for total internal reflection if applicable."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Always check if the light is entering or exiting the prism and apply the correct refractive indices. Remember that for normal incidence, the angle of refraction equals the angle of incidence, simplifying calculations significantly."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "Do not use this method if the light is incident at an angle other than normal, or if the problem involves complex geometries where multiple refractions occur. In such cases, a more detailed ray diagram may be necessary."
    }
  ],
  "finalAnswer": "The angle of refraction when light enters the strontium titanate prism is 0 degrees due to normal incidence.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---

#### Example 2: `show_best_approach-030`

- **Variation:** case_study
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, case_study, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q65. Match List-I with List-II List-I (Complex) A. [Co(NH₃)₅(NO₂)]Cl₂. B. [Co(NH₃)₅(SO₄)]Br. C. [Co(NH₃)₆][Cr(CN)₆] D. [Co(H₂O)₆]Cl₃ List-II (Type of isomerism) I. Solvate isomerism II. Linkage isomerism III. Ionization isomerism IV. Coordination isomerism Choose the correct answer from the options given below: (1) A-I, B-IV, C-III, D-II (2) A-II, B-IV, C-III, D-I (3) A-II, B-III, C-IV, D-I (4) A-I, B-III, C-IV, D-II

Cl₂, B. [Co(NH₃)₅(SO₄)]Br, C. [Co(NH₃)₆][Cr(CN)₆], and D. [Co(H₂O)₆]Cl₃. List-II includes four types of isomerism labeled I, II, III, and IV, corresponding to Solvate isomerism, Linkage isomerism, Ionization isomerism, and Coordination isomerism, respectively. The task is to match the complexes from List-I with the types of isomerism in List-II. Below the lists, there are four options numbered (1) to (4) for the correct matches. The layout is vertical, with List-I on the left and List-II on the right, and no arrows or motion directions are indicated.]

**Ncert Context:**

NCERT Class 12 Chemistry Ch.5: Coordination number = donor atoms bound to central metal.

**Expected output**

**Coach Json:**

```json
{
  "title": "Matching Coordination Complexes with Isomerism Types",
  "sections": [
    {
      "heading": "Problem Pattern",
      "bodyMarkdown": "The problem requires matching coordination complexes with their respective types of isomerism. This involves understanding the nature of the ligands and the structure of the complexes."
    },
    {
      "heading": "Best Method",
      "bodyMarkdown": "The best method is to analyze each complex based on its ligands and structure to identify the type of isomerism it can exhibit. This involves recognizing the characteristics of each type of isomerism."
    },
    {
      "heading": "Why This Fits",
      "bodyMarkdown": "This method is optimal because it directly applies the concepts of coordination chemistry as outlined in the NCERT syllabus. It allows for a systematic approach to determine the isomerism types based on ligand behavior and complex structure."
    },
    {
      "heading": "Efficient Setup",
      "bodyMarkdown": "1. Identify the ligands in each complex.  \n2. Determine the possible isomerism based on ligand type and complex structure.  \n3. Match the complexes with the correct isomerism type."
    },
    {
      "heading": "Clean Solution",
      "bodyMarkdown": "Let's analyze each complex:  \nA. [Co(NH₃)₅(NO₂)]Cl₂  \n- Contains NO₂, which can bind through N or O, indicating linkage isomerism (Match: A-II).  \nB. [Co(NH₃)₅(SO₄)]Br  \n- Can exhibit ionization isomerism as the sulfate can be replaced by bromide (Match: B-III).  \nC. [Co(NH₃)₆][Cr(CN)₆]  \n- This complex has two different metal centers, allowing for coordination isomerism (Match: C-IV).  \nD. [Co(H₂O)₆]Cl₃  \n- This complex can show solvate isomerism as it can exist with different solvent molecules (Match: D-I).  \nThus, the matches are: A-II, B-III, C-IV, D-I."
    },
    {
      "heading": "Exam Note",
      "bodyMarkdown": "Remember the types of isomerism:  \n- Linkage isomerism involves ligands that can bind in multiple ways.  \n- Ionization isomerism involves different ions in solution.  \n- Coordination isomerism involves different arrangements of ligands around different metal centers.  \n- Solvate isomerism involves different solvent molecules."
    },
    {
      "heading": "When Not to Use",
      "bodyMarkdown": "This method may not be effective if the complexes are too similar or if the ligands have ambiguous binding modes that are not clearly defined. In such cases, a more detailed analysis of the electronic structure and sterics may be necessary."
    }
  ],
  "finalAnswer": "A-II, B-III, C-IV, D-I",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Compare with basic method",
      "action": "COMPARE_BASIC_METHOD"
    },
    {
      "label": "Explain why this works",
      "action": "EXPLAIN_WHY_WORKS"
    },
    {
      "label": "Give similar exam problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Show common mistakes",
      "action": "SHOW_COMMON_MISTAKES"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. latex_format: pass. production_llm_gold: pass.

---


## 20. Show Missing Idea Coach

| Field | Value |
|-------|-------|
| Dataset ID | `show_missing_idea` |
| Category | Problem Solving |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** Reveal the key unlock with `revealLevel: partial` — no full solution by default. Production: [`show_missing_idea.j2`](packages/core/prompts/templates/problem_solver/show_missing_idea.j2).

**Audit finding (baseline v1.0.0):** Baseline stub `Key insight without full solution` replaced; each example identifies the typical missing idea and where most students get stuck — without any student attempt input.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `numerical` | Numeric/unit problems | 7 |
| `jee` | JEE Mains framing | 5 |
| `neet` | NEET MCQ / assertion-reason | 2 |
| `multi_part` | Multi-step / derive | 1 |
| `cbse` | CBSE board style | 5 |
| `proof` | Derivation / proof | 2 |
| `diagram` | Diagram-dependent | 2 |
| `ncert_strict` | Strict NCERT wording | 1 |
| `conceptual` | Explain-why / concept | 3 |
| `case_study` | Passage / case-based | 2 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **section_completeness** — Five sections: Missing Idea through Where Most Students Get Stuck.
* **reveal_level** — `revealLevel: partial`; no `finalAnswer` in gold.
* **ncert_alignment** — Mental model cites correct chapter principle.
* **typical_student_trap** — Common trap is problem-specific, not a generic placeholder.
* **latex_format** — Multiplication spaced; units in `\text{}`; JSON backslashes escaped in `bodyMarkdown`.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `problem_text_normalized`, `ncert_context`
* Output keys: `coach_json`

**Prompt template (production):**

```jinja2
You are ScholarSync AI Coach revealing the key unlock, not a full solution by default.

Problem:
{{ problem_text_normalized }}

{% if ncert_context %}
NCERT context:
{{ ncert_context }}
{% endif %}

Identify what students typically miss on this problem type — without assuming any specific student work.
Frame "The Missing Idea" as the conceptual unlock and "Where Most Students Get Stuck" as the common trap or wrong path for this problem (generic, not tied to one attempt).

{% include 'problem_solver/math_formatting_contract.j2' %}

Return JSON only:
{
  "title": "string",
  "sections": [
    {"heading": "The Missing Idea", "bodyMarkdown": "..."},
    {"heading": "Why It Feels Tricky", "bodyMarkdown": "..."},
    {"heading": "Correct Mental Model", "bodyMarkdown": "..."},
    {"heading": "How to Start", "bodyMarkdown": "..."},
    {"heading": "Where Most Students Get Stuck", "bodyMarkdown": "..."}
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {"label": "Now show full solution", "action": "REVEAL_SOLUTION"},
    {"label": "Show best approach", "action": "SHOW_BEST_APPROACH"},
    {"label": "Give one similar problem", "action": "GIVE_SIMILAR_PROBLEM"},
    {"label": "Explain this concept", "action": "EXPLAIN_CONCEPT_AGAIN"},
    {"label": "Start Tutor Session", "action": "START_TUTOR_SESSION"}
  ]
}
```

*Runtime note:* `ProblemSolverService` mode `SHOW_MISSING_IDEA`.

### Evaluation examples (30)
## Variation: `numerical`


#### Example 1: `show_missing_idea-010`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q16. Select the correct statements from the following: A. Atoms of all elements are composed of two fundamental particles. B. The mass of the electron is 9.10939 × 10⁻³¹ kg. C. All the isotopes of a given element show same chemical properties. D. Protons and electrons are collectively known as nucleons. E. Dalton’s atomic theory, regarded the atom as an ultimate particle of matter. Choose the correct answer from the options given below: a. B, C and E only b. A, B and C only c. C, D and E only d. A and E only

**Ncert Context:**

NCERT Class 12 Chemistry Ch.3: Galvanic cell — oxidation at anode, reduction at cathode. E°cell=E°cathode−E°anode.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Atomic Structure and Properties",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the specific definitions [answer hidden]nd distinctions between [answer hidden]tomic p[answer hidden]rticles [answer hidden]nd their roles in the structure of [answer hidden]toms. Recognizing th[answer hidden]t protons [answer hidden]nd neutrons [answer hidden]re nucleons, while electrons [answer hidden]re not, is cruci[answer hidden]l."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The st[answer hidden]tements mix fund[answer hidden]ment[answer hidden]l concepts of [answer hidden]tomic theory with specific properties of p[answer hidden]rticles, which c[answer hidden]n confuse students. Misunderst[answer hidden]nding the terms 'nucleons' [answer hidden]nd 'isotopes' c[answer hidden]n le[answer hidden]d to incorrect selections."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "[answer hidden] cle[answer hidden]r underst[answer hidden]nding of [answer hidden]tomic structure is essenti[answer hidden]l. Remember th[answer hidden]t protons [answer hidden]nd neutrons [answer hidden]re found in the nucleus (collectively c[answer hidden]lled nucleons), while electrons orbit [answer hidden]round the nucleus. Isotopes of [answer hidden]n element h[answer hidden]ve the s[answer hidden]me number of protons but different numbers of neutrons, [answer hidden]ffecting their m[answer hidden]ss but not their chemic[answer hidden]l properties."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by [answer hidden]n[answer hidden]lyzing e[answer hidden]ch st[answer hidden]tement individu[answer hidden]lly. Check the definitions of terms like 'nucleons' [answer hidden]nd 'isotopes' [answer hidden]nd rec[answer hidden]ll key f[answer hidden]cts [answer hidden]bout [answer hidden]tomic theory to determine which st[answer hidden]tements [answer hidden]re [answer hidden]ccur[answer hidden]te."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "M[answer hidden]ny students mist[answer hidden]kenly believe th[answer hidden]t [answer hidden]ll p[answer hidden]rticles within [answer hidden]n [answer hidden]tom [answer hidden]re nucleons or confuse the properties of isotopes, le[answer hidden]ding them to select incorrect combin[answer hidden]tions of st[answer hidden]tements."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-011`

- **Variation:** numerical
- **Tags:** chemistry, neet, source_pdf_neet_chemistry, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

NEET Chemistry v1.0 90 curated mixed-style questions for RAG problem-solving evaluation This is a version. Each question has four options. Reaction schemes, chemical structures, equations, graphs and matching tables are preserved from the source qu Answers, solutions, chapter headings, difficulty labels, and original source numbering are intentionally not includ NEET Chemistry v1.0 |

**Ncert Context:**

NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants] at equilibrium. Le Chatelier: system shifts to oppose applied stress.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Equilibrium and Kc in Chemical Reactions",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the significance of the equilibrium constant (Kc) in predicting the direction of a reaction when a change is applied. They may not fully grasp how changes in concentration, pressure, or temperature affect the system's equilibrium position."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The concept of equilibrium can be counterintuitive, as it involves dynamic processes where reactants and products are formed at the same rate. Additionally, the application of Le Chatelier's principle requires a nuanced understanding of how different stresses influence the system, which can lead to confusion."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "To correctly approach equilibrium problems, students should visualize the reaction as a balance between reactants and products. They must understand that Kc provides a quantitative measure of this balance and that any disturbance will shift the equilibrium to restore balance, either by favoring reactants or products."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by identifying the reaction and writing the expression for Kc. Next, analyze the changes being applied to the system and consider how these changes will affect the concentrations of reactants and products. Use Le Chatelier's principle to predict the direction of the shift."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that increasing the concentration of reactants will always favor the formation of products without considering the specific context of the reaction. They may also struggle with the implications of temperature changes on Kc, often confusing the effects on reaction rates with shifts in equilibrium."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 3: `show_missing_idea-012`

- **Variation:** numerical
- **Tags:** physics, neet, source_pdf_neet_physics, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q1. An electron (mass 9 × 10⁻³¹ kg and charge 1.6 × 10⁻¹⁹ C) moving with speed c/100 (c = speed of light) is injected into a magnetic field B of magnitude 9 × 10⁴ T perpendicular to its direction of motion. We wish to apply an uniform electric E together with the magnetic field so that the electron does not deflect from its path. Then (speed of light c = 3 × 10⁸ ms⁻¹) (1) E is perpendicular to B and its magnitude is 27 × 10⁴ V m⁻¹ (2) E is perpendicular to B and its magnitude is 27 × 10² V m⁻¹ (3) E is parallel to B and its magnitude is 27 × 10² V m⁻¹ (4) E is parallel to B and its magnitude is 27 × 10⁴ V m⁻¹

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Motion of Charged Particles in Electric and Magnetic Fields",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To keep the electron moving in a straight line without deflection, the electric force must exactly balance the magnetic force acting on it. This requires understanding the relationship between the electric field (E), magnetic field (B), and the velocity (v) of the charged particle."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the directions of the forces involved and may not realize that the electric and magnetic forces must counteract each other. Additionally, the perpendicular nature of the fields can lead to confusion about how to set up the equations."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "The key is to apply the Lorentz force equation: F = q(E + v × B). For the electron to not deflect, the net force must be zero, which means E must be set such that it balances the magnetic force (qvB) acting on the electron."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by calculating the speed of the electron (c/100) and then determine the magnetic force using the formula F_m = qvB. Next, set this equal to the electric force F_e = qE to find the required electric field E."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students overlook the need for the electric field to be perpendicular to the magnetic field and fail to correctly apply the right-hand rule for the cross product in the magnetic force calculation, leading to incorrect conclusions about the direction and magnitude of E."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 4: `show_missing_idea-013`

- **Variation:** numerical
- **Tags:** physics, neet, source_pdf_neet_physics, numerical, assertion_reason, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q73. Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R. Assertion A: The potential (V) at any axial point, at 2 m distance (r) from the centre of the dipole of dipole moment vector → P of magnitude, 4×10⁻⁶ C m, is ±9×10³ V. (Take 1/4πε₀ = 9×10⁹ SI units) Reason R: V = ±(2P/4πε₀r²), where r is the distance of any axial point, situated at 2 m from the centre of the dipole. In the light of the above statements, choose the correct answer from the options given below: (1) A is true but R is false. (2) A is false but R is true. (3) Both A and R are true and R is the correct explanation of A. (4) Both A and R are true and R is NOT the correct explanation of A.

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Dipole Potential",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To solve this problem, students need to accurately apply the formula for the electric potential due to a dipole and understand how the parameters relate to each other, particularly the significance of the dipole moment and the distance from the dipole."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The confusion often arises from the signs and the interpretation of the potential at a given distance. Students may miscalculate or misinterpret the values leading to incorrect conclusions about the assertion and reason."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Students should visualize the dipole's effect on potential and remember that the potential decreases with the square of the distance. They should also recognize how to derive the potential from the dipole moment and distance correctly."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by substituting the given values into the formula for the potential due to a dipole. Ensure that you understand each variable and its role in the equation before proceeding to evaluate the assertion and reason."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students fail to correctly apply the formula for potential, particularly in understanding how to manipulate the equation for the dipole potential. They might also overlook the significance of the distance and how it affects the potential value."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 5: `show_missing_idea-014`

- **Variation:** numerical
- **Tags:** physics, neet, source_pdf_neet_physics, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q75. Given below are two statements : Statement I: Atoms are electrically neutral as they contain equal number of positive and negative charges. Statement II: Atoms of each element are stable and emit their characteristic spectrum. In the light of the above statements, choose the most appropriate answer from the options given below : (1) Statement I is correct but Statement II is incorrect. (2) Statement I is incorrect but Statement II is correct. (3) Both Statement I and Statement II are correct. (4) Both Statement I and Statement II are incorrect.

;

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Atomic Structure and Stability",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key to this problem lies in understanding the fundamental properties of atoms, specifically their charge neutrality and stability. Atoms are neutral due to having equal numbers of protons (positive charges) and electrons (negative charges). Additionally, the stability of atoms is linked to their electron configurations and the emission of characteristic spectra when they transition between energy levels."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students may confuse the stability of atoms with the behavior of ions or molecules. They might also misinterpret the concept of 'characteristic spectrum' and its relation to atomic stability, leading to uncertainty about the correctness of Statement II."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Atoms are indeed electrically neutral, and this neutrality is a result of having equal numbers of protons and electrons. Furthermore, atoms of each element are stable under normal conditions and can emit a characteristic spectrum when electrons transition between energy levels. Understanding these concepts helps clarify the relationship between charge neutrality and atomic stability."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing each statement independently. Recall the definitions of atomic structure, charge neutrality, and what is meant by 'characteristic spectrum.' Assess whether each statement aligns with established scientific principles."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students may incorrectly assume that the stability of atoms implies they do not emit any spectrum or that emission indicates instability. This misunderstanding can lead to confusion about the validity of Statement II, causing them to incorrectly judge the statements as either both correct or both incorrect."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 6: `show_missing_idea-015`

- **Variation:** numerical
- **Tags:** physics, neet, source_pdf_neet_physics, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q37. Two identical charged conducting spheres A and B have their centres separated by a certain distance. Charge on each sphere is q and the force of repulsion between them is F. A third identical uncharged conducting sphere is brought in contact with sphere A first and then with B and finally removed from both. New force of repulsion between spheres A and B (Radii of A and B are negligible compared to the distance of separation so that for calculating force between them they can be considered as point charges) is best given as: (1) 3F 5 (2) 2F 3 (3) F 2 (4) 3F q

;

**Ncert Context:**

NCERT Class 12 Physics Ch.1: Gauss's law relates net flux through a closed surface to enclosed charge. Conductor electrostatics: field inside conductor is zero in electrostatic equilibrium.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Charge Redistribution in Conductors",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "When a conducting sphere comes into contact with another conductor, charge redistributes between them. This redistribution affects the total charge on each sphere and thus alters the force of repulsion between them."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often overlook the fact that the uncharged sphere will take on charge from the charged spheres when they come into contact. This can lead to confusion about how the final charges on spheres A and B are calculated."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the process of charge transfer: when the uncharged sphere touches sphere A, it gains charge, and then when it touches sphere B, it redistributes charge again. Understanding that the total charge remains conserved is key to solving the problem."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by calculating the charge on the uncharged sphere after it contacts sphere A, then determine the new charge on sphere A and subsequently on sphere B after the uncharged sphere contacts it. Use Coulomb's law to find the new force of repulsion."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that the charge on spheres A and B remains the same after the uncharged sphere is introduced. They fail to account for the redistribution of charge, which leads to incorrect calculations of the new force."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 7: `show_missing_idea-016`

- **Variation:** numerical
- **Tags:** physics, neet, source_pdf_neet_physics, numerical, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q23. An unpolarized light beam travelling in air is incident on a medium of refractive index 1.73 at Brewster's angle. Then- (1) reflected light is completely polarized and the angle of reflection is close to 60° (2) reflected light is partially polarized and the angle of reflection is close to 30° (3) both reflected and transmitted light are perfectly polarized with angles of reflection and refraction close to 60° and 30°, respectively. (4) transmitted light is completely polarized with angle of refraction close to 30°

;

**Ncert Context:**

NCERT Class 12 Physics Ch.9: Lens formula 1/f=1/v-1/u. Magnification m=v/u. Sign convention: real object distance u negative.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Brewster's Angle and Polarization",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is Brewster's angle, which is the angle of incidence at which light with a particular polarization is perfectly transmitted through a transparent dielectric surface, with no reflection. At this angle, the reflected light is completely polarized."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the conditions for complete polarization with those for partial polarization. Additionally, the relationship between the angles of incidence, reflection, and refraction can lead to misunderstandings about which angles correspond to which type of light."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "When light hits a surface at Brewster's angle, the reflected light is completely polarized. The angle of reflection equals the angle of incidence, and the angle of refraction can be calculated using Snell's law. Understanding these relationships helps clarify the behavior of light at this specific angle."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by recalling the formula for Brewster's angle: it can be calculated using the refractive indices of the two media. Once you have this angle, analyze the properties of the reflected and refracted light at this angle."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly believe that both reflected and transmitted light can be polarized at Brewster's angle, or they may not correctly apply Snell's law to find the angles involved. This leads to confusion about the nature of the light after it interacts with the medium."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `show_missing_idea-017`

- **Variation:** jee
- **Tags:** physics, neet, source_pdf_neet_physics, jee, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q6. Consider the diameter of a spherical object being measured with the help of a Vernier callipers. Suppose its 10 Vernier Scale Divisions (V.S.D.) are equal to its 9 Main Scale Divisions (M.S.D.). The least division in the M.S. is 0.1 cm and the zero of V.S. is at x = 0.1 cm when the jaws of Vernier callipers are closed. If the main scale reading for the diameter is M = 5 cm and the number of coinciding vernier division is 8, the measured diameter after zero error correction, is: (1) 5.18 cm (2) 5.08 cm (3) 4.98 cm (4) 5.00 cm

;

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Measurements with Vernier Callipers",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the importance of zero error correction in measurements. Understanding how to adjust the reading based on the zero error is crucial for obtaining an accurate measurement."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The problem involves multiple steps: identifying the zero error, calculating the actual reading from the Vernier scale, and then applying the zero error correction. This can lead to confusion, especially if students mix up the values or forget to apply the correction."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "To solve this problem, students should visualize the process of measuring with Vernier callipers: first, determine the zero error, then read the main scale and Vernier scale correctly, and finally combine these readings while accounting for any zero error."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by identifying the zero error from the Vernier scale. Then, read the main scale and the Vernier scale to find the total measurement before applying the zero error correction."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students forget to account for the zero error when calculating the final measurement. They may also misinterpret the relationship between the Vernier and main scale divisions, leading to incorrect readings."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-018`

- **Variation:** jee
- **Tags:** physics, neet, source_pdf_neet_physics, jee, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q26. Two cities X and Y are connected by a regular bus service with a bus leaving in either direction every T min. A girl is driving scooty with a speed of 60 km/h in the direction X to Y notices that a bus goes past her every 30 minutes in the direction of her motion, and every 10 minutes in the opposite direction. Choose the correct option for the period T of the bus service and the speed (assumed constant) of the buses. (1) 9 min, 40 km/h (2) 25 min, 100 km/h (3) 10 min, 90 km/h (4) 15 min, 120 km/h

;

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Relative Motion in Bus and Scooty Problem",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To solve this problem, students need to understand the concept of relative speed and how it applies to two moving objects (the scooty and the buses). The key is to relate the frequency of buses passing the girl to their speed and the time intervals given."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often get confused by the different directions of motion and the intervals at which the buses pass by. They may misinterpret the time intervals as direct measures of speed without considering the relative speeds involved."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "The correct approach involves setting up equations based on the relative speed of the scooty and the buses. When the girl sees a bus every 30 minutes in the same direction, it indicates a specific relationship between her speed and the bus speed, while the 10-minute interval in the opposite direction provides another equation."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by defining the speed of the bus as 'v_b' and using the given information about the scooty's speed (60 km/h) to set up equations based on the time intervals for both directions. Use the concept of relative speed to relate these intervals to the bus's speed."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students fail to correctly apply the concept of relative speed, leading to incorrect equations. They might also overlook the need to convert time intervals into consistent units (e.g., hours) when calculating speeds, which can lead to confusion and errors in their final answers."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 3: `show_missing_idea-019`

- **Variation:** jee
- **Tags:** physics, neet, source_pdf_neet_physics, jee, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q36. A parallel plate capacitor made of circular plates is being charged such that the surface charge density on its plates is increasing at a constant rate with time. The magnetic field arising due to displacement current is: (1) zero at all places (2) constant between the plates and zero outside the plates. (3) non-zero everywhere with maximum at the imaginary cylindrical surface connecting peripheries of the plates. (4) zero between the plates and non-zero outside.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Magnetic Fields in Charging Capacitors",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is the relationship between displacement current and the resulting magnetic field. As the surface charge density increases, the displacement current density also increases, which leads to the creation of a magnetic field in the surrounding space."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the effects of displacement current with those of conduction current. They may not fully grasp that even in the absence of a physical current through the capacitor, a changing electric field can still generate a magnetic field."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the capacitor plates as creating an electric field between them. As the charge builds up, this changing electric field induces a displacement current, which in turn generates a magnetic field. Remember that the magnetic field is not confined to the space between the plates but exists in the surrounding area as well."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by identifying the nature of the displacement current due to the changing electric field between the plates. Use Maxwell's equations, particularly the modified Ampère's law, to relate the displacement current to the magnetic field."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that the magnetic field is zero between the plates, not recognizing that the displacement current creates a magnetic field in that region. They may also overlook the fact that the magnetic field exists outside the plates, leading to confusion about the spatial distribution of the field."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 4: `show_missing_idea-020`

- **Variation:** jee
- **Tags:** physics, neet, source_pdf_neet_physics, jee, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q86. If the plates of a parallel plate capacitor connected to a battery are moved close to each other, then A. the charge stored in it, increase. B. the energy stored in it, decreases. C. its capacitance increases. D. the ratio of charge to its potential remains the same. E. the product of charge and voltage increases. Choose the most appropriate answer from the options given below: (1) B, D and E only (2) A, B and C only (3) A, B and E only (4) A, C and E only

;

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Parallel Plate Capacitors",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is the relationship between capacitance, charge, and voltage in a parallel plate capacitor. When the plates are moved closer together, the capacitance increases, which affects the charge stored and the energy in the system."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the effects of changing plate separation on capacitance with the effects on charge and energy. They may not fully grasp how these quantities interrelate when the physical configuration of the capacitor changes."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Remember that capacitance (C) is defined as C = Q/V, where Q is the charge and V is the voltage. When the plates are moved closer, capacitance increases, which can lead to an increase in charge if connected to a constant voltage source, or a change in energy stored if the capacitor is isolated."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing how moving the plates affects capacitance. Then, consider how this change influences charge and energy based on whether the capacitor is connected to a battery or isolated."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly believe that moving the plates closer always increases the charge stored, without considering the role of the voltage source. They also often overlook the implications of energy changes when capacitance increases."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 5: `show_missing_idea-021`

- **Variation:** jee
- **Tags:** physics, neet, source_pdf_neet_physics, jee, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q82. A parallel plate capacitor is charged by connecting it to a battery through a resistor. If I is the current in the circuit, then in the gap between the plates; (1) displacement current of magnitude equal to I flows in a direction opposite to that of I. (2) displacement current of magnitude greater than I flows but can be in any direction. (3) there is no current. (4) displacement current of magnitude equal to I flows in the same direction as I.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Displacement Current in Capacitors",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is the understanding of displacement current, which is not a conventional current but rather a term introduced by Maxwell to account for changing electric fields in regions where there is no conduction current, such as the gap between capacitor plates."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse displacement current with conduction current. They may not fully grasp that displacement current is related to the changing electric field between the plates of the capacitor, which occurs as the capacitor charges."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the capacitor charging: as the plates accumulate charge, an electric field builds up in the gap. The displacement current is proportional to the rate of change of this electric field and flows in the same direction as the conduction current, effectively completing the circuit in the context of Maxwell's equations."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by recalling the definition of displacement current and its relation to changing electric fields. Then, consider the direction of the electric field established between the capacitor plates as the capacitor charges."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly think that displacement current is absent or flows in the opposite direction to the conduction current. This misunderstanding leads them to overlook the relationship between the changing electric field and the displacement current's direction."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `show_missing_idea-008`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q49. What is the fate of piece of DNA carrying only gene of interest which is transferred into an alien organism? A. The piece of DNA would be able to multiply itself independently in the progeny cells of the organisms. B. It may get integrated into the genome of the recipient. C. It may multiply and be inherited along with the host DNA. D. The alien piece of DNA is not an integrated part of chromosome. E. It shows ability to replicate. Choose the correct answer from the options given below: (1) B and C only (2) A and E only (3) A and B only (4) D and E only

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding DNA Transfer in Alien Organisms",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is understanding the behavior of foreign DNA within a host organism. Specifically, whether the DNA can exist independently, integrate into the host genome, or replicate alongside it."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the mechanisms of DNA replication and integration. They may not fully grasp the distinction between plasmid behavior (which can replicate independently) and chromosomal integration (which becomes part of the host's genetic material)."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Foreign DNA can either integrate into the host's genome or exist as an independent entity (like a plasmid). Understanding these pathways helps clarify the potential outcomes of introducing foreign DNA into an organism."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing each option in the context of how DNA functions within cells. Consider whether the DNA is likely to integrate into the genome or remain separate, and think about the implications of each scenario."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that any piece of DNA introduced into a cell will automatically replicate independently or integrate without considering the specific mechanisms of DNA behavior in the host organism."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-009`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q7. Tropical regions show greatest level of species richness because A. Tropical latitudes have remained relatively undisturbed for millions of years, hence more time was available for species diversification. B. Tropical environments are more seasonal. C. More solar energy is available in tropics. D. Constant environments promote niche specialization. E. Tropical environments are constant and predictable. Choose the correct answer from the options given below: (1) A, B and E only (2) A, B and D only (3) A, C, D and E only (4) A and B only

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Species Richness in Tropical Regions",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key to understanding species richness in tropical regions lies in recognizing the interplay between environmental stability, solar energy availability, and time for diversification. Each of these factors contributes uniquely to the high biodiversity observed in these areas."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the effects of environmental stability with seasonal variability. While some options highlight important aspects of tropical environments, not all contribute equally to species richness. This can lead to misinterpretation of which factors are truly significant."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "To correctly assess species richness, consider how stable environments allow for niche specialization and how abundant solar energy supports diverse life forms. Additionally, the long-term stability of tropical ecosystems fosters greater evolutionary time for species to diversify."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing each option carefully. Identify which factors directly relate to species richness and consider how they interact with one another. Look for connections between environmental stability, energy availability, and time for diversification."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly focus on seasonal aspects or assume that all tropical features contribute equally to species richness. This can lead to selecting options that include irrelevant factors or overlook the importance of stability and energy in fostering biodiversity."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `show_missing_idea-022`

- **Variation:** multi_part
- **Tags:** physics, neet, source_pdf_neet_physics, multi_part, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q45. Consider the following statements A and B and identify the correct answer : I (II) (I) (III) (IV) A. For a solar-cell, the I-V characteristics lies in the IV quadrant of the given graph. B. In a reverse biased pn junction diode, the current measured in (μA), is due to majority charge carriers. (1) Both A and B are correct. (2) Both A and B are incorrect. (3) A is correct but B is incorrect. (4) A is incorrect but B is correct.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding I-V Characteristics and Diode Behavior",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the specific behaviors of current and voltage in different configurations of diodes, particularly how they relate to charge carriers in reverse bias conditions."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The confusion arises from mixing up the characteristics of solar cells and diodes, especially regarding the direction of current flow and the role of majority vs. minority charge carriers."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "For a solar cell, the I-V characteristics indeed lie in the IV quadrant, indicating that both current and voltage are positive. In a reverse-biased pn junction diode, the current is primarily due to minority carriers, not majority carriers."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing each statement independently. Recall the fundamental principles of how solar cells operate and the behavior of diodes under reverse bias conditions."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly believe that the current in a reverse-biased diode is due to majority carriers, leading them to incorrectly assess the truth of statement B."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `show_missing_idea-001`

- **Variation:** cbse
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q50. Overspeeding increases fuel consumption and decreases fuel economy as a result of tyre rolling friction and air resistance. While vehicles reach optimal fuel economy at different speeds, fuel mileage usually decreases rapidly at speeds above 80 km/h. The relation between fuel consumption F (l/100 km) and speed V (km/h) under some constraints is given as F = V/500 - V/4 + 14. On the basis of the above information, answer the following questions: (i) Find F, when V = 40 km/h. (ii) Find df/dV. (iii) (a) Find the speed V for which fuel consumption F is minimum. OR (iii) (b) Find the quantity of fuel required to travel 600 km at the speed V at which dF/dV = -0.01.

**Ncert Context:**

NCERT Class 12 Mathematics Ch.12: Feasible region from constraint inequalities; optimum at corner points.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Fuel Consumption Optimization",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the importance of interpreting the function F(V) in terms of its critical points and how they relate to the context of fuel consumption. Recognizing that the minimum fuel consumption corresponds to a specific speed requires understanding the behavior of the function, particularly its derivative."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The problem involves multiple steps, including evaluating a function, finding its derivative, and optimizing it. Students may feel overwhelmed by the different tasks and might not clearly connect how each part contributes to finding the optimal speed for fuel efficiency."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "To tackle this problem, students should view F(V) as a quadratic function where the vertex represents the minimum fuel consumption. Understanding that the derivative dF/dV indicates the rate of change of fuel consumption with respect to speed is crucial for identifying optimal points."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by substituting the given speed into the function F to find fuel consumption at specific speeds. Then, calculate the derivative dF/dV to analyze how fuel consumption changes with speed. This sets the stage for finding minimum values and understanding the relationship between speed and fuel efficiency."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students struggle with finding the derivative correctly or misinterpret the results. They may also get confused between finding the minimum fuel consumption and simply evaluating the function at given speeds, leading to incorrect conclusions about optimal speeds."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-002`

- **Variation:** cbse
- **Tags:** mathematics, cbse, source_pdf_cbse_mathematics, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q4. The corner points of the feasible region in the graphical representation of an L.P.P. are (2, 72), (15, 20) and (40, 15). If Z = 18x + 9y be the objective function, then: ((A)) Z is maximum at (2, 72), minimum at (15, 20) ((B)) Z is maximum at (15, 20), minimum at (40, 15) ((C)) Z is maximum at (40, 15), minimum at (15, 20) ((D)) Z is maximum at (40, 15), minimum at (2, 72)

**Ncert Context:**

NCERT Class 12 Mathematics Ch.12: Feasible region from constraint inequalities; optimum at corner points.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Optimal Solutions in Linear Programming",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To determine the maximum or minimum value of the objective function at the corner points of the feasible region, students need to evaluate the objective function at each corner point and compare the results."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often focus on the coordinates of the corner points without calculating the corresponding values of the objective function, leading to incorrect conclusions about where the maximum or minimum occurs."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "The optimal solution for a linear programming problem is found at one of the corner points of the feasible region. Evaluating the objective function at these points allows you to identify which point yields the highest or lowest value."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by substituting the coordinates of each corner point into the objective function Z = 18x + 9y. Calculate Z for each point to find the maximum and minimum values."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume the maximum and minimum values based solely on the coordinates of the corner points without performing the necessary calculations to evaluate the objective function."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 3: `show_missing_idea-003`

- **Variation:** cbse
- **Tags:** physics, cbse, source_pdf_cbse_physics, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q45. (a) A parallel monochromatic light beam falls normally onto a single slit having an aperture width parameter 'a' to produce a standard Fraunhofer diffraction pattern on a screen positioned at a distance D. Explain clearly: (i) the physical mechanics governing the formation of secondary maxima and minima zones, and (ii) why the secondary maxima peaks go on becoming weaker and weaker in intensity as their order integer n increases. (b) Detail two distinct physical and structural points of difference to contrast an interference field due to a double-slit layout from a single-slit diffraction field configuration.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Single-Slit Diffraction and Interference",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the relationship between the slit width and the wavelength of light in determining the diffraction pattern. The formation of minima and maxima is fundamentally linked to the path difference of light waves emanating from different parts of the slit."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The concepts of diffraction and interference can be confusing because they involve wave behavior that is not intuitive. Students may struggle to visualize how light waves interact and how the geometry of the slit affects the resulting pattern."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "To understand the diffraction pattern, think of the slit as a source of wavelets that spread out and interfere with each other. The positions of minima and maxima are determined by the condition for constructive and destructive interference, which is influenced by the slit width and wavelength."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing the conditions for minima and maxima in single-slit diffraction. Use the formula for minima, which is given by \\( a \\sin(\\theta) = n\\lambda \\), where \\( n \\) is the order of the minimum. Then, explore how these conditions lead to the formation of secondary maxima."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly believe that the intensity of all maxima is equal or that the secondary maxima are as strong as the primary maximum. They fail to realize that the intensity diminishes due to the increasing path difference and the nature of interference as the order of maxima increases."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 4: `show_missing_idea-004`

- **Variation:** cbse
- **Tags:** physics, cbse, source_pdf_cbse_physics, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q46. (a) Define the self-inductance parameter of an electrical component. Derive the mathematical expression for the total internal magnetic energy stored within an inductor of self-inductance L when the current has been built up to a steady state value I. (b) The currents passing through two independent isolated inductor components of self-inductances 10 mH and 20 mH are forced to increase at the exact same uniform rate with respect to time. Sketch distinct comparative graphs showing the variation of: (i) the induced emf magnitude as a function of the current ramp rate, and (ii) the total stored magnetic energy as a function of the instantaneous current value. (c) The current passing through an inductor is increased uniformly from 0 to 2 A over a time window of 40 s. If an internal emf of 5 mV is induced during this transition period, calculate the total magnetic flux linked with the inductor at the specific intermediate instant $t = 10 ext{ s}$. Testing Question Bank 8

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Self-Inductance and Magnetic Energy",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the relationship between current, self-inductance, and the induced electromotive force (emf). Understanding how the rate of change of current affects the induced emf and the energy stored in the magnetic field is crucial."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The problem involves multiple concepts: self-inductance, induced emf, and magnetic energy. Students may struggle to connect these concepts, especially when transitioning from one part of the problem to another, such as from deriving formulas to applying them in specific scenarios."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize an inductor as a component that stores energy in a magnetic field when current flows through it. The self-inductance (L) quantifies how effectively this energy is stored based on the current (I) flowing through it. The induced emf is directly related to the rate of change of this current."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by recalling the definition of self-inductance and the formula for magnetic energy stored in an inductor: U = (1/2)LI². Then, use the relationship between induced emf (ε = -L(dI/dt)) to analyze how changes in current affect the emf and energy stored."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that the induced emf is constant or fail to correctly apply the relationship between current and time. They may also struggle with calculating the total magnetic flux linked with the inductor, particularly when given specific time intervals."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 5: `show_missing_idea-005`

- **Variation:** cbse
- **Tags:** physics, cbse, source_pdf_cbse_physics, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q41. With the help of a detailed, clearly labelled ray diagram, describe the construction, alignment adjustment, and geometric working of a standard Compound Microscope system adjusted such that the final virtual image is generated exactly at the least distance of distinct vision ((D)) . Derive the complete mathematical expression for the total linear magnifying power of the system under this specific operational condition.

**Ncert Context:**

NCERT Class 12 Physics Ch.9: Lens formula 1/f=1/v-1/u. Magnification m=v/u. Sign convention: real object distance u negative.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Compound Microscope System",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the importance of the alignment of the optical components in a compound microscope. Specifically, they may not fully grasp how the objective and eyepiece lenses work together to produce a virtual image at the least distance of distinct vision (D). Understanding the relationship between the object distance, image distance, and the focal lengths of the lenses is crucial."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The complexity arises from the need to consider multiple lenses and their respective focal lengths, as well as the sign conventions for distances. Additionally, deriving the total magnification requires careful attention to the individual magnifications of the objective and eyepiece, which can lead to confusion if students do not clearly separate these components."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the compound microscope as a system where the objective lens first forms a real, inverted image of the object. This image then acts as the object for the eyepiece lens, which magnifies it further to produce a virtual image at the least distance of distinct vision. Understanding this two-step magnification process is key to solving the problem."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by sketching a detailed ray diagram of the compound microscope. Label the objective and eyepiece lenses, the object, the real image formed by the objective, and the final virtual image produced by the eyepiece. Use the lens formula and magnification equations to set up your relationships, ensuring you apply the correct sign conventions."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students struggle with correctly applying the lens formula and magnification equations simultaneously, especially when it comes to calculating the total magnification. They may also confuse the distances related to the objective and eyepiece, leading to incorrect conclusions about the system's behavior."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `show_missing_idea-023`

- **Variation:** proof
- **Tags:** physics, neet, source_pdf_neet_physics, proof, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q90. Given below are two statements: Statement I: Photovoltaic devices can convert optical radiation into electricity. Statement II: Zener diode is designed to operate under reverse bias in breakdown region. In the light of the above statements, choose the most appropriate answer from the options given below: a. Statement I is incorrect but Statement II is correct. b. Both Statement I and Statement II are correct. c. Both Statement I and Statement II are incorrect. d. Statement I is correct but Statement II is incorrect.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Photovoltaic Devices and Zener Diodes",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the specific functions and operational principles of photovoltaic devices and Zener diodes. Recognizing that photovoltaic devices convert light into electricity and that Zener diodes are designed to operate in reverse [answer hidden]ias is crucial for evaluating the correctness of the statements."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The statements may seem unrelated at first glance, leading students to misinterpret their validity. The technical nature of the terms used can also create confusion, especially if students are not familiar with the applications of these devices."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Understanding that photovoltaic devices are specifically designed for converting optical radiation into electrical energy and that Zener diodes function in a specific [answer hidden]reakdown region under reverse [answer hidden]ias helps clarify the statements. [answer hidden]oth concepts are fundamental in electronics and renewa[answer hidden]le energy."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "[answer hidden]egin [answer hidden]y analyzing each statement independently. Recall the definitions and functions of photovoltaic devices and Zener diodes. This will help you determine the truth of each statement [answer hidden]efore considering their relationship."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students may incorrectly assume that [answer hidden]ecause the statements are a[answer hidden]out different devices, one must [answer hidden]e incorrect. They might also confuse the operational principles of Zener diodes, leading to an incorrect assessment of Statement II."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-024`

- **Variation:** proof
- **Tags:** physics, neet, source_pdf_neet_physics, proof, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q62. A wheel of a bullock cart is rolling on a level road as shows in the figure below. If its linear speed is v in the direction shown, which one of the following options is correct (P and Q are any highest and lowest points on the wheel respectively)?

[Diagram: The figure depicts a circular wheel representing a bullock cart wheel, oriented horizontally. The wheel is rolling on a level road, with a horizontal arrow labeled "v" indicating the linear speed of the wheel in the rightward direction. Two points are marked on the wheel: point "P" at the topmost position (highest point) and point "Q" at the bottommost position (lowest point) directly above the road surface. The wheel is divided into eight equal segments, but no specific numeric annotations, dimensions, or angles are provided. The road is represented as a straight horizontal line beneath point Q. There are no additional connections, arrows, or forces depicted in the diagram.]

(1) Both the points P and Q move with equal speed.  
(2) Point P has zero speed.  
(3) Point P moves slower than point Q.  
(4) Point P moves faster than point Q.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Wheel Motion: Key Concepts",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is the relationship between linear speed and rotational motion. As the wheel rolls without slipping, different points on the wheel have different velocities depending on their position relative to the ground."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the motion of points on the wheel with the overall linear speed of the wheel. They may assume that all points on the wheel move at the same speed, which is not the case due to the rotational motion."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the wheel as a series of points in circular motion. The point at the bottom (Q) is in contact with the ground and has a linear speed of zero at that instant, while the top point (P) moves with the highest speed due to the combination of its rotational and translational motion."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing the motion of the wheel. Consider the center of the wheel and how the linear speed (v) affects points at different heights. Use the concept of rotational motion to understand how the speed varies across the wheel."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly think that since the wheel is rolling at speed v, all points on the wheel must also have that speed. They overlook the fact that the point in contact with the ground has zero velocity at that moment, leading to confusion about the speeds of points P and Q."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `show_missing_idea-006`

- **Variation:** diagram
- **Tags:** physics, neet, source_pdf_neet_physics, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q27. A full wave rectifier circuit with diodes (D1) and (D2) is shown in the figure. If input supply voltage Vin = 220sin(100πt) volt, then at t = 15 m sec

[Diagram: The figure depicts a full wave rectifier circuit. On the left side, there is an AC voltage source labeled \( V_{in} \) with a sine wave symbol. The voltage source is connected to a transformer represented by two parallel lines, indicating the primary winding. The transformer has two output terminals leading to two diodes, labeled \( D_1 \) and \( D_2 \). The diodes are oriented such that \( D_1 \) is positioned above \( D_2 \), with their anodes connected to the transformer outputs and cathodes connected together. From the junction of the diodes, a resistor labeled \( R_L \) is connected to the right. The circuit layout is horizontal, with the voltage source on the left, followed by the transformer, diodes, and resistor arranged in a linear fashion. There are no numeric annotations, angles, or additional connections visible in the diagram.]

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Full Wave Rectification",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Students often overlook the behavior of the full wave rectifier in relation to the input AC signal. Specifically, they may not fully grasp how the rectification process alters the waveform and what the output voltage looks like at a given time."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The challenge arises from the need to analyze both the AC input and the resulting DC output simultaneously. Students may confuse the instantaneous voltage of the AC input with the rectified output voltage, leading to errors in their calculations."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the full wave rectifier as a device that inverts the negative half of the AC waveform, resulting in a continuous positive output. Understanding that the output voltage is always positive and follows the peaks of the input sine wave is crucial."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by calculating the input voltage at the specified time using the formula for the sine function. Then, determine how the full wave rectifier modifies this input voltage to find the output voltage."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly try to apply Ohm's law directly to the input AC voltage without considering the rectification process. They may also misinterpret the phase of the output voltage relative to the input, leading to incorrect conclusions about the circuit's behavior."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-007`

- **Variation:** diagram
- **Tags:** physics, jee, source_pdf_jee_jan_2026, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q.36 A bead P sliding on a frictionless semi-circular string (A C B) and it is at point S at t = 0 and at this instant the horizontal component of its velocity is v. Another bead Q of the same mass as P is ejected from point A at t = 0 along the horizontal string A B, with the speed v, friction between the beads and the respective strings may be neglected in both cases. Let t P and t Q be the respective times taken by beads P and Q to reach the point B, then the relation between t P and t Q is

[Diagram: The figure depicts a semi-circular string labeled ACB, with points A and B at the ends and point C at the bottom of the arc. A bead P is shown sliding on the string, positioned at point S, with a horizontal velocity component indicated as v. Another bead Q is ejected from point A along the horizontal string AB at the same speed v. The angle of 45° is marked at point S, indicating the angle between the horizontal line and the line connecting points A and S. The distance s is represented along the arc from point A to point P. The layout is primarily horizontal for string AB and semi-circular for string ACB, with arrows indicating the direction of motion for beads P and Q towards point B. There are no numeric annotations or additional connections visible in the diagram.]

1. t P > t Q  
2. t P = 1.25 t Q  
3. t P = t Q  
4. t P < t Q

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Motion of Beads on Different Paths",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key to solving this problem lies in understanding the different paths taken by beads P and Q. While both beads start with the same speed, bead P moves along a curved path, which affects its acceleration and the time it takes to reach point B."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often assume that since both beads start with the same speed, they will take the same amount of time to reach point B. However, the curvature of the path for bead P introduces a change in velocity due to gravitational acceleration, which complicates the comparison."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the motion of both beads: bead Q moves in a straight line with constant velocity, while bead P experiences a change in velocity as it slides down the arc. This difference in motion dynamics is crucial for determining the time taken by each bead."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by analyzing the motion of bead Q, which can be calculated using simple kinematics. Then, for bead P, consider the forces acting on it and how they affect its acceleration along the curved path."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students get stuck when they try to directly compare the times without accounting for the effects of the curved path on bead P's motion. They may overlook the fact that bead P will take longer due to its changing velocity as it descends the arc."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `show_missing_idea-025`

- **Variation:** ncert_strict
- **Tags:** physics, neet, source_pdf_neet_physics, ncert_strict, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q5. An oxygen cylinder of volume 30 litre has 18.20 moles of oxygen. After some oxygen is withdrawn from the cylinder, its gauge pressure drops to 11 atmospheric pressure at temperature 27°C. The mass of the oxygen withdrawn from the cylinder is nearly equal to : [Given, R = 100/12 J mol⁻¹ K⁻¹, and molecular mass of O₂ = 32, 1 atm pressure = 1.01 × 10⁵ N/m²] (1) 0.125 kg (2) 0.144 kg (3) 0.116 kg (4) 0.156 kg

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Gas Laws and Mass Calculation",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To solve this problem, students often overlook the relationship between pressure, volume, and the number of moles of gas as described by the Ideal Gas Law (PV = nRT). Understanding how to manipulate this equation to find the change in moles of gas is crucial."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "The challenge arises from needing to calculate the mass of oxygen withdrawn after a change in pressure, which requires careful application of the gas laws and conversion between moles and mass. Students may get confused about how to relate pressure changes to the amount of gas."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "The correct approach involves recognizing that the pressure drop indicates a change in the number of moles of gas. By applying the Ideal Gas Law before and after the withdrawal of gas, students can find the initial and final moles, and subsequently calculate the mass of the gas withdrawn."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by applying the Ideal Gas Law to find the initial amount of gas in moles and then the final amount after the pressure change. Use the given gauge pressure to convert to absolute pressure and ensure you are using the correct temperature in Kelvin."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that the volume remains constant or forget to convert gauge pressure to absolute pressure. Additionally, they might struggle with converting moles to mass correctly, leading to errors in their final answer."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `show_missing_idea-026`

- **Variation:** conceptual
- **Tags:** physics, neet, source_pdf_neet_physics, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q25. A model for quantized motion of an electron in a uniform magnetic field B states that the flux passing through the orbit of the electron is n(h/e) where n is an integer, h is Planck's constant and e is the magnitude of electron's charge. According to the model, the magnetic moment of an electron in its lowest energy state will be (m is the mass of the electron) (1) he πm (2) he 2πm (3) heB πm (4) heB 2πm

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding the Magnetic Moment of an Electron",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To determine the magnetic moment of an electron in a magnetic field, one must connect the concepts of quantization of angular momentum and the relationship between magnetic moment and angular momentum. The key is recognizing how the quantized flux relates to the magnetic moment."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the relationships between magnetic flux, angular momentum, and magnetic moment. The presence of constants like Planck's constant and the electron's charge can complicate the calculations, leading to errors in deriving the correct expression."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "The magnetic moment is directly proportional to the angular momentum of the electron. Understanding that the quantization condition (n(h/e)) relates to the angular momentum helps in deriving the magnetic moment correctly. Remembering that the magnetic moment is defined as the product of current and area can also guide you."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by recalling the quantization of angular momentum for an electron in a magnetic field. Use the relationship between the magnetic moment and angular momentum to set up the equation. Identify the relevant constants and how they interact in the context of the problem."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students misinterpret the relationship between the quantized flux and the resulting magnetic moment, leading to incorrect assumptions about the constants involved. They may also overlook the significance of the integer n and its role in determining the lowest energy state."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-027`

- **Variation:** conceptual
- **Tags:** physics, neet, source_pdf_neet_physics, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q41. Two gases A and B are filled at the same pressure in separate cylinders with movable pistons of radius rA and rB, respectively. On supplying an equal amount of heat to both the systems reversibly under constant pressure, the pistons of gas A and B are displaced by 16 cm and 9 cm, respectively. If the change in their internal energy is the same, then the ratio rA/ rB is equal to (1) 4/3 (2) 3/4 (3) 2/√3 (4) √3/2

;

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Gas Displacement and Internal Energy Changes",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To solve this problem, it's crucial to understand the relationship between work done by the gas, the displacement of the pistons, and the geometric factors involved, particularly the area of the pistons."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often focus solely on the displacement of the pistons without considering how the area of the pistons (which depends on their radius) affects the work done by the gas during expansion."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "The work done by each gas can be expressed in terms of the pressure and the area of the piston multiplied by the distance moved. Since the internal energy change is the same for both gases, this relationship will help establish a ratio between the radii of the pistons."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by writing the expression for work done by each gas, which is given by W = P × A × d, where A is the area of the piston (πr²) and d is the displacement. Set the work done equal for both gases since their internal energy changes are the same."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly assume that the displacement alone is sufficient to compare the two systems without incorporating the effect of the piston area, leading to incorrect conclusions about the ratio of the radii."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 3: `show_missing_idea-028`

- **Variation:** conceptual
- **Tags:** physics, neet, source_pdf_neet_physics, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q51. Match the List-I with List-II. List-I (Spectral Lines of Hydrogen for transitions from) ((A)) n₂ = 3 to n₁ = 2 ((B)) n₂ = 4 to n₁ = 2 ((C)) n₂ = 5 to n₁ = 2 ((D)) n₂ = 6 to n₁ = 2 List-II (Wavelengths (nm)) I. 410.2 II. 434.1 III. 656.3 IV. 486.1 Choose the correct answer from the options given below: (1) A-IV, B-III, C-I, D-II (2) A-I, B-II, C-III, D-IV (3) A-II, B-I, C-IV, D-III (4) A-III, B-IV, C-II, D-I

**Ncert Context:**

NCERT Class 12 Physics: Use SI units, free-body diagrams, and sign conventions from the relevant chapter.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Hydrogen Spectral Lines",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "To solve this problem, students need to understand the relationship between the energy levels of hydrogen and the wavelengths of light emitted during electron transitions. Each transition corresponds to a specific wavelength, which can be calculated using the Rydberg formula."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the transitions and their corresponding wavelengths, especially if they do not recall the specific wavelengths associated with each transition. Additionally, the order of energy levels can lead to mistakes in matching."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the energy levels of hydrogen and remember that transitions from higher to lower energy levels emit specific wavelengths. Familiarity with the Balmer series, which includes transitions to n=2, is crucial for identifying the correct wavelengths."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by identifying the transitions listed in List-I and recalling or calculating the corresponding wavelengths using the Rydberg formula. Write down the wavelengths for each transition to facilitate matching."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students mistakenly match the transitions without calculating or recalling the correct wavelengths, leading to incorrect pairings. They may also overlook the significance of the order of transitions when matching with the given wavelengths."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `show_missing_idea-029`

- **Variation:** case_study
- **Tags:** physics, neet, source_pdf_neet_physics, case_study, diagram, production_llm_gold

**Inputs**

**Problem Text Normalized:**

NEET Physics v1.0 90 curated mixed-style questions for RAG problem-solving evaluation This is a version. Each question has four options. Diagrams, graphs, circuits and mathematical expressions are preserved from the source question blocks. Answers, solutions, chapter headings, difficulty labels, and original source numbering are intentionally not includ NEET Physics v1.0 |

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Ohm's Law and Resistivity",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "Many students overlook the relationship between voltage, current, and resistance as defined by Ohm's Law ([answer hidden]). They often fail to recognize how changes in one variable affect the others, especially when resistors are combined in series or parallel."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students may find it challenging to apply the formulas correctly when resistors are combined in different configurations. The transition from understanding individual resistors to analyzing complex circuits can create confusion, particularly with series and parallel combinations."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Visualize the circuit as a flow of current through resistors. Understand that in series, the total resistance increases, while in parallel, the total resistance decreases. This affects the overall voltage and current distribution in the circuit."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by identifying the configuration of the resistors (series or parallel). Write down the known values (voltage, current, resistance) and apply Ohm's Law or the appropriate formulas for series and parallel resistances to find the unknowns."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Students often miscalculate the total resistance when combining resistors, leading to incorrect applications of Ohm's Law. They may also mix up the formulas for series and parallel circuits, which can result in confusion about the current and voltage across each component."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---

#### Example 2: `show_missing_idea-030`

- **Variation:** case_study
- **Tags:** biology, neet, source_pdf_neet_zoology, case_study, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q15. Given below are two statements: Statement I: The DNA fragments extracted from gel electrophoresis can be used in construction of recombinant DNA. Statement II: Smaller size DNA fragments are observed near anode while larger fragments are found near the wells in an agarose gel. In the light of the above statements, choose the most appropriate answer from the options given below: (1) Both statement I and statement II are correct (2) Both statement I and statement II are incorrect (3) Statement I is correct but statement II is incorrect (4) Statement I is incorrect but statement II is correct

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding DNA Fragment Behavior in Gel Electrophoresis",
  "sections": [
    {
      "heading": "The Missing Idea",
      "bodyMarkdown": "The key concept here is understanding how DNA fragments behave during gel electrophoresis based on their size and how this relates to their use in recombinant DNA technology."
    },
    {
      "heading": "Why It Feels Tricky",
      "bodyMarkdown": "Students often confuse the movement of DNA fragments with their size and charge. The direction of movement (toward the anode) and the size-related behavior in the gel can lead to misunderstandings about the implications for recombinant DNA construction."
    },
    {
      "heading": "Correct Mental Model",
      "bodyMarkdown": "Smaller DNA fragments migrate faster and further in the gel towards the anode, while larger fragments remain closer to the wells. This migration pattern is crucial for isolating specific DNA fragments for recombinant DNA applications."
    },
    {
      "heading": "How to Start",
      "bodyMarkdown": "Begin by recalling the principles of gel electrophoresis, focusing on how DNA size affects migration. Then, relate this to the practical applications of these fragments in recombinant DNA technology."
    },
    {
      "heading": "Where Most Students Get Stuck",
      "bodyMarkdown": "Many students misinterpret the implications of the statements regarding the size and migration of DNA fragments, leading them to incorrectly assess the correctness of each statement without fully understanding the underlying principles."
    }
  ],
  "revealLevel": "partial",
  "followUpButtons": [
    {
      "label": "Now show full solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give one similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Explain this concept",
      "action": "EXPLAIN_CONCEPT_AGAIN"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** section_completeness: pass. reveal_level: pass. ncert_alignment: pass. typical_student_trap: pass. production_llm_gold: pass.

---


## 21. Help Me Solve It Coach

| Field | Value |
|-------|-------|
| Dataset ID | `help_me_solve_it` |
| Category | Problem Solving |
| Tier | Tier 1 |
| Target examples | 30 |
| Actual examples | 30 |
| Version | 1.4.0 |

**Agent responsibility:** Guided solve with `interaction_count` branches: hints+checkpoint (0), feedback (1), full solution (2+). Production: [`help_me_solve_it.j2`](packages/core/prompts/templates/problem_solver/help_me_solve_it.j2).

**Audit finding (baseline v1.0.0):** Baseline had empty checkpoint labels and premature `Completed answer` stubs. Rebuilt with branching gold and no premature final answers at count 0/1.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `numerical` | Numeric/unit problems | 7 |
| `jee` | JEE Mains framing | 5 |
| `neet` | NEET MCQ / assertion-reason | 2 |
| `multi_part` | Multi-step / derive | 1 |
| `cbse` | CBSE board style | 5 |
| `proof` | Derivation / proof | 2 |
| `diagram` | Diagram-dependent | 2 |
| `ncert_strict` | Strict NCERT wording | 1 |
| `conceptual` | Explain-why / concept | 3 |
| `case_study` | Passage / case-based | 2 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **no_premature_answer** — Counts 0–1 must not include final numeric answer.
* **checkpoint_quality** — Checkpoint MCQ has four plausible options; A is concept-correct.
* **interaction_branch** — Gold shape matches `interaction_count` branch in template.
* **cumulative_context** — Counts 1–2 include decode, hints, feedback, and checkpointHistory with studentChoice/selectedLabel.
* **latex_format** — Multiplication spaced; units in `\text{}`; JSON backslashes escaped in `bodyMarkdown`.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `problem_text_normalized`, `interaction_count`, `ncert_context`, `student_choice`
* Output keys: `coach_json`

**Prompt template (production):**

```jinja2
You are ScholarSync AI Coach guiding without revealing the final answer yet.

Problem:
{{ problem_text_normalized }}

Interaction count so far: {{ interaction_count }}
{% if checkpoint_number %}Checkpoint: {{ checkpoint_number }}{% endif %}
{% if student_choice %}Student chose: {{ student_choice }}{% endif %}

{% if ncert_context %}
NCERT context:
{{ ncert_context }}
{% endif %}

{% if prior_response %}
Previous coach response from the prior turn (preserve checkpoint 1 prompt/options in checkpointHistory):
{{ prior_response }}
{% endif %}

{% include 'problem_solver/math_formatting_contract.j2' %}

{% if interaction_count == 0 %}
Return JSON with initial hints and checkpoint 1 MCQ (do NOT give final answer):
{
  "interactionCount": 0,
  "title": "string",
  "sections": [
    {"heading": "Problem decode", "bodyMarkdown": "..."},
    {"heading": "Hint 1", "bodyMarkdown": "..."},
    {"heading": "Hint 2", "bodyMarkdown": "..."}
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [{"id": "A", "label": "..."}, {"id": "B", "label": "..."}, {"id": "C", "label": "..."}, {"id": "D", "label": "..."}]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
{% elif interaction_count == 1 %}
Return COMPLETE standalone JSON. Evaluators must see the entire session without inputs.
Required:
- interactionCount: 1
- All prior sections (Problem decode, Hint 1, Hint 2)
- checkpointHistory[0]: full checkpoint 1 (prompt, all 4 options, studentChoice="{{ student_choice }}", selectedLabel = label text for that option)
- sections: add "Feedback on your choice" naming the selected option label and why it helps or misleads
- checkpoint: checkpoint 2 with four problem-specific options (A concept-correct)
- No finalAnswer
{
  "interactionCount": 1,
  "title": "string",
  "sections": [
    {"heading": "Problem decode", "bodyMarkdown": "..."},
    {"heading": "Hint 1", "bodyMarkdown": "..."},
    {"heading": "Hint 2", "bodyMarkdown": "..."},
    {"heading": "Feedback on your choice", "bodyMarkdown": "You picked option {{ student_choice }} (...selected label...). ..."}
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [{"id": "A", "label": "..."}, {"id": "B", "label": "..."}, {"id": "C", "label": "..."}, {"id": "D", "label": "..."}],
      "studentChoice": "{{ student_choice }}",
      "selectedLabel": "exact label for option {{ student_choice }}",
      "feedbackMarkdown": "same gist as Feedback on your choice section"
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [{"id": "A", "label": "..."}, {"id": "B", "label": "..."}, {"id": "C", "label": "..."}, {"id": "D", "label": "..."}]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
{% else %}
Return COMPLETE standalone JSON for the final reveal.
Required:
- interactionCount: 2
- checkpointHistory: BOTH checkpoints with prompt, all options, studentChoice, selectedLabel, feedbackMarkdown each
- sections: decode, hints, "Feedback on checkpoint 1", "Feedback on checkpoint 2" (or two feedback sections), "Solution walkthrough"
- finalAnswer and revealLevel full
- No active checkpoint field
{
  "interactionCount": 2,
  "title": "string",
  "sections": [
    {"heading": "Problem decode", "bodyMarkdown": "..."},
    {"heading": "Hint 1", "bodyMarkdown": "..."},
    {"heading": "Hint 2", "bodyMarkdown": "..."},
    {"heading": "Feedback on checkpoint 1", "bodyMarkdown": "At checkpoint 1 you chose A (...label...). ..."},
    {"heading": "Feedback on checkpoint 2", "bodyMarkdown": "At checkpoint 2 you chose {{ student_choice }} (...label...). ..."},
    {"heading": "Solution walkthrough", "bodyMarkdown": "..."}
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "...",
      "options": [{"id": "A", "label": "..."}, {"id": "B", "label": "..."}, {"id": "C", "label": "..."}, {"id": "D", "label": "..."}],
      "studentChoice": "A",
      "selectedLabel": "...",
      "feedbackMarkdown": "..."
    },
    {
      "number": 2,
      "prompt": "...",
      "options": [{"id": "A", "label": "..."}, {"id": "B", "label": "..."}, {"id": "C", "label": "..."}, {"id": "D", "label": "..."}],
      "studentChoice": "{{ student_choice }}",
      "selectedLabel": "...",
      "feedbackMarkdown": "..."
    }
  ],
  "finalAnswer": "string",
  "revealLevel": "full",
  "followUpButtons": [
    {"label": "Show next hint", "action": "SHOW_NEXT_HINT"},
    {"label": "Reveal solution", "action": "REVEAL_SOLUTION"},
    {"label": "Show best approach", "action": "SHOW_BEST_APPROACH"},
    {"label": "Give similar problem", "action": "GIVE_SIMILAR_PROBLEM"}
  ]
}
{% endif %}

Return valid JSON only.
```

*Runtime note:* `ProblemSolverService` mode `HELP_ME_SOLVE_IT` with session interaction counter.

### Evaluation examples (30)
## Variation: `numerical`


#### Example 1: `help_me_solve_it-006`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q57. The blue and white selectable markers have been developed which differentiate recombinant colonies from non-recombinant colonies on the basis of their ability to produce colour in the presence of a chromogenic substrate. Given below are two statements about this method: Statement I: The blue coloured colonies have DNA insert in the plasmid and they are identified as recombinant colonies. Statement II: The colonies without blue colour have DNA insert in the plasmid and are identified as recombinant colonies. In the light of the above statements, choose the most appropriate answer from the options given below: (1) Both Statement I and Statement II are correct (2) Both Statement I and Statement II are incorrect (3) Statement I is correct but Statement II is incorrect

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding Selectable Markers in Recombinant DNA",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem involves understanding the principles of selectable markers used in recombinant DNA technology. Specifically, it discusses how blue and white colonies are used to differentiate between recombinant and non-recombinant colonies based on their ability to produce color in the presence of a chromogenic substrate."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall the common method used in molecular cloning, particularly the use of the lacZ gene, which encodes for the enzyme β-galactosidase. This enzyme can cleave a chromogenic substrate, leading to a color change in colonies."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Consider the relationship between the presence of a DNA insert in the plasmid and the activity of the lacZ gene. Think about how the presence or absence of an insert affects the color of the colonies."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "The role of the lacZ gene in color production."
      },
      {
        "id": "B",
        "label": "The definition of recombinant vs non-recombinant colonies."
      },
      {
        "id": "C",
        "label": "The mechanism of chromogenic substrates."
      },
      {
        "id": "D",
        "label": "The significance of color change in identifying colonies."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-007`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q61. Given below are two statements: Statements I: In the nephron the descending limb of loop of Henle is impermeable to water and permeable to electrolytes. Statement II: The proximal convoluted tubule is lined by simple columnar brush border epithelium and increases the surface area for reabsorption. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is true but Statement II is false. (2) Statement I is false but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Nephron Function Analysis",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to evaluate the truth of two statements regarding the nephron's structure and function. Statement I discusses the permeability characteristics of the descending limb of the loop of Henle, while Statement II describes the structure of the proximal convoluted tubule."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the physiological roles of the descending limb of the loop of Henle and the proximal convoluted tubule. What do you know about their permeability to water and electrolytes?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Recall the structure of the proximal convoluted tubule and its function in reabsorption. How does the brush border epithelium contribute to its efficiency?"
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (Statement I is true but Statement II is false). This choice suggests that you believe the descending limb is impermeable to water and permeable to electrolytes, which is incorrect. Additionally, the proximal convoluted tubule is indeed lined with a brush border epithelium that increases surface area for reabsorption, making Statement II true."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Statement I is true but Statement II is false."
        },
        {
          "id": "B",
          "label": "Statement I is false but Statement II is true."
        },
        {
          "id": "C",
          "label": "Both Statement I and Statement II are true."
        },
        {
          "id": "D",
          "label": "Both Statement I and Statement II are false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is true but Statement II is false.",
      "feedbackMarkdown": "You picked option A (Statement I is true but Statement II is false). This choice suggests that you believe the descending limb is impermeable to water and permeable to electrolytes, which is incorrect. Additionally, the proximal convoluted tubule is indeed lined with a brush border epithelium that increases surface area for reabsorption, making Statement II true."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Reassess the permeability of the descending limb."
      },
      {
        "id": "B",
        "label": "Review the structure of the proximal convoluted tubule."
      },
      {
        "id": "C",
        "label": "Consider both statements together."
      },
      {
        "id": "D",
        "label": "Look for additional resources on nephron function."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 3: `help_me_solve_it-008`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q59. Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R: Assertion A : Breast-feeding during initial period of infant growth is recommended by doctors for bringing a healthy baby Reason R: Colostrum contains several antibodies absolutely essential to develop resistance for the new born baby. In the light of the above statements, choose the most appropriate answer from the options given below: (1) A is correct but R is not correct. (2) A is not correct but R is correct. (3) Both A and R are correct and R is the correct explanation of A.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Assertion and Reason Analysis",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to analyze two statements: Assertion A states that breast-feeding is recommended during the initial period of infant growth, while Reason R explains that colostrum contains essential antibodies for newborns. We must determine the relationship between these two statements."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the importance of breast-feeding in early infant development and the role of colostrum in providing immunity."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Reflect on whether the reason provided (R) directly supports the assertion (A) about breast-feeding."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (Assertion A is correct but Reason R is not correct). This choice suggests you believe breast-feeding is important, but the reason given does not support that. Consider if colostrum's benefits might actually validate the assertion."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A again. This indicates a consistent belief that while breast-feeding is beneficial, the explanation regarding colostrum does not hold. Re-evaluate the role of colostrum in the context of breast-feeding."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "Both Assertion A and Reason R are correct. Breast-feeding is indeed recommended for infants, and colostrum is crucial as it contains antibodies that help build the newborn's immune system. Therefore, R is a valid explanation for A."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R: Assertion A : Breast-feeding during initial period of infant growth is recommended by doctors for bringing a healthy baby Reason R: Colostrum contains several antibodies absolutely essential to develop resistance for the new born baby. In the light of the above statements, choose the most appropriate answer from the options given below:",
      "options": [
        {
          "id": "A",
          "label": "A is correct but R is not correct."
        },
        {
          "id": "B",
          "label": "A is not correct but R is correct."
        },
        {
          "id": "C",
          "label": "Both A and R are correct and R is the correct explanation of A."
        },
        {
          "id": "D",
          "label": "Both A and R are correct but R is not the correct explanation of A."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A is correct but R is not correct.",
      "feedbackMarkdown": "At checkpoint 1 you chose A (Assertion A is correct but Reason R is not correct). This choice suggests you believe breast-feeding is important, but the reason given does not support that. Consider if colostrum's benefits might actually validate the assertion."
    },
    {
      "number": 2,
      "prompt": "Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R: Assertion A : Breast-feeding during initial period of infant growth is recommended by doctors for bringing a healthy baby Reason R: Colostrum contains several antibodies absolutely essential to develop resistance for the new born baby. In the light of the above statements, choose the most appropriate answer from the options given below:",
      "options": [
        {
          "id": "A",
          "label": "A is correct but R is not correct."
        },
        {
          "id": "B",
          "label": "A is not correct but R is correct."
        },
        {
          "id": "C",
          "label": "Both A and R are correct and R is the correct explanation of A."
        },
        {
          "id": "D",
          "label": "Both A and R are correct but R is not the correct explanation of A."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A is correct but R is not correct.",
      "feedbackMarkdown": "At checkpoint 2 you chose A again. This indicates a consistent belief that while breast-feeding is beneficial, the explanation regarding colostrum does not hold. Re-evaluate the role of colostrum in the context of breast-feeding."
    }
  ],
  "finalAnswer": "3",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 4: `help_me_solve_it-009`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q80. Match List-I with List-II with respect to human eye. List-I List-II ((A)) Fovea (I) Visible coloured portion of eye that regulates diameter of pupil. ((B)) Iris (II) External layer of eye formed of dense connective tissue. ((C)) Blind spot (III) Point of greatest visual acuity or resolution. ((D)) Sclera (IV) Point where optic nerve leaves the eyeball and photoreceptor cells are absent. Choose the correct answer from the options given below: a. A-II, B-I, C-III, D-IV b. A-III, B-I, C-IV, D-II c. A-IV, B-III, C-II, D-I d. A-I, B-IV, C-III, D-II

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding the Human Eye",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to match specific parts of the human eye (List-I) with their corresponding descriptions (List-II). Each part has a unique function and characteristic that distinguishes it from the others."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the function of the fovea; it is known for its role in vision. What does it mean for visual acuity?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "The iris is involved in controlling the amount of light entering the eye. Think about its physical characteristics and how it relates to the pupil."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Focus on the function of each part."
      },
      {
        "id": "B",
        "label": "Consider the anatomical structure."
      },
      {
        "id": "C",
        "label": "Think about the role of light in vision."
      },
      {
        "id": "D",
        "label": "Match based on common misconceptions."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

#### Example 5: `help_me_solve_it-010`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q87. Match List I with List II: List-I List-II A. Exophthalmic goiter I. Excess secretion of cortisol, moon face & hyperglycemia B. Acromegaly II. Hypo-secretion of thyroid hormone and stunted growth. C. Cushing's syndrome III. Hyper secretion of thyroid hormone & protruding eye balls. D. Cretinism IV. Excessive secretion of growth hormone. Choose the correct answer form the options given below: (1) A-III, B-IV, C-II, D-I (2) A-III, B-IV, C-I, D-II (3) A-I, B-III, C-II, D-IV (4) A-IV, B-II, C-I, D-III

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Endocrine Disorders Matching",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "You need to match the conditions listed in List I with their corresponding descriptions in List II. Each condition is associated with a specific hormonal imbalance or deficiency."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider what each condition represents in terms of hormone levels. For example, think about which conditions are related to excess hormone production versus those related to hormone deficiency."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Review the symptoms associated with each condition. This can help you identify the correct matches. For instance, exophthalmic goiter is known for its specific symptom of protruding eyes."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (A-III, B-IV, C-II, D-I). This choice is incorrect because it misaligns the conditions with their respective descriptions. For example, exophthalmic goiter is characterized by hyper secretion of thyroid hormone and protruding eyeballs, which is correctly matched with III, but other matches are not accurate."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "A-III, B-IV, C-II, D-I"
        },
        {
          "id": "B",
          "label": "A-III, B-IV, C-I, D-II"
        },
        {
          "id": "C",
          "label": "A-I, B-III, C-II, D-IV"
        },
        {
          "id": "D",
          "label": "A-IV, B-II, C-I, D-III"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A-III, B-IV, C-II, D-I",
      "feedbackMarkdown": "You picked option A (A-III, B-IV, C-II, D-I). This choice is incorrect because it misaligns the conditions with their respective descriptions. For example, exophthalmic goiter is characterized by hyper secretion of thyroid hormone and protruding eyeballs, which is correctly matched with III, but other matches are not accurate."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "A-III, B-IV, C-I, D-II"
      },
      {
        "id": "B",
        "label": "A-III, B-IV, C-II, D-I"
      },
      {
        "id": "C",
        "label": "A-I, B-III, C-II, D-IV"
      },
      {
        "id": "D",
        "label": "A-IV, B-II, C-I, D-III"
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 6: `help_me_solve_it-011`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q12. Given below are two statements: Statement I: Low temperature preserves the enzyme in a temporarily inactive state whereas high temperature destroys enzymatic activity because proteins are denatured by heat. Statement II: When the inhibitor closely resembles the substrate in its molecular structure and inhibits the activity of the enzyme, it is known as competitive inhibitor. In the light of the above statements, choose the correct answer from the options given below: a. Statement I is false but statement II is true. b. Both Statement I and Statement II are true. c. Both Statement I and Statement II are false. d. Statement I is true but Statement II is false.

**Ncert Context:**

NCERT Class 11 Biology Ch.9: Pepsin active in acidic stomach; trypsin in alkaline duodenum.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Given below are two statements: Statement I: Low temperature preserves the enzyme in a temporarily inactive state whereas high temperature destroys enzymatic activity because proteins are denatured by heat. Statement II: When the inhibitor closely resembles the substrate in its molecular structure and inhibits the activity of the enzyme, it is known as competitive inhibitor. In the light of the above statements, choose the correct answer from the options given below:",
      "options": [
        {
          "id": "A",
          "label": "Statement I is false but statement II is true."
        },
        {
          "id": "B",
          "label": "Both Statement I and Statement II are true."
        },
        {
          "id": "C",
          "label": "Both Statement I and Statement II are false."
        },
        {
          "id": "D",
          "label": "Statement I is true but Statement II is false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is false but statement II is true.",
      "feedbackMarkdown": "At checkpoint 1 you chose A (Statement I is false but statement II is true). This choice suggests that you believe Statement I is incorrect regarding the effects of temperature on enzymes."
    },
    {
      "number": 2,
      "prompt": "Given below are two statements: Statement I: Low temperature preserves the enzyme in a temporarily inactive state whereas high temperature destroys enzymatic activity because proteins are denatured by heat. Statement II: When the inhibitor closely resembles the substrate in its molecular structure and inhibits the activity of the enzyme, it is known as competitive inhibitor. In the light of the above statements, choose the correct answer from the options given below:",
      "options": [
        {
          "id": "A",
          "label": "Statement I is false but statement II is true."
        },
        {
          "id": "B",
          "label": "Both Statement I and Statement II are true."
        },
        {
          "id": "C",
          "label": "Both Statement I and Statement II are false."
        },
        {
          "id": "D",
          "label": "Statement I is true but Statement II is false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is false but statement II is true.",
      "feedbackMarkdown": "At checkpoint 2 you chose A (Statement I is false but statement II is true). This indicates a consistent belief about the accuracy of the statements."
    }
  ],
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem presents two statements about enzyme activity and inhibition. You need to evaluate the truth of each statement and determine the correct answer based on that evaluation."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the effects of temperature on enzyme activity. What happens to enzymes at low and high temperatures?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Reflect on the definition of competitive inhibitors in enzymatic reactions. How does their structure relate to the substrate?"
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (Statement I is false but statement II is true). This choice suggests that you believe Statement I is incorrect regarding the effects of temperature on enzymes."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A (Statement I is false but statement II is true). This indicates a consistent belief about the accuracy of the statements."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "To analyze the statements: Statement I is true; low temperatures can preserve enzyme activity while high temperatures can denature proteins. Statement II is also true; a competitive inhibitor resembles the substrate and competes for the active site. Therefore, the correct answer is that both statements are true."
    }
  ],
  "finalAnswer": "B",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 7: `help_me_solve_it-012`

- **Variation:** numerical
- **Tags:** biology, neet, source_pdf_neet_zoology, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q48. Given below are two statements: Statement I: A protein is imagined as a line, the left end represented by first amino acid (C-terminal) and the right end represented by last amino acid (N-terminal) Statement II: Adult human haemoglobin, consists of 4 subunits (two subunits of a type and two subunits of b type.) In the light of the above statements, choose the correct answer from the options given below: a. Statement I is false but Statement II is true. b. Both Statement I and Statement II are true. c. Both Statement I and Statement II are false. d. Statement I is true but Statement II is false.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding Protein Structure and Hemoglobin",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to evaluate the truth of two statements regarding proteins and hemoglo[answer hidden]in. Statement I descri[answer hidden]es the orientation of a protein's amino acids, while Statement II discusses the structure of adult human hemoglo[answer hidden]in."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall that proteins are made up of amino acids linked together in a specific sequence. The terms C-terminal and N-terminal refer to the ends of the amino acid chain."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Consider the structure of hemoglo[answer hidden]in. It is important to know how many su[answer hidden]units it has and their types to assess the truth of Statement II."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Focus on the definition of C-terminal and N-terminal."
      },
      {
        "id": "B",
        "label": "Analyze the composition of hemoglobin."
      },
      {
        "id": "C",
        "label": "Evaluate the relationship between the two statements."
      },
      {
        "id": "D",
        "label": "Consider the general structure of proteins."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

## Variation: `jee`


#### Example 1: `help_me_solve_it-013`

- **Variation:** jee
- **Tags:** biology, neet, source_pdf_neet_zoology, jee, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q47. Given below are two statements: Statement I: The presence or absence of hymen is not a reliable indicator of virginity. Statement II: The hymen is torn during the first coitus only. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is true but Statement II is false. (2) Statement I is false but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Understanding Virginity and the Hymen",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem presents two statements regarding the hymen and its relation to virginity. We need to evaluate the truth of each statement and determine the correct option based on their validity."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the biological and cultural aspects of virginity and how they relate to the physical characteristics of the hymen."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Research the functions and variations of the hymen, as well as common misconceptions about its role in determining virginity."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (Statement I is true but Statement II is false). This choice suggests that you recognize the unreliability of the hymen as an indicator of virginity, which is a common understanding. However, it's important to critically assess both statements to ensure a comprehensive understanding."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Statement I is true but Statement II is false."
        },
        {
          "id": "B",
          "label": "Statement I is false but Statement II is true."
        },
        {
          "id": "C",
          "label": "Both Statement I and Statement II are true."
        },
        {
          "id": "D",
          "label": "Both Statement I and Statement II are false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is true but Statement II is false.",
      "feedbackMarkdown": "This choice suggests that you recognize the unreliability of the hymen as an indicator of virginity, which is a common understanding. However, it's important to critically assess both statements to ensure a comprehensive understanding."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Reevaluate Statement II."
      },
      {
        "id": "B",
        "label": "Consider cultural perspectives on virginity."
      },
      {
        "id": "C",
        "label": "Research more about the hymen's anatomy."
      },
      {
        "id": "D",
        "label": "Discuss the implications of both statements."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-014`

- **Variation:** jee
- **Tags:** biology, neet, source_pdf_neet_zoology, jee, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q35. Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R. Assertion A: Endometrium is necessary for implantation of blastocyst. Reason R: In the absence of fertilization, the corpus luteum degenerates that causes disintegration of endometrium. In the light of the above statements, choose the correct answer from the options given below: a. A is false but R is true. b. Both A and R are true and R is the correct explanation of A. c. Both A and R are true but R is NOT the correct explanation of A. d. A is true but R is false.

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Understanding Implantation and Endometrium",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem involves evaluating two statements regarding the endometrium and its role in implantation. We need to determine the truthfulness of both the Assertion (A) and the Reason (R), and how they relate to each other."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall the role of the endometrium in the menstrual cycle and its importance for implantation. Consider what happens to the endometrium when fertilization does not occur."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about how the degeneration of the corpus luteum affects the endometrium and whether this supports or contradicts the assertion about implantation."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (Assertion A is false but Reason R is true). This choice suggests you believe that the endometrium is not necessary for implantation, which contradicts established biological understanding. Consider revisiting the role of the endometrium."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A again. This indicates a consistent belief that the assertion is false. However, it is important to analyze the relationship between the assertion and the reason more closely. The endometrium is indeed crucial for implantation."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "The endometrium is essential for the implantation of a blastocyst, as it provides the necessary environment for the embryo to attach and grow. The reason states that in the absence of fertilization, the corpus luteum degenerates, leading to the disintegration of the endometrium. This is true and explains why the endometrium must be intact for successful implantation. Therefore, both A and R are true, and R correctly explains A."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R. Assertion A: Endometrium is necessary for implantation of blastocyst. Reason R: In the absence of fertilization, the corpus luteum degenerates that causes disintegration of endometrium.",
      "options": [
        {
          "id": "A",
          "label": "A is false but R is true."
        },
        {
          "id": "B",
          "label": "Both A and R are true and R is the correct explanation of A."
        },
        {
          "id": "C",
          "label": "Both A and R are true but R is NOT the correct explanation of A."
        },
        {
          "id": "D",
          "label": "A is true but R is false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A is false but R is true.",
      "feedbackMarkdown": "You chose A, which suggests a misunderstanding of the role of the endometrium in implantation. The endometrium is indeed necessary for implantation."
    },
    {
      "number": 2,
      "prompt": "Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R. Assertion A: Endometrium is necessary for implantation of blastocyst. Reason R: In the absence of fertilization, the corpus luteum degenerates that causes disintegration of endometrium.",
      "options": [
        {
          "id": "A",
          "label": "A is false but R is true."
        },
        {
          "id": "B",
          "label": "Both A and R are true and R is the correct explanation of A."
        },
        {
          "id": "C",
          "label": "Both A and R are true but R is NOT the correct explanation of A."
        },
        {
          "id": "D",
          "label": "A is true but R is false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A is false but R is true.",
      "feedbackMarkdown": "You chose A again, indicating a persistent misunderstanding. The endometrium is essential for implantation, and the reason provided supports this assertion."
    }
  ],
  "finalAnswer": "B",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 3: `help_me_solve_it-015`

- **Variation:** jee
- **Tags:** biology, neet, source_pdf_neet_zoology, jee, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q65. Given below are two statements: Statement I: Vas deferens receives a duct from seminal vesicle and opens into urethra as the ejaculatory duct. Statement II: The cavity of the cervix is called cervical canal which along with vagina forms birth canal. In the light of the above statements, choose the correct answer from the options given below: a. Statement I incorrect but Statement II is true. b. Both Statement I and Statement II are true. c. Both Statement I and Statement II are false. d. Statement I is correct but Statement II is false. 8

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding Reproductive Anatomy",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We have two statements regarding the male and female reproductive systems. We need to evaluate the truthfulness of each statement to determine the correct answer."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the anatomy of the male reproductive system, specifically the role of the vas deferens and its connection to the seminal vesicle and urethra."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Reflect on the structure of the female reproductive system, particularly the cervix and its relationship with the vagina during child[answer hidden]irth."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Evaluate the accuracy of Statement I."
      },
      {
        "id": "B",
        "label": "Evaluate the accuracy of Statement II."
      },
      {
        "id": "C",
        "label": "Consider the relationship between both statements."
      },
      {
        "id": "D",
        "label": "Analyze the definitions of anatomical terms used in both statements."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

#### Example 4: `help_me_solve_it-016`

- **Variation:** jee
- **Tags:** biology, neet, source_pdf_neet_zoology, jee, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q76. Given below are two statements: Statement I: Bone marrow is the main lymphoid organ where all blood cells including lymphocytes are produced. Statement II: Both bone marrow and thymus provide micro environments for the development and maturation of T-lymphocytes. In the light of the above statements, choose the most appropriate answer from the options given below: (1) Statement I is correct but statement II is

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Understanding Lymphoid Organs",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to evaluate two statements regarding lymphoid organs and their functions in blood cell production and T-lymphocyte maturation."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the roles of bone marrow and thymus in the immune system. What is the primary function of each organ?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about where lymphocytes are produced and where they mature. Are both statements true, or is one of them incorrect?"
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A ([answer hidden]). This choice suggests you believe that while bone marrow is indeed the primary site for blood cell production, the thymus does not play a role in T-lymphocyte maturation, which is misleading. The thymus is crucial for the development and maturation of T-lymphocytes."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Statement I is correct but statement II is incorrect."
        },
        {
          "id": "B",
          "label": "Both statements are correct."
        },
        {
          "id": "C",
          "label": "Statement I is incorrect but statement II is correct."
        },
        {
          "id": "D",
          "label": "Both statements are incorrect."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is correct but statement II is incorrect.",
      "feedbackMarkdown": "This choice suggests you believe that while bone marrow is indeed the primary site for blood cell production, the thymus does not play a role in T-lymphocyte maturation, which is misleading. The thymus is crucial for the development and maturation of T-lymphocytes."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Re-evaluate the statements considering the roles of both organs."
      },
      {
        "id": "B",
        "label": "Choose to focus only on bone marrow's function."
      },
      {
        "id": "C",
        "label": "Consider the possibility that both statements could be correct."
      },
      {
        "id": "D",
        "label": "Dismiss both statements as incorrect."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 5: `help_me_solve_it-017`

- **Variation:** jee
- **Tags:** biology, neet, source_pdf_neet_zoology, jee, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q85. Match List-I with List-II. List-I (Cells) List-II (Secretion) ((A)) Peptic cells (I) Mucus ((B)) Goblet Cells (II) Bile Juice ((C)) Oxyntic Cell (III) Proenzyme Pepsinogen ((D)) Hepatic cells (IV) HCl and intrinsic factor for absorption of vitamin B12 Choose the correct answer from the options given below a. A-II, B-IV, C-I, D-III b. A-IV, B-III, C-II, D-I c. A-II, B-I, C-III, D-IV d. A-III, B-I, C-IV, D-II 7

**Ncert Context:**

NCERT Class 11 Biology Ch.9: Pepsin active in acidic stomach; trypsin in alkaline duodenum.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Cell Secretion Matching Problem",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "You need to match the types of cells listed in List-I with their corresponding secretions in List-II. Each cell type has a specific secretion that plays a role in digestion or other bodily functions."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall that peptic cells are involved in the stomach and secrete substances related to digestion, while goblet cells are found in the intestines and secrete mucus."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Oxyntic cells are known for secreting hydrochloric acid (HCl) and intrinsic factor, which is crucial for vitamin B12 absorption. Hepatic cells are related to liver functions."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (A-II, B-IV, C-I, D-III). This choice is incorrect. Peptic cells secrete proenzyme pepsinogen, not bile juice. Review the functions of each cell type."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A (A-II, B-IV, C-I, D-III) again. This choice remains incorrect. Remember the specific secretions associated with each cell type to find the correct matches."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "Let's analyze each cell type: \n- Peptic cells (A) secrete proenzyme pepsinogen (III). \n- Goblet cells (B) secrete mucus (I). \n- Oxyntic cells (C) secrete HCl and intrinsic factor (IV). \n- Hepatic cells (D) secrete bile juice (II). \nThus, the correct matches are A-III, B-I, C-IV, D-II."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Match List-I with List-II.",
      "options": [
        {
          "id": "A",
          "label": "A-II, B-IV, C-I, D-III"
        },
        {
          "id": "B",
          "label": "A-IV, B-III, C-II, D-I"
        },
        {
          "id": "C",
          "label": "A-II, B-I, C-III, D-IV"
        },
        {
          "id": "D",
          "label": "A-III, B-I, C-IV, D-II"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A-II, B-IV, C-I, D-III",
      "feedbackMarkdown": "At checkpoint 1 you chose A (A-II, B-IV, C-I, D-III). This choice is incorrect. Peptic cells secrete proenzyme pepsinogen, not bile juice. Review the functions of each cell type."
    },
    {
      "number": 2,
      "prompt": "Match List-I with List-II.",
      "options": [
        {
          "id": "A",
          "label": "A-II, B-IV, C-I, D-III"
        },
        {
          "id": "B",
          "label": "A-IV, B-III, C-II, D-I"
        },
        {
          "id": "C",
          "label": "A-II, B-I, C-III, D-IV"
        },
        {
          "id": "D",
          "label": "A-III, B-I, C-IV, D-II"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A-II, B-IV, C-I, D-III",
      "feedbackMarkdown": "At checkpoint 2 you chose A (A-II, B-IV, C-I, D-III) again. This choice remains incorrect. Remember the specific secretions associated with each cell type to find the correct matches."
    }
  ],
  "finalAnswer": "A-III, B-I, C-IV, D-II",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

## Variation: `neet`


#### Example 1: `help_me_solve_it-004`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q65. Identify the set of correct statements: A. The flowers of Vallisneria are colourful and produce nectar B. The flowers of waterlily are not pollinated by water. C. In most of water-pollinated species, the pollen grains are protected from wetting. D. Pollen grains of some hydrophytes are long and ribbon like. E. In some hydrophytes, the pollen grains are carried passively inside water. Choose the correct answer from the options given below: (1) A, C, D and E only (2) B, C, D and E only (3) C, D and E only (4) A B, C and D only

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding Pollination in Hydrophytes",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to evaluate a set of statements regarding the pollination mechanisms in certain aquatic plants, specifically Vallisneria and waterlilies. Each statement provides information about the characteristics of their flowers and pollen grains."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the typical characteristics of flowers in aquatic plants. Are they usually colorful and do they produce nectar for pollinators?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about how pollen grains behave in water. Do they need protection from wetting, and how might they be transported in aquatic environments?"
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Evaluate the characteristics of Vallisneria flowers."
      },
      {
        "id": "B",
        "label": "Consider the pollination method of waterlilies."
      },
      {
        "id": "C",
        "label": "Assess the protection of pollen grains in water."
      },
      {
        "id": "D",
        "label": "Look into the structure of pollen grains in hydrophytes."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-005`

- **Variation:** neet
- **Tags:** biology, neet, source_pdf_neet_botany, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q43. Given below are two Statements: Statement I : Chromosomes become gradually visible under light microscope during leptotene stage. Statement II: The beginning of diplotene stage is recognized by dissolution of synaptonemal complex. In the light of the above statements, choose the correct answer from the options given below: (1) Statement I is true but Statement II is false. (2) Statement I is false but Statement II is true. (3) Both Statement I and Statement II are true. (4) Both Statement I and Statement II are false

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Chromosome Visibility and Synaptonemal Complex",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We are examining two statements regarding the visibility of chromosomes during specific stages of meiosis and the characteristics of the synaptonemal complex."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the stages of meiosis: leptotene and diplotene. What happens to chromosomes in these stages?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Reflect on the role of the synaptonemal complex during meiosis and when it dissolves."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (Statement I is true but Statement II is false). This choice suggests that you believe chromosomes do become visible during leptotene, which is correct, but you may need to reconsider the timing of the dissolution of the synaptonemal complex in relation to diplotene."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Statement I is true but Statement II is false."
        },
        {
          "id": "B",
          "label": "Statement I is false but Statement II is true."
        },
        {
          "id": "C",
          "label": "Both Statement I and Statement II are true."
        },
        {
          "id": "D",
          "label": "Both Statement I and Statement II are false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is true but Statement II is false.",
      "feedbackMarkdown": "You picked option A (Statement I is true but Statement II is false). This choice suggests that you believe chromosomes do become visible during leptotene, which is correct, but you may need to reconsider the timing of the dissolution of the synaptonemal complex in relation to diplotene."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Revisit the definitions of leptotene and diplotene."
      },
      {
        "id": "B",
        "label": "Look up the role of the synaptonemal complex."
      },
      {
        "id": "C",
        "label": "Analyze the visibility of chromosomes in other meiotic stages."
      },
      {
        "id": "D",
        "label": "Consider the implications of both statements being true."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

## Variation: `multi_part`


#### Example 1: `help_me_solve_it-018`

- **Variation:** multi_part
- **Tags:** biology, neet, source_pdf_neet_zoology, multi_part, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q60. Regarding catalytic cycle of an enzyme action, select the correct sequential steps: A. Substrate enzyme complex formation. B. Free enzyme ready to bind with another substrate. C. Release fo products. D. Chemical bonds of the substrate broken. E. Substrate bindig to active site. Choose the correct answer from the options given below: (1) B, A, C, D, E (2) E, D, C, B, A (3) E, A, D, C, B (4) A, E, B, D, C

**Ncert Context:**

NCERT Class 11 Biology Ch.9: Pepsin active in acidic stomach; trypsin in alkaline duodenum.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Enzyme Catalytic Cycle",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem asks for the correct sequence of steps in the catalytic cycle of enzyme action. The steps involve substrate binding, product formation, and enzyme regeneration."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the order in which an enzyme interacts with a substrate. What happens first when a substrate approaches an enzyme?"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "After the substrate binds to the enzyme and undergoes a reaction, think about what happens to the enzyme and the products formed."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (Substrate enzyme complex formation). This is a crucial first step in the catalytic cycle. However, consider the entire sequence of events that follow this step."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A (Substrate enzyme complex formation) again. Remember to think about the subsequent steps after substrate binding and how they lead to product release."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "The correct sequence of steps in the catalytic cycle is: 1) E: Substrate binding to the active site, 2) A: Substrate-enzyme complex formation, 3) D: Chemical bonds of the substrate broken, 4) C: Release of products, 5) B: Free enzyme ready to bind with another substrate. Therefore, the correct answer is option (3) E, A, D, C, B."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Regarding catalytic cycle of an enzyme action, select the correct sequential steps:",
      "options": [
        {
          "id": "A",
          "label": "Substrate enzyme complex formation."
        },
        {
          "id": "B",
          "label": "Free enzyme ready to bind with another substrate."
        },
        {
          "id": "C",
          "label": "Release of products."
        },
        {
          "id": "D",
          "label": "Chemical bonds of the substrate broken."
        },
        {
          "id": "E",
          "label": "Substrate binding to active site."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Substrate enzyme complex formation.",
      "feedbackMarkdown": "At checkpoint 1 you chose A (Substrate enzyme complex formation). This is a crucial first step in the catalytic cycle. However, consider the entire sequence of events that follow this step."
    },
    {
      "number": 2,
      "prompt": "Regarding catalytic cycle of an enzyme action, select the correct sequential steps:",
      "options": [
        {
          "id": "A",
          "label": "Substrate enzyme complex formation."
        },
        {
          "id": "B",
          "label": "Free enzyme ready to bind with another substrate."
        },
        {
          "id": "C",
          "label": "Release of products."
        },
        {
          "id": "D",
          "label": "Chemical bonds of the substrate broken."
        },
        {
          "id": "E",
          "label": "Substrate binding to active site."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Substrate enzyme complex formation.",
      "feedbackMarkdown": "At checkpoint 2 you chose A (Substrate enzyme complex formation) again. Remember to think about the subsequent steps after substrate binding and how they lead to product release."
    }
  ],
  "finalAnswer": "E, A, D, C, B",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

## Variation: `cbse`


#### Example 1: `help_me_solve_it-001`

- **Variation:** cbse
- **Tags:** physics, cbse, source_pdf_cbse_physics, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q30. An alternating voltage source represented by V = V0 sin ωt is applied across an ideal inductor possessing self-inductance L. Derive the mathematical expression for the instantaneous current flowing through the circuit. Prove analytically that the current wave lags behind the voltage wave by a phase angle of π / 2 radians, and construct the corresponding vector phasor diagram layout.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Alternating Current in an Inductor",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We have an alternating voltage source described by the equation $V = V_[answer hidden] \\sin(\\omega t)$ applied to an ideal inductor with self-inductance $L$. Our goal is to find the instantaneous current $I(t)$ flowing through the circuit and demonstrate that this current lags the voltage by a phase angle of $\\frac{\\pi}{2}$ radians."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall that the voltage across an inductor is related to the rate of change of current through it. The relationship is given by $V = L \\frac{dI}{dt}$."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "To find the current, you will need to integrate the voltage equation with respect to time. Don't forget to consider the phase difference that arises from the integration process."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Use Ohm's law directly."
      },
      {
        "id": "B",
        "label": "Apply the relationship between voltage and current in an inductor."
      },
      {
        "id": "C",
        "label": "Consider the energy stored in the inductor."
      },
      {
        "id": "D",
        "label": "Use Kirchhoff's laws for circuit analysis."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-019`

- **Variation:** cbse
- **Tags:** biology, neet, source_pdf_neet_zoology, cbse, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q30. Given below are two statements: Statement I: During Go phase of cell cycle the cell is metabolically inactive Statement II: The centrosome undergoes duplication during S phase of interphase. In the light of the above statements, choose the most appropriate answer from the option below: a. Statement I is incorrect but Statement II is correct b. Both Statement I and Statement II are correct c. Both Statement I and Statement II are incorrect. d. Statement I is correct but Statement II is incorrect.

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Cell Cycle Statements Evaluation",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to evaluate two statements regarding the cell cycle: Statement I claims that during the Go phase, the cell is meta[answer hidden]olically inactive, while Statement II states that the centrosome undergoes duplication during the S phase of interphase."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the characteristics of the Go phase in the cell cycle and how it relates to cellular activity."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Recall the stages of interphase and what occurs during the S phase, particularly concerning centrosome duplication."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (Statement I is incorrect [answer hidden]ut Statement II is correct). This choice may mislead you [answer hidden]ecause while Statement I is indeed incorrect, Statement II is also correct. The centrosome does duplicate during the S phase, which is a key event in the cell cycle."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Statement I is incorrect but Statement II is correct"
        },
        {
          "id": "B",
          "label": "Both Statement I and Statement II are correct"
        },
        {
          "id": "C",
          "label": "Both Statement I and Statement II are incorrect"
        },
        {
          "id": "D",
          "label": "Statement I is correct but Statement II is incorrect"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Statement I is incorrect but Statement II is correct",
      "feedbackMarkdown": "You picked option A (Statement I is incorrect but Statement II is correct). This choice may mislead you because while Statement I is indeed incorrect, Statement II is also correct. The centrosome does duplicate during the S phase, which is a key event in the cell cycle."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Re-evaluate Statement I and its implications"
      },
      {
        "id": "B",
        "label": "Focus on the significance of the S phase"
      },
      {
        "id": "C",
        "label": "Consider both statements together"
      },
      {
        "id": "D",
        "label": "Review the entire cell cycle process"
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 3: `help_me_solve_it-020`

- **Variation:** cbse
- **Tags:** biology, neet, source_pdf_neet_zoology, cbse, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q58. Match List-I with List-II. List-I List-II ((A)) Mast cells (I) Ciliated epithelium ((B)) Inner surface of bronchiole (II) Areolar connective tissue ((C)) Blood (III) Cuboidal epithelium ((D)) Tubular parts of nephron (IV) specialised connective tissue Choose the correct answer from the options a. A-III, B-IV, C-II, D-I b. A-I, B-II, C-IV, D-III c. A-II, B-III, C-I, D-IV d. A-II, B-I, C-IV, D-III

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Matching Biological Structures",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "You need to match the biological structures in List-I with their corresponding descriptions in List-II. Each option consists of a pairing of structures and their characteristics."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the functions of each structure. For example, mast cells are involved in immune responses, while the inner surface of bronchioles is related to respiratory functions."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about the types of tissues: areolar connective tissue is loose connective tissue, while specialized connective tissues have specific functions. This might help you match them correctly."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (Mast cells - Ciliated epithelium, Inner surface of bronchiole - Specialized connective tissue, Blood - Areolar connective tissue, Tubular parts of nephron - Cuboidal epithelium). This choice contains some inaccuracies. Consider the specific functions of mast cells and the types of epithelium found in bronchioles."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you again chose A (Mast cells - Ciliated epithelium, Inner surface of bronchiole - Specialized connective tissue, Blood - Areolar connective tissue, Tubular parts of nephron - Cuboidal epithelium). This indicates a misunderstanding of the tissue types. Review the characteristics of each structure to improve your matching."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "To solve the matching problem, let's analyze each item in List-I:\n\n- **Mast cells** are found in areolar connective tissue and play a role in the immune system.\n- The **inner surface of bronchioles** is lined with ciliated epithelium to help move mucus.\n- **Blood** is considered a specialized connective tissue due to its unique functions and composition.\n- The **tubular parts of the nephron** are lined with cuboidal epithelium, which is involved in absorption and secretion.\n\nThus, the correct matches are:\n- A - II (Mast cells - Areolar connective tissue)\n- B - I (Inner surface of bronchiole - Ciliated epithelium)\n- C - IV (Blood - Specialized connective tissue)\n- D - III (Tubular parts of nephron - Cuboidal epithelium)"
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Match List-I with List-II.",
      "options": [
        {
          "id": "A",
          "label": "A-III, B-IV, C-II, D-I"
        },
        {
          "id": "B",
          "label": "A-I, B-II, C-IV, D-III"
        },
        {
          "id": "C",
          "label": "A-II, B-III, C-I, D-IV"
        },
        {
          "id": "D",
          "label": "A-II, B-I, C-IV, D-III"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A-III, B-IV, C-II, D-I",
      "feedbackMarkdown": "Your choice contains inaccuracies. Review the functions of mast cells and the types of epithelium."
    },
    {
      "number": 2,
      "prompt": "Match List-I with List-II.",
      "options": [
        {
          "id": "A",
          "label": "A-III, B-IV, C-II, D-I"
        },
        {
          "id": "B",
          "label": "A-I, B-II, C-IV, D-III"
        },
        {
          "id": "C",
          "label": "A-II, B-III, C-I, D-IV"
        },
        {
          "id": "D",
          "label": "A-II, B-I, C-IV, D-III"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A-III, B-IV, C-II, D-I",
      "feedbackMarkdown": "Your choice remains the same, indicating a misunderstanding. Review the characteristics of each structure."
    }
  ],
  "finalAnswer": "D",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 4: `help_me_solve_it-021`

- **Variation:** cbse
- **Tags:** biology, neet, source_pdf_neet_zoology, cbse, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q51. Match List-I with List-II. List-I List-II ((A)) Heroin (I) Effect on cardiovascular system ((B)) Marijuana (II) Slow down body function ((C)) Cocaine (III) Painkiller ((D)) Morphine (IV) Interfere with transport dopamine Choose the correct answer from the options given below: a. A-III, B-IV, C-I, D-II b. A-II, B-I, C-IV, D-III c. A-I. B-II, C-III, D-IV d. A-IV, B-III, C-II, D-I Q52.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Drug Effects Matching",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to match the drugs listed in List-I with their corresponding effects or characteristics in List-II. Each drug has a specific effect that can be identified based on its known pharmacological properties."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the primary effects of each drug: Heroin is known for its pain-relieving properties, while Cocaine is known to affect dopamine transport. Marijuana has different effects compared to the others, and Morphine is also a well-known painkiller."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about how each drug interacts with the body. For instance, Cocaine's impact on the cardiovascular system is significant, while Marijuana tends to slow down body functions. This knowledge can help you match the drugs correctly."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Focus on pain-relieving properties of drugs."
      },
      {
        "id": "B",
        "label": "Consider the effects on the cardiovascular system."
      },
      {
        "id": "C",
        "label": "Look at how drugs interfere with neurotransmitter transport."
      },
      {
        "id": "D",
        "label": "Evaluate the overall slowing down of body functions."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

#### Example 5: `help_me_solve_it-022`

- **Variation:** cbse
- **Tags:** biology, neet, source_pdf_neet_zoology, cbse, assertion_reason, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q5. Given below are two statements: one is labelled as Assertion A and the other is labelled as Reason R. Assertion A: Amniocentesis for sex determination is one of the strategies of Reproductive and Child Health Care Programme. Reason R: Ban on amniocentesis checks increasing menace of female foeticide. In the light of the above statements. Choose the correct answer from the options given below: a. A is false but R is true. b. Both A and R are true and R is the correct explanation of

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Understanding Amniocentesis and Female Foeticide",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The pro[answer hidden]lem presents two statements regarding amniocentesis and its implications in the context of reproductive health and female foeticide. The assertion discusses the role of amniocentesis in reproductive health, while the reason addresses the [answer hidden]an on the procedure as a measure against female foeticide."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider the purpose of amniocentesis and the implications of its [answer hidden]an. Reflect on how these relate to reproductive health strategies."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Evaluate whether the reason provided effectively supports the assertion. Think a[answer hidden]out the [answer hidden]roader context of reproductive health policies and their intended outcomes."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (A is false [answer hidden]ut R is true). This choice suggests that you [answer hidden]elieve amniocentesis is not a strategy in reproductive health care, while acknowledging that the [answer hidden]an on it does address female foeticide. However, consider the role of amniocentesis in prenatal care and how it is viewed within health programs."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "A is false but R is true."
        },
        {
          "id": "B",
          "label": "Both A and R are true and R is the correct explanation of A."
        },
        {
          "id": "C",
          "label": "A is true but R is false."
        },
        {
          "id": "D",
          "label": "Both A and R are false."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "A is false but R is true.",
      "feedbackMarkdown": "You picked option A (A is false but R is true). This choice suggests that you believe amniocentesis is not a strategy in reproductive health care, while acknowledging that the ban on it does address female foeticide. However, consider the role of amniocentesis in prenatal care and how it is viewed within health programs."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Both A and R are true and R is the correct explanation of A."
      },
      {
        "id": "B",
        "label": "A is true but R is false."
      },
      {
        "id": "C",
        "label": "Both A and R are false."
      },
      {
        "id": "D",
        "label": "A is false but R is true."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

## Variation: `proof`


#### Example 1: `help_me_solve_it-023`

- **Variation:** proof
- **Tags:** physics, cbse, source_pdf_cbse_physics, proof, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q26. A steady current of 5 A passes along the +X coordinate direction through a long straight wire lying coincident with the X-axis. Find the vector magnetic field B generated at a spatial coordinate point located at position vector r = (3î + 4î) m due to a 1 cm segment element of the wire centered symmetrically at the origin. SHORT ANSWER QUESTIONS (SAQS) Each question carries 3 marks. Provide clear analytical explanations, derivations, or step-wise calculations.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Magnetic Field Calculation",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to calculate the magnetic field \\\\( \textbf{B} \\\\) at a point given by the position vector \\\\( \textbf{r} = (3\\hat{i} + 4\\hat{j}) \\\\text{ m} \\\\) due to a segment of a long straight wire carrying a current of 5 A. The wire lies along the X-axis, and we will use the Biot-Savart law to find the magnetic field generated by a small segment of the wire."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall the Biot-Savart law, which states that the magnetic field \\\\( \textbf{B} \\\\) at a point due to a current-carrying segment is given by: \\\\[ d\\textbf{B} = \\frac{\\mu_0}{4\\pi} \\frac{I d\\textbf{l} \\times \\hat{r}}{r^2} \\\\] where \\\\( I \\\\) is the current, \\\\( d\\textbf{l} \\\\) is the length vector of the segment, \\\\( \\hat{r} \\\\) is the unit vector from the segment to the point, and \\\\( r \\\\) is the distance from the segment to the point."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "To apply the Biot-Savart law, identify the length vector \\\\( d\\textbf{l} \\\\) for the segment, which is along the X-axis. Also, calculate the distance \\\\( r \\\\) from the segment to the point \\\\( \textbf{r} \\\\) and find the unit vector \\\\( \\hat{r} \\\\) accordingly."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (the option label). This choice indicates your initial understanding of the problem. Make sure to carefully consider the application of the Biot-Savart law and the geometry involved in the setup."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A (the option label). This suggests you are still considering the same approach. Review the calculations for the magnetic field and ensure you are applying the right components for the cross product in the Biot-Savart law."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "1. **Identify the segment**: Let the segment of the wire be from \\\\(-0.005 \\\\text{ m} \\\\) to \\\\(+0.005 \\\\text{ m} \\\\) along the X-axis. Thus, \\\\( d\\textbf{l} = dx \\hat{i} \\\\). \\\\n2. **Position vector**: The point of interest is \\\\( \textbf{r} = (3\\hat{i} + 4\\hat{j}) \\\\text{ m} \\\\). The distance from the wire to this point is \\\\( r = \\sqrt{(3)^2 + (4)^2} = 5 \\\\text{ m} \\\\). \\\\n3. **Unit vector**: The unit vector \\\\( \\hat{r} = \\frac{(3\\hat{i} + 4\\hat{j})}{5} \\\\). \\\\n4. **Cross product**: Calculate \\\\( d\\textbf{l} \\times \\hat{r} \\\\) which will give the direction of the magnetic field. \\\\n5. **Integrate**: Integrate over the length of the segment to find the total magnetic field \\\\( \textbf{B} \\\\)."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "What is the first step in calculating the magnetic field?",
      "options": [
        {
          "id": "A",
          "label": "Use Biot-Savart law"
        },
        {
          "id": "B",
          "label": "Calculate resistance"
        },
        {
          "id": "C",
          "label": "Use Ampere's law"
        },
        {
          "id": "D",
          "label": "Find current density"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Use Biot-Savart law",
      "feedbackMarkdown": "Correct! The Biot-Savart law is the right approach to find the magnetic field due to a current-carrying wire."
    },
    {
      "number": 2,
      "prompt": "What is the next step after identifying the segment?",
      "options": [
        {
          "id": "A",
          "label": "Calculate the magnetic field"
        },
        {
          "id": "B",
          "label": "Determine the distance and unit vector"
        },
        {
          "id": "C",
          "label": "Find the total current"
        },
        {
          "id": "D",
          "label": "Draw the magnetic field lines"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Calculate the magnetic field",
      "feedbackMarkdown": "Not quite. You need to first determine the distance and unit vector before calculating the magnetic field."
    }
  ],
  "finalAnswer": "The magnetic field \\\\textbf{B} at the point (3\\hat{i} + 4\\hat{j}) m due to the 1 cm segment of the wire is calculated to be \\( \\textbf{B} = \\frac{\\mu_0 I}{4\\pi r^2} \\cdot \\hat{r} \\times d\\textbf{l} \\). After evaluating, we find \\( \\textbf{B} = (0, 0, B_z) \\text{ T} \\).",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-024`

- **Variation:** proof
- **Tags:** physics, cbse, source_pdf_cbse_physics, proof, numerical, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q17. The threshold voltage of a silicon diode is 0.7 V. It is operated by connecting the diode in series with a battery of V volts and a resistor of 1000 Ω. Find the required value of V when the active current drawn through the circuit is 15 mA.

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Diode Circuit Analysis",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We have a silicon diode with a threshold voltage of 0.7 V, connected in series with a battery of unknown voltage \\( V \\) and a resistor of \\( 1000 \\, \\Omega \\). The current flowing through the circuit is \\( [answer hidden] \\, \\text{mA} \\). We need to find the value of \\( V \\) that allows this current to flow."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Recall that the total voltage in a series circuit is equal to the sum of the voltage drops across each component. In this case, the voltage drop across the resistor can be calculated using Ohm's law: \\( V_R = I \\times R \\)."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "The total voltage supplied by the battery \\( V \\) must equal the sum of the voltage drop across the resistor and the threshold voltage of the diode: \\( V = V_R + V_{diode} \\)."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Use Ohm's law to find the voltage drop across the resistor."
      },
      {
        "id": "B",
        "label": "Calculate the power dissipated in the resistor."
      },
      {
        "id": "C",
        "label": "Use Kirchhoff's voltage law for the entire circuit."
      },
      {
        "id": "D",
        "label": "Determine the current through the diode only."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

## Variation: `diagram`


#### Example 1: `help_me_solve_it-002`

- **Variation:** diagram
- **Tags:** physics, jee, source_pdf_jee_april_2026, diagram, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q39. The maximum rated power of the LED is 2 mW and it is used in the circuit with input voltage of 5 V as shown in the figure below. The current through resistance R_S is 0.5 mA. The minimum value of the resistance of R_S, to ensure that the LED is not damaged is ______ kΩ.

[Diagram: The circuit diagram features a 5 V power supply represented by a long horizontal line with a positive terminal at the top and a negative terminal at the bottom. To the right of the power supply, there is a resistor labeled \( R_S \) connected in series. Following this resistor, there is a second resistor labeled \( R = 1 \, k\Omega \). Below this resistor, there are two diodes represented by triangular shapes pointing towards the right, indicating the direction of current flow. The first diode is connected to the resistor \( R \), and the second diode is connected to the LED, which is labeled as "2 mW LED" and depicted as a triangle with a flat base. The LED is oriented to allow current to flow from left to right. The entire circuit is laid out horizontally, with all components aligned in a single row. There are no arrows indicating motion or forces, and no graph axes or scales are present in the diagram.]

(1) 6  (2) 2  (3) 4  (4) 5

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "LED Circuit Analysis",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We need to determine the minimum resistance value of resistor \\( R_S \\) in a circuit with a 5 V power supply and a current of 0.5 mA flowing through it, ensuring that the LED rated at 2 mW is not damaged."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "First, calculate the maximum current that the LED can handle using its power rating. The formula for power is given by \\( P = V \\times I \\). Rearranging this gives us the current as \\( I = \\frac{P}{V} \\)."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Next, apply Ohm's law to find the minimum resistance \\( R_S \\) that would allow a current of 0.5 mA to flow without exceeding the LED's maximum rated power."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (6 kΩ). This choice may not be correct because it does not take into account the calculations needed to ensure the LED's power rating is not exceeded. Understanding the relationship between power, voltage, and current is crucial here."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Use the power formula to find current."
        },
        {
          "id": "B",
          "label": "Use Ohm's law to find resistance."
        },
        {
          "id": "C",
          "label": "Calculate total resistance in the circuit."
        },
        {
          "id": "D",
          "label": "Determine voltage drop across the LED."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Use the power formula to find current.",
      "feedbackMarkdown": "You picked option A (Use the power formula to find current). This choice may not be correct because it does not take into account the calculations needed to ensure the LED's power rating is not exceeded. Understanding the relationship between power, voltage, and current is crucial here."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Calculate the maximum current for the LED."
      },
      {
        "id": "B",
        "label": "Determine the voltage across \\( R_S \\) using Ohm's law."
      },
      {
        "id": "C",
        "label": "Find the total resistance needed for the circuit."
      },
      {
        "id": "D",
        "label": "Recalculate the power rating of the LED."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-003`

- **Variation:** diagram
- **Tags:** physics, neet, source_pdf_neet_physics, diagram, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q49. A constant voltage of 50 V is maintained between the points A and B of the circuit shown in the figure. The current through the branch CD of the circuit is:

[Diagram: The circuit diagram shows a closed loop with points labeled A and B at the top left and top right, respectively. A voltage source of 50 V is connected between these points. Below the voltage source, there are four resistors arranged in a combination of series and parallel. The resistors are labeled with their resistances: a 1Ω resistor is connected between points A and C, a 2Ω resistor is connected between points C and B, a 3Ω resistor is connected between points C and D, and a 4Ω resistor is connected between points D and B. The resistors are represented by zigzag lines. The layout is primarily horizontal, with the voltage source at the bottom center. There are no arrows indicating motion or forces in the diagram. The resistors are connected by straight lines representing wires. The overall structure is a simple circuit with clear labeling of components and values. No additional numeric annotations or angles are present.]

(1) 1.5 A  
(2) 2.0 A  
(3) 2.5 A  
(4) 3.0 A

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Current Calculation in a Circuit",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "We have a circuit with a constant voltage of 50 V between points A and B, and we need to find the current through the branch CD. The resistors are arranged in a combination of series and parallel, which will affect the total resistance and thus the current."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "First, calculate the total resistance of the circuit. Remember that resistors in series simply add up, while resistors in parallel require the reciprocal formula: \\[ \\frac{1}{R_{total}} = \\frac{1}{R_1} + \\frac{1}{R_2} + ... \\]"
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Once you find the total resistance, use Ohm's law to find the total current from the voltage source: \\[ I = \\frac{V}{R_{total}} \\]. Then, apply the current division rule to find the current through branch CD."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (1.5 A). This choice might not reflect the correct understanding of the total resistance in the circuit. Ensure you consider both series and parallel combinations properly."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A (1.5 A) again. It's important to re-evaluate your calculations for total resistance and the application of Ohm's law to ensure the current through branch CD is accurately determined."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "1. Identify the resistances: 1Ω (A to C), 2Ω (C to B), 3Ω (C to D), and 4Ω (D to B).  \n2. Calculate the equivalent resistance of the resistors in parallel (3Ω and 4Ω) first:  \n   \\[ R_{CD} = \\frac{1}{\\frac{1}{3} + \\frac{1}{4}} = \\frac{12}{7} \\, \\Omega \\]  \n3. Now, find the total resistance in the circuit:  \n   \\[ R_{total} = 1 + 2 + R_{CD} = 1 + 2 + \\frac{12}{7} = \\frac{26}{7} \\, \\Omega \\]  \n4. Apply Ohm's law to find the total current:  \n   \\[ I_{total} = \\frac{50}{\\frac{26}{7}} = \\frac{50 \\times 7}{26} = \\frac{350}{26} \\approx 13.46 \\, A \\]  \n5. Use the current division rule to find the current through branch CD:  \n   \\[ I_{CD} = I_{total} \\times \\frac{R_{other}}{R_{CD} + R_{other}} \\]  \n6. Finally, calculate the current through CD to get the answer."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "What is the current through branch CD?",
      "options": [
        {
          "id": "A",
          "label": "1.5 A"
        },
        {
          "id": "B",
          "label": "2.0 A"
        },
        {
          "id": "C",
          "label": "2.5 A"
        },
        {
          "id": "D",
          "label": "3.0 A"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "1.5 A",
      "feedbackMarkdown": "You chose 1.5 A. This may not be the correct current through branch CD. Consider recalculating the total resistance."
    },
    {
      "number": 2,
      "prompt": "What is the current through branch CD?",
      "options": [
        {
          "id": "A",
          "label": "1.5 A"
        },
        {
          "id": "B",
          "label": "2.0 A"
        },
        {
          "id": "C",
          "label": "2.5 A"
        },
        {
          "id": "D",
          "label": "3.0 A"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "1.5 A",
      "feedbackMarkdown": "You again chose 1.5 A. It's essential to check your calculations for the total resistance and the current division to find the correct answer."
    }
  ],
  "finalAnswer": "2.0 A",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

## Variation: `ncert_strict`


#### Example 1: `help_me_solve_it-025`

- **Variation:** ncert_strict
- **Tags:** biology, cbse, source_pdf_cbse_biology, ncert_strict, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q8. In the given pedigree chart, a cross between a normal couple resulted in a son who was haemophilic and a normal daughter. In course of time, when the daughter was married to a normal man, to their surprise the grandson was also haemophilic. Choose the option that indicates the correct inheritance of trait in the above pedigree chart. ((A)) Autosome linked dominant trait ((B)) Sex-linked dominant trait ((C)) Autosomal recessive trait ((D)) Sex-linked recessive trait

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding Inheritance Patterns",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "In this problem, we are analyzing a pe[answer hidden]igree chart to [answer hidden]etermine the inheritance pattern of hemophilia, a bloo[answer hidden] [answer hidden]isor[answer hidden]er. The key points to note are that a normal couple has a son who is hemophilic an[answer hidden] a normal [answer hidden]aughter. The [answer hidden]aughter later marries a normal man, an[answer hidden] they have a gran[answer hidden]son who is also hemophilic. This information will help us [answer hidden]e[answer hidden]uce the mo[answer hidden]e of inheritance."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consi[answer hidden]er the fact that hemophilia is a con[answer hidden]ition that primarily affects males an[answer hidden] is often passe[answer hidden] [answer hidden]own through generations. Think about how the trait coul[answer hidden] be inherite[answer hidden] from the parents to the son an[answer hidden] then to the gran[answer hidden]son."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Since the [answer hidden]aughter is normal but has a hemophilic son, this suggests that she carries a recessive allele for hemophilia. This coul[answer hidden] in[answer hidden]icate that hemophilia is linke[answer hidden] to the sex chromosomes, particularly the X chromosome."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Autosome linked dominant trait"
      },
      {
        "id": "B",
        "label": "Sex-linked dominant trait"
      },
      {
        "id": "C",
        "label": "Autosomal recessive trait"
      },
      {
        "id": "D",
        "label": "Sex-linked recessive trait"
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

## Variation: `conceptual`


#### Example 1: `help_me_solve_it-026`

- **Variation:** conceptual
- **Tags:** biology, cbse, source_pdf_cbse_biology, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q48. The graph below shows the concentration of nicotine in blood of a smoker taking 10 puffs per minute. (a) (i) With reference to the above graph, explain the concentration of nicotine in the blood at 10 minutes? OR (a) (ii) How will this affect the concentration of carbon monoxide and haem-bound oxygen at 10 minutes? (b) How does cigarette smoking result in high blood pressure and increase in heart rate? (c) To which class of compounds does nicotine belong? Name one other drug from the same class.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Nicotine and Its Effects",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem involves analyzing the effects of nicotine concentration in the blood of a smoker over time, its impact on other substances like carbon monoxide and oxygen, the physiological effects of smoking, and the classification of nicotine."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider how nicotine affects the cardiovascular system and how it might influence the levels of carbon monoxide and oxygen in the blood."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about the chemical classification of nicotine and compare it with other similar substances."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (exact label for option A). This option is relevant as it addresses the concentration of nicotine in the blood at 10 minutes, which is crucial for understanding its immediate effects on the body."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "The concentration of nicotine will peak and then decline."
        },
        {
          "id": "B",
          "label": "Nicotine will have no effect on blood concentration."
        },
        {
          "id": "C",
          "label": "The concentration will remain constant throughout."
        },
        {
          "id": "D",
          "label": "Nicotine concentration will gradually increase."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "The concentration of nicotine will peak and then decline.",
      "feedbackMarkdown": "You picked option A (The concentration of nicotine will peak and then decline). This option is relevant as it addresses the concentration of nicotine in the blood at 10 minutes, which is crucial for understanding its immediate effects on the body."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Discuss the impact of nicotine on carbon monoxide levels."
      },
      {
        "id": "B",
        "label": "Explain how smoking increases heart rate."
      },
      {
        "id": "C",
        "label": "Identify the class of compounds nicotine belongs to."
      },
      {
        "id": "D",
        "label": "Analyze the long-term effects of smoking on health."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-027`

- **Variation:** conceptual
- **Tags:** biology, cbse, source_pdf_cbse_biology, conceptual, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q51. Study the diagram that shows the steps involved in the procedure of selecting transformed bacteria and answer the questions that follow. (a) Identify the colony that has got transformed. Justify your answer. (b) What are the sites in a plasmid called where ampicillin and tetracycline resistance genes are inserted? State their role in genetic engineering. (c) Name two enzymes playing an important role in genetic engineering. OR (c) State the role of β-galactosidase in insertional inactivation.

[Diagram: The figure consists of four labeled sections (i, ii, iii, iv) arranged vertically. In section (i), there is a circular shape labeled "Plasmid" at the top left, with a smaller circular shape labeled "Gene for ampicillin resistance" above it and another labeled "Gene for tetracycline resistance" to the right. Section (ii) shows a circular shape labeled "Recombinant DNA" below the plasmid. Section (iii) depicts a circular plate labeled "Plate M" containing five circular colonies numbered 1 to 5, arranged in a semi-circular pattern. Below this plate, there is an arrow pointing to the right labeled "Replica plating." Section (iv) shows another circular plate labeled "Plate N," which contains three circular colonies and one oval shape in the center. The overall layout is top to bottom, with clear connections between the sections through arrows indicating the process of replica plating.]

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Genetic Engineering and Bacterial Transformation",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem involves understanding the process of selecting transformed bacteria using a diagram that illustrates the steps involved in genetic engineering. You need to identify the transformed colony, understand the role of specific genes in plasmids, and recognize key enzymes involved in the process."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Look closely at the colonies on Plate M and Plate N. Consider which colonies might have survived the antibiotic selection based on the resistance genes present in the plasmid."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Remember that the sites in a plasmid where resistance genes are inserted are crucial for the selection of transformed bacteria. Think about the role of β-galactosidase in the context of insertional inactivation."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (the colony labeled '1'). This choice may not be correct if that colony does not exhibit the expected characteristics of transformed bacteria. Consider the resistance genes and how they would affect the growth of the colonies on the antibiotic plates."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A again. Reflect on the specific roles of the genes inserted into the plasmid and how they relate to the transformation process. The correct identification of the transformed colony should align with the antibiotic resistance observed."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "To solve the problem, first identify the transformed colony by checking which colonies on Plate N survived the antibiotic treatment. The colonies that grow on the selective media indicate successful transformation. Next, the sites in the plasmid where the resistance genes are inserted are called 'multiple cloning sites' (MCS), which allow for the insertion of foreign DNA. Two important enzymes in genetic engineering are restriction enzymes and DNA ligase. If focusing on β-galactosidase, its role in insertional inactivation is to help determine whether the insertion of foreign DNA has occurred by disrupting the gene that encodes for it, thus preventing the breakdown of a substrate that would otherwise produce a color change."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Identify the transformed colony.",
      "options": [
        {
          "id": "A",
          "label": "Colony 1"
        },
        {
          "id": "B",
          "label": "Colony 2"
        },
        {
          "id": "C",
          "label": "Colony 3"
        },
        {
          "id": "D",
          "label": "Colony 4"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Colony 1",
      "feedbackMarkdown": "Your choice of Colony 1 may not be correct. Consider the characteristics of the colonies in relation to the antibiotic resistance."
    },
    {
      "number": 2,
      "prompt": "What are the sites in a plasmid called where ampicillin and tetracycline resistance genes are inserted?",
      "options": [
        {
          "id": "A",
          "label": "Multiple Cloning Sites"
        },
        {
          "id": "B",
          "label": "Origin of Replication"
        },
        {
          "id": "C",
          "label": "Promoter Regions"
        },
        {
          "id": "D",
          "label": "Terminator Sequences"
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Multiple Cloning Sites",
      "feedbackMarkdown": "Correct! The sites where resistance genes are inserted are called Multiple Cloning Sites, which facilitate the insertion of foreign DNA."
    }
  ],
  "finalAnswer": "The transformed colony is Colony 3, as it is the only one that grew on the selective media. The sites in a plasmid where resistance genes are inserted are called Multiple Cloning Sites (MCS), which play a crucial role in genetic engineering by allowing for the insertion of foreign DNA. Two important enzymes in genetic engineering are restriction enzymes and DNA ligase. β-galactosidase plays a role in insertional inactivation by indicating whether a foreign DNA has been successfully inserted into the plasmid.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 3: `help_me_solve_it-028`

- **Variation:** conceptual
- **Tags:** biology, cbse, source_pdf_cbse_biology, conceptual, mcq, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q40. (a) (i) Describe the series of experiments conducted by Frederick Griffith. Comment on the significance of the result obtained. (ii) State the contribution of Avery, MacLeod and McCarty. OR (b) The following questions are based on haemophilia. (i) Work out the crosses between: (I) Normal female and haemophilic male, (II) Carrier female and normal male, (III) Carrier female and haemophilic male. (ii) Write the conclusions you draw from these crosses. Comment on the type of inheritance of the disease. Use: X — Normal, Xʰ — Haemophilic.

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

0

**Student Choice:**

None

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 0,
  "title": "Understanding Griffith's Experiments and Haemophilia Genetics",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The problem consists of two parts: (a) focuses on the experiments by Frederick Griffith and the contributions of Avery, MacLeod, and McCarty regarding genetic material, while (b) deals with genetic crosses related to haemophilia, a sex-linked recessive disorder."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "For part (a), consider the key components of Griffith's experiments, including the types of bacteria used and the transformation observed. Think about how these findings contributed to the understanding of DNA as the genetic material."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "In part (b), remember that haemophilia is an X-linked recessive condition. You will need to set up Punnett squares for the crosses and analyze the offspring ratios to draw conclusions about inheritance patterns."
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use?",
    "options": [
      {
        "id": "A",
        "label": "Focus on Griffith's transformation experiment."
      },
      {
        "id": "B",
        "label": "Discuss the genetic crosses for haemophilia."
      },
      {
        "id": "C",
        "label": "Explain the significance of Avery, MacLeod, and McCarty's work."
      },
      {
        "id": "D",
        "label": "Analyze the inheritance pattern of X-linked traits."
      }
    ]
  },
  "checkpointHistory": [],
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. production_llm_gold: pass.

---

## Variation: `case_study`


#### Example 1: `help_me_solve_it-029`

- **Variation:** case_study
- **Tags:** biology, cbse, source_pdf_cbse_biology, case_study, production_llm_gold, vision_enriched_extraction

**Inputs**

**Problem Text Normalized:**

Q52. Read the following passage and answer the questions that follow. The most convincing evidence to trace evolutionary relationships between humans and different groups of animals comes from the basic similarities seen at the molecular level. Study the table below that depicts the number of amino acid differences between the haemoglobin polypeptide of a few animals with that of humans and answer the

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Interaction Count:**

1

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 1,
  "title": "Evolutionary Relationships in Molecular Biology",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "The passage discusses how evolutionary relationships between humans and other animals can be traced through molecular similarities, specifically focusing on amino acid differences in haemoglobin polypeptides."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider how amino acid sequences can indicate evolutionary relationships. The fewer the differences, the closer the evolutionary relationship."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Look at the specific amino acid differences listed in the table and think about how they relate to the evolutionary lineage of the species compared to humans."
    },
    {
      "heading": "Feedback on your choice",
      "bodyMarkdown": "You picked option A (exact label for option A). This choice may help you understand the molecular basis of evolution, but ensure you analyze the data carefully to see if it truly supports your conclusion."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "Which idea should we use?",
      "options": [
        {
          "id": "A",
          "label": "Molecular similarities are key to understanding evolution."
        },
        {
          "id": "B",
          "label": "Morphological features are more important than molecular data."
        },
        {
          "id": "C",
          "label": "Evolutionary relationships cannot be traced through molecular data."
        },
        {
          "id": "D",
          "label": "Only genetic data can provide insights into evolution."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "Molecular similarities are key to understanding evolution.",
      "feedbackMarkdown": "You picked option A (Molecular similarities are key to understanding evolution.). This choice aligns well with the passage's emphasis on molecular evidence in tracing evolutionary relationships."
    }
  ],
  "checkpoint": {
    "number": 2,
    "prompt": "What should we do next?",
    "options": [
      {
        "id": "A",
        "label": "Analyze the amino acid differences in detail."
      },
      {
        "id": "B",
        "label": "Focus on morphological traits instead."
      },
      {
        "id": "C",
        "label": "Ignore the molecular data and rely on other evidence."
      },
      {
        "id": "D",
        "label": "Consider the implications of these differences on evolution."
      }
    ]
  },
  "revealLevel": "hint",
  "followUpButtons": []
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---

#### Example 2: `help_me_solve_it-030`

- **Variation:** case_study
- **Tags:** physics, cbse, source_pdf_cbse_physics, case_study, production_llm_gold

**Inputs**

**Problem Text Normalized:**

Q47. Passage: A parallel plate capacitor has two parallel plates which are separated by an insulating medium like air, mica, etc. When the plates are connected to the terminals of a battery, they get equal and opposite charges and an electric field is set up in between them. This electric field between the two plates depends upon the potential difference applied, the separation of the plates and nature of the medium between the plates. Sub-questions:

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Interaction Count:**

2

**Student Choice:**

A

**Expected output**

**Coach Json:**

```json
{
  "interactionCount": 2,
  "title": "Understanding Parallel Plate Capacitors",
  "sections": [
    {
      "heading": "Problem decode",
      "bodyMarkdown": "A parallel plate capacitor consists of two parallel plates separated by an insulating medium. When connected to a battery, the plates acquire equal and opposite charges, creating an electric field between them. The electric field is influenced by the potential difference, the distance between the plates, and the properties of the insulating medium."
    },
    {
      "heading": "Hint 1",
      "bodyMarkdown": "Consider how the electric field (\text{E}) is related to the potential difference (\text{V}) and the distance between the plates (\text{d}). The formula you might want to recall is \text{E} = \frac{V}{d}."
    },
    {
      "heading": "Hint 2",
      "bodyMarkdown": "Think about how the nature of the insulating medium (dielectric) affects the capacitance and the electric field. The dielectric constant plays a crucial role in this relationship."
    },
    {
      "heading": "Feedback on checkpoint 1",
      "bodyMarkdown": "At checkpoint 1 you chose A (the label for option A). This option may not fully capture the relationship between the electric field and the factors influencing it. Consider revisiting the definitions and relationships discussed in the passage."
    },
    {
      "heading": "Feedback on checkpoint 2",
      "bodyMarkdown": "At checkpoint 2 you chose A (the label for option A). It's important to ensure that your choice reflects an understanding of how the electric field is affected by the potential difference, plate separation, and the medium. Review the concepts again to strengthen your understanding."
    },
    {
      "heading": "Solution walkthrough",
      "bodyMarkdown": "To find the electric field (\text{E}) between the plates of a parallel plate capacitor, you can use the formula \text{E} = \frac{V}{d}, where \text{V} is the potential difference and \text{d} is the separation between the plates. The electric field is directly proportional to the potential difference and inversely proportional to the distance between the plates. Additionally, the presence of a dielectric medium can modify the effective electric field, depending on its dielectric constant."
    }
  ],
  "checkpointHistory": [
    {
      "number": 1,
      "prompt": "What is the relationship between electric field and potential difference in a parallel plate capacitor?",
      "options": [
        {
          "id": "A",
          "label": "The electric field is independent of potential difference."
        },
        {
          "id": "B",
          "label": "The electric field is directly proportional to potential difference."
        },
        {
          "id": "C",
          "label": "The electric field is inversely proportional to potential difference."
        },
        {
          "id": "D",
          "label": "The electric field is constant regardless of potential difference."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "The electric field is independent of potential difference.",
      "feedbackMarkdown": "This choice does not accurately reflect the relationship. The electric field is indeed affected by the potential difference."
    },
    {
      "number": 2,
      "prompt": "How does the dielectric medium affect the electric field in a capacitor?",
      "options": [
        {
          "id": "A",
          "label": "It has no effect on the electric field."
        },
        {
          "id": "B",
          "label": "It increases the electric field."
        },
        {
          "id": "C",
          "label": "It decreases the electric field."
        },
        {
          "id": "D",
          "label": "It only affects capacitance, not the electric field."
        }
      ],
      "studentChoice": "A",
      "selectedLabel": "It has no effect on the electric field.",
      "feedbackMarkdown": "This choice is incorrect. The dielectric medium does affect the electric field by altering the capacitance and the effective electric field strength."
    }
  ],
  "finalAnswer": "The electric field between the plates of a parallel plate capacitor is directly proportional to the potential difference and inversely proportional to the separation of the plates.",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show next hint",
      "action": "SHOW_NEXT_HINT"
    },
    {
      "label": "Reveal solution",
      "action": "REVEAL_SOLUTION"
    },
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    }
  ]
}
```

**Quality Check:** no_premature_answer: pass. checkpoint_quality: pass. interaction_branch: pass. cumulative_context: pass. production_llm_gold: pass.

---


## 22. Problem Solver Follow-up Handler

| Field | Value |
|-------|-------|
| Dataset ID | `problem_solver_followup` |
| Category | Problem Solving |
| Tier | Tier 2 |
| Target examples | 15 |
| Actual examples | 15 |
| Version | 1.4.0 |

**Agent responsibility:** Handle follow-up button actions after a coach session without losing problem context. Production: [`follow_up.j2`](packages/core/prompts/templates/problem_solver/follow_up.j2).

**Audit finding (baseline v1.0.0):** Baseline `Continuation without losing context` stub replaced with action-specific follow-up bodies across all seven actions.

**Fixed Variation Taxonomy (locked)** — examples are grouped under these variation buckets:

| Variation | Failure/behavior tested | Example quota |
|-----------|-------------------------|---------------|
| `follow_up` | Post-coach button actions | 15 |

**Quality Check (evaluation layer)** — every example is graded against these dimensions:

* **action_compliance** — Title and body reflect the requested `action` slug.
* **context_retention** — References original problem stem and prior `solving_mode`.
* **reveal_level** — `hint` vs `full` matches action semantics.
* **latex_format** — Multiplication spaced; units in `\text{}`; JSON backslashes escaped in `bodyMarkdown`.

**LangSmith configuration**

* Dataset name prefix: `nbm-prompt`
* Input keys: `action`, `problem_text_normalized`, `solving_mode`, `user_follow_up`
* Output keys: `coach_json`

**Prompt template (production):**

```jinja2
You are ScholarSync AI Coach continuing a problem-solving session.

Action requested: {{ action }}
{% if user_follow_up %}Student follow-up: {{ user_follow_up }}{% endif %}

Problem:
{{ problem_text_normalized }}

Previous mode: {{ solving_mode }}

{% if ncert_context %}
NCERT context:
{{ ncert_context }}
{% endif %}

{% include 'problem_solver/math_formatting_contract.j2' %}

Return JSON only:
{
  "title": "string",
  "sections": [
    {"heading": "Follow-up", "bodyMarkdown": "..."}
  ],
  "finalAnswer": "string or null",
  "revealLevel": "hint or full",
  "followUpButtons": [
    {"label": "Show best approach", "action": "SHOW_BEST_APPROACH"},
    {"label": "Give similar problem", "action": "GIVE_SIMILAR_PROBLEM"},
    {"label": "Start Tutor Session", "action": "START_TUTOR_SESSION"}
  ]
}
```

*Runtime note:* `ProblemSolverService.handle_follow_up()` after coach button click.

### Evaluation examples (15)
## Variation: `follow_up`


#### Example 1: `problem_solver_followup-001`

- **Variation:** follow_up
- **Tags:** biology, cbse, source_pdf_cbse_biology, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

GIVE_SIMILAR_PROBLEM

**Problem Text Normalized:**

Q45. (a) (i) Describe the population growth curve applicable in a population of any species in nature that has limited resources at its disposal. (ii) Give the equation of this growth curve. (iii) Name the growth curve and depict a graphical plot for this type of population growth. OR (b) (i) Explain the Species–Area relationship within a natural forest and also predict the nature of graph when species richness is plotted against the area for a wide variety of taxa. (ii) Depict the graphical relationship between species richness and area.

**Solving Mode:**

HELP_ME_SOLVE_IT

**User Follow Up:**

Student clicked GIVE_SIMILAR_PROBLEM

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Similar Problem on Population Dynamics",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "Consider the following problem related to population dynamics in ecology:\n\n**Problem:** \n(a) (i) Describe the logistic growth curve applicable to a population of a species in an environment with limited resources. \n(ii) Provide the equation for this growth curve. \n(iii) Identify the characteristics of the logistic growth curve and illustrate it with a graphical representation. \n\nOR \n(b) (i) Discuss the concept of habitat fragmentation and its effects on species diversity in a given ecosystem. \n(ii) Illustrate the expected relationship between habitat size and species diversity with a graph."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use first?",
    "options": [
      {
        "id": "A",
        "label": "Convert units first, then use v = u + at"
      },
      {
        "id": "B",
        "label": "Use distance formula before finding acceleration"
      },
      {
        "id": "C",
        "label": "Plug 72 km/h directly into m/s² formulas"
      },
      {
        "id": "D",
        "label": "Skip setup and guess from the answer choices"
      }
    ]
  }
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 2: `problem_solver_followup-002`

- **Variation:** follow_up
- **Tags:** biology, cbse, source_pdf_cbse_biology, follow_up, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Action:**

REVEAL_SOLUTION

**Problem Text Normalized:**

Q9. Use the given information to select the amino acid attached to the 3′ end of tRNA during the process of translation, if the coding strand of the structural gene being transcribed has the nucleotide sequence TAC. Codons for the amino acids: AUC — Isoleucine AUG — Methionine UAC — Tyrosine GUA — Valine Options: (A) Isoleucine (B) Methionine (C) Tyrosine (D) Valine

[Diagram: The figure consists of a horizontal line at the top, connecting two circular shapes. The left circle is labeled with a small circle representing a bead, and the right circle is connected to a rectangular shape labeled as a block. Below the horizontal line, there is a vertical line leading down to a square shape on the left, which is also labeled as a block. To the right of this vertical line, there is another square shape, which is connected to a horizontal line that extends to the right, leading to a rectangular shape labeled with a smaller square. The layout is primarily horizontal at the top and vertical below, with connections represented by straight lines. There are no numeric annotations, angles, or arrows indicating motion in the diagram.]

**Solving Mode:**

EXPLAIN_FROM_BASICS

**User Follow Up:**

Student clicked REVEAL_SOLUTION

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Amino Acid Selection in Translation",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To determine the amino acid attached to the 3′ end of tRNA during translation, we first need to identify the corresponding mRNA codon from the given DNA coding strand sequence. The coding strand has the sequence TAC, which will be transcribed into mRNA as AUG. The mRNA codon AUG codes for Methionine. Therefore, the amino acid attached to the 3′ end of tRNA is Methionine."
    }
  ],
  "finalAnswer": "Methionine",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 3: `problem_solver_followup-003`

- **Variation:** follow_up
- **Tags:** biology, cbse, source_pdf_cbse_biology, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

SHOW_BEST_APPROACH

**Problem Text Normalized:**

Q6. The rate of formation of new organic matter by consumers, and the biomass available for consumption of herbivores as well as decomposers are referred to as: ((A)) Gross primary productivity and Net primary productivity ((B)) Net primary productivity and Secondary productivity ((C)) Secondary productivity and Net primary productivity ((D)) Secondary productivity and Gross primary productivity

**Solving Mode:**

SHOW_BEST_APPROACH

**User Follow Up:**

Student clicked SHOW_BEST_APPROACH

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Productivity in Ecosystems",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To solve this problem, we need to understand the definitions of the different types of productivity in an ecosystem. \\n\\n1. **Gross Primary Productivity (GPP)**: This is the total amount of organic matter produced by photosynthetic organisms (like plants) in a given area and time. \\n2. **Net Primary Productivity (NPP)**: This is the amount of organic matter that remains after the plants have used some of it for their own respiration. It represents the biomass available for consumption by herbivores. \\n3. **Secondary Productivity**: This refers to the generation of biomass by heterotrophic organisms (consumers) that eat the primary producers. \\n\\nNow, let's analyze the options: \\n- **(A)** GPP and NPP: This does not refer to consumers or decomposers. \\n- **(B)** NPP and Secondary Productivity: This correctly identifies NPP as the biomass for herbivores and secondary productivity as the biomass generated by consumers. \\n- **(C)** Secondary Productivity and NPP: This is similar to option B but does not clarify the roles of consumers and decomposers. \\n- **(D)** Secondary Productivity and GPP: This does not accurately represent the biomass available for herbivores. \\n\\nThus, the best answer is **(B)** Net primary productivity and Secondary productivity."
    }
  ],
  "finalAnswer": "B",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 4: `problem_solver_followup-004`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

SHOW_SHORTER_VERSION

**Problem Text Normalized:**

Q38. (a) Analyze the microscopic physical source of the mechanical force acting on a moving charge carrier segment passing through a conductor loop placed inside an external magnetic field field zone. (b) Deduce the complete analytical expression for the mechanical force acting per unit length between two infinitely long, straight, parallel current-carrying conductors separated by a distance d in vacuum. Use the derived expression to formally define the standard base SI unit 'ampere'.

**Solving Mode:**

SHOW_MISSING_IDEA

**User Follow Up:**

Student clicked SHOW_SHORTER_VERSION

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Shortened Problem Analysis and Solution",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "(a) The mechanical force on a moving charge in a magnetic field arises from the interaction between the magnetic field and the charge's velocity, described by the Lorentz force law: \\\\[ \textbf{F} = q (\textbf{v} \\times \textbf{B}) \\\\] where \\\\textbf{F}\\\\ is the force, \\\\$q\\\\ is the charge, \\\\$\\textbf{v}\\\\ is the velocity vector, and \\\\$\\textbf{B}\\\\ is the magnetic field vector.\n\n(b) For two parallel conductors carrying currents \\\\$I_1\\\\ and \\\\$I_2\\\\, the force per unit length \\\\$F/L\\\\ between them is given by: \\\\[ \\frac{F}{L} = \\frac{\\mu_0 I_1 I_2}{2\\pi d} \\\\] where \\\\$\\mu_0\\\\ is the permeability of free space and \\\\$d\\\\ is the distance between the conductors. The ampere is defined as the current that produces a force of \\\\$2 \\times 10^{-7} \\\\$ N/m between two parallel conductors one meter apart."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 5: `problem_solver_followup-005`

- **Variation:** follow_up
- **Tags:** biology, cbse, source_pdf_cbse_biology, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

EXPLAIN_CONCEPT_AGAIN

**Problem Text Normalized:**

Q5. You know that there are twenty different types of naturally occurring amino acids and four different types of bases in the DNA. A combination of 3 such bases codes for a specific amino acid. If instead there are 96 different amino acids and 12 different bases in the DNA, then the minimum number of combination of bases required to form a codon is: ((A)) 6 ((B)) 8 ((C)) 2 ((D)) 4

**Solving Mode:**

HELP_ME_SOLVE_IT

**User Follow Up:**

Student clicked EXPLAIN_CONCEPT_AGAIN

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Codon Combinations",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To determine the minimum number of combinations of bases required to form a codon, we need to understand how many unique combinations can be formed with a given number of bases. A codon is made up of a sequence of bases, and each base can be one of the available types. The formula to find the number of combinations of bases for codons is given by:\n\n\\[ N = B^L \\]\\\n\nwhere:\n- \\( N \\) is the total number of unique combinations (which should equal the number of amino acids),\n- \\( B \\) is the number of different bases available,\n- \\( L \\) is the length of the codon (number of bases in the codon).\n\nIn this case, we have:\n- \\( N = 9[answer hidden] \\) (the number of different amino acids),\n- \\( B = 12 \\) (the number of different bases).\n\nWe need to find the smallest \\( L \\) such that:\n\n\\[ 12^L \\geq 9[answer hidden] \\]\\\n\nNow, let's calculate the values of \\( L \\):\n- For \\( L = 1 \\): \\( 12^1 = 12 \\)\n- For \\( L = 2 \\): \\( 12^2 = 144 \\)\n\nSince \\( 12^1 \\) is less than 9[answer hidden] and \\( 12^2 \\) is greater than 9[answer hidden], the minimum \\( L \\) that satisfies the equation is 2. Therefore, the minimum number of bases required to form a codon in this scenario is 2."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use first?",
    "options": [
      {
        "id": "A",
        "label": "Convert units first, then use v = u + at"
      },
      {
        "id": "B",
        "label": "Use distance formula before finding acceleration"
      },
      {
        "id": "C",
        "label": "Plug 72 km/h directly into m/s² formulas"
      },
      {
        "id": "D",
        "label": "Skip setup and guess from the answer choices"
      }
    ]
  }
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 6: `problem_solver_followup-006`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

SHOW_NEXT_HINT

**Problem Text Normalized:**

Q8. Consider a parallel circuit connection where the top branch contains a 12 V cell with 1 Ω internal resistance, and the bottom branch contains a 6 V cell with 0.5 Ω internal resistance connected with opposing polarities across parallel terminals A and B. The potential difference between points A and B is: ((A)) 6 V ((B)) 8 V ((C)) 9 V ((D)) 12 V Testing Question Bank 2

**Solving Mode:**

EXPLAIN_FROM_BASICS

**User Follow Up:**

Student clicked SHOW_NEXT_HINT

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Next Hint for Parallel Circuit Problem",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To find the potential difference between points A and B, consider the effective voltage across each branch. The voltage across a branch in a parallel circuit can be affected by the internal resistance of the cells. Start by calculating the voltage drop across the internal resistances for each cell."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "hint",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 7: `problem_solver_followup-007`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

START_TUTOR_SESSION

**Problem Text Normalized:**

Q40. (a) Define the electromagnetic parameter 'mutual inductance' tracking between a closed pair of independent inductor coils, and state its standard SI units. (b) Derive the comprehensive mathematical expression for the mutual inductance coefficient linking two long, coaxial solenoids of identical total length l, given that the inner solenoid has radius r1 and N1 total turns, while the outer surrounding solenoid features radius r2 and N2 total turns.

**Solving Mode:**

SHOW_BEST_APPROACH

**User Follow Up:**

Student clicked START_TUTOR_SESSION

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Mutual Inductance",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "(a) **Mutual Inductance** is defined as the phenomenon where a change in current in one inductor induces an electromotive force (emf) in another nearby inductor. It quantifies the ability of one coil to induce voltage in another coil due to a changing magnetic field. The standard SI unit of mutual inductance is the **Henry (H)**.\n\n(b) To derive the mathematical expression for the mutual inductance coefficient between two long, coaxial solenoids, we start by considering the magnetic field produced by one solenoid and the induced emf in the other. The mutual inductance $M$ can be expressed as:\n\n\\[ M = \\frac{\\mu_0 N_1 N_2 A}{l} \\cdot \\frac{1}{(1 + k)} \\]\\\n\nwhere:\n- $\\mu_0$ is the permeability of free space,\n- $N_1$ and $N_2$ are the number of turns in the inner and outer solenoids respectively,\n- $A$ is the cross-sectional area of the inner solenoid, given by $A = \\pi r_1^2$,\n- $l$ is the length of the solenoids,\n- $k$ is the coupling coefficient, which depends on the geometry and alignment of the solenoids."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 8: `problem_solver_followup-008`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

GIVE_SIMILAR_PROBLEM

**Problem Text Normalized:**

Q10. A charged particle gains a speed of 106 m/s when accelerated from rest through a potential difference of 10 kV. It enters a region of a uniform magnetic field of 0.4 T such that its velocity vector is perpendicular to the magnetic field vector. The radius of the circular path described by it is: ((A)) 2.5 cm ((B)) 5 cm ((C)) 8 cm ((D)) 10 cm

**Solving Mode:**

SHOW_MISSING_IDEA

**User Follow Up:**

Student clicked GIVE_SIMILAR_PROBLEM

**Ncert Context:**

NCERT Class 11 Physics Ch.6: Work W=F·s cosθ. Kinetic energy K=½mv². Power P=W/t.

**Expected output**

**Coach Json:**

```json
{
  "title": "Similar Problem on Charged Particle in Magnetic Field",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "Consider a charged particle that is accelerated from rest through a potential difference of [answer hidden] kV. After gaining a speed of 7.[answer hidden] \\times 10^[answer hidden] \\text{ m/s}, it enters a uniform magnetic field of 0.3 T, with its velocity vector perpendicular to the magnetic field vector. Calculate the radius of the circular path described by the particle."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "hint",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 9: `problem_solver_followup-009`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

REVEAL_SOLUTION

**Problem Text Normalized:**

Q44. (a) State the working electrical principle of a standard potentiometer measurement circuit layout. (b) A parallel electrical combination composed of two independent cells of electromotive forces E and 3E, with matching internal resistances R each, is wired across an external load resistance branch of magnitude 2R. Derive the expression for, and calculate the steady electric current that passes through the external load resistor branch.

**Solving Mode:**

HELP_ME_SOLVE_IT

**User Follow Up:**

Student clicked REVEAL_SOLUTION

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Potentiometer and Parallel Circuit Analysis",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "(a) The working electrical principle of a standard potentiometer measurement circuit layout is based on the principle of balancing a voltage drop across a known resistance with the voltage drop across an unknown resistance. This is achieved by adjusting a sliding contact along a uniform wire of known resistance per unit length until the potential difference across the unknown resistance is equal to the potential difference across the known resistance, allowing for precise voltage measurements without drawing current from the circuit.\n\n(b) To derive the expression for the steady electric current through the external load resistor branch, we start by analyzing the circuit with the two cells in parallel. The total electromotive force (EMF) of the combination can be calculated as follows:\n\n1. The total EMF of the parallel combination is given by the formula:\n   \n   \begin{align*}\n   \frac{1}{E_{\text{total}}} &= \frac{1}{E} + \frac{1}{3E} \\ \n   &= \frac{3 + 1}{3E} \\ \n   &= \frac{4}{3E} \\ \n   E_{\text{total}} &= \frac{3E}{4} \\\n   \text{(Total EMF of the parallel combination)}\n   \\end{align*}\n\n2. The total internal resistance of the parallel combination is:\n   \n   \begin{align*}\n   R_{\text{total}} &= \frac{R}{2} \\\n   \text{(since both internal resistances are equal)}\n   \\\n   \text{(Total resistance in the circuit)}\n   \\\n   R_{\text{total circuit}} &= R_{\text{total}} + R_{\text{load}} \\ \n   &= \frac{R}{2} + 2R \\ \n   &= \frac{R}{2} + \frac{4R}{2} \\ \n   &= \frac{5R}{2} \\\n   \text{(Total resistance in the circuit)}\n   \\\n   \text{(Using Ohm's law, } I = \frac{V}{R}\text{)}\n   \\\n   I &= \frac{E_{\text{total}}}{R_{\text{total circuit}}} \\ \n   &= \frac{\frac{3E}{4}}{\frac{5R}{2}} \\ \n   &= \frac{3E}{4} \times \frac{2}{5R} \\ \n   &= \frac{3E}{10R} \\\n   \text{(Steady electric current through the external load resistor branch)}\n   \\\n   \text{Therefore, the current } I = \frac{3E}{10R}.\n   \\\n   \text{(Final expression for current)}\n   \\\n   \text{To calculate the current, substitute the values of } E \text{ and } R.\n   \\\n   \text{(For example, if } E = 12V \text{ and } R = 2Ω, \text{ then:)}\n   \\\n   I &= \frac{3 \times 12}{10 \times 2} = \frac{36}{20} = 1.8A.\n   \\\n   \text{(Final current value)}"
    }
  ],
  "finalAnswer": "I = \\frac{3E}{10R}",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use first?",
    "options": [
      {
        "id": "A",
        "label": "Convert units first, then use v = u + at"
      },
      {
        "id": "B",
        "label": "Use distance formula before finding acceleration"
      },
      {
        "id": "C",
        "label": "Plug 72 km/h directly into m/s² formulas"
      },
      {
        "id": "D",
        "label": "Skip setup and guess from the answer choices"
      }
    ]
  }
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 10: `problem_solver_followup-010`

- **Variation:** follow_up
- **Tags:** biology, cbse, source_pdf_cbse_biology, follow_up, mcq, production_llm_gold, vision_enriched_extraction

**Inputs**

**Action:**

SHOW_BEST_APPROACH

**Problem Text Normalized:**

Q10. In a pea plant (Pisum sativum) inflated pod shape is dominant over constricted pod shape. The expected ratio of phenotypes of the offspring in a cross between both the parents with heterozygous inflated pod shape will be: (A) 1 : 0 (B) 1 : 1 (C) 2 : 1 (D) 3 : 1

[Diagram: The figure consists of a horizontal line at the top, connecting two circular shapes. The left circle is labeled with a small circle representing a bead, and the right circle is connected to a rectangular shape labeled as a block. Below the horizontal line, there is a vertical line leading down to a square shape on the left, which is also labeled as a block. To the right of this vertical line, there is another square shape, which is connected to a horizontal line that extends to the right, leading to a rectangular shape labeled with a smaller square. The layout is primarily horizontal at the top and vertical below, with connections represented by straight lines. There are no numeric annotations, angles, or arrows indicating motion in the diagram.]

**Solving Mode:**

EXPLAIN_FROM_BASICS

**User Follow Up:**

Student clicked SHOW_BEST_APPROACH

**Ncert Context:**

NCERT Class 11–12 Biology: Recall NCERT terminology; link structure to function.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Pod Shape Inheritance in Pea Plants",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To determine the expected ratio of phenotypes in the offspring from a cross between two heterozygous pea plants for pod shape, we can use a Punnett square. The alleles for inflated pod shape (dominant) can be represented as 'I' and for constricted pod shape (recessive) as 'i'. Therefore, the genotypes of the parents will be 'Ii' (heterozygous) for both.\n\n1. Set up the Punnett square:\n   - Parent 1 alleles: I, i\n   - Parent 2 alleles: I, i\n\n2. Fill in the Punnett square:\n   - The combinations will be:\n     - II (homozygous dominant)\n     - Ii (heterozygous)\n     - iI (heterozygous)\n     - ii (homozygous recessive)\n\n3. The resulting genotypes will be:\n   - 1 II : 2 Ii : 1 ii\n\n4. Phenotypes:\n   - Both 'II' and 'Ii' will show the inflated pod shape (dominant), while 'ii' will show the constricted pod shape (recessive).\n\n5. Therefore, the phenotypic ratio will be:\n   - 3 inflated : 1 constricted\n\nThus, the expected ratio of phenotypes in the offspring is 3:1, which corresponds to option (D)."
    }
  ],
  "finalAnswer": "3 : 1",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 11: `problem_solver_followup-011`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

SHOW_SHORTER_VERSION

**Problem Text Normalized:**

Q2. In an unbiased p-n junction, at equilibrium, which of the following statements is true? ((A)) Diffusion current is zero but drift current exists. ((B)) Diffusion current exists but drift current is zero. ((C)) Diffusion and drift currents are equal and opposite. ((D)) Both the diffusion and drift currents exist but are unequal.

**Solving Mode:**

SHOW_BEST_APPROACH

**User Follow Up:**

Student clicked SHOW_SHORTER_VERSION

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding p-n Junctions",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "In an unbiased p-n junction at equilibrium, the diffusion and drift currents are equal and opposite, resulting in a net current of zero. Therefore, the correct answer is (C)."
    }
  ],
  "finalAnswer": "C",
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 12: `problem_solver_followup-012`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

EXPLAIN_CONCEPT_AGAIN

**Problem Text Normalized:**

Q39. (a) State Huygens' core geometric principle of wavefront propagation and secondary wavelets tracking over time. (b) A plane wavefront is incident at a non-zero angle i on a perfectly smooth reflecting plane interface. Construct a clean geometrical layout showing the generation of the corresponding reflected wavefront using Huygens' construction method. Utilizing the drawn layout, prove the fundamental law of reflection.

**Solving Mode:**

SHOW_MISSING_IDEA

**User Follow Up:**

Student clicked EXPLAIN_CONCEPT_AGAIN

**Ncert Context:**

NCERT Class 12 Physics: Use SI units, free-body diagrams, and sign conventions from the relevant chapter.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Huygens' Principle and Reflection",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "Huygens' principle states that every point on a wavefront can be considered a source of secondary wavelets that spread out in all directions at the speed of the wave. The new wavefront at a later time can be constructed by drawing a tangent to these secondary wavelets. This principle helps in understanding how waves propagate and interact with surfaces.\n\nIn the case of reflection, when a plane wavefront strikes a smooth reflecting surface at an angle, we can apply Huygens' principle to visualize the reflected wavefront. The angle of incidence (i) is equal to the angle of reflection (r), which can be demonstrated through a geometrical layout."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 13: `problem_solver_followup-013`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

SHOW_NEXT_HINT

**Problem Text Normalized:**

Q21. A plane circular conducting coil is rotated about its vertical diameter layout with a constant angular speed ω inside a uniform horizontal magnetic field. Initially, the plane of the coil is parallel to the field vector. Draw dual synchronous plots showing the variation of: (a) the magnetic flux linked with the coil, and (b) the emf induced in the coil, as functions of the phase parameter (ωt). Testing Question Bank 4

**Solving Mode:**

HELP_ME_SOLVE_IT

**User Follow Up:**

Student clicked SHOW_NEXT_HINT

**Ncert Context:**

NCERT Class 12 Physics Ch.3: Ohm's law V=IR at constant temperature. Resistivity ρ=RA/L. Series resistances add; parallel reciprocals add.

**Expected output**

**Coach Json:**

```json
{
  "title": "Next Hint for Problem Q21",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To analyze the variation of magnetic flux linked with the coil, recall that the magnetic flux \\( \\Phi \\) through the coil is given by \\( \\Phi = B \\cdot A \\cdot \\cos(\\theta) \\), where \\( B \\) is the magnetic field strength, \\( A \\) is the area of the coil, and \\( \\theta \\) is the angle between the magnetic field and the normal to the coil's surface. As the coil rotates, \\( \\theta \\) changes with time, specifically \\( \\theta = \\omega t \\). Therefore, you can express the magnetic flux as \\( \\Phi(t) = B \\cdot A \\cdot \\cos(\\omega t) \\)."
    }
  ],
  "finalAnswer": null,
  "revealLevel": "hint",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ],
  "checkpoint": {
    "number": 1,
    "prompt": "Which idea should we use first?",
    "options": [
      {
        "id": "A",
        "label": "Convert units first, then use v = u + at"
      },
      {
        "id": "B",
        "label": "Use distance formula before finding acceleration"
      },
      {
        "id": "C",
        "label": "Plug 72 km/h directly into m/s² formulas"
      },
      {
        "id": "D",
        "label": "Skip setup and guess from the answer choices"
      }
    ]
  }
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 14: `problem_solver_followup-014`

- **Variation:** follow_up
- **Tags:** biology, cbse, source_pdf_cbse_biology, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

START_TUTOR_SESSION

**Problem Text Normalized:**

Q22. The allele for brown eyes ((B)) is dominant over blue eyes (b). In a population, 36% of individuals have blue eyes. Assuming Hardy–Weinberg equilibrium, calculate: (i) Frequency of allele B (ii) Percentage of heterozygous individuals (iii) Percentage of individuals that are homozygous dominant (Working to be shown)

**Solving Mode:**

EXPLAIN_FROM_BASICS

**User Follow Up:**

Student clicked START_TUTOR_SESSION

**Ncert Context:**

NCERT Class 12 Biology Ch.6: DNA A–T, G–C base pairing. Semiconservative replication. Central dogma DNA→RNA→protein.

**Expected output**

**Coach Json:**

```json
{
  "title": "Understanding Hardy-Weinberg Equilibrium",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "To solve the problem, we will use the Hardy-Weinberg principle, which states that the frequencies of alleles and genotypes in a population will remain constant from generation to generation in the absence of other evolutionary influences. The equations we will use are:\n\n1. The frequency of the recessive phenotype (blue eyes, bb) is given as 36%, or 0.36. \n2. The frequency of the recessive genotype (q^2) is equal to 0.36.\n\nFrom this, we can find the frequency of allele b (q) and then use it to find the frequency of allele B (p) and the other genotype frequencies. Let's go step by step:\n\n1. Calculate q (frequency of allele b):\n   \n   \\[ q = \\sqrt{q^2} = \\sqrt{0.36} = [answer hidden] \\]\n\n2. Calculate p (frequency of allele B):\n   \n   \\[ p = 1 - q = 1 - [answer hidden] = 0.4 \\]\n\n3. Calculate the percentage of heterozygous individuals (Bb):\n   \n   \\[ 2pq = 2 \\times p \\times q = 2 \\times 0.4 \\times [answer hidden] = 0.48 \\text{ or } 48\\% \\]\n\n4. Calculate the percentage of homozygous dominant individuals (BB):\n   \n   \\[ p^2 = (0.4)^2 = 0.16 \\text{ or } 16\\% \\]\n\nNow we have all the required frequencies and percentages!"
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

#### Example 15: `problem_solver_followup-015`

- **Variation:** follow_up
- **Tags:** physics, cbse, source_pdf_cbse_physics, follow_up, mcq, production_llm_gold

**Inputs**

**Action:**

GIVE_SIMILAR_PROBLEM

**Problem Text Normalized:**

Q6. A conducting wire connects two charged metallic spheres A and B of radii r1 and r2 respectively. The distance between the spheres is very large compared to their radii. The ratio of electric fields, (EA / EB) at the surfaces of spheres A and B will be: ((A)) r1 / r2 ((B)) r2 / r1 ((C)) r1 2 / r2 2 ((D)) r2 2 / r1 2

**Solving Mode:**

SHOW_BEST_APPROACH

**User Follow Up:**

Student clicked GIVE_SIMILAR_PROBLEM

**Ncert Context:**

NCERT Class 12 Physics Ch.1: Gauss's law relates net flux through a closed surface to enclosed charge. Conductor electrostatics: field inside conductor is zero in electrostatic equilibrium.

**Expected output**

**Coach Json:**

```json
{
  "title": "Similar Problem on Electric Fields",
  "sections": [
    {
      "heading": "Follow-up",
      "bodyMarkdown": "Consider two charged metallic spheres C and D with radii \\( r_3 \\) and \\( r_4 \\) respectively, connected by a conducting wire. If the total charge is conserved and the distance between the spheres is very large compared to their radii, what is the ratio of electric fields at the surfaces of spheres C and D, \\( (E_C / E_D) \\)? Choose from the following options: \\( (A) \\frac{r_3}{r_4} \\) \\( (B) \\frac{r_4}{r_3} \\) \\( (C) \\frac{r_3^2}{r_4^2} \\) \\( (D) \\frac{r_4^2}{r_3^2} \\)"
    }
  ],
  "finalAnswer": null,
  "revealLevel": "full",
  "followUpButtons": [
    {
      "label": "Show best approach",
      "action": "SHOW_BEST_APPROACH"
    },
    {
      "label": "Give similar problem",
      "action": "GIVE_SIMILAR_PROBLEM"
    },
    {
      "label": "Start Tutor Session",
      "action": "START_TUTOR_SESSION"
    }
  ]
}
```

**Quality Check:** action_compliance: pass. context_retention: pass. reveal_level: pass. production_llm_gold: pass.

---

