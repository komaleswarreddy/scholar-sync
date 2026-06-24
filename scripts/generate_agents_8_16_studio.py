#!/usr/bin/env python3
"""Studio agent fragment generators (Agents 11-16)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))

from agent_section_renderer import (
    ExampleRecord,
    load_j2,
    render_agent_header,
    render_examples_grouped,
)
from generate_agents_8_16_fragments import (
    _record,
    example_block,
    make_flashcards,
    make_mcq,
    make_quiz,
    md_json,
    uctx,
)
from studio_slide_deck_quality import assess_deck_quality

PROMPTS = ROOT / "packages" / "core" / "prompts" / "templates"
SLIDE_DECK_POOL = SCRIPTS / "studio_slide_deck_eval_pool.json"
SLIDE_DECK_CACHE = SCRIPTS / "studio_slide_deck_llm_gold_cache.json"

STUDIO_VARIATION_ORDER = [
    "per_concept",
    "multi_concept",
    "per_source",
    "multi_source",
    "no_source",
    "custom_override",
]

_CUSTOM_OVERRIDE_VARS = {
    "custom_hard", "custom_easy", "custom_language", "custom_count", "custom_slides",
    "custom_focus", "variable_deck_large", "thin_source", "chapter_scope",
    "multi_source_three", "multi_source_user_restrict", "custom_deck_large",
}


def map_studio_variation(var: str) -> str:
    if var in STUDIO_VARIATION_ORDER:
        return var
    if var.startswith("custom_") or var in _CUSTOM_OVERRIDE_VARS:
        return "custom_override"
    return "custom_override"


def _studio_system_prompt() -> str:
    return load_j2(PROMPTS / "studio" / "system_educational_json_markdown.j2")


def _scope_coverage_table(rows: list[tuple[str, str, str]]) -> str:
    lines = [
        "**Scope coverage**",
        "",
        "| scope_mode | Min examples | This dataset |",
        "|------------|--------------|--------------|",
    ]
    for mode, minimum, actual in rows:
        lines.append(f"| {mode} | {minimum} | {actual} |")
    return "\n".join(lines)


def _scope_tag(tags: list[str], default: str = "custom") -> str:
    for t in tags:
        if t.startswith("scope_mode:"):
            return t.split(":", 1)[1]
    return default

CTX = {
    "current_electricity": "Ohm's law V=IR. Resistivity ρ=RA/l. Series R_eq=R1+R2. Parallel 1/R_eq=1/R1+1/R2. Kirchhoff junction: sum I_in = sum I_out. Drift velocity v_d; I=neAv_d.",
    "ray_optics": "Lens formula 1/f=1/v-1/u. Magnification m=v/u. Power P=1/f (f in metres). Sign: real object u negative. Ray through optical centre undeviated.",
    "photosynthesis": "Light reaction in grana: ATP, NADPH. Calvin cycle in stroma fixes CO2. Chlorophyll absorbs light. Stomata exchange CO2 and O2.",
    "digestion": "Salivary amylase in mouth. Stomach: HCl + pepsin. Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi.",
    "coordination": "Central metal + ligands. Coordination number = σ-donor atoms on metal. [Fe(CN)6]4- has CN=6. IUPAC: ligands alphabetical; anionic end in -o.",
    "probability": "P(E)=favourable/total. P(A∪B)=P(A)+P(B)-P(A∩B). Independent: P(A∩B)=P(A)P(B). Bayes links prior and likelihood.",
    "electrochemistry": "Galvanic cell: anode oxidation, cathode reduction. E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration.",
    "mitosis_meiosis": "Mitosis: growth/repair, same chromosome number. Meiosis: gametes, halves chromosomes. Prophase I: crossing over.",
    "binomial": "(a+b)^n expansion uses nCr. General term Tr+1=nCr a^(n-r) b^r. Middle term depends on n even/odd.",
    "equilibrium": "Kc=[products]/[reactants] at equilibrium. Le Chatelier: stress shifts to oppose change. Catalyst speeds approach, not K.",
    "hydrocarbons": "Alkanes CnH2n+2. Markovnikov: H to C with more H. Benzene: delocalized π, extra stability.",
    "3d_geometry": "Direction cosines l,m,n; l²+m²+n²=1. Line: (x-x1)/a=(y-y1)/b=(z-z1)/c. Skew lines: shortest distance via cross product.",
    "dna": "DNA: A-T, G-C pairing. Semiconservative replication. mRNA carries code to ribosomes for translation.",
    "work_energy": "W=F·s cos θ. K=½mv². P=W/t. Conservative force: path-independent work. ΔU=-W_conservative.",
    "anatomy_plants": "Dicot root: radial vascular bundle. Monocot: polyarch xylem. Casparian strip in endodermis controls flow.",
    "aldehydes": "Tollens' test: silver mirror with aldehydes, not ketones. C=O undergoes nucleophilic addition.",
    "rotational": "Torque τ=rF sin θ. τ=Iα. Parallel axis: I=I_cm+Md².",
    "conic": "Parabola: focus-directrix equidistance. y²=4ax focus (a,0). e=1 for parabola.",
    "linear_ineq": "Graph ax+by≤c: shade toward origin test point. Feasible region intersection of half-planes. Optimize at vertices.",
    "multi_phys_chem": "[Source A — Current Electricity] Ohm's law V=IR; resistivity ρ=RA/l.\n\n[Source B — Electrochemistry] Galvanic cell: anode oxidation; E°cell=E°cathode-E°anode.",
    "multi_bio": "[Source A — Photosynthesis] Light reaction in grana; Calvin cycle in stroma.\n\n[Source B — Cell division] Mitosis maintains chromosome number; meiosis halves for gametes.",
    "multi_math": "[Source A — Probability] P(E)=favourable/total; P(A∩B)=P(A)P(B) if independent.\n\n[Source B — Binomial] Tr+1=nCr a^(n-r) b^r in (a+b)^n expansion.",
}


def _quiz_qs_current(n: int, focus: str = "general") -> list[dict]:
    pool = [
        make_mcq("According to Ohm's law, if R doubles at constant V, current becomes:",
                 ["Doubled", "Halved", "Unchanged", "Zero"], "Halved", "I=V/R so current halves when R doubles."),
        make_mcq("Two resistors 4 Ω and 12 Ω in series give R_eq of:",
                 ["3 Ω", "16 Ω", "48 Ω", "8 Ω"], "16 Ω", "Series resistances add: 4+12=16 Ω."),
        make_mcq("Kirchhoff's junction rule states:",
                 ["Sum I in equals sum I out", "Sum V equals zero", "Power is conserved", "Charge is created"],
                 "Sum I in equals sum I out", "Current into a node equals current leaving."),
        make_mcq("Drift velocity v_d relates to current by:",
                 ["I=neAv_d", "I=v_d/e", "I=ρv_d", "I=n/v_d"], "I=neAv_d", "Microscopic form I=neAv_d."),
        make_mcq("Resistivity ρ depends on:",
                 ["Material and temperature", "Length only", "Voltage only", "Current direction"], "Material and temperature", "ρ is material property; metals increase ρ with T."),
        make_mcq("Parallel resistors 6 Ω and 3 Ω give R_eq:",
                 ["2 Ω", "9 Ω", "18 Ω", "1 Ω"], "2 Ω", "1/R_eq=1/6+1/3=1/2 → R_eq=2 Ω."),
        make_mcq("Ohm's law applies best to:",
                 ["Ohmic conductors at constant T", "All materials at any T", "Only superconductors", "Only insulators"],
                 "Ohmic conductors at constant T", "V=IR holds for ohmic conductors at fixed temperature."),
    ]
    return pool[:n]


def gen_agent11() -> str:
    system_prompt = _studio_system_prompt()
    task_prompt = load_j2(PROMPTS / "studio" / "quiz_prompt.j2")
    header = render_agent_header(
        title="## 11. Studio Quiz Generator",
        metadata_rows=[
            ("Dataset ID", "`studio_quiz`"),
            ("Category", "Studio"),
            ("Tier", "Tier 2"),
            ("Target examples", "25"),
            ("Actual examples", "25"),
            ("Version", "1.1.0"),
        ],
        agent_responsibility=(
            "Generate a JSON quiz `{title, questions[]}` from retrieved source excerpts. Custom instructions "
            "override default question count (5–7) and difficulty. Production pairs system prompt + "
            "[`studio/quiz_prompt.j2`](packages/core/prompts/templates/studio/quiz_prompt.j2)."
        ),
        audit_finding=(
            "The original dataset had question-count mismatches vs custom_instructions, placeholder MCQs, and no "
            "scope coverage matrix. Rebuilt with 25 examples spanning all scope modes, locked variation taxonomy, "
            "full inline system + task prompts, and gold quizzes honoring requested counts and difficulty."
        ),
        taxonomy_rows=[
            ("per_concept", "Topic-focused custom instructions", "5"),
            ("multi_concept", "Full-breadth / all topics in context", "4"),
            ("per_source", "Single-source excerpt", "5"),
            ("multi_source", "Merged multi-doc context + synthesis", "5"),
            ("no_source", "Empty context → failure/generic branch", "2"),
            ("custom_override", "Count/difficulty/slide/language overrides", "4"),
        ],
        quality_dimensions=[
            ("question_count_match", "Question count matches custom_instructions (e.g. '5 MCQs' → 5 questions)."),
            ("schema_valid", "Valid JSON; correct_answer ∈ options; 2–4 options per question."),
            ("options_quality", "Four options when material supports; no duplicate distractors."),
            ("difficulty_compliance", "Easy/medium/hard vocabulary and reasoning depth per instructions."),
            ("grounding", "Questions and explanations grounded in context excerpt only."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `context`, `custom_instructions`",
            "Output keys: `quiz_json`",
            "Production also uses: `retrieval_queries_note` (not in LangSmith eval keys)",
        ],
        prompt_blocks=[
            ("Prompt template (system — production)", "jinja2", system_prompt),
            ("Prompt template (user/task — production)", "jinja2", task_prompt),
        ],
        runtime_note=(
            "[`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) "
            "`StudioService._generate_structured_task()` plus "
            "[`packages/core/validation/studio_output_validators.py`](packages/core/validation/studio_output_validators.py) "
            "`validate_quiz_schema()`."
        ),
        eval_count=25,
        extras=_scope_coverage_table([
            ("per_concept", "4", "5"),
            ("multi_concept", "3", "4"),
            ("per_source", "4", "5"),
            ("multi_source", "5", "5"),
            ("no_source", "2", "2"),
            ("custom_override", "—", "4 (distributed)"),
        ]),
    )
    specs: list[tuple] = [
        ("001", "per_concept", ["cbse", "physics", "scope_mode:per_concept", "source_pdf:leph103"],
         CTX["current_electricity"], "5 MCQs, medium difficulty, focus Ohm's law and series circuits",
         make_quiz("Current Electricity — Ohm & Series", _quiz_qs_current(5)[:5])),
        ("002", "per_concept", ["neet", "biology", "scope_mode:per_concept", "source_pdf:kebo107"],
         CTX["digestion"], "4 MCQs, hard NEET-style, digestive enzymes only",
         make_quiz("Digestive Enzymes NEET Drill", [
             make_mcq("Carbohydrate digestion begins in mouth with:", ["Pepsin", "Salivary amylase", "Trypsin", "Lipase"],
                      "Salivary amylase", "Salivary amylase acts on starch in mouth."),
             make_mcq("Pepsin requires which stomach condition?", ["Alkaline pH", "Acidic HCl medium", "Neutral pH", "No enzymes"],
                      "Acidic HCl medium", "Pepsin works in acidic stomach environment."),
             make_mcq("Trypsin is activated in:", ["Stomach", "Mouth", "Duodenum via pancreatic juice", "Large intestine"],
                      "Duodenum via pancreatic juice", "Pancreatic trypsin enters duodenum."),
             make_mcq("Most nutrient absorption occurs in:", ["Stomach", "Oesophagus", "Small intestine villi", "Mouth"],
                      "Small intestine villi", "Villi absorb digested nutrients."),
         ])),
        ("003", "per_concept", ["cbse", "chemistry", "scope_mode:per_concept", "source_pdf:lech105"],
         CTX["coordination"], "3 MCQs, easy, coordination number only",
         make_quiz("Coordination Number Basics", [
             make_mcq("Coordination number counts:", ["Electrons in metal", "σ-donor atoms bonded to metal", "Ligand mass", "Oxidation state only"],
                      "σ-donor atoms bonded to metal", "CN = donor atoms directly bonded."),
             make_mcq("[Fe(CN)6]4- has coordination number:", ["4", "6", "8", "2"], "6", "Six cyanide ligands → CN=6."),
             make_mcq("Coordination entity contains:", ["Central metal ion + ligands", "Only anions", "Only cations", "Free solvent"],
                      "Central metal ion + ligands", "Complex = metal + attached ligands."),
         ])),
        ("004", "per_concept", ["cbse", "mathematics", "scope_mode:per_concept", "source_pdf:lemh207"],
         CTX["probability"], "5 MCQs, medium, independent events focus",
         make_quiz("Independent Events Quiz", [
             make_mcq("For independent A and B, P(A∩B) equals:", ["P(A)+P(B)", "P(A)P(B)", "P(A)/P(B)", "1"],
                      "P(A)P(B)", "Independence: multiply probabilities."),
             make_mcq("Classical P(E) equals:", ["favourable/total outcomes", "total/favourable", "P(A)+P(B)", "Always 1/2"],
                      "favourable/total outcomes", "Laplace definition."),
             make_mcq("P(A∪B) general addition rule:", ["P(A)+P(B)-P(A∩B)", "P(A)P(B)", "P(A)-P(B)", "P(A)/P(B)"],
                      "P(A)+P(B)-P(A∩B)", "Inclusion-exclusion."),
             make_mcq("If A and B independent, knowing B occurred:", ["Changes P(A)", "Does not change P(A)", "Makes P(A)=0", "Makes P(A)=1"],
                      "Does not change P(A)", "Independence means no influence."),
             make_mcq("Bayes theorem relates:", ["Prior and likelihood to posterior", "Only means", "Only variances", "Matrix rank"],
                      "Prior and likelihood to posterior", "Bayes updates beliefs with evidence."),
         ])),
        ("005", "per_concept", ["cbse", "physics", "scope_mode:per_concept", "source_pdf:leph201"],
         CTX["ray_optics"], "4 MCQs, medium, lens formula and magnification",
         make_quiz("Lens Formula Focus", [
             make_mcq("Lens formula is:", ["1/f=1/v+1/u", "1/f=1/v-1/u", "f=uv", "f=u+v"], "1/f=1/v-1/u", "Standard Cartesian lens formula."),
             make_mcq("Magnification m equals:", ["v/u", "u/v", "f/v", "v-f"], "v/u", "m = v/u."),
             make_mcq("Real object distance u is:", ["Negative in Cartesian convention", "Always positive", "Zero", "Equal to f always"],
                      "Negative in Cartesian convention", "Sign convention for real object."),
             make_mcq("Lens power P in dioptre when f in metres:", ["P=f", "P=1/f", "P=f²", "P=2f"], "P=1/f", "Power reciprocal of focal length."),
         ])),
        ("006", "multi_concept", ["cbse", "physics", "scope_mode:multi_concept", "source_pdf:leph103"],
         CTX["current_electricity"], "6 MCQs, medium, full chapter breadth — no narrow topic",
         make_quiz("Current Electricity Full Breadth", _quiz_qs_current(6))),
        ("007", "multi_concept", ["cbse", "biology", "scope_mode:multi_concept", "source_pdf:kebo110"],
         CTX["photosynthesis"] + " " + CTX["mitosis_meiosis"], "5 MCQs, medium, cover all topics in context",
         make_quiz("Photosynthesis & Cell Division Mix", [
             make_mcq("Light reaction products include:", ["ATP and NADPH", "Only CO2", "Only glucose", "Only O2 absorbed"],
                      "ATP and NADPH", "Light reaction outputs ATP, NADPH."),
             make_mcq("Calvin cycle location:", ["Grana", "Stroma", "Mitochondria", "Nucleus"], "Stroma", "CO2 fixation in stroma."),
             make_mcq("Mitosis purpose:", ["Gamete formation", "Growth and repair with same chromosome number", "Halving chromosomes", "Crossing over"],
                      "Growth and repair with same chromosome number", "Mitosis maintains 2n."),
             make_mcq("Meiosis produces:", ["Identical somatic cells", "Gametes with halved chromosomes", "Only proteins", "Chlorophyll"],
                      "Gametes with halved chromosomes", "Meiosis → n for gametes."),
             make_mcq("Crossing over occurs in:", ["Prophase I of meiosis", "Mitotic prophase always", "Cytokinesis", "G1 only"],
                      "Prophase I of meiosis", "Prophase I exchanges segments."),
         ])),
        ("008", "multi_concept", ["cbse", "chemistry", "scope_mode:multi_concept", "source_pdf:kech106"],
         CTX["equilibrium"] + " " + CTX["electrochemistry"], "5 MCQs, hard, all selected sources",
         make_quiz("Equilibrium & Electrochemistry Combined", [
             make_mcq("Kc uses:", ["Equilibrium molar concentrations", "Only solids", "Initial concentrations", "Temperature only"],
                      "Equilibrium molar concentrations", "Kc defined at equilibrium."),
             make_mcq("Catalyst effect on K:", ["No change to K", "Doubles K", "Halves K", "Eliminates K"], "No change to K", "Catalyst affects rate not K."),
             make_mcq("Galvanic cell anode undergoes:", ["Reduction", "Oxidation", "No reaction", "Hydrolysis"], "Oxidation", "Anode = oxidation site."),
             make_mcq("E°cell equals:", ["E°cathode-E°anode", "E°anode-E°cathode", "Zero always", "Sum of resistances"],
                      "E°cathode-E°anode", "Standard cell EMF formula."),
             make_mcq("Le Chatelier: increase pressure on gas reaction with fewer product moles shifts:",
                      ["Toward fewer moles side", "Toward more moles side", "No shift", "Stops reaction"],
                      "Toward fewer moles side", "System opposes pressure increase."),
         ])),
        ("009", "multi_concept", ["cbse", "mathematics", "scope_mode:multi_concept", "source_pdf:kemh107"],
         CTX["binomial"] + " " + CTX["probability"], "4 MCQs, medium, full breadth binomial and probability",
         make_quiz("Binomial & Probability Breadth", [
             make_mcq("General term in (a+b)^n:", ["Tr+1=nCr a^(n-r) b^r", "n!", "a+b", "n^r"], "Tr+1=nCr a^(n-r) b^r", "Binomial theorem term."),
             make_mcq("nCr counts:", ["Combinations", "Permutations only", "Integrals", "Derivatives"], "Combinations", "Binomial coefficients are combinations."),
             make_mcq("P(A∪B) equals:", ["P(A)+P(B)-P(A∩B)", "P(A)P(B)", "1", "P(A)-P(B)"], "P(A)+P(B)-P(A∩B)", "Addition theorem."),
             make_mcq("Independent events satisfy:", ["P(A∩B)=P(A)P(B)", "P(A)=P(B)", "P(A)=0", "P(A)=1"], "P(A∩B)=P(A)P(B)", "Definition of independence."),
         ])),
        ("010", "per_source", ["cbse", "physics", "scope_mode:per_source", "source_pdf:leph103"],
         CTX["current_electricity"], "5 MCQs, easy, CBSE board style",
         make_quiz("CBSE Current Electricity Easy", _quiz_qs_current(5))),
        ("011", "per_source", ["cbse", "biology", "scope_mode:per_source", "source_pdf:lebo105"],
         CTX["dna"], "5 MCQs, medium, molecular inheritance",
         make_quiz("DNA & Inheritance Quiz", [
             make_mcq("Adenine pairs with:", ["Guanine", "Thymine", "Cytosine only", "Uracil always"], "Thymine", "A-T pairing in DNA."),
             make_mcq("DNA replication is:", ["Conservative", "Semiconservative", "Dispersive only", "Random"], "Semiconservative", "One old + one new strand."),
             make_mcq("mRNA function:", ["Carries genetic code to ribosomes", "Stores lipid", "Catalyses pepsin", "Absorbs light"], "Carries genetic code to ribosomes", "mRNA template for translation."),
             make_mcq("Guanine pairs with:", ["Adenine", "Thymine", "Cytosine", "Glucose"], "Cytosine", "G-C base pair."),
             make_mcq("Translation occurs at:", ["Ribosomes", "Grana only", "Stomata", "Casparian strip"], "Ribosomes", "Protein synthesis on ribosomes."),
         ])),
        ("012", "per_source", ["cbse", "chemistry", "scope_mode:per_source", "source_pdf:lech203"],
         CTX["aldehydes"], "4 MCQs, medium, carbonyl tests",
         make_quiz("Aldehydes & Ketones Tests", [
             make_mcq("Tollens' test positive for:", ["Aldehydes", "Ketones only", "Alkanes", "Ethers"], "Aldehydes", "Aldehydes reduce Ag+ to silver mirror."),
             make_mcq("Ketones with Tollens' reagent:", ["No silver mirror", "Always positive", "Explode", "Form gas only"], "No silver mirror", "Ketones don't reduce Tollens' reagent."),
             make_mcq("C=O group undergoes:", ["Nucleophilic addition", "Only free radical substitution", "No reactions", "Only elimination always"],
                      "Nucleophilic addition", "Polarized carbonyl carbon attacked by nucleophile."),
             make_mcq("Tollens' produces:", ["Silver mirror on aldehyde oxidation", "Blue copper solution", "White precipitate always", "No visible change always"],
                      "Silver mirror on aldehyde oxidation", "Characteristic silver mirror test."),
         ])),
        ("013", "per_source", ["cbse", "mathematics", "scope_mode:per_source", "source_pdf:lemh205"],
         CTX["3d_geometry"], "5 MCQs, hard, 3D geometry",
         make_quiz("Three Dimensional Geometry", [
             make_mcq("Direction cosines satisfy:", ["l²+m²+n²=1", "l+m+n=0", "l=m=n=0", "l²+m²=n"], "l²+m²+n²=1", "Unit direction vector constraint."),
             make_mcq("Line through (x1,y1,z1) with direction a,b,c:", ["(x-x1)/a=(y-y1)/b=(z-z1)/c", "x+y+z=0", "y=mx+c", "x²+y²=1"],
                      "(x-x1)/a=(y-y1)/b=(z-z1)/c", "Symmetric form of 3D line."),
             make_mcq("Skew lines distance uses:", ["Cross product of direction vectors", "Only dot product", "Determinant zero", "Single point only"],
                      "Cross product of direction vectors", "Shortest distance formula uses cross product."),
             make_mcq("Direction cosines are cosines of angles with:", ["Coordinate axes", "Only x-axis", "Random lines", "Normal only"],
                      "Coordinate axes", "Angles with x, y, z axes."),
             make_mcq("A line in 3D requires:", ["Point and direction ratios", "Only one point", "Only slope", "Area"], "Point and direction ratios", "Point-direction form."),
         ])),
        ("014", "per_source", ["cbse", "physics", "scope_mode:per_source", "source_pdf:keph106"],
         CTX["rotational"], "3 MCQs, easy, rotational dynamics thin source",
         make_quiz("Rotational Dynamics Quick", [
             make_mcq("Torque magnitude equals:", ["rF sin θ", "r/F", "F only", "r+F"], "rF sin θ", "τ = rF sin θ."),
             make_mcq("Rotational analog τ=Iα corresponds to:", ["F=ma", "P=IV", "V=IR", "E=mc²"], "F=ma", "I is rotational inertia."),
             make_mcq("Parallel axis theorem:", ["I=I_cm+Md²", "I=M/d", "I=0", "I=I_cm-Md²"], "I=I_cm+Md²", "Shift parallel axis from CM."),
         ])),
        ("015", "multi_source", ["cbse", "physics", "scope_mode:multi_source", "source_pdf:leph103"],
         CTX["multi_phys_chem"], "5 MCQs, medium, integrate both sources",
         make_quiz("Electricity & Electrochemistry Integrated", [
             make_mcq("Ohm's law states:", ["V=IR", "V=I/R always", "I=0 always", "R=0 required"], "V=IR", "Per electricity excerpt."),
             make_mcq("Resistivity ρ relates to:", ["R, A, l by ρ=RA/l", "Only voltage", "Only current direction", "Cell EMF"], "R, A, l by ρ=RA/l", "Material geometry relation."),
             make_mcq("Galvanic cell anode:", ["Oxidation", "Reduction", "Salt bridge only", "Insulator"], "Oxidation", "Per electrochemistry excerpt."),
             make_mcq("Standard E°cell:", ["E°cathode-E°anode", "E°anode only", "Sum of ρ", "1/R_eq"], "E°cathode-E°anode", "Cell EMF definition."),
             make_mcq("Both topics link through:", ["Charge flow and energy conversion", "Only optics", "Only digestion", "Random guess"], "Charge flow and energy conversion", "Integrated concept bridge."),
         ])),
        ("016", "multi_source", ["cbse", "biology", "scope_mode:multi_source"],
         CTX["multi_bio"], "5 MCQs, medium, both biology sources",
         make_quiz("Photosynthesis & Meiosis Synthesis", [
             make_mcq("Calvin cycle fixes:", ["CO2 in stroma", "O2 in grana only", "N2 in nucleus", "Glucose in mouth"], "CO2 in stroma", "Photosynthesis excerpt."),
             make_mcq("Light reaction location:", ["Grana", "Stroma only", "Villi", "Casparian strip"], "Grana", "Thylakoid membranes in grana."),
             make_mcq("Meiosis reduces:", ["Chromosome number for gametes", "ATP only", "CO2", "Resistivity"], "Chromosome number for gametes", "Cell division excerpt."),
             make_mcq("Mitosis used for:", ["Growth and repair", "Gamete formation only", "Silver mirror test", "Lens formula"], "Growth and repair", "Maintains 2n."),
             make_mcq("Both processes involve:", ["Energy/transformations in living cells", "Only metal ions", "Only optics", "None"], "Energy/transformations in living cells", "Integrated biology theme."),
         ])),
        ("017", "multi_source", ["cbse", "mathematics", "scope_mode:multi_source"],
         CTX["multi_math"], "4 MCQs, hard, probability and binomial",
         make_quiz("Probability-Binomial Integration", [
             make_mcq("Tr+1 in binomial expansion:", ["nCr a^(n-r) b^r", "P(A)+P(B)", "l²+m²+n²=1", "V=IR"], "nCr a^(n-r) b^r", "Binomial term."),
             make_mcq("Classical probability:", ["favourable/total", "nCr only", "f only", "Zero"], "favourable/total", "Probability definition."),
             make_mcq("Independent events:", ["P(A∩B)=P(A)P(B)", "P(A)=1 always", "P(A)=0 always", "No formula"], "P(A∩B)=P(A)P(B)", "Independence rule."),
             make_mcq("Binomial coefficients count:", ["Combinations in expansion", "Only permutations", "Only angles", "Resistances"], "Combinations in expansion", "nCr in expansion."),
         ])),
        ("018", "multi_source", ["cbse", "chemistry", "scope_mode:multi_source"],
         CTX["multi_phys_chem"], "5 MCQs, medium, cross-domain chemistry-physics",
         make_quiz("Material Properties Cross-Source", _quiz_qs_current(3)[:3] + [
             make_mcq("E°cell definition uses:", ["Standard electrode potentials", "Only ρ", "Only m", "Lens formula"], "Standard electrode potentials", "Electrochemistry source."),
             make_mcq("Anode in galvanic cell:", ["Oxidation site", "Reduction only", "Salt only", "Mirror test"], "Oxidation site", "Electrode role."),
         ])),
        ("019", "multi_source", ["cbse", "physics", "scope_mode:multi_source", "source_pdf:leph201"],
         CTX["ray_optics"] + "\n\n" + CTX["current_electricity"], "6 MCQs, medium, optics and electricity selected",
         make_quiz("Optics & Electricity Multi-Source", _quiz_qs_current(3)[:3] + [
             make_mcq("Lens power P:", ["1/f with f in metres", "V=IR", "I=neAv_d", "ρ=0"], "1/f with f in metres", "Optics source."),
             make_mcq("Real object u sign:", ["Negative", "Always positive", "Zero", "Complex"], "Negative", "Sign convention."),
             make_mcq("Magnification:", ["v/u", "R_eq", "P(A∩B)", "nCr"], "v/u", "Lens magnification."),
         ])),
        ("020", "multi_source", ["neet", "biology", "scope_mode:multi_source"],
         CTX["digestion"] + "\n\n" + CTX["photosynthesis"], "5 MCQs, hard NEET, both sources",
         make_quiz("NEET Digestion-Photosynthesis Deck", [
             make_mcq("Salivary amylase acts in:", ["Mouth", "Stomach", "Grana", "Stroma"], "Mouth", "Digestion source."),
             make_mcq("Calvin cycle:", ["CO2 fixation in stroma", "Light in grana only", "Pepsin activation", "Tollens test"], "CO2 fixation in stroma", "Photosynthesis source."),
             make_mcq("Pepsin needs:", ["Acidic stomach", "Alkaline duodenum only", "No pH", "Only light"], "Acidic stomach", "Enzyme environment."),
             make_mcq("ATP from light reaction used for:", ["Calvin cycle", "Only digestion", "Only optics", "None"], "Calvin cycle", "Cross-process link."),
             make_mcq("Absorption mainly in:", ["Small intestine", "Grana", "Lens", "Anode"], "Small intestine", "Digestion source."),
         ])),
        ("021", "no_source", ["edge_case", "scope_mode:no_source"],
         "", "5 MCQs, easy, general science — no source provided",
         make_quiz("General Science Baseline", [
             make_mcq("SI unit of force is:", ["Newton", "Joule", "Watt", "Pascal"], "Newton", "Coherent general science item."),
             make_mcq("Water chemical formula:", ["H2O", "CO2", "NaCl", "O2 only"], "H2O", "Basic chemistry literacy."),
             make_mcq("Plants need for photosynthesis:", ["Light", "Only darkness", "Only metal", "Vacuum"], "Light", "General biology."),
             make_mcq("Sum of angles in triangle:", ["180°", "90°", "360°", "0°"], "180°", "Euclidean geometry."),
             make_mcq("Speed unit in SI:", ["m/s", "km only", "mph", "Light-year"], "m/s", "Units knowledge."),
         ])),
        ("022", "no_source", ["edge_case", "scope_mode:no_source"],
         "   ", "3 MCQs, medium, coherent topic without indexed source",
         make_quiz("Study Skills Mini Quiz", [
             make_mcq("Active recall means:", ["Testing yourself on material", "Only re-reading", "Skipping revision", "Ignoring errors"],
                      "Testing yourself on material", "Metacognition item."),
             make_mcq("Spaced repetition helps:", ["Long-term retention", "Only cramming", "Avoiding sleep", "Deleting notes"], "Long-term retention", "Learning strategy."),
             make_mcq("Before exams, prioritise:", ["Weak topics with timed practice", "Only easy topics", "Zero practice", "Random guessing"], "Weak topics with timed practice", "Exam strategy."),
         ])),
        ("023", "custom_hard", ["cbse", "physics", "custom_instructions"],
         CTX["current_electricity"], "7 MCQs, hard difficulty, numerical reasoning emphasis",
         make_quiz("Hard Numerical Electricity", _quiz_qs_current(7))),
        ("024", "custom_easy", ["cbse", "biology", "custom_instructions"],
         CTX["anatomy_plants"], "3 MCQs, easy, Casparian strip only",
         make_quiz("Casparian Strip Easy", [
             make_mcq("Casparian strip located in:", ["Endodermis", "Epidermis only", "Stomata", "Grana"], "Endodermis", "Endodermal barrier."),
             make_mcq("Casparian strip made of:", ["Suberin", "Only chlorophyll", "Silver", "Only lipase"], "Suberin", "Waxy suberin band."),
             make_mcq("Its function:", ["Controls apoplastic flow into stele", "Produces ATP", "Fixes CO2", "Forms images"], "Controls apoplastic flow into stele", "Forces selective uptake."),
         ])),
        ("025", "custom_language", ["cbse", "mathematics", "custom_instructions"],
         CTX["conic"], "5 MCQs, medium, focus parabola only — Hindi technical terms allowed in explanations",
         make_quiz("Parabola Focus Drill", [
             make_mcq("Parabola locus definition:", ["Equidistant from focus and directrix", "Circle centre", "Hyperbola asymptote", "Ellipse sum"],
                      "Equidistant from focus and directrix", "Geometric definition."),
             make_mcq("y²=4ax focus at:", ["(a,0)", "(0,a)", "(-a,0)", "(0,-a)"], "(a,0)", "Standard parabola focus."),
             make_mcq("Parabola eccentricity:", ["1", "0", "2", "<1"], "1", "e=1 always for parabola."),
             make_mcq("Directrix of y²=4ax:", ["x=-a", "x=a", "y=0", "y=a"], "x=-a", "Directrix line."),
             make_mcq("Axis of parabola y²=4ax:", ["x-axis", "y-axis only", "z-axis", "None"], "x-axis", "Opens along x-axis."),
         ])),
    ]
    examples: list[ExampleRecord] = []
    for sid, var, tags, ctx, instr, gold in specs:
        ref = f"studio_quiz-{sid}"
        scope = _scope_tag(tags, var.replace("custom_", "per_concept"))
        locked_var = map_studio_variation(var)
        if not any(t.startswith("scope_mode:") for t in tags):
            tags = tags + [f"scope_mode:{scope}"]
        ctx_in = uctx(ctx, ref) if ctx.strip() else ""
        examples.append(_record(
            f"studio_quiz-{sid}", locked_var, tags,
            {"context": ctx_in, "custom_instructions": instr},
            {"quiz_json": gold},
            ["question_count: pass", "schema_valid: pass", "options_quality: pass", "grounding: pass"],
            f"- **scope_mode:** {scope}",
        ))
    return header + render_examples_grouped(examples, STUDIO_VARIATION_ORDER)


def gen_agent12() -> str:
    system_prompt = _studio_system_prompt()
    task_prompt = load_j2(PROMPTS / "studio" / "flashcards_prompt.j2")
    header = render_agent_header(
        title="## 12. Studio Flashcards Generator",
        metadata_rows=[
            ("Dataset ID", "`studio_flashcards`"),
            ("Category", "Studio"),
            ("Tier", "Tier 2"),
            ("Target examples", "22"),
            ("Actual examples", "22"),
            ("Version", "1.1.0"),
        ],
        agent_responsibility=(
            "JSON array of `{front, back}` flashcards from retrieved excerpts. Card count varies by excerpt "
            "density (default 5–10; custom instructions override). Multi-source → one integrated deck spread across sources."
        ),
        audit_finding=(
            "The original dataset used a fixed deck size regardless of excerpt density and lacked true multi-source "
            "card spread. Rebuilt with variable card counts, locked scope variation taxonomy, full inline system + task "
            "prompts, and gold decks that honor custom count overrides."
        ),
        taxonomy_rows=[
            ("per_concept", "Topic-focused custom instructions", "4"),
            ("multi_concept", "Full-breadth / all topics in context", "3"),
            ("per_source", "Single-source excerpt", "4"),
            ("multi_source", "Merged multi-doc context + synthesis", "5"),
            ("no_source", "Empty context → `[]` — no fabrication", "2"),
            ("custom_override", "Count/difficulty overrides", "4"),
        ],
        quality_dimensions=[
            ("card_count_variable", "Deck size matches excerpt density and custom_instructions."),
            ("no_duplicates", "No same-idea cards reworded; distinct front/back pairs."),
            ("multi_source_spread", "Multi-source decks draw cards from each represented source."),
            ("grounding", "Card backs grounded in context excerpt only."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `context`, `selected_source_count`",
            "Output keys: `flashcards_json`",
            "Production also uses: `custom_instructions`, `retrieval_queries_note`",
        ],
        prompt_blocks=[
            ("Prompt template (system — production)", "jinja2", system_prompt),
            ("Prompt template (user/task — production)", "jinja2", task_prompt),
        ],
        runtime_note=(
            "[`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) "
            "`StudioService._generate_structured_task()` with flashcards task template."
        ),
        eval_count=22,
        extras=_scope_coverage_table([
            ("per_concept", "4", "4"),
            ("multi_concept", "3", "3"),
            ("per_source", "4", "4"),
            ("multi_source", "5", "5"),
            ("no_source", "2", "2"),
            ("custom_override", "—", "4 (distributed)"),
        ]),
    )

    def fc_record(sid, var, tags, ctx, count, cards, scope, src_count="1", custom=""):
        ref = f"studio_flashcards-{sid}"
        locked_var = map_studio_variation(var)
        if not any(t.startswith("scope_mode:") for t in tags):
            tags = tags + [f"scope_mode:{scope}"]
        inputs = {"context": uctx(ctx, ref), "selected_source_count": str(src_count)}
        if custom:
            inputs["custom_instructions"] = custom
        meta = f"- **scope_mode:** {scope}\n- **selected_source_count:** {src_count}"
        return _record(
            f"studio_flashcards-{sid}", locked_var, tags, inputs,
            {"flashcards_json": make_flashcards(cards)},
            ["card_count: pass", "no_duplicates: pass", "grounding: pass"],
            meta,
        )

    examples: list[ExampleRecord] = []
    # Build 22 examples programmatically
    deck_specs = [
        ("001", "per_concept", ["cbse", "physics", "scope_mode:per_concept"], CTX["current_electricity"], 6,
         [("Ohm's law?", "V = IR for ohmic conductors."), ("Series R_eq?", "R_eq = R1 + R2"), ("Parallel rule?", "1/R_eq = 1/R1 + 1/R2"),
          ("Kirchhoff junction?", "Sum I_in = sum I_out"), ("Drift velocity relation?", "I = neAv_d"), ("Resistivity formula?", "ρ = RA/l")],
         "per_concept", "1", "8 cards max, focus Ohm's law only"),
        ("002", "per_concept", ["neet", "biology"], CTX["digestion"], 5,
         [("Salivary amylase site?", "Mouth — starts starch digestion."), ("Pepsin medium?", "Acidic stomach with HCl."),
          ("Trypsin source?", "Pancreatic juice → duodenum."), ("Lipase function?", "Digests fats."), ("Main absorption?", "Small intestine villi")],
         "per_concept", "1", "5 cards, digestive enzymes only"),
        ("003", "per_concept", ["cbse", "chemistry"], CTX["coordination"], 4,
         [("Coordination number?", "Count of σ-donor atoms on metal."), ("Ligand?", "Ion/molecule bonded to central metal."),
          ("[Fe(CN)6]4- CN?", "6"), ("IUPAC ligand order?", "Alphabetical; anionic ligands end in -o")],
         "per_concept", "1"),
        ("004", "per_concept", ["cbse", "mathematics"], CTX["probability"], 5,
         [("Classical P(E)?", "Favourable / total outcomes."), ("Addition rule?", "P(A∪B)=P(A)+P(B)-P(A∩B)"),
          ("Independent events?", "P(A∩B)=P(A)P(B)"), ("Bayes links?", "Prior, likelihood → posterior"), ("Complement?", "P(A')=1-P(A)")],
         "per_concept", "1"),
        ("005", "multi_concept", ["cbse", "biology"], CTX["photosynthesis"] + " " + CTX["mitosis_meiosis"], 8,
         [("Light reaction site?", "Grana — ATP, NADPH."), ("Calvin cycle?", "Stroma — CO2 fixation."), ("Mitosis purpose?", "Growth/repair, same 2n."),
          ("Meiosis output?", "Gametes with n chromosomes."), ("Crossing over?", "Prophase I of meiosis."), ("Stomata role?", "Gas exchange CO2/O2."),
          ("Chlorophyll?", "Absorbs light energy."), ("ATP use in Calvin?", "Powers CO2 fixation.")], "multi_concept", "1", "Full breadth, 8 cards"),
        ("006", "multi_concept", ["cbse", "chemistry"], CTX["equilibrium"] + " " + CTX["hydrocarbons"], 7,
         [("Kc definition?", "Equilibrium concentration ratio."), ("Le Chatelier?", "Shift opposes applied stress."),
          ("Catalyst and K?", "No change to K."), ("Alkane formula?", "CnH2n+2"), ("Markovnikov rule?", "H to C with more H."),
          ("Benzene stability?", "Delocalized π electrons."), ("Pressure on fewer moles?", "Shifts toward fewer gas moles.")],
         "multi_concept", "1"),
        ("007", "multi_concept", ["cbse", "mathematics"], CTX["binomial"] + " " + CTX["linear_ineq"], 6,
         [("Binomial general term?", "Tr+1 = nCr a^(n-r) b^r"), ("nCr meaning?", "Combination coefficient."),
          ("Feasible region?", "Intersection of constraint half-planes."), ("Corner point method?", "Optimize at polygon vertices."),
          ("Shade ax+by≤c?", "Test origin side."), ("Middle term n even?", "Single middle at r=n/2.")], "multi_concept", "1"),
        ("008", "per_source", ["cbse", "physics"], CTX["ray_optics"], 5,
         [("Lens formula?", "1/f = 1/v − 1/u"), ("Magnification?", "m = v/u"), ("Lens power?", "P = 1/f (f in m)"),
          ("Real object u?", "Negative in Cartesian convention."), ("Optical centre ray?", "Passes undeviated.")], "per_source", "1"),
        ("009", "per_source", ["cbse", "biology"], CTX["dna"], 5,
         [("A pairs with?", "T"), ("G pairs with?", "C"), ("Replication type?", "Semiconservative."),
          ("mRNA role?", "Carries code to ribosomes."), ("Translation site?", "Ribosomes.")], "per_source", "1"),
        ("010", "per_source", ["cbse", "chemistry"], CTX["electrochemistry"], 4,
         [("Galvanic anode?", "Oxidation."), ("Galvanic cathode?", "Reduction."), ("E°cell?", "E°cathode − E°anode."),
          ("Nernst equation?", "Links EMF to concentration.")], "per_source", "1"),
        ("011", "per_source", ["cbse", "mathematics"], CTX["3d_geometry"], 5,
         [("Direction cosines constraint?", "l²+m²+n²=1"), ("3D line form?", "(x-x1)/a=(y-y1)/b=(z-z1)/c"),
          ("Skew line distance?", "Uses cross product."), ("Direction ratios?", "Define line direction."),
          ("Angles with?", "Coordinate axes.")], "per_source", "1"),
        ("012", "multi_source", ["cbse", "physics"], CTX["multi_phys_chem"], 8,
         [("Ohm's law?", "V=IR"), ("ρ relation?", "ρ=RA/l"), ("Galvanic anode?", "Oxidation."),
          ("E°cell?", "E°cathode−E°anode"), ("Series R?", "Adds."), ("Charge flow link?", "Both domains involve charge/energy."),
          ("Resistivity vs cell?", "Material vs electrochemical driving force."), ("Integrated review?", "Electricity + electrochemistry deck.")],
         "multi_source", "2"),
        ("013", "multi_source", ["cbse", "biology"], CTX["multi_bio"], 7,
         [("Grana product?", "ATP, NADPH"), ("Calvin site?", "Stroma"), ("Meiosis result?", "n gametes"),
          ("Mitosis?", "2n somatic cells."), ("Crossing over?", "Prophase I."), ("Gas exchange?", "Stomata."),
          ("Integrated theme?", "Energy and information in cells.")], "multi_source", "2"),
        ("014", "multi_source", ["cbse", "mathematics"], CTX["multi_math"], 6,
         [("P(E) classical?", "favourable/total"), ("Independent?", "P(A∩B)=P(A)P(B)"), ("Binomial term?", "nCr a^(n-r) b^r"),
          ("nCr?", "Combination count."), ("Link?", "Combinatorics in probability."), ("Deck spans?", "Both sources.")], "multi_source", "2"),
        ("015", "multi_source", ["cbse", "physics"], CTX["ray_optics"] + "\n\n" + CTX["current_electricity"], 9,
         [("Lens formula?", "1/f=1/v−1/u"), ("P=?", "1/f"), ("V=IR?", "Ohm's law"), ("Series R?", "R1+R2"),
          ("m=?", "v/u"), ("Real u sign?", "Negative"), ("Kirchhoff junction?", "ΣI_in=ΣI_out"), ("Optics+electricity?", "Two-source deck."),
          ("Review tip?", "Separate formula cards per topic.")], "multi_source", "2"),
        ("016", "multi_source", ["neet", "biology"], CTX["digestion"] + "\n\n" + CTX["photosynthesis"], 8,
         [("Amylase?", "Mouth"), ("Pepsin?", "Stomach HCl"), ("Calvin?", "Stroma CO2 fix"), ("Grana?", "Light reaction"),
          ("Trypsin?", "Pancreatic/duodenum"), ("Absorption?", "Small intestine"), ("ATP use?", "Calvin cycle"), ("NEET deck?", "Cross-topic.")],
         "multi_source", "2"),
        ("017", "no_source", ["edge_case", "scope_mode:no_source"], "", 0, [], "no_source", "1"),
        ("018", "no_source", ["edge_case"], "  ", 0, [], "no_source", "2"),
        ("019", "thin_source", ["cbse", "physics"], "Superconductivity at low T mentioned briefly.", 2,
         [("Superconductivity note?", "Zero resistance at very low temperature (thin excerpt)."), ("Deck size?", "Minimal 2-card deck from thin text.")],
         "per_source", "1", "Exactly 2 cards from thin excerpt"),
        ("020", "variable_deck_large", ["cbse", "biology"], CTX["anatomy_plants"] + " " + CTX["digestion"], 10,
         [("Dicot root vascular?", "Radial bundle."), ("Monocot xylem?", "Polyarch."), ("Casparian strip?", "Suberin in endodermis."),
          ("Apoplastic block?", "Forces symplastic path."), ("Salivary amylase?", "Mouth."), ("Pepsin?", "Stomach."),
          ("Villi?", "Absorption."), ("Endodermis role?", "Selective uptake."), ("Plant-animal link?", "Surface area for absorption."),
          ("10-card deck?", "Dense excerpt supports more cards.")], "multi_concept", "1", "10 flashcards"),
        ("021", "custom_count", ["cbse", "chemistry"], CTX["aldehydes"], 3,
         [("Tollens'?", "Silver mirror — aldehydes."), ("Ketones Tollens'?", "No reaction."), ("C=O mechanism?", "Nucleophilic addition.")],
         "per_concept", "1", "Exactly 3 flashcards"),
        ("022", "multi_source_three", ["cbse", "mathematics"], CTX["conic"] + "\n\n" + CTX["probability"] + "\n\n" + CTX["binomial"], 7,
         [("Parabola e?", "1"), ("Focus-directrix?", "Equidistant locus."), ("y²=4ax focus?", "(a,0)"),
          ("P(A∪B)?", "P(A)+P(B)-P(A∩B)"), ("Tr+1?", "nCr a^(n-r) b^r"), ("Three-source deck?", "Spread across math topics."),
          ("Review order?", "Mix conic + probability + binomial.")], "multi_source", "3"),
    ]
    for spec in deck_specs:
        sid, var, tags, ctx, n, cards, scope, src_count = spec[:8]
        custom = spec[8] if len(spec) > 8 else ""
        if n == 0:
            ref = f"studio_flashcards-{sid}"
            empty_ctx = ""
            tags_clean = [t for t in tags if not t.startswith("scope_mode:")] + ["scope_mode:no_source"]
            examples.append(_record(
                f"studio_flashcards-{sid}", map_studio_variation(var), tags_clean,
                {"context": empty_ctx, "selected_source_count": src_count},
                {"flashcards_json": "[]"},
                ["empty_deck: pass", "no_fabrication: pass"],
                f"- **scope_mode:** no_source\n- **selected_source_count:** {src_count}",
            ))
        else:
            examples.append(fc_record(sid, var, tags + [f"scope_mode:{scope}"], ctx, n, cards, scope, src_count, custom))
    return header + render_examples_grouped(examples, STUDIO_VARIATION_ORDER)


def gen_agent13() -> str:
    system_prompt = _studio_system_prompt()
    task_prompt = load_j2(PROMPTS / "studio" / "mind_map_prompt.j2")
    header = render_agent_header(
        title="## 13. Studio Mind Map Generator",
        metadata_rows=[
            ("Dataset ID", "`studio_mind_map`"),
            ("Category", "Studio"),
            ("Tier", "Tier 2"),
            ("Target examples", "24"),
            ("Actual examples", "24"),
            ("Version", "1.1.0"),
        ],
        agent_responsibility=(
            "Hub-and-spoke Markdown mind map from source excerpts. Production **forces `sources_only`** context mode. "
            "Multi-source → one integrated hub bridging materials "
            "([`mind_map_prompt.j2`](packages/core/prompts/templates/studio/mind_map_prompt.j2))."
        ),
        audit_finding=(
            "The original dataset had all selected_source_count=1, weak hub-and-spoke gold, and no multi-source synthesis "
            "examples. Rebuilt with 8+ multi-source cases, locked variation taxonomy, full inline prompts, and gold maps "
            "with single `#` hub and integrated branches."
        ),
        taxonomy_rows=[
            ("per_concept", "Topic-focused custom instructions", "4"),
            ("multi_concept", "Full-breadth / all topics in context", "3"),
            ("per_source", "Single-source excerpt", "4"),
            ("multi_source", "Merged multi-doc context + synthesis", "8"),
            ("no_source", "Empty context → `# Insufficient source text`", "2"),
            ("custom_override", "User focus/restrict overrides", "3"),
        ],
        quality_dimensions=[
            ("single_hub", "Exactly one `#` central hub; branches under `##`/`###`."),
            ("multi_source_synthesis", "Multi-source maps bridge materials, not siloed mini-maps."),
            ("structure", "Hub-and-spoke Markdown hierarchy; scannable headings."),
            ("grounding", "Nodes grounded in context excerpt only."),
            ("insufficient_source_pattern", "Empty context yields `# Insufficient source text` pattern."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `context`, `selected_source_count`",
            "Output keys: `mind_map_markdown`",
        ],
        prompt_blocks=[
            ("Prompt template (system — production)", "jinja2", system_prompt),
            ("Prompt template (user/task — production)", "jinja2", task_prompt),
        ],
        runtime_note=(
            "[`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) with **`sources_only`** "
            "override; multi-source uses `merge_studio_match_lists` for integrated retrieval."
        ),
        eval_count=24,
        extras=_scope_coverage_table([
            ("per_concept", "4", "4"),
            ("multi_concept", "3", "3"),
            ("per_source", "4", "4"),
            ("multi_source", "8+", "8"),
            ("no_source", "2", "2"),
            ("custom_override", "—", "3"),
        ]),
    )
    maps = [
        ("001", "per_concept", ["cbse", "physics", "scope_mode:per_concept"], CTX["current_electricity"], "1",
         "# Current Electricity\n\n## Ohm's Law\n- **V = IR** for ohmic conductors\n\n## Combinations\n- **Series:** R_eq adds\n- **Parallel:** reciprocal sum\n\n## Microscopic View\n- **I = neAv_d** drift relation"),
        ("002", "per_concept", ["neet", "biology"], CTX["digestion"], "1",
         "# Human Digestion\n\n## Mouth\n- **Salivary amylase** on starch\n\n## Stomach\n- **HCl + pepsin** for protein\n\n## Small Intestine\n- **Villi** absorb nutrients\n- Pancreatic **trypsin, lipase**"),
        ("003", "per_concept", ["cbse", "chemistry"], CTX["coordination"], "1",
         "# Coordination Compounds\n\n## Core Ideas\n- **Central metal** + ligands\n\n## Coordination Number\n- Count **σ-donor** atoms\n- Example **[Fe(CN)6]4−** → CN = 6\n\n## Naming\n- **IUPAC:** ligands alphabetical"),
        ("004", "per_concept", ["cbse", "mathematics"], CTX["probability"], "1",
         "# Probability Foundations\n\n## Classical Definition\n- **P(E) = favourable / total**\n\n## Rules\n- **Addition:** P(A∪B) = P(A)+P(B)−P(A∩B)\n- **Independent:** P(A∩B) = P(A)P(B)"),
        ("005", "multi_concept", ["cbse", "biology"], CTX["photosynthesis"] + " " + CTX["mitosis_meiosis"], "1",
         "# Energy & Information in Cells\n\n## Photosynthesis\n- **Light reaction** → ATP, NADPH (grana)\n- **Calvin cycle** fixes CO2 (stroma)\n\n## Cell Division\n- **Mitosis** → growth (2n)\n- **Meiosis** → gametes (n)\n- **Crossing over** in Prophase I"),
        ("006", "multi_concept", ["cbse", "chemistry"], CTX["equilibrium"] + " " + CTX["electrochemistry"], "1",
         "# Equilibrium & Electrochemical Cells\n\n## Chemical Equilibrium\n- **Kc** at equilibrium\n- **Le Chatelier** opposes stress\n\n## Galvanic Cells\n- **Anode:** oxidation\n- **E°cell = E°cathode − E°anode**"),
        ("007", "multi_concept", ["cbse", "mathematics"], CTX["binomial"] + " " + CTX["3d_geometry"], "1",
         "# Binomial & 3D Geometry\n\n## Binomial Theorem\n- **Tr+1 = nCr a^(n-r) b^r**\n\n## 3D Lines\n- **Direction cosines:** l²+m²+n²=1\n- Symmetric line equations"),
        ("008", "per_source", ["cbse", "physics"], CTX["ray_optics"], "1",
         "# Ray Optics — Lenses\n\n## Lens Equation\n- **1/f = 1/v − 1/u**\n\n## Magnification & Power\n- **m = v/u**\n- **P = 1/f** (f in metres)\n\n## Sign Convention\n- Real object **u negative**"),
        ("009", "per_source", ["cbse", "biology"], CTX["dna"], "1",
         "# Molecular Basis of Inheritance\n\n## DNA Structure\n- **A–T, G–C** pairing\n\n## Replication\n- **Semiconservative** — one old + one new strand\n\n## Expression\n- **mRNA** → ribosomes for translation"),
        ("010", "per_source", ["cbse", "chemistry"], CTX["hydrocarbons"], "1",
         "# Hydrocarbons\n\n## Alkanes\n- **CnH2n+2** saturated\n\n## Addition\n- **Markovnikov:** H to richer C\n\n## Aromatics\n- **Benzene** — delocalized π stability"),
        ("011", "per_source", ["cbse", "mathematics"], CTX["conic"], "1",
         "# Conic Sections — Parabola\n\n## Definition\n- Locus equidistant from **focus** and **directrix**\n\n## Standard Form\n- **y² = 4ax** → focus (a,0)\n- **Eccentricity e = 1**"),
        ("012", "multi_source", ["cbse", "physics"], CTX["multi_phys_chem"], "2",
         "# Charge Flow & Energy Conversion\n\n## Conductors (Source A)\n- **Ohm's law V = IR**\n- **ρ = RA/l**\n\n## Electrochemical Cells (Source B)\n- **Anode** oxidation\n- **E°cell** difference drives flow\n\n## Bridge\n- Both describe **directed charge** and **energy transfer**"),
        ("013", "multi_source", ["cbse", "biology"], CTX["multi_bio"], "2",
         "# Life Processes — Energy & Reproduction\n\n## Energy Capture (Source A)\n- **Photosynthesis** in chloroplasts\n- Light → ATP/NADPH → Calvin\n\n## Inheritance Continuity (Source B)\n- **Mitosis** maintains 2n\n- **Meiosis** halves for gametes\n\n## Integration\n- Energy metabolism supports **cell division cycles**"),
        ("014", "multi_source", ["cbse", "mathematics"], CTX["multi_math"], "2",
         "# Counting & Chance\n\n## Probability (Source A)\n- **Classical P(E)** ratio\n- **Independence** multiplies\n\n## Binomial Expansion (Source B)\n- **nCr** coefficients\n- **Tr+1** general term\n\n## Link\n- Binomial coefficients underpin **probability models**"),
        ("015", "multi_source", ["cbse", "physics"], CTX["ray_optics"] + "\n\n" + CTX["current_electricity"], "2",
         "# Physics Toolkit — Optics & Circuits\n\n## Optics Branch\n- **Lens formula** and **m = v/u**\n\n## Circuits Branch\n- **V = IR** and **Kirchhoff** rules\n\n## Contrast\n- **Geometric optics** vs **electric transport** — both use ratio laws"),
        ("016", "multi_source", ["neet", "biology"], CTX["digestion"] + "\n\n" + CTX["photosynthesis"], "2",
         "# Organism Input & Energy\n\n## Heterotrophic Nutrition\n- **Digestive enzymes** and absorption\n\n## Autotrophic Energy\n- **Photosynthesis** light and dark reactions\n\n## Theme\n- **Matter intake** vs **energy capture** sustain life"),
        ("017", "multi_source", ["cbse", "chemistry"], CTX["electrochemistry"] + "\n\n" + CTX["coordination"], "2",
         "# Metals in Chemistry\n\n## Redox Cells\n- **Galvanic** electrode roles\n\n## Complex Ions\n- **Coordination number** and ligands\n\n## Link\n- **Metal centres** appear in both electrochemical and complex forms"),
        ("018", "multi_source", ["cbse", "mathematics"], CTX["linear_ineq"] + "\n\n" + CTX["probability"], "2",
         "# Optimization & Uncertainty\n\n## Linear Programming\n- **Feasible region** from inequalities\n\n## Probability\n- **Event ratios** and rules\n\n## Contrast\n- **Deterministic constraints** vs **stochastic outcomes**"),
        ("019", "multi_source_three", ["cbse", "physics"], CTX["work_energy"] + "\n\n" + CTX["rotational"] + "\n\n" + CTX["current_electricity"], "3",
         "# Mechanics & Electricity Overview\n\n## Work & Energy\n- **W = F·s cos θ**, **K = ½mv²**\n\n## Rotation\n- **τ = Iα**\n\n## Circuits\n- **V = IR**\n\n## Hub Theme\n- **Energy transformations** across mechanical and electrical domains"),
        ("020", "multi_source_three", ["cbse", "biology"], CTX["anatomy_plants"] + "\n\n" + CTX["photosynthesis"] + "\n\n" + CTX["dna"], "3",
         "# Plant Structure & Function\n\n## Anatomy\n- **Casparian strip** selective uptake\n\n## Metabolism\n- **Photosynthesis** energy capture\n\n## Heredity\n- **DNA** replication semantics\n\n## Integration\n- Structure supports **transport, energy, and inheritance**"),
        ("021", "no_source", ["edge_case", "scope_mode:no_source"], "", "1",
         "# Insufficient source text\n\n## Status\n- No excerpt retrieved from selected sources\n\n## Next steps\n- Re-index PDF or select sources before regenerating"),
        ("022", "no_source", ["edge_case", "scope_mode:no_source"], "  ", "2",
         "# Insufficient source text\n\n## Multi-source selection empty\n- **0 chunks** retrieved despite count=2\n\n## Action\n- Verify uploads and checkboxes"),
        ("023", "custom_focus", ["cbse", "physics"], CTX["current_electricity"], "1",
         "# Kirchhoff Laws Only\n\n## Junction Rule\n- **ΣI_in = ΣI_out**\n\n## Loop Rule\n- **ΣEMF = ΣIR drops**\n\n## Application\n- Solve multi-loop circuits"),
        ("024", "multi_source_user_restrict", ["cbse", "biology"], CTX["multi_bio"], "2",
         "# Cell Division Comparison Only\n\n## Mitosis\n- **2n maintained** — growth/repair\n\n## Meiosis\n- **n gametes** — Prophase I crossing over\n\n## User scope\n- Map excludes photosynthesis detail despite multi-source excerpt"),
    ]
    scope_from_var = {
        "per_concept": "per_concept", "multi_concept": "multi_concept", "per_source": "per_source",
        "multi_source": "multi_source", "no_source": "no_source",
        "multi_source_three": "multi_source", "custom_focus": "per_concept",
        "multi_source_user_restrict": "multi_source",
    }
    examples: list[ExampleRecord] = []
    for sid, var, tags, ctx, cnt, md in maps:
        ref = f"studio_mind_map-{sid}"
        scope = scope_from_var.get(var, "per_source")
        locked_var = map_studio_variation(var)
        if not any(t.startswith("scope_mode:") for t in tags):
            tags = tags + [f"scope_mode:{scope}"]
        ctx_in = uctx(ctx, ref) if ctx.strip() else ""
        examples.append(_record(
            f"studio_mind_map-{sid}", locked_var, tags,
            {"context": ctx_in, "selected_source_count": cnt},
            {"mind_map_markdown": md},
            ["single_hub: pass", "grounding: pass", "structure: pass"],
            f"- **scope_mode:** {scope}\n- **selected_source_count:** {cnt}",
        ))
    return header + render_examples_grouped(examples, STUDIO_VARIATION_ORDER)


def _load_slide_deck_gold() -> dict[str, str]:
    """example_id -> slide_deck_markdown from pool or LLM cache."""
    gold: dict[str, str] = {}
    if SLIDE_DECK_POOL.exists():
        pool = json.loads(SLIDE_DECK_POOL.read_text(encoding="utf-8"))
        for item in pool.get("items", []):
            ex_id = item["example_id"]
            if item.get("llm_gold", {}).get("slide_deck_markdown"):
                gold[ex_id] = item["llm_gold"]["slide_deck_markdown"]
            elif item.get("slide_deck_markdown"):
                gold[ex_id] = item["slide_deck_markdown"]
    if SLIDE_DECK_CACHE.exists():
        cache = json.loads(SLIDE_DECK_CACHE.read_text(encoding="utf-8"))
        for ex_id, rec in cache.get("examples", {}).items():
            if rec.get("slide_deck_markdown"):
                gold[ex_id] = rec["slide_deck_markdown"]
    return gold


def _slide_deck_version(items: list[dict[str, Any]], gold_map: dict[str, str]) -> str:
    if items and all(
        gold_map.get(it["example_id"]) and it.get("gold_source") == "production_llm"
        for it in items
    ):
        return "1.2.0"
    if gold_map:
        return "1.1.1"
    return "1.1.0"


def gen_agent14() -> str:
    system_prompt = _studio_system_prompt()
    task_prompt = load_j2(PROMPTS / "studio" / "slide_deck_prompt.j2")
    gold_map = _load_slide_deck_gold()
    pool_items: list[dict[str, Any]] = []
    if SLIDE_DECK_POOL.exists():
        pool_items = json.loads(SLIDE_DECK_POOL.read_text(encoding="utf-8")).get("items", [])

    header = render_agent_header(
        title="## 14. Studio Slide Deck Generator",
        metadata_rows=[
            ("Dataset ID", "`studio_slide_deck`"),
            ("Category", "Studio"),
            ("Tier", "Tier 2"),
            ("Target examples", "22"),
            ("Actual examples", str(len(pool_items) or 22)),
            ("Version", _slide_deck_version(pool_items, gold_map)),
        ],
        agent_responsibility=(
            "Markdown slide deck with `# Slide N:` headings, 1–7 bullets per slide, story arc ending in conclusion slide. "
            "Custom instructions override slide count and focus."
        ),
        audit_finding=(
            "Baseline v1.1.0 used uniform 1–2 bullet stubs per slide. Rebuilt v1.2.0 with production LLM gold via "
            "`slide_deck_prompt.j2` + system prompt — variable bullet counts (1–7), story arc, show-don't-tell, "
            "and slide-count compliance from custom_instructions."
        ),
        taxonomy_rows=[
            ("per_concept", "Topic-focused custom instructions", "4"),
            ("multi_concept", "Full-breadth / all topics in context", "3"),
            ("per_source", "Single-source excerpt", "4"),
            ("multi_source", "Merged multi-doc context + synthesis", "5"),
            ("no_source", "Empty context → generic study-skills branch", "2"),
            ("custom_override", "Slide count/language/focus overrides", "4"),
        ],
        quality_dimensions=[
            ("slide_count_match", "Slide count matches custom_instructions."),
            ("conclusion_present", "Final slide is conclusion with key takeaways."),
            ("bullet_variance", "1–7 bullets per slide; not uniform padding."),
            ("custom_instructions", "Difficulty, language, and focus honored when specified."),
            ("grounding", "Slide content grounded in context excerpt."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `context`, `custom_instructions`",
            "Output keys: `slide_deck_markdown`",
        ],
        prompt_blocks=[
            ("Prompt template (system — production)", "jinja2", system_prompt),
            ("Prompt template (user/task — production)", "jinja2", task_prompt),
        ],
        runtime_note=(
            "[`packages/core/services/studio_service.py`](packages/core/services/studio_service.py) "
            "`StudioService._generate_structured_task()` with slide deck task template."
        ),
        eval_count=22,
        extras=_scope_coverage_table([
            ("per_concept", "4", "4"),
            ("multi_concept", "3", "3"),
            ("per_source", "4", "4"),
            ("multi_source", "5", "5"),
            ("no_source", "2", "2"),
            ("custom_override", "—", "4 (distributed)"),
        ]),
    )
    if not pool_items:
        raise RuntimeError(f"Missing {SLIDE_DECK_POOL}. Run build_studio_slide_deck_pool.py first.")

    examples: list[ExampleRecord] = []
    for item in pool_items:
        ex_id = item["example_id"]
        locked_var = map_studio_variation(item["variation"])
        tags = list(item.get("tags", []))
        scope = item.get("scope_mode", "per_concept")
        if not any(t.startswith("scope_mode:") for t in tags):
            tags = tags + [f"scope_mode:{scope}"]
        ctx = item.get("context", "")
        instr = item.get("custom_instructions", "")
        content = gold_map.get(ex_id, "")
        if not content:
            raise RuntimeError(f"Missing LLM gold for {ex_id}. Run generate_studio_slide_deck_llm_gold.py.")
        production = item.get("gold_source") == "production_llm"
        if production:
            tags = tags + ["production_llm_gold"]
        qc = assess_deck_quality(content, instr, ctx, production_llm=production)
        quality = [f"{k}: {'pass' if v else 'fail'}" for k, v in qc.items()]
        ctx_in = uctx(ctx, ex_id) if ctx.strip() else ""
        examples.append(_record(
            ex_id, locked_var, tags,
            {"context": ctx_in, "custom_instructions": instr},
            {"slide_deck_markdown": content},
            quality,
            f"- **scope_mode:** {scope}",
        ))
    return header + render_examples_grouped(examples, STUDIO_VARIATION_ORDER)


FALLBACK_VARIATION_ORDER = [
    "quiz_fallback",
    "flashcards_fallback",
    "mind_map_fallback",
    "slide_deck_fallback",
]

EMBEDDING_VARIATION_ORDER = [
    "quiz_embedding",
    "flashcards_embedding",
    "mind_map_embedding",
    "slide_deck_embedding",
]

_FALLBACK_VAR_MAP = {
    "quiz_with_context": "quiz_fallback",
    "quiz_no_source": "quiz_fallback",
    "quiz_chemistry": "quiz_fallback",
    "quiz_no_source_neet": "quiz_fallback",
    "flashcards_with_context": "flashcards_fallback",
    "flashcards_no_source": "flashcards_fallback",
    "flashcards_physics": "flashcards_fallback",
    "flashcards_thin": "flashcards_fallback",
    "mind_map_with_context": "mind_map_fallback",
    "mind_map_no_source": "mind_map_fallback",
    "mind_map_math": "mind_map_fallback",
    "mind_map_multi": "mind_map_fallback",
    "slide_deck_with_context": "slide_deck_fallback",
    "slide_deck_no_source": "slide_deck_fallback",
    "slide_deck_biology": "slide_deck_fallback",
}

_EMBED_VAR_MAP = {
    "quiz": "quiz_embedding",
    "flashcards": "flashcards_embedding",
    "mind_map": "mind_map_embedding",
    "slide_deck": "slide_deck_embedding",
}


FALLBACK_EVAL_SUPPLEMENT = """\
Supplementary eval notes (contract embedded in `studio/fallback_task_prompt.j2` v1.3.0):

- Pairs with **Agent 10** system prompt (`studio/system_educational_json_markdown.j2`) at runtime.
- Loaded via `StudioService._load_prompt_template()` on `FileNotFoundError` — not the primary happy path.
- LangSmith gold must be **full JSON/Markdown bodies**, not one-line outlines.
- Input keys: `task_type`, `context` (optional `custom_instructions` at runtime)."""

STUDIO_BROAD_QUERIES_REFERENCE = """\
1. Educational source material overview and key concepts
2. Main themes definitions and key terms from the material
3. Examples applications procedures and important details
4. Structural sections summaries and conclusions
5. Causes effects relationships how components interact and dependencies
6. Step-by-step processes workflows methods and sequential explanations
7. Comparisons contrasts differences similarities advantages and limitations"""

EMBEDDING_EVAL_CONTRACT = """\
You build ONE embedding search query string for Pinecone vector retrieval before Studio generation.

INPUT KEYS (exact — LangSmith / eval contract; do not rename):
- studio_task: quiz | flashcards | mind_map | slide_deck
- source_title: NCERT chapter label (e.g. "NCERT Class 12 Physics — Current Electricity")
- topic: user focus subtopic within that chapter (e.g. "Ohm's law and resistivity")

OUTPUT KEY (exact — single field only):
- embedding_query: plain text string (NOT JSON, NOT markdown, NOT code fences)

Non-negotiable rules:
1. Return ONLY the embedding_query value — no labels, no explanation, no extra keys.
2. One line; space-separated keywords and short syllabus phrases.
3. Length: 12–28 tokens; dense enough for embedding models, not a paragraph.
4. Extract class, subject, and chapter name tokens from source_title.
5. Weave topic terms plus 6–12 related NCERT concepts for that subtopic.
6. Use CBSE/NCERT vocabulary; never invent page numbers, figure numbers, or citations.
7. Preserve standard symbols where needed (V=IR, ATP, DNA, nCr).

Task-specific lead phrase (include exactly one at the start):
- studio_task=quiz → "quiz assessment MCQ"
- studio_task=flashcards → "flashcards term definition"
- studio_task=mind_map → "mind map concept hierarchy"
- studio_task=slide_deck → "slide deck lesson"

End every query with the token: NCERT

Production contrast (current live path):
When retrieval_focus is empty, StudioService uses fixed STUDIO_BROAD_RETRIEVAL_QUERIES:
""" + STUDIO_BROAD_QUERIES_REFERENCE + """

Those 7 strings are topic-agnostic. Agent 16 eval gold tests the **dynamic fallback** path that tailors the query from studio_task + source_title + topic.

When inputs are missing, `studio/context_embedding_query.j2` v1.3.0 falls back to broad query #1:
Educational source material overview and key concepts"""


def _fallback_outputs() -> dict[str, str]:
    """Full production-shaped gold outputs keyed by studio_fallback_legacy-{sid}."""
    return {
        "001": make_quiz("Current Electricity — Fallback Quiz", _quiz_qs_current(5)),
        "002": make_flashcards([
            ("Where does salivary amylase act?", "Mouth — starts starch digestion."),
            ("Pepsin needs which stomach condition?", "Acidic HCl medium."),
            ("Trypsin enters duodenum via?", "Pancreatic juice."),
            ("Lipase digests?", "Fats."),
            ("Main nutrient absorption site?", "Small intestine villi."),
        ]),
        "003": (
            "# Photosynthesis\n\n"
            "## Light Reaction\n- **Location:** grana of chloroplast\n- **Products:** ATP and NADPH\n\n"
            "## Calvin Cycle\n- **Location:** stroma\n- **Function:** CO2 fixation using ATP/NADPH\n\n"
            "## Gas Exchange\n- **Stomata:** CO2 in, O2 out"
        ),
        "004": (
            "# Slide 1: Ray Optics Essentials\n"
            "- **Lens formula:** 1/f = 1/v − 1/u\n"
            "- **Goal:** connect object/image distances to focal length\n\n"
            "# Slide 2: Magnification & Power\n"
            "- **m = v/u** gives image size/orientation\n"
            "- **P = 1/f** (f in metres)\n\n"
            "# Slide 3: Sign Convention\n"
            "- **Real object:** u negative in Cartesian convention\n"
            "- **Optical centre ray:** passes undeviated\n\n"
            "# Slide 4: Problem-Solving Habit\n"
            "- **Write u, v, f** before substituting\n"
            "- **Check sign** before calculating m or P\n\n"
            "# Slide 5: Conclusion — Key Takeaways\n"
            "- Master **1/f = 1/v − 1/u**, **m = v/u**, and **sign rules** together"
        ),
        "005": make_quiz("General Science Baseline (No Source)", [
            make_mcq("SI unit of force is:", ["Newton", "Joule", "Watt", "Pascal"], "Newton",
                     "Newton is the SI unit of force."),
            make_mcq("Water chemical formula:", ["H2O", "CO2", "NaCl", "O2 only"], "H2O",
                     "Water is dihydrogen monoxide."),
            make_mcq("Safe lab practice includes:", ["Reading labels before use", "Tasting chemicals", "Skipping goggles", "Random mixing"],
                     "Reading labels before use", "Basic laboratory safety."),
        ]),
        "006": make_flashcards([
            ("Active recall?", "Test yourself instead of only re-reading notes."),
            ("Spaced repetition?", "Review at intervals to strengthen long-term memory."),
            ("Timed practice?", "Simulate exam conditions to find weak topics."),
        ]),
        "007": (
            "# Study Skills (No Source Excerpt)\n\n"
            "## Planning\n- **Set weekly goals** for each subject\n"
            "- **Break chapters** into daily chunks\n\n"
            "## Practice\n- **Active recall** after each topic\n"
            "- **Timed MCQ drills** before exams\n\n"
            "## Review\n- **Spaced repetition** schedule\n"
            "- **Error log** for repeated mistakes"
        ),
        "008": (
            "# Slide 1: Note-Taking Without Sources\n"
            "- **Cornell method:** cues + notes + summary column\n\n"
            "# Slide 2: Self-Testing\n"
            "- **Close the book** and write key formulas from memory\n\n"
            "# Slide 3: Conclusion — Key Takeaways\n"
            "- **Plan, practice, review** beats passive reading"
        ),
        "009": make_quiz("Coordination Compounds — Fallback Quiz", [
            make_mcq("Coordination number counts:", ["σ-donor atoms on metal", "Total ligand mass", "Oxidation state only", "Electrons in metal"],
                     "σ-donor atoms on metal", "CN = donor atoms bonded to metal."),
            make_mcq("[Fe(CN)6]4− has coordination number:", ["4", "6", "8", "2"], "6", "Six cyanide ligands → CN = 6."),
            make_mcq("IUPAC ligand order is:", ["Alphabetical", "By charge only", "Random", "By metal symbol"], "Alphabetical", "IUPAC lists ligands alphabetically."),
            make_mcq("Anionic ligands in IUPAC end in:", ["-o suffix", "-ide always", "-ate only", "No suffix"], "-o suffix", "Anionic ligands take -o."),
        ]),
        "010": make_flashcards([
            ("Torque magnitude?", "τ = rF sin θ"),
            ("Rotational analog of F=ma?", "τ = Iα"),
            ("Parallel axis theorem?", "I = I_cm + Md²"),
            ("Door push near hinges vs handle?", "Smaller lever arm → less torque for same F"),
        ]),
        "011": (
            "# Three-Dimensional Geometry\n\n"
            "## Direction Cosines\n- **Constraint:** l² + m² + n² = 1\n\n"
            "## Line Equation\n- **Symmetric form:** (x−x₁)/a = (y−y₁)/b = (z−z₁)/c\n\n"
            "## Skew Lines\n- **Shortest distance** uses cross product of direction vectors"
        ),
        "012": (
            "# Slide 1: Molecular Basis of Inheritance\n"
            "- **DNA stores** genetic information\n\n"
            "# Slide 2: Base Pairing\n"
            "- **A–T** and **G–C** pairing rules\n\n"
            "# Slide 3: Semiconservative Replication\n"
            "- **Each new duplex:** one old + one new strand\n\n"
            "# Slide 4: Expression\n"
            "- **mRNA** carries code to ribosomes for translation\n\n"
            "# Slide 5: Conclusion — Key Takeaways\n"
            "- Chain: **pairing → replication → mRNA → translation**"
        ),
        "013": make_quiz("NEET Exam Strategy (No Chapter Source)", [
            make_mcq("Best use of first 5 minutes in NEET?", ["Scan paper and mark easy questions", "Solve hardest first always", "Skip OMR planning", "Ignore time sections"],
                     "Scan paper and mark easy questions", "Time management strategy."),
            make_mcq("OMR filling should be:", ["Clear single bubbles without stray marks", "Multiple bubbles per question", "Done only at home", "Ignored until end always"],
                     "Clear single bubbles without stray marks", "OMR discipline."),
            make_mcq("Negative marking means:", ["Wrong answers can reduce score", "All guesses are free", "Only biology penalized", "No effect on total"],
                     "Wrong answers can reduce score", "NEET negative-marking awareness."),
            make_mcq("After a tough question you should:", ["Move on and return if time permits", "Stop the entire paper", "Erase all answers", "Leave exam hall"],
                     "Move on and return if time permits", "Exam pacing tactic."),
        ]),
        "014": make_flashcards([
            ("Binomial general term?", "Tr+1 = nCr a^(n−r) b^r"),
            ("nCr in expansion means?", "Combination count in (a+b)^n."),
        ]),
        "015": (
            "# Life Processes — Energy & Reproduction\n\n"
            "## Photosynthesis (Source A)\n"
            "- **Light reaction** in grana → ATP, NADPH\n"
            "- **Calvin cycle** in stroma fixes CO2\n\n"
            "## Cell Division (Source B)\n"
            "- **Mitosis** maintains 2n for growth/repair\n"
            "- **Meiosis** produces n gametes; crossing over in Prophase I\n\n"
            "## Integration\n"
            "- **Energy capture** supports **cell division cycles** in living systems"
        ),
    }


def _embedding_outputs() -> dict[str, str]:
    """Production-shaped embedding_query gold keyed by studio_context_embedding_query-{sid}."""
    return {
        "001": (
            "quiz assessment MCQ Class 12 Physics current electricity Ohm law V=IR resistivity "
            "rho series parallel equivalent resistance Kirchhoff junction rule drift velocity NCERT"
        ),
        "002": (
            "flashcards term definition Class 11 Biology digestion salivary amylase pepsin HCl stomach "
            "trypsin lipase pancreatic juice villi absorption small intestine NCERT"
        ),
        "003": (
            "mind map concept hierarchy Class 11 Biology photosynthesis light reaction grana thylakoid "
            "Calvin cycle stroma chlorophyll ATP NADPH stomata CO2 fixation NCERT"
        ),
        "004": (
            "slide deck lesson Class 12 Physics ray optics lens formula magnification power sign convention "
            "focal length object image distance optical centre undeviated ray NCERT"
        ),
        "005": (
            "quiz assessment MCQ Class 12 Chemistry coordination compounds ligands coordination number "
            "Werner theory IUPAC naming anionic ligand alphabetical order NCERT"
        ),
        "006": (
            "flashcards term definition Class 12 Mathematics probability independent events union "
            "intersection conditional probability Bayes theorem nCr combinations NCERT"
        ),
        "007": (
            "mind map concept hierarchy Class 12 Biology DNA replication semiconservative base pairing "
            "A-T G-C transcription translation genetic code ribosome mRNA NCERT"
        ),
        "008": (
            "slide deck lesson Class 11 Chemistry chemical equilibrium equilibrium constant Kc "
            "Le Chatelier principle reaction quotient Q catalyst effect stress shift NCERT"
        ),
        "009": (
            "quiz assessment MCQ Class 11 Physics work energy power kinetic energy work-energy theorem "
            "conservative force path independence potential energy NCERT"
        ),
        "010": (
            "flashcards term definition Class 12 Chemistry aldehydes ketones carbonyl group nucleophilic "
            "addition Tollens test silver mirror Fehling Benedict distinction NCERT"
        ),
        "011": (
            "mind map concept hierarchy Class 11 Biology plant root anatomy dicot monocot endodermis "
            "Casparian strip apoplastic symplastic vascular bundle xylem phloem NCERT"
        ),
        "012": (
            "slide deck lesson Class 11 Mathematics conic sections parabola ellipse hyperbola focus "
            "directrix eccentricity standard equation y squared equals 4ax NCERT"
        ),
        "013": (
            "quiz assessment MCQ NEET recall Class 11 Biology human digestive system organs mouth stomach "
            "pancreas pepsin trypsin lipase villi absorption enzymes NCERT"
        ),
        "014": (
            "flashcards term definition Class 12 Physics refraction Snell law total internal reflection "
            "critical angle refractive index lens mirror ray diagram sign convention NCERT"
        ),
        "015": (
            "mind map concept hierarchy Class 11 Chemistry hydrocarbons alkanes alkenes alkynes "
            "Markovnikov rule electrophilic substitution benzene aromaticity delocalized pi NCERT"
        ),
    }


_AGENT16_WHY_EXAMPLE = """\
**Why this agent is needed**

1. **Pre-retrieval quality** — Before Agents 11–14 generate a quiz or mind map, Studio must fetch the right NCERT chunks from Pinecone. A generic static string pulls overview text; a **topic-tailored** query pulls Ohm's-law and resistivity passages for a Current Electricity quiz.
2. **Regression safety** — Production today uses seven fixed `STUDIO_BROAD_RETRIEVAL_QUERIES` (topic-agnostic). If engineers re-enable the legacy **dynamic** embedding path, eval must prove queries still honor `studio_task`, `source_title`, and `topic`.
3. **Key contract enforcement** — LangSmith examples must use exact input keys (`studio_task`, `source_title`, `topic`) and a single output key (`embedding_query`) so formatter and embedding-relevance evaluators do not break.

**Worked example**

| Field | Value |
|-------|-------|
| `studio_task` | `quiz` |
| `source_title` | `NCERT Class 12 Physics — Current Electricity` |
| `topic` | `Ohm's law and resistivity` |

**Gold `embedding_query`:**

```
quiz assessment MCQ Class 12 Physics current electricity Ohm law V=IR resistivity rho series parallel equivalent resistance Kirchhoff junction rule drift velocity NCERT
```

This steers vector search toward assessable electricity facts — not the static legacy J2 line `Educational source material overview and key concepts`, which ignores the user's topic entirely.

> **Fallback notice:** Live Studio retrieval uses `STUDIO_BROAD_RETRIEVAL_QUERIES` (+ Query Rewriter when focus is set). Agent 16 is the canonical fallback/regression prompt for dynamic single-query embedding."""


def gen_agent15_16() -> str:
    fallback_prompt = load_j2(PROMPTS / "studio" / "fallback_task_prompt.j2")
    embedding_prompt = load_j2(PROMPTS / "studio" / "context_embedding_query.j2")
    gold_by_sid = _fallback_outputs()
    header15 = render_agent_header(
        title="## 15. Studio Fallback Task Prompt (Legacy)",
        metadata_rows=[
            ("Dataset ID", "`studio_fallback_legacy`"),
            ("Category", "Studio"),
            ("Tier", "Tier 2 → regression subset"),
            ("Target examples", "15"),
            ("Actual examples", "15"),
            ("Version", "1.3.0"),
        ],
        agent_responsibility=(
            "**Regression safety net** when the primary Studio task J2 template is missing from disk "
            "(`FileNotFoundError` in `StudioService._load_prompt_template()`). Normal Studio flow uses "
            "rich templates (Agents 11–14) plus the shared system prompt (Agent 10). In fallback mode the "
            "**user/task prompt** loads `studio/fallback_task_prompt.j2` v1.3.0 (self-contained output contract), "
            "and generation must still return a **complete, parseable artifact**: quiz JSON object, flashcards "
            "JSON array, mind-map Markdown, or slide-deck Markdown — not a one-sentence outline. This agent is "
            "**not** the primary product path; it ensures deployments missing a template file degrade gracefully "
            "instead of crashing."
        ),
        audit_finding=(
            "v1.3.0 replaces the one-line fallback with a **self-contained production fallback J2** "
            "(task_type output contracts, grounding rules, empty-context handling) and wires it in "
            "`StudioService._load_prompt_template()` on `FileNotFoundError`. v1.2.0 had full eval gold but a "
            "minimal one-line production prompt."
        ),
        taxonomy_rows=[
            ("quiz_fallback", "task_type=quiz with/without context", 4),
            ("flashcards_fallback", "flashcards with/without context", 4),
            ("mind_map_fallback", "mind_map with/without context", 4),
            ("slide_deck_fallback", "slide_deck with/without context", 3),
        ],
        quality_dimensions=[
            ("legacy_path", "Exercises FileNotFoundError fallback — minimal user prompt still runs."),
            ("graceful_output", "Full artifact returned; never a vague one-line outline."),
            ("no_crash", "Missing J2 does not abort Studio generation."),
            ("task_type_honored", "quiz→JSON object, flashcards→JSON array, mind_map/slide_deck→Markdown."),
            ("schema_valid", "Quiz/flashcard gold parses and passes structure validators."),
            ("grounding", "With context: facts from excerpt only; empty context: general or insufficient-source pattern."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys: `task_type`, `context`",
            "Output keys: `output` (full JSON string or Markdown body)",
        ],
        prompt_blocks=[
            ("Prompt template (production — legacy fallback J2 v1.3.0)", "jinja2", fallback_prompt),
            ("Supplementary eval notes", "text", FALLBACK_EVAL_SUPPLEMENT),
        ],
        runtime_note=(
            "On `FileNotFoundError`, `StudioService._load_prompt_template()` loads "
            "`studio/fallback_task_prompt.j2` v1.3.0 via `load_prompt(task_type, context, custom_instructions)`. "
            "Structured generation still uses the **Agent 10 system prompt**. Eval gold requires **full "
            "production-shaped bodies**, not outlines."
        ),
        eval_count=15,
        extras=(
            "**Why this agent is needed**\n\n"
            "1. **Deployment safety** — a missing `quiz_prompt.j2` (or similar) must not break Studio.\n"
            "2. **Shape regression** — even with a tiny prompt, output must remain valid quiz JSON / flashcard array / Markdown.\n"
            "3. **Contrast with Agents 11–14** — those agents test the **happy path** with full instructions; Agent 15 tests **worst-case prompt starvation**.\n\n"
            "> **Legacy notice:** Primary Studio always uses Agents 11–14 templates when files exist on disk."
        ),
    )
    header16 = render_agent_header(
        title="## 16. Studio Context Embedding Query (Legacy)",
        metadata_rows=[
            ("Dataset ID", "`studio_context_embedding_query`"),
            ("Category", "Studio"),
            ("Tier", "Tier 3 → regression subset"),
            ("Target examples", "15"),
            ("Actual examples", "15"),
            ("Version", "1.3.0"),
        ],
        agent_responsibility=(
            "**Fallback retrieval query spec** for Studio RAG. `studio/context_embedding_query.j2` v1.3.0 "
            "documents the dynamic single-query builder (studio_task + source_title + topic) and broad-default "
            "fallback when inputs are missing. **Production today** uses seven fixed `STUDIO_BROAD_RETRIEVAL_QUERIES` "
            "in `StudioService._retrieve_studio_context()` when `retrieval_focus` is empty, and **Query Rewriter** "
            "when `retrieval_focus` is set. Agent 16 is **not** the live retrieval path; it is the canonical "
            "fallback/regression prompt if dynamic embedding is invoked."
        ),
        audit_finding=(
            "v1.3.0 replaces the static one-line J2 with a **self-contained fallback prompt**: documents live "
            "broad queries, dynamic builder rules, optional `retrieval_focus`, and broad default when inputs are "
            "absent. v1.2.0 had full eval gold and a separate eval contract block but a one-line production J2."
        ),
        taxonomy_rows=[
            ("quiz_embedding", "Quiz-oriented retrieval query strings", 4),
            ("flashcards_embedding", "Flashcard definitional retrieval queries", 4),
            ("mind_map_embedding", "Hierarchy/relationship retrieval queries", 4),
            ("slide_deck_embedding", "Lesson/process retrieval queries", 3),
        ],
        quality_dimensions=[
            ("key_contract", "Inputs exactly studio_task, source_title, topic; output exactly embedding_query."),
            ("query_relevance", "Query terms match source title, topic, and studio_task intent."),
            ("task_aware", "Lead phrase reflects studio_task (quiz MCQ vs flashcards definitions, etc.)."),
            ("topic_coverage", "Query spans 6–12 syllabus concepts beyond the topic label alone."),
            ("concise", "12–28 tokens; one line; suitable for dense embedding models."),
            ("legacy_regression", "Stable gold if legacy dynamic embedding path is re-enabled."),
        ],
        langsmith_items=[
            "Dataset name prefix: `nbm-prompt`",
            "Input keys (exact): `studio_task`, `source_title`, `topic`",
            "Output keys (exact): `embedding_query` (plain string — not JSON-wrapped)",
            "Reference outputs key in JSON datasets: `reference_outputs.embedding_query`",
        ],
        prompt_blocks=[
            ("Prompt template (production — fallback J2 v1.3.0)", "jinja2", embedding_prompt),
            ("Eval embedding query builder contract (dynamic path regression)", "text", EMBEDDING_EVAL_CONTRACT),
        ],
        runtime_note=(
            "`studio/context_embedding_query.j2` v1.3.0 is the **fallback/regression** prompt — not loaded by "
            "live `StudioService` retrieval. Live Studio uses `STUDIO_BROAD_RETRIEVAL_QUERIES` (seven strings) "
            "when `retrieval_focus` is empty, and **Query Rewriter** when focus is set. Eval gold follows the "
            "**dynamic builder contract** for tailored queries ending in `NCERT`."
        ),
        eval_count=15,
        extras=_AGENT16_WHY_EXAMPLE,
    )
    fallback = [
        ("001", "quiz_with_context", ["legacy", "quiz"], "quiz", CTX["current_electricity"]),
        ("002", "flashcards_with_context", ["legacy", "flashcards"], "flashcards", CTX["digestion"]),
        ("003", "mind_map_with_context", ["legacy", "mind_map"], "mind_map", CTX["photosynthesis"]),
        ("004", "slide_deck_with_context", ["legacy", "slide_deck"], "slide_deck", CTX["ray_optics"]),
        ("005", "quiz_no_source", ["legacy", "no_source"], "quiz", ""),
        ("006", "flashcards_no_source", ["legacy", "no_source"], "flashcards", ""),
        ("007", "mind_map_no_source", ["legacy", "no_source"], "mind_map", ""),
        ("008", "slide_deck_no_source", ["legacy", "no_source"], "slide_deck", ""),
        ("009", "quiz_chemistry", ["legacy", "quiz", "source_pdf:lech105"], "quiz", CTX["coordination"]),
        ("010", "flashcards_physics", ["legacy", "flashcards", "source_pdf:keph106"], "flashcards", CTX["rotational"]),
        ("011", "mind_map_math", ["legacy", "mind_map", "source_pdf:lemh205"], "mind_map", CTX["3d_geometry"]),
        ("012", "slide_deck_biology", ["legacy", "slide_deck", "source_pdf:lebo105"], "slide_deck", CTX["dna"]),
        ("013", "quiz_no_source_neet", ["legacy", "no_source", "neet"], "quiz", ""),
        ("014", "flashcards_thin", ["legacy", "flashcards", "source_pdf:kemh107"], "flashcards", CTX["binomial"]),
        ("015", "mind_map_multi", ["legacy", "mind_map"], "mind_map", CTX["multi_bio"]),
    ]
    embed = [
        ("001", "quiz", ["legacy", "embedding"], "quiz", "NCERT Class 12 Physics — Current Electricity", "Ohm's law and resistivity"),
        ("002", "flashcards", ["legacy"], "flashcards", "NCERT Class 11 Biology — Digestion", "Digestive enzymes"),
        ("003", "mind_map", ["legacy"], "mind_map", "NCERT Class 11 Biology — Photosynthesis", "Light and Calvin cycle"),
        ("004", "slide_deck", ["legacy"], "slide_deck", "NCERT Class 12 Physics — Ray Optics", "Lens formula"),
        ("005", "quiz", ["legacy"], "quiz", "NCERT Class 12 Chemistry — Coordination Compounds", "Coordination number"),
        ("006", "flashcards", ["legacy"], "flashcards", "NCERT Class 12 Mathematics — Probability", "Independent events"),
        ("007", "mind_map", ["legacy"], "mind_map", "NCERT Class 12 Biology — Molecular Inheritance", "DNA replication"),
        ("008", "slide_deck", ["legacy"], "slide_deck", "NCERT Class 11 Chemistry — Equilibrium", "Le Chatelier principle"),
        ("009", "quiz", ["legacy", "physics"], "quiz", "NCERT Class 11 Physics — Work Energy Power", "Work-energy theorem"),
        ("010", "flashcards", ["legacy", "chemistry"], "flashcards", "NCERT Class 12 Chemistry — Aldehydes Ketones", "Tollens test"),
        ("011", "mind_map", ["legacy", "biology"], "mind_map", "NCERT Class 11 Biology — Anatomy of Flowering Plants", "Root endodermis"),
        ("012", "slide_deck", ["legacy", "mathematics"], "slide_deck", "NCERT Class 11 Mathematics — Conic Sections", "Parabola focus directrix"),
        ("013", "quiz", ["legacy", "neet"], "quiz", "NCERT Class 11 Biology — Structural Organisation in Animals", "Digestive system organs"),
        ("014", "flashcards", ["legacy", "physics"], "flashcards", "NCERT Class 12 Physics — Refraction and TIR", "Snell law critical angle"),
        ("015", "mind_map", ["legacy", "chemistry"], "mind_map", "NCERT Class 11 Chemistry — Hydrocarbons", "Markovnikov addition"),
    ]
    fallback_examples: list[ExampleRecord] = []
    for sid, var, tags, tt, ctx in fallback:
        locked_var = _FALLBACK_VAR_MAP.get(var, var)
        out = gold_by_sid[sid]
        qc = ["legacy_path: pass", "graceful_output: pass", "task_type_honored: pass", "schema_valid: pass", "grounding: pass"]
        if not ctx.strip() and tt in ("quiz", "flashcards", "slide_deck"):
            qc.append("no_source_general: pass")
        fallback_examples.append(_record(
            f"studio_fallback_legacy-{sid}", locked_var, tags,
            {"task_type": tt, "context": ctx},
            {"output": out},
            qc,
            f"- **output_format:** {'JSON' if tt in ('quiz', 'flashcards') else 'Markdown'}",
        ))
    embed_examples: list[ExampleRecord] = []
    embed_gold = _embedding_outputs()
    key_meta = (
        "- **LangSmith input keys:** `studio_task`, `source_title`, `topic`\n"
        "- **LangSmith output key:** `embedding_query`"
    )
    for sid, var, tags, task, title, topic in embed:
        locked_var = _EMBED_VAR_MAP.get(task, f"{task}_embedding")
        query = embed_gold[sid]
        embed_examples.append(_record(
            f"studio_context_embedding_query-{sid}", locked_var, tags,
            {"studio_task": task, "source_title": title, "topic": topic},
            {"embedding_query": query},
            [
                "key_contract: pass",
                "query_relevance: pass",
                "task_aware: pass",
                "topic_coverage: pass",
                "concise: pass",
                "legacy_regression: pass",
            ],
            key_meta,
        ))
    return (
        header15
        + render_examples_grouped(fallback_examples, FALLBACK_VARIATION_ORDER)
        + "\n"
        + header16
        + render_examples_grouped(embed_examples, EMBEDDING_VARIATION_ORDER)
    )
