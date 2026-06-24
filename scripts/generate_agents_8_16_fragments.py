#!/usr/bin/env python3
"""Generate markdown fragments for Agents 8-16 evaluation datasets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agent_section_renderer import (
    ExampleRecord,
    example_block_v2,
    load_j2,
    render_agent_header,
    render_examples_grouped,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
COMPLETE_MD = ROOT / "Reference dataset" / "Complete_Agent_DataSet.md"

PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def md_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def uctx(ctx: str, ref: str = "") -> str:
    """Return context as-is (ref kept for call-site compatibility; not embedded in inputs)."""
    return (ctx or "").strip()


def example_block(
    ex_id: str,
    variation: str,
    tags: list[str],
    inputs: dict[str, str],
    outputs: dict[str, str],
    quality: list[str],
    extra_meta: str = "",
) -> str:
    """Legacy flat example block (studio generators still use during record build)."""
    num = int(ex_id.rsplit("-", 1)[-1])
    return example_block_v2(num, ex_id, variation, tags, inputs, outputs, quality, extra_meta)


def _record(
    ex_id: str,
    variation: str,
    tags: list[str],
    inputs: dict[str, str],
    outputs: dict[str, str],
    quality: list[str],
    extra_meta: str = "",
) -> ExampleRecord:
    return ExampleRecord(ex_id, variation, tags, inputs, outputs, quality, extra_meta)


def make_quiz(title: str, qs: list[dict]) -> str:
    return md_json({"title": title, "questions": qs})


def make_mcq(q: str, opts: list[str], correct: str, expl: str) -> dict:
    return {
        "question": q,
        "options": opts,
        "correct_answer": correct,
        "explanation": expl,
    }


def make_flashcards(cards: list[tuple[str, str]]) -> str:
    return md_json([{"front": f, "back": b} for f, b in cards])


# ---------------------------------------------------------------------------
# Agent 10 — Studio System JSON (10 examples)
# ---------------------------------------------------------------------------

def gen_agent10() -> str:
    system_prompt = load_j2(PROMPTS / "studio" / "system_educational_json_markdown.j2")
    header = render_agent_header(
        title="## 10. Studio System Prompt (JSON tasks)",
        metadata_rows=[
            ("Dataset ID", "`studio_system_json`"),
            ("Category", "Studio"),
            ("Tier", "Tier 3 baseline → focused enrichment set"),
            ("Target examples", "15"),
            ("Actual examples", "15"),
            ("Version", "1.1.0"),
        ],
        agent_responsibility=(
            "Shared **system prompt** (`studio/system_educational_json_markdown.j2`) prepended to all structured "
            "Studio tasks (quiz, flashcards, mind map, slide deck). Enforces **format discipline** — JSON-only when "
            "the task requests JSON, Markdown-only when the task requests Markdown. Does **not** generate pedagogical "
            "content alone; the paired **user/task template** supplies the task."
        ),
        audit_finding=(
            "The original 10-example set reused one task instruction across mismatched gold shapes (object vs array), "
            "abbreviated the system prompt to four bullet lines, and did not document the system-only eval role. "
            "Expanded to 15 examples with locked variation buckets, full inline production system prompt, and explicit "
            "format-discipline gold for array, object, markdown, empty, and thin-source cases."
        ),
        taxonomy_rows=[
            ("json_array", "Array of term/definition or formula objects", 4),
            ("json_object", "Nested object schema", 3),
            ("markdown_only", "No JSON fences", 3),
            ("empty_context", "Refusal / `[]` — no fabrication", 2),
            ("thin_source", "Minimum viable output from thin excerpt", 2),
            ("json_numeric_object", "Numeric/conic facts object", 1),
        ],
        quality_dimensions=[
            ("valid_json", "Output parses as JSON when task requests JSON; no trailing prose."),
            ("format_discipline", "Markdown-only tasks return no JSON; JSON tasks return no markdown fences."),
            ("schema_match", "Object vs array shape matches task_instruction keys and counts."),
            ("grounding", "Facts appear in context excerpt; no invented numbers or terms."),
            ("no_fences", "No ``` markdown code fences wrapping JSON output."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `context`, `task_instruction`",
            "Output keys: `json_output` (JSON tasks) or `markdown_output` (Markdown tasks)",
        ],
        prompt_blocks=[
            ("Prompt template (system — production)", "jinja2", system_prompt),
        ],
        runtime_note=(
            "Paired as **system** prompt in "
            "[`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) "
            "`StudioService._generate_structured_task()`. Agent 10 evals system format discipline **in isolation**; "
            "task templates are Agents 11–14."
        ),
        eval_count=15,
    )
    examples: list[ExampleRecord] = []

    # 1 JSON array
    ctx1 = "Ohm's law: V = IR. Resistivity ρ = RA/l. Series: R_eq = R1+R2. Parallel: 1/R_eq = 1/R1+1/R2. Kirchhoff's junction rule: sum of currents into a node equals sum leaving."
    out1 = md_json([
        {"term": "Ohm's law", "definition": "Potential difference V equals current I times resistance R (V = IR)."},
        {"term": "Resistivity", "definition": "Material property ρ related to resistance by ρ = RA/l."},
        {"term": "Kirchhoff's junction rule", "definition": "Sum of currents entering a junction equals sum leaving."},
    ])
    examples.append(_record(
        "studio_system_json-001", "json_array", ["cbse", "physics", "source_pdf:leph103"],
        {"context": uctx(ctx1, "studio_system_json-001"), "task_instruction": "Return a JSON array of exactly 3 objects, each with keys term and definition, using only the excerpt."},
        {"json_output": out1},
        ["valid_json: pass", "schema_match: pass", "grounding: pass", "no_fences: pass"],
        "- **source_pdf:** leph103.pdf",
    ))

    # 2 JSON object nested
    ctx2 = "Photosynthesis: light reaction in grana produces ATP and NADPH; Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata allow gas exchange."
    out2 = md_json({
        "process": "Photosynthesis",
        "stages": [
            {"name": "Light reaction", "location": "grana", "products": ["ATP", "NADPH"]},
            {"name": "Calvin cycle", "location": "stroma", "function": "CO2 fixation"},
        ],
        "key_structures": ["chlorophyll", "stomata"],
    })
    examples.append(_record(
        "studio_system_json-002", "json_object", ["cbse", "biology", "source_pdf:kebo110"],
        {"context": uctx(ctx2, "studio_system_json-002"), "task_instruction": "Return a JSON object with keys process, stages (array of objects with name, location, and products or function), and key_structures (array of strings). Excerpt only."},
        {"json_output": out2},
        ["valid_json: pass", "nested_schema: pass", "grounding: pass"],
        "- **source_pdf:** kebo110.pdf",
    ))

    # 3 Markdown-only
    ctx3 = "Lens formula: 1/f = 1/v - 1/u. Sign convention: distances measured from optical centre; u negative for real object."
    out3 = "## Lens formula (sign convention)\n\n- **Formula:** 1/f = 1/v − 1/u\n- **Origin:** Measure distances from the optical centre\n- **Real object:** Object distance u is taken as negative"
    examples.append(_record(
        "studio_system_json-003", "markdown_only", ["cbse", "physics", "source_pdf:leph201"],
        {"context": uctx(ctx3, "studio_system_json-003"), "task_instruction": "Return Markdown only (no JSON). Use a ## heading and bullet list summarizing the lens formula and sign convention from the excerpt."},
        {"markdown_output": out3},
        ["markdown_only: pass", "no_json: pass", "grounding: pass"],
        "- **source_pdf:** leph201.pdf",
    ))

    # 4 Empty context
    examples.append(_record(
        "studio_system_json-004", "empty_context", ["edge_case", "no_source"],
        {"context": "", "task_instruction": "Return a JSON array of key terms with definitions from the excerpt."},
        {"json_output": "[]"},
        ["empty_context: pass", "no_hallucination: pass", "valid_json: pass"],
    ))

    # 5 JSON formulas array
    ctx5 = "Work W = F·s cos θ. Kinetic energy K = ½mv². Power P = W/t. Work-energy theorem: net work equals change in kinetic energy."
    out5 = md_json([
        {"formula": "W = F·s cos θ", "quantity": "Work"},
        {"formula": "K = ½mv²", "quantity": "Kinetic energy"},
        {"formula": "P = W/t", "quantity": "Power"},
        {"formula": "W_net = ΔK", "quantity": "Work-energy theorem"},
    ])
    examples.append(_record(
        "studio_system_json-005", "json_array", ["cbse", "physics", "source_pdf:keph105"],
        {"context": uctx(ctx5, "studio_system_json-005"), "task_instruction": "Return a JSON array of 4 objects with keys formula and quantity extracted from the excerpt."},
        {"json_output": out5},
        ["count_match: pass", "grounding: pass"],
        "- **source_pdf:** keph105.pdf",
    ))

    # 6 Chemistry coordination
    ctx6 = "Coordination entity: central metal ion + ligands. Coordination number = number of σ-donor atoms bonded to metal. IUPAC: ligands named alphabetically; anionic ligands end in -o."
    out6 = md_json([
        {"term": "Coordination entity", "definition": "Central metal ion bonded to ligands in a complex."},
        {"term": "Coordination number", "definition": "Count of σ-donor atoms directly bonded to the metal."},
        {"term": "IUPAC ligand naming", "definition": "Ligands listed alphabetically; anionic ligands take -o suffix."},
    ])
    examples.append(_record(
        "studio_system_json-006", "json_array", ["cbse", "chemistry", "source_pdf:lech105"],
        {"context": uctx(ctx6, "studio_system_json-006"), "task_instruction": "Output JSON array of 3 {term, definition} pairs — valid JSON only, no markdown."},
        {"json_output": out6},
        ["grounding: pass", "valid_json: pass"],
        "- **source_pdf:** lech105.pdf",
    ))

    # 7 Math probability
    ctx7 = "P(E) = favourable outcomes / total outcomes. P(A∪B) = P(A)+P(B)−P(A∩B). For independent events P(A∩B) = P(A)P(B)."
    out7 = md_json({
        "topic": "Probability axioms",
        "rules": [
            {"rule": "Classical probability", "expression": "P(E) = n(E)/n(S)"},
            {"rule": "Addition theorem", "expression": "P(A∪B) = P(A)+P(B)−P(A∩B)"},
            {"rule": "Independent events", "expression": "P(A∩B) = P(A)P(B)"},
        ],
    })
    examples.append(_record(
        "studio_system_json-007", "json_object", ["cbse", "mathematics", "source_pdf:lemh207"],
        {"context": uctx(ctx7, "studio_system_json-007"), "task_instruction": "Return one JSON object with topic (string) and rules (array of {rule, expression}). No extra text."},
        {"json_output": out7},
        ["schema_match: pass", "grounding: pass"],
        "- **source_pdf:** lemh207.pdf",
    ))

    # 8 Biology inheritance
    ctx8 = "DNA double helix: antiparallel strands, A pairs T, G pairs C. Replication is semiconservative. mRNA carries genetic code to ribosomes for translation."
    out8 = md_json([
        {"term": "Base pairing", "definition": "Adenine with thymine; guanine with cytosine in DNA."},
        {"term": "Semiconservative replication", "definition": "Each new DNA duplex has one old and one new strand."},
        {"term": "Translation", "definition": "Ribosomes synthesize protein using mRNA template."},
    ])
    examples.append(_record(
        "studio_system_json-008", "json_array", ["neet", "biology", "source_pdf:lebo105"],
        {"context": uctx(ctx8, "studio_system_json-008"), "task_instruction": "JSON array of exactly 3 term/definition objects from excerpt. JSON only."},
        {"json_output": out8},
        ["grounding: pass", "count_match: pass"],
        "- **source_pdf:** lebo105.pdf",
    ))

    # 9 Electrochemistry markdown table style
    ctx9 = "Galvanic cell: anode oxidation, cathode reduction. EMF E°cell = E°cathode − E°anode. Nernst equation relates EMF to concentration."
    out9 = "## Galvanic cell essentials\n\n- **Anode:** site of oxidation\n- **Cathode:** site of reduction\n- **Standard EMF:** E°cell = E°cathode − E°anode\n- **Nernst equation:** links cell EMF to ion concentrations"
    examples.append(_record(
        "studio_system_json-009", "markdown_only", ["cbse", "chemistry", "source_pdf:lech103"],
        {"context": uctx(ctx9, "studio_system_json-009"), "task_instruction": "Produce Markdown summary with ## heading and bullets. Do NOT return JSON."},
        {"markdown_output": out9},
        ["format_discipline: pass", "grounding: pass"],
        "- **source_pdf:** lech103.pdf",
    ))

    # 10 Thin source minimum
    ctx10 = "Binomial theorem: (a+b)^n expansion uses nCr coefficients."
    out10 = md_json([{"term": "Binomial coefficient", "definition": "nCr counts combinations in (a+b)^n expansion."}])
    examples.append(_record(
        "studio_system_json-010", "thin_source", ["cbse", "mathematics", "source_pdf:kemh107"],
        {"context": uctx(ctx10, "studio_system_json-010"), "task_instruction": "Return JSON array with as many term/definition pairs as the thin excerpt supports (minimum 1). JSON only."},
        {"json_output": out10},
        ["thin_source_handling: pass", "valid_json: pass"],
        "- **source_pdf:** kemh107.pdf",
    ))

    # 11 JSON steps array (chemistry)
    ctx11 = "Electrolysis of molten NaCl: Na+ migrates to cathode, Cl− to anode. Faraday's first law: mass deposited proportional to charge passed."
    out11 = md_json([
        {"step": 1, "event": "Na+ ions move to cathode"},
        {"step": 2, "event": "Cl− ions move to anode"},
        {"step": 3, "rule": "Faraday's first law — mass ∝ charge"},
    ])
    examples.append(_record(
        "studio_system_json-011", "json_array", ["cbse", "chemistry", "source_pdf:lech103"],
        {"context": uctx(ctx11, "studio_system_json-011"), "task_instruction": "Return JSON array of step objects with step (number) and event or rule (string). Exactly 3 items. JSON only."},
        {"json_output": out11},
        ["valid_json: pass", "grounding: pass"],
        "- **source_pdf:** lech103.pdf",
    ))

    # 12 Markdown comparison table style
    ctx12 = "Mitosis: one division, 2n→2n, growth/repair. Meiosis: two divisions, 2n→n, gamete formation; crossing over in Prophase I."
    out12 = "## Mitosis vs Meiosis\n\n| Feature | Mitosis | Meiosis |\n|---------|---------|--------|\n| Divisions | One | Two |\n| Chromosome number | Maintained (2n) | Halved (n) |\n| Purpose | Growth/repair | Gametes |\n| Crossing over | Not typical | Prophase I |"
    examples.append(_record(
        "studio_system_json-012", "markdown_only", ["neet", "biology", "source_pdf:kebo110"],
        {"context": uctx(ctx12, "studio_system_json-012"), "task_instruction": "Return Markdown only: ## heading plus a comparison table of mitosis vs meiosis from excerpt. No JSON."},
        {"markdown_output": out12},
        ["markdown_only: pass", "grounding: pass"],
        "- **source_pdf:** kebo110.pdf",
    ))

    # 13 JSON Q&A pairs
    ctx13 = "Casparian strip in endodermis has suberin. It blocks apoplastic flow forcing symplastic uptake into stele."
    out13 = md_json([
        {"question": "Where is the Casparian strip?", "answer": "In the endodermis of roots."},
        {"question": "What does suberin do?", "answer": "Blocks apoplastic flow at the endodermis."},
        {"question": "Why does it matter?", "answer": "Forces selective symplastic uptake into stele."},
    ])
    examples.append(_record(
        "studio_system_json-013", "thin_source", ["cbse", "biology", "source_pdf:kebo106"],
        {"context": uctx(ctx13, "studio_system_json-013"), "task_instruction": "JSON array of 3 {question, answer} pairs grounded in excerpt. No markdown fences."},
        {"json_output": out13},
        ["valid_json: pass", "grounding: pass"],
        "- **source_pdf:** kebo106.pdf",
    ))

    # 14 Empty context markdown refusal
    examples.append(_record(
        "studio_system_json-014", "empty_context", ["edge_case", "no_source"],
        {"context": "   ", "task_instruction": "Return Markdown summary of key concepts from the excerpt."},
        {"markdown_output": "## Insufficient source\n\n- No indexed excerpt available; cannot summarize without evidence."},
        ["empty_context: pass", "no_hallucination: pass"],
    ))

    # 15 JSON numeric facts
    ctx15 = "For y²=4ax parabola: focus at (a,0), directrix x=−a, eccentricity e=1. Latus rectum length 4a."
    out15 = md_json({
        "conic": "parabola",
        "standard_form": "y²=4ax",
        "focus": "(a, 0)",
        "directrix": "x = -a",
        "eccentricity": 1,
        "latus_rectum": "4a",
    })
    examples.append(_record(
        "studio_system_json-015", "json_numeric_object", ["cbse", "mathematics", "source_pdf:kemh111"],
        {"context": uctx(ctx15, "studio_system_json-015"), "task_instruction": "Return one JSON object with keys conic, standard_form, focus, directrix, eccentricity, latus_rectum. Valid JSON only."},
        {"json_output": out15},
        ["schema_match: pass", "grounding: pass"],
        "- **source_pdf:** kemh111.pdf",
    ))

    variation_order = [
        "json_array", "json_object", "markdown_only", "empty_context", "thin_source", "json_numeric_object",
    ]
    return header + render_examples_grouped(examples, variation_order)


# ---------------------------------------------------------------------------
# Agent 8 — Chat Summarizer (20 examples) — abbreviated builder
# ---------------------------------------------------------------------------

CONVERSATIONS = [
    ("short_ohms", "cbse, physics, source_pdf:leph103", "User: What is Ohm's law?\nAssistant: V equals I times R for ohmic conductors at constant temperature.\nUser: Quick numerical?\nAssistant: With R=5 Ω and I=3 A, voltage V=15 V."),
    ("photosynthesis_neet", "neet, biology, source_pdf:kebo110", "User: Light vs dark reaction location?\nAssistant: Light reaction in grana; Calvin cycle in stroma of chloroplast.\nUser: What enters Calvin cycle?\nAssistant: CO2 is fixed using ATP and NADPH from light reactions.\nUser: NEET one-liner?\nAssistant: Photosynthesis converts light energy to chemical energy in glucose."),
    ("digestive_enzymes", "neet, biology, source_pdf:kebo107", "User: Where does protein digestion start?\nAssistant: Stomach — pepsin works in acidic HCl medium.\nUser: Pancreatic enzymes?\nAssistant: Trypsin, chymotrypsin, lipase, amylase enter duodenum via pancreatic juice.\nUser: Absorption site?\nAssistant: Small intestine villi absorb most nutrients."),
    ("lens_optics", "cbse, physics, source_pdf:leph201", "User: Sign of u for real object?\nAssistant: Real object distance u is negative in Cartesian sign convention.\nUser: Lens formula?\nAssistant: 1/f = 1/v − 1/u.\nUser: Magnification?\nAssistant: m = v/u; negative m means inverted image.\nUser: Ray through optical centre?\nAssistant: Undeviated straight-line path."),
    ("coordination_chem", "cbse, chemistry, source_pdf:lech105", "User: What is coordination number?\nAssistant: Number of donor atoms directly bonded to central metal ion.\nUser: Example with CN=6?\nAssistant: [Fe(CN)6]4− has coordination number six.\nUser: Ligand?\nAssistant: Ion or molecule attached to metal via coordinate bond."),
    ("probability_cards", "cbse, mathematics, source_pdf:lemh207", "User: P(drawing ace from deck)?\nAssistant: 4 favourable / 52 total ≈ 1/13.\nUser: Independent events?\nAssistant: P(A∩B)=P(A)P(B) when outcomes don't affect each other.\nUser: Addition rule?\nAssistant: P(A∪B)=P(A)+P(B)−P(A∩B)."),
    ("rotational_motion", "cbse, physics, source_pdf:keph106", "User: Torque definition?\nAssistant: τ = r × F; magnitude τ = rF sin θ.\nUser: Moment of inertia role?\nAssistant: Rotational analog of mass; τ = Iα.\nUser: Parallel axis theorem?\nAssistant: I = I_cm + Md² shifts axis parallel to CM axis."),
    ("hydrocarbons", "cbse, chemistry, source_pdf:kech203", "User: Alkane general formula?\nAssistant: CnH2n+2; saturated hydrocarbons.\nUser: Markovnikov rule?\nAssistant: In asymmetric alkene addition, H goes to C with more H atoms.\nUser: Benzene stability?\nAssistant: Delocalized π electrons give extra stability (resonance)."),
    ("conic_sections", "cbse, mathematics, source_pdf:kemh111", "User: Parabola definition?\nAssistant: Locus equidistant from focus and directrix.\nUser: Standard form y²=4ax?\nAssistant: Focus at (a,0), directrix x=−a.\nUser: Eccentricity of parabola?\nAssistant: e = 1 always."),
    ("dna_replication", "cbse, biology, source_pdf:lebo105", "User: Semiconservative means?\nAssistant: Each new DNA has one parental and one new strand.\nUser: Enzyme for unwinding?\nAssistant: Helicase separates strands at replication fork.\nUser: Leading vs lagging?\nAssistant: Continuous synthesis on leading; Okazaki fragments on lagging strand."),
    ("electrochemistry_nernst", "cbse, chemistry, source_pdf:lech103", "User: Anode in galvanic cell?\nAssistant: Oxidation occurs; electrons leave anode.\nUser: Standard hydrogen electrode?\nAssistant: Reference with E° = 0.00 V by convention.\nUser: When does cell stop?\nAssistant: When equilibrium reached — net reaction ceases."),
    ("3d_geometry", "cbse, mathematics, source_pdf:lemh205", "User: Direction cosines?\nAssistant: cos α, cos β, cos γ of line with axes; l²+m²+n²=1.\nUser: Equation of line in 3D?\nAssistant: (x−x1)/a = (y−y1)/b = (z−z1)/c.\nUser: Shortest distance skew lines?\nAssistant: Formula using cross product of direction vectors."),
    ("anatomy_plants", "cbse, biology, source_pdf:kebo106", "User: Dicot vs monocot root?\nAssistant: Dicot: radial vascular bundle; monocot: polyarch xylem.\nUser: Casparian strip?\nAssistant: Suberin band in endodermis controls apoplastic flow.\nUser: Why important?\nAssistant: Forces selective symplastic uptake into stele."),
    ("work_energy", "cbse, physics, source_pdf:keph105", "User: Work by variable force?\nAssistant: W = ∫F·dx; graphically area under F-x curve.\nUser: Conservative force?\nAssistant: Work independent of path; e.g. gravity.\nUser: Potential energy relation?\nAssistant: ΔU = −W_conservative."),
    ("aldehydes_ketones", "cbse, chemistry, source_pdf:lech203", "User: Tollens' test?\nAssistant: Ag+ reduced to silver mirror by aldehydes.\nUser: Ketones with Tollens?\nAssistant: No reaction — distinguishes aldehyde vs ketone.\nUser: Nucleophilic addition?\nAssistant: C=O polarized; nucleophile attacks carbonyl carbon."),
    ("binomial_neet", "cbse, mathematics, source_pdf:kemh107", "User: (x+y)^5 middle term?\nAssistant: For n=5, middle term is T3 with coefficient 5C2=10.\nUser: General term?\nAssistant: Tr+1 = nCr x^(n−r) y^r.\nUser: When n even?\nAssistant: Single middle term at r = n/2."),
    ("equilibrium_le_chatelier", "cbse, chemistry, source_pdf:kech106", "User: Kc definition?\nAssistant: Ratio of product to reactant molar concentrations at equilibrium.\nUser: Increase pressure on N2+3H2⇌2NH3?\nAssistant: Shifts toward fewer moles — forward to NH3.\nUser: Catalyst effect on K?\nAssistant: No change to K; speeds attainment only."),
    ("cell_division", "cbse, biology, source_pdf:kebo110", "User: Mitosis vs meiosis purpose?\nAssistant: Mitosis growth/repair; meiosis gamete formation halves chromosome number.\nUser: Prophase I feature?\nAssistant: Crossing over between homologous chromosomes.\nUser: Analogy you used?\nAssistant: Mitosis like photocopy; meiosis like shuffling deck for variety."),
    ("linear_inequalities", "cbse, mathematics, source_pdf:kemh105", "User: Graph 2x+y≤6?\nAssistant: Boundary line 2x+y=6; shade toward origin for ≤.\nUser: Feasible region?\nAssistant: Intersection of all constraint half-planes.\nUser: Corner point method?\nAssistant: Evaluate objective function at vertices of feasible polygon."),
    ("long_mixed_review", "cbse, physics, source_pdf:leph103", "User: Define drift velocity.\nAssistant: Average velocity of electrons under electric field in conductor.\nUser: Relation to current?\nAssistant: I = neAv_d.\nUser: Resistivity temperature dependence?\nAssistant: For metals ρ increases with T due to more collisions.\nUser: Series circuit rule?\nAssistant: Same current through each element.\nUser: Parallel rule?\nAssistant: Same potential across branches.\nUser: Kirchhoff loop law?\nAssistant: Algebraic sum of EMFs equals sum of IR drops.\nUser: Open question?\nAssistant: We should practice wheatstone bridge next.\nUser: Analogy?\nAssistant: Water flow in pipes parallels current in wires."),
]

SUMMARIES = [
    "## Summary\n\nReviewed Ohm's law and a quick numerical using V=IR.\n\n## Key points from the chat\n\n- Ohm's law: V = IR at constant temperature\n- Example: 3 A through 5 Ω gives 15 V\n\n## Definitions / formulas (if any)\n\n- V = IR",
    "## Summary\n\nLocated photosynthesis stages and linked them to NEET revision.\n\n## Key points from the chat\n\n- Light reaction in grana; Calvin cycle in stroma\n- CO2 fixed using ATP and NADPH\n- Converts light energy to chemical energy in glucose\n\n## Open questions / next steps\n\n- Revise C4 vs C3 pathways separately",
    "## Summary\n\nTraced protein digestion and enzyme locations for NEET.\n\n## Key points from the chat\n\n- Pepsin starts protein digestion in acidic stomach\n- Pancreatic trypsin, lipase, amylase act in duodenum\n- Villi in small intestine absorb nutrients",
    "## Summary\n\nCovered lens sign convention, formula, and magnification.\n\n## Key points from the chat\n\n- Real object: u negative\n- Lens formula 1/f = 1/v − 1/u\n- m = v/u; negative m → inverted image\n- Ray through optical centre passes undeviated\n\n## Definitions / formulas (if any)\n\n- 1/f = 1/v − 1/u\n- m = v/u",
    "## Summary\n\nDefined coordination number and ligands with an example complex.\n\n## Key points from the chat\n\n- Coordination number counts σ-donor atoms on metal\n- [Fe(CN)6]4− has CN = 6\n- Ligands attach via coordinate bonds",
    "## Summary\n\nPractised basic probability rules with a card example.\n\n## Key points from the chat\n\n- Classical P = favourable/total (ace ≈ 1/13)\n- Independent: P(A∩B)=P(A)P(B)\n- Addition: P(A∪B)=P(A)+P(B)−P(A∩B)\n\n## Examples / analogies used\n\n- Standard deck ace draw",
    "## Summary\n\nDiscussed torque, moment of inertia, and parallel axis theorem.\n\n## Key points from the chat\n\n- τ = rF sin θ\n- τ = Iα analog of F = ma\n- I = I_cm + Md² for parallel axis shift\n\n## Definitions / formulas (if any)\n\n- τ = r × F",
    "## Summary\n\nReviewed alkane formula, Markovnikov rule, and benzene stability.\n\n## Key points from the chat\n\n- Alkanes: CnH2n+2\n- Markovnikov: H adds to C with more H\n- Benzene stability from delocalized π electrons",
    "## Summary\n\nDefined parabola, standard form, and eccentricity.\n\n## Key points from the chat\n\n- Parabola: equidistant from focus and directrix\n- y²=4ax → focus (a,0), directrix x=−a\n- Eccentricity e = 1\n\n## Definitions / formulas (if any)\n\n- y² = 4ax",
    "## Summary\n\nExplained semiconservative replication and strand synthesis.\n\n## Key points from the chat\n\n- Each new DNA: one old + one new strand\n- Helicase unwinds at fork\n- Leading continuous; lagging Okazaki fragments",
    "## Summary\n\nReviewed galvanic cell electrodes and equilibrium stopping condition.\n\n## Key points from the chat\n\n- Anode: oxidation; electrons leave\n- SHE reference E° = 0\n- Cell stops at equilibrium",
    "## Summary\n\nCovered direction cosines and 3D line equations.\n\n## Key points from the chat\n\n- Direction cosines satisfy l²+m²+n²=1\n- Symmetric line: (x−x1)/a = (y−y1)/b = (z−z1)/c\n- Skew line distance uses cross product\n\n## Definitions / formulas (if any)\n\n- l² + m² + n² = 1",
    "## Summary\n\nCompared root anatomy features and Casparian strip function.\n\n## Key points from the chat\n\n- Dicot vs monocot vascular arrangement differs\n- Casparian strip in endodermis has suberin\n- Forces selective uptake into stele",
    "## Summary\n\nConnected work, conservative forces, and potential energy.\n\n## Key points from the chat\n\n- Variable work W = ∫F·dx\n- Conservative force: path-independent work\n- ΔU = −W_conservative\n\n## Definitions / formulas (if any)\n\n- W = ∫F·dx",
    "## Summary\n\nUsed Tollens' test to distinguish aldehydes from ketones.\n\n## Key points from the chat\n\n- Tollens' gives silver mirror with aldehydes\n- Ketones do not react with Tollens'\n- C=O undergoes nucleophilic addition\n\n## Examples / analogies used\n\n- Silver mirror as visual test",
    "## Summary\n\nPractised binomial expansion middle term and general term.\n\n## Key points from the chat\n\n- n=5 middle term T3, coeff 5C2=10\n- Tr+1 = nCr x^(n−r) y^r\n- Even n: single middle at r=n/2\n\n## Definitions / formulas (if any)\n\n- Tr+1 = nCr x^(n−r) y^r",
    "## Summary\n\nApplied equilibrium constant and Le Chatelier to ammonia synthesis.\n\n## Key points from the chat\n\n- Kc uses molar concentrations at equilibrium\n- Higher pressure favors NH3 (fewer moles)\n- Catalyst does not change K\n\n## Definitions / formulas (if any)\n\n- Kc = [products]/[reactants]",
    "## Summary\n\nContrasted mitosis and meiosis with crossing over highlight.\n\n## Key points from the chat\n\n- Mitosis for growth; meiosis for gametes\n- Prophase I: crossing over\n\n## Examples / analogies used\n\n- Mitosis = photocopy; meiosis = shuffled deck",
    "## Summary\n\nGraphed linear inequality and corner-point optimization idea.\n\n## Key points from the chat\n\n- Shade toward origin for 2x+y≤6\n- Feasible region = intersection of constraints\n- Optimize at polygon vertices",
    "## Summary\n\nExtended current electricity review from drift velocity through Kirchhoff laws.\n\n## Key points from the chat\n\n- Drift velocity v_d; I = neAv_d\n- Metal resistivity rises with temperature\n- Series: same I; parallel: same V\n- Loop law: ΣEMF = ΣIR\n\n## Definitions / formulas (if any)\n\n- I = neAv_d\n\n## Examples / analogies used\n\n- Water flow in pipes parallels current\n\n## Open questions / next steps\n\n- Practice Wheatstone bridge problems",
]


AGENT8_VARIATION_BY_INDEX = [
    "short_transcript",      # 0
    "neet_exam_framing",     # 1
    "neet_exam_framing",     # 2
    "medium_transcript",     # 3
    "medium_transcript",     # 4
    "short_transcript",      # 5
    "numerical_formula",     # 6
    "medium_transcript",     # 7
    "short_transcript",      # 8
    "medium_transcript",     # 9
    "medium_transcript",     # 10
    "numerical_formula",     # 11
    "medium_transcript",     # 12
    "medium_transcript",     # 13
    "numerical_formula",     # 14
    "short_transcript",      # 15
    "medium_transcript",     # 16
    "neet_exam_framing",     # 17
    "long_multi_topic",      # 18
    "long_multi_topic",      # 19
]

AGENT8_VARIATION_ORDER = [
    "short_transcript",
    "medium_transcript",
    "long_multi_topic",
    "numerical_formula",
    "neet_exam_framing",
]


def gen_agent8() -> str:
    summarizer_prompt = load_j2(PROMPTS / "chat" / "chat_summarizer_prompt.j2")
    header = render_agent_header(
        title="## 8. Chat Summarizer Agent",
        metadata_rows=[
            ("Dataset ID", "`chat_summarizer`"),
            ("Category", "Generation"),
            ("Tier", "Tier 2"),
            ("Target examples", "20"),
            ("Actual examples", "20"),
            ("Version", "1.1.0"),
        ],
        agent_responsibility=(
            "Compress a multi-turn tutor chat into structured Markdown for later review. Operates on "
            "**conversation transcript only** — no source PDF retrieval. Must not invent facts beyond the chat."
        ),
        audit_finding=(
            "The original 20-example set rotated only two transcript templates ~15×, causing tag/subject mismatches "
            "and insufficient section variety (formulas, analogies, open questions). "
            "Rebuilt with 20 unique NCERT-grounded transcripts, locked variation taxonomy, full inline production prompt, "
            "and gold summaries that omit empty sections per prompt contract."
        ),
        taxonomy_rows=[
            ("short_transcript", "2–3 turn chats; minimal sections", 4),
            ("medium_transcript", "4–6 turns; standard section mix", 8),
            ("long_multi_topic", "8+ turns; open questions / analogies", 2),
            ("numerical_formula", "Formulas in `## Definitions / formulas`", 3),
            ("neet_exam_framing", "NEET/CBSE drill tone in transcript", 3),
        ],
        quality_dimensions=[
            ("structure", "Required `##` headings present when content exists; bullets not wall-of-text."),
            ("no_hallucination", "Summary facts appear in conversation transcript only."),
            ("section_omit_empty", "Empty optional sections omitted per prompt contract."),
            ("concise", "Summary 2–4 sentences; key points 3–7 bullets."),
            ("tag_alignment", "Tags reflect conversation subject and exam framing."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `old_conversation`",
            "Output keys: `summary_markdown`",
        ],
        prompt_blocks=[
            ("Prompt template (production)", "jinja2", summarizer_prompt),
        ],
        runtime_note=(
            "Loaded from [`packages/core/memory/chat_summarizer.py`](packages/core/memory/chat_summarizer.py) "
            "when conversation history exceeds token threshold in chat memory pipeline."
        ),
        eval_count=20,
    )
    examples: list[ExampleRecord] = []
    for i in range(20):
        var = AGENT8_VARIATION_BY_INDEX[i]
        tags_str = CONVERSATIONS[i][1]
        conv = CONVERSATIONS[i][2]
        summ = SUMMARIES[i]
        ex_id = f"chat_summarizer-{i+1:03d}"
        tag_list = tags_str.split(", ")
        examples.append(_record(
            ex_id, var, tag_list,
            {"old_conversation": conv},
            {"summary_markdown": summ},
            ["structure: pass", "no_hallucination: pass", "concise: pass", "tag_alignment: pass"],
        ))
    return header + render_examples_grouped(examples, AGENT8_VARIATION_ORDER)


# ---------------------------------------------------------------------------
# Agent 9 — Hallucination Guard (12 examples, 6 rewrite + 6 pass)
# ---------------------------------------------------------------------------

AGENT9_VARIATION_ORDER = [
    "rewrite_remove",
    "rewrite_soften",
    "rewrite_label_gk",
    "pass_through",
    "pass_minor_edit",
]

HALLUCINATION_GUARD_PROMPT = """Grounding instruction (hallucination guard):
- Remove, soften, or label as `General knowledge:` any sentence not directly supported by the Context evidence.
- Prefer restating the evidence using the same terms as the excerpts.
- Do not add new specific numbers, names, dates, or quotes unless they appear in the evidence.

Unsupported sentences detected:
- {unsupported_sentence_1}
- {unsupported_sentence_2}
"""


def gen_agent9() -> str:
    header = render_agent_header(
        title="## 9. Hallucination Guard Retry Suffix",
        metadata_rows=[
            ("Dataset ID", "`hallucination_guard_retry`"),
            ("Category", "Generation"),
            ("Tier", "Tier 3 baseline → focused enrichment set"),
            ("Target examples", "15"),
            ("Actual examples", "15"),
            ("Version", "1.1.0"),
        ],
        agent_responsibility=(
            "When deterministic grounding check flags unsupported sentences, production appends "
            "`strict_retry_suffix()` from [`hallucination_guard.py`](packages/core/rag/hallucination_guard.py) "
            "to the RAG generation prompt. The model must rewrite the answer using **only context evidence**."
        ),
        audit_finding=(
            "The original 12-example set used 100% placeholder gold for corrected answers and had no pass-through "
            "cases where grounded answers remain unchanged. Expanded to 15 examples with ~50% rewrite vs pass balance, "
            "production-faithful retry suffix inline, and real corrected_answer gold grounded in NCERT excerpts."
        ),
        taxonomy_rows=[
            ("rewrite_remove", "Drop unsupported claims", 5),
            ("rewrite_soften", "Replace with excerpt-grounded wording", 3),
            ("rewrite_label_gk", "Label `General knowledge:` when appropriate", 2),
            ("pass_through", "Already grounded — minimal/no change", 4),
            ("pass_minor_edit", "Trivial punctuation/clarity only", 1),
        ],
        quality_dimensions=[
            ("grounding", "Corrected answer supported by context excerpt terms."),
            ("unsupported_removed", "Flagged sentences absent or properly softened/labeled."),
            ("no_new_facts", "No new numbers, names, or dates beyond evidence."),
            ("retry_suffix_compliance", "Rewrite follows hallucination guard suffix rules."),
            ("pass_balance", "Pass cases retain grounded content without over-stripping."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `answer`, `context`, `unsupported_sentences`",
            "Output keys: `corrected_answer`",
        ],
        prompt_blocks=[
            ("Prompt suffix (production — `strict_retry_suffix()`)", "text", HALLUCINATION_GUARD_PROMPT),
        ],
        runtime_note=(
            "Appended in [`packages/core/langgraph/chat_graph.py`](packages/core/langgraph/chat_graph.py) on retry "
            "when `ENABLE_HALLUCINATION_GUARD` flags unsupported sentences after initial RAG response."
        ),
        eval_count=15,
    )
    rewrite_cases = [
        ("hallucination_guard_retry-001", "rewrite_remove", ["grounding", "biology", "negative"],
         "The human heart has five chambers and blue blood circulates in all arteries.",
         "NCERT Biology: Pepsin acts in stomach at acidic pH; trypsin and chymotrypsin act in duodenum with pancreatic juice.",
         '["The human heart has five chambers"]',
         "Pepsin acts in the stomach at acidic pH. Trypsin and chymotrypsin act in the duodenum with pancreatic juice."),
        ("hallucination_guard_retry-002", "rewrite_remove", ["grounding", "physics", "negative"],
         "Newton published Principia in 1685 and invented calculus independently of Leibniz.",
         "Ray optics: Lens formula 1/f = 1/v − 1/u. Magnification m = v/u. Power P = 1/f.",
         '["Newton published Principia in 1685"]',
         "For lenses, 1/f = 1/v − 1/u and magnification m = v/u. Lens power P = 1/f."),
        ("hallucination_guard_retry-003", "rewrite_remove", ["grounding", "biology", "negative"],
         "Photosynthesis occurs only at night in all plant species worldwide.",
         "Photosynthesis in chloroplasts: light reaction in grana produces ATP and NADPH; Calvin cycle in stroma fixes CO2.",
         '["Photosynthesis occurs only at night"]',
         "Photosynthesis occurs in chloroplasts: the light reaction in grana produces ATP and NADPH, and the Calvin cycle in stroma fixes CO2."),
        ("hallucination_guard_retry-004", "rewrite_soften", ["grounding", "chemistry", "negative"],
         "Gold is the most abundant metal in Earth's crust and dissolves easily in water.",
         "Electrochemistry: In galvanic cells oxidation occurs at anode; E°cell = E°cathode − E°anode.",
         '["Gold is the most abundant metal", "dissolves easily in water"]',
         "In galvanic cells, oxidation occurs at the anode. Standard cell EMF E°cell = E°cathode − E°anode."),
        ("hallucination_guard_retry-005", "rewrite_label_gk", ["grounding", "mathematics", "negative"],
         "The probability of rolling sum 7 with two dice is exactly 1/2 every time.",
         "Probability: P(E) = favourable outcomes / total outcomes. For two fair dice, sum 7 has 6 favourable outcomes out of 36.",
         '["The probability of rolling sum 7 with two dice is exactly 1/2 every time"]',
         "P(E) = favourable outcomes / total outcomes. For two fair dice, sum 7 has 6 favourable outcomes out of 36 (P = 6/36 = 1/6)."),
        ("hallucination_guard_retry-006", "rewrite_remove", ["grounding", "physics", "negative"],
         "Superconductors have infinite resistance at room temperature in all household wires.",
         "Current electricity: Ohm's law V = IR. Resistivity ρ increases with temperature for metals.",
         '["Superconductors have infinite resistance at room temperature"]',
         "Ohm's law states V = IR. For metals, resistivity ρ increases with temperature."),
    ]
    pass_cases = [
        ("hallucination_guard_retry-007", "pass_through", ["grounding", "physics", "positive"],
         "Ohm's law states V = IR for ohmic conductors. In series, equivalent resistance adds: R_eq = R1 + R2.",
         "Ohm's law: V = IR. Series combination R_eq = R1 + R2. Parallel: 1/R_eq = 1/R1 + 1/R2.",
         "[]",
         "Ohm's law states V = IR for ohmic conductors. In series, equivalent resistance adds: R_eq = R1 + R2."),
        ("hallucination_guard_retry-008", "pass_through", ["grounding", "biology", "positive"],
         "Mitosis produces genetically identical cells for growth; meiosis halves chromosome number for gametes.",
         "Cell division: Mitosis maintains chromosome number for growth and repair. Meiosis reduces chromosome number to form gametes.",
         "[]",
         "Mitosis produces genetically identical cells for growth; meiosis halves chromosome number for gametes."),
        ("hallucination_guard_retry-009", "pass_minor_edit", ["grounding", "chemistry", "positive"],
         "In coordination compounds, the coordination number counts donor atoms bonded to the central metal ion.",
         "Coordination compounds: Coordination number is the count of σ-donor atoms directly bonded to the metal.",
         "[]",
         "In coordination compounds, the coordination number counts σ-donor atoms directly bonded to the central metal ion."),
        ("hallucination_guard_retry-010", "pass_through", ["grounding", "mathematics", "positive"],
         "For a parabola y² = 4ax, the focus is at (a, 0) and eccentricity equals 1.",
         "Conic sections: Standard parabola y² = 4ax has focus (a,0), directrix x = −a, eccentricity e = 1.",
         "[]",
         "For a parabola y² = 4ax, the focus is at (a, 0) and eccentricity equals 1."),
        ("hallucination_guard_retry-011", "pass_through", ["grounding", "biology", "positive"],
         "DNA replication is semiconservative: each new duplex contains one parental and one newly synthesized strand.",
         "Molecular basis of inheritance: DNA replication is semiconservative — each new molecule has one old and one new strand.",
         "[]",
         "DNA replication is semiconservative: each new duplex contains one parental and one newly synthesized strand."),
        ("hallucination_guard_retry-012", "pass_through", ["grounding", "physics", "positive"],
         "Lens power P equals the reciprocal of focal length in metres: P = 1/f.",
         "Ray optics: Lens power P = 1/f when f is in metres. Sign convention uses Cartesian distances from optical centre.",
         "[]",
         "Lens power P equals the reciprocal of focal length in metres: P = 1/f."),
        ("hallucination_guard_retry-013", "rewrite_remove", ["grounding", "chemistry", "negative"],
         "Benzene has alternating single and double bonds that flip every millisecond at room temperature.",
         "Hydrocarbons: Benzene has delocalized π electrons giving extra stability (resonance). Markovnikov rule applies to asymmetric alkene addition.",
         '["alternating single and double bonds that flip every millisecond"]',
         "Benzene has delocalized π electrons giving extra stability through resonance."),
        ("hallucination_guard_retry-014", "rewrite_soften", ["grounding", "mathematics", "negative"],
         "Every linear inequality graph is always a circle in the coordinate plane.",
         "Linear inequalities: Graph ax+by≤c by shading the half-plane toward the origin test point. Feasible region is intersection of constraints.",
         '["always a circle"]',
         "Graph ax+by≤c by shading the half-plane that satisfies the inequality (e.g. toward origin for ≤). Feasible region is the intersection of all constraint half-planes."),
        ("hallucination_guard_retry-015", "pass_through", ["grounding", "chemistry", "positive"],
         "Le Chatelier's principle states that a system at equilibrium shifts to oppose an applied stress such as pressure or concentration change.",
         "Equilibrium: Le Chatelier — system shifts to partially counteract imposed stress. Catalyst does not change Kc.",
         "[]",
         "Le Chatelier's principle states that a system at equilibrium shifts to oppose an applied stress such as pressure or concentration change."),
    ]
    examples: list[ExampleRecord] = []
    for ex_id, var, tags, ans, ctx, unsup, corrected in rewrite_cases + pass_cases:
        unsup_list = json.loads(unsup.replace("'", '"')) if unsup.startswith("[") else []
        unsup_str = json.dumps(unsup_list) if unsup_list else "[]"
        examples.append(_record(
            ex_id, var, tags,
            {"answer": ans, "context": uctx(ctx, ex_id), "unsupported_sentences": unsup_str},
            {"corrected_answer": corrected},
            ["grounding: pass", "retry_suffix_compliance: pass"],
        ))
    return header + render_examples_grouped(examples, AGENT9_VARIATION_ORDER)


# Continue in part 2 — studio generators loaded from separate module
if __name__ == "__main__":
    from generate_agents_8_16_studio import (  # noqa: WPS433
        gen_agent11,
        gen_agent12,
        gen_agent13,
        gen_agent14,
        gen_agent15_16,
    )

    SCRIPTS.mkdir(exist_ok=True)
    (SCRIPTS / "agent8_chat_summarizer.md").write_text(gen_agent8(), encoding="utf-8")
    (SCRIPTS / "agent9_hallucination_guard.md").write_text(gen_agent9(), encoding="utf-8")
    (SCRIPTS / "agent10_studio_system_json.md").write_text(gen_agent10(), encoding="utf-8")
    (SCRIPTS / "agent11_studio_quiz.md").write_text(gen_agent11(), encoding="utf-8")
    (SCRIPTS / "agent12_studio_flashcards.md").write_text(gen_agent12(), encoding="utf-8")
    (SCRIPTS / "agent13_studio_mind_map.md").write_text(gen_agent13(), encoding="utf-8")
    (SCRIPTS / "agent14_studio_slide_deck.md").write_text(gen_agent14(), encoding="utf-8")
    (SCRIPTS / "agents15_16_studio_legacy.md").write_text(gen_agent15_16(), encoding="utf-8")
    print("Generated all agent 8-16 fragment files.")
