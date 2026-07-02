"""Curated document, chunk, and map-reduce sources for Agents 26–30 eval pool."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "scripts" / "problem_solver_question_bank.json"

# 13 slots — diagram variation removed
VARIATION_SLOTS_13: list[str] = [
    "numerical", "numerical", "conversational", "conversational",
    "cbse", "cbse", "neet", "jee",
    "multi_part", "conceptual", "case_study", "ncert_strict", "proof", "typo",
][:13]

# Back-compat alias for imports
VARIATION_SLOTS_15 = VARIATION_SLOTS_13

REDUCE_USER_MESSAGES: list[str] = [
    "Summarize the entire document for exam revision.",
    "List the key formulas and definitions I should remember.",
    "What are the main topics covered across all sections?",
    "Give me a structured overview with bullet points for each part.",
    "Explain how the sections connect for NEET preparation.",
    "Create concise revision notes from the whole chapter.",
    "What should I focus on for board exam questions?",
    "Compare the main ideas in each section briefly.",
    "Summarize for a 5-minute oral recap.",
    "Highlight definitions, procedures, and examples from all parts.",
    "Make exam-oriented notes covering every section.",
    "What are the critical takeaways from each part?",
    "Summarize the document without missing any major section.",
    "Give a JEE-style quick recap of all parts.",
    "Prepare short notes I can paste into my notebook.",
]

NCERT_CHAPTER_DOCS: list[dict[str, Any]] = [
    {
        "doc_id": "ncert-phy-12-ch3",
        "header": "NCERT Class 12 Physics Ch.3 Current Electricity",
        "subject": "physics", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "3.1 Introduction. Electric current is the flow of electric charge through a conductor. "
            "3.2 Electric Current. The current I = dQ/dt; drift velocity and mobility relate microscopic "
            "motion to macroscopic current. Ohm's law: V = IR for ohmic conductors at constant temperature. "
            "3.3 Ohm's Law and Resistance. Resistivity ρ = RA/L; temperature dependence of resistance. "
            "3.4 Electrical Energy and Power. P = VI = I²R; heating effect Joule's law. "
            "3.5 Cells in Series and Parallel. EMF, internal resistance, terminal voltage. "
            "3.6 Kirchhoff's Rules. Junction rule ΣI_in = ΣI_out; loop rule ΣΔV = 0. "
            "Example 3.1: Finding current in a series circuit. Example 3.2: Wheatstone bridge balance. "
            "Exercise 3.1–3.15 on combination of resistors and meter bridge."
        ),
    },
    {
        "doc_id": "ncert-bio-11-ch16",
        "header": "NCERT Class 11 Biology Ch.16 Digestion and Absorption",
        "subject": "biology", "exam_type": "cbse", "class_num": "11", "is_ncert": True,
        "document_text": (
            "16.1 Digestive System. Alimentary canal and associated glands. "
            "16.2 Digestion of Food. Carbohydrates: salivary amylase in mouth; pancreatic amylase. "
            "Proteins: pepsin in stomach (HCl activates pepsinogen); trypsin in duodenum. "
            "Fats: bile emulsification; lipase action. "
            "16.3 Absorption. Villi and microvilli increase surface area; absorption in small intestine. "
            "Table 16.1: Enzymes, site of action, and products. "
            "Activity 16.1: Testing action of salivary amylase on starch. "
            "Exercise questions on disorders of digestion and enzyme specificity."
        ),
    },
    {
        "doc_id": "ncert-chem-12-ch4",
        "header": "NCERT Class 12 Chemistry Ch.4 Chemical Bonding",
        "subject": "chemistry", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "4.1 Kossel-Lewis approach. Octet rule and limitations. "
            "4.2 Ionic Bonding. Lattice enthalpy; Born-Haber cycle. "
            "4.3 Covalent Bonding. VSEPR theory predicts geometry from electron pair repulsion. "
            "4.4 Valence Bond Theory. Hybridisation sp, sp², sp³; sigma and pi bonds. "
            "4.5 Molecular Orbital Theory. Bond order; paramagnetic vs diamagnetic. "
            "Example 4.1: NH₃ pyramidal geometry. Example 4.2: O₂ MO configuration. "
            "Exercise 4.1–4.12 on polarity, dipole moment, and hydrogen bonding."
        ),
    },
    {
        "doc_id": "ncert-math-12-ch7",
        "header": "NCERT Class 12 Mathematics Ch.7 Integrals",
        "subject": "mathematics", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "7.1 Integration as inverse of differentiation. Indefinite integral ∫f(x)dx = F(x) + C. "
            "7.2 Methods: substitution, partial fractions, integration by parts. "
            "7.3 Definite integrals. Fundamental theorem: ∫ₐᵇ f(x)dx = F(b) − F(a). "
            "7.4 Area under a curve between x = a and x = b. "
            "Example 7.1: ∫ x√(1−x²) dx by substitution. Example 7.2: Area bounded by parabola. "
            "Theorem 7.1: Properties of definite integrals. Exercise 7.1–7.20."
        ),
    },
    {
        "doc_id": "ncert-bio-12-ch6",
        "header": "NCERT Class 12 Biology Ch.6 Molecular Basis of Inheritance",
        "subject": "biology", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "6.1 The DNA. Double helix; A–T and G–C base pairing. Antiparallel strands. "
            "6.2 Search for Genetic Material. Griffith, Avery, Hershey-Chase experiments. "
            "6.3 DNA Replication. Semiconservative model; leading and lagging strands; Okazaki fragments. "
            "6.4 Transcription. mRNA synthesis; template strand. "
            "6.5 Genetic Code. Triplet codons; degeneracy; start/stop codons. "
            "Figure 6.5: Replication fork. Exercise 6.1–6.10 on central dogma and mutations."
        ),
    },
    {
        "doc_id": "ncert-phy-11-ch7",
        "header": "NCERT Class 11 Physics Ch.7 Gravitation",
        "subject": "physics", "exam_type": "cbse", "class_num": "11", "is_ncert": True,
        "document_text": (
            "7.1 Kepler's laws of planetary motion. T² ∝ r³. "
            "7.2 Universal law of gravitation F = Gm₁m₂/r². "
            "7.3 Acceleration due to gravity g = GM/R²; variation with altitude and depth. "
            "7.4 Gravitational potential energy. Escape velocity v_e = √(2gR). "
            "Example 7.1: Satellite orbital speed. Example 7.2: Energy of satellite. "
            "Exercise 7.1–7.15 on orbits and gravitational field."
        ),
    },
    {
        "doc_id": "ncert-chem-11-ch7",
        "header": "NCERT Class 11 Chemistry Ch.7 Equilibrium",
        "subject": "chemistry", "exam_type": "cbse", "class_num": "11", "is_ncert": True,
        "document_text": (
            "7.1 Equilibrium in physical processes. Solid-liquid, liquid-vapour equilibrium. "
            "7.2 Chemical equilibrium. Kc = [products]/[reactants]; homogeneous and heterogeneous. "
            "7.3 Le Chatelier's principle. Effect of concentration, pressure, temperature. "
            "7.4 Ionic equilibrium. Ka, Kb, Kw; pH scale; buffer solutions. "
            "Example 7.1: Calculating Kc from equilibrium concentrations. "
            "Exercise 7.1–7.18 on Q vs K and degree of dissociation."
        ),
    },
    {
        "doc_id": "ncert-sci-10-ch12",
        "header": "NCERT Class 10 Science Ch.12 Electricity",
        "subject": "science", "exam_type": "cbse", "class_num": "10", "is_ncert": True,
        "document_text": (
            "12.1 Electric current and circuit. Ammeter, voltmeter, switch. "
            "12.2 Ohm's law V = IR. Resistance R = ρL/A. "
            "12.3 Factors affecting resistance. Series: R = R₁+R₂; parallel: 1/R = 1/R₁+1/R₂. "
            "12.4 Heating effect. H = I²Rt; electric fuse. "
            "12.5 Electric power P = VI. Commercial unit kWh. "
            "Activity 12.1: Compare current in series vs parallel. Exercise 12.1–12.10."
        ),
    },
    {
        "doc_id": "ncert-math-10-ch4",
        "header": "NCERT Class 10 Mathematics Ch.4 Quadratic Equations",
        "subject": "mathematics", "exam_type": "cbse", "class_num": "10", "is_ncert": True,
        "document_text": (
            "4.1 Standard form ax²+bx+c=0. Roots by factorisation and quadratic formula. "
            "4.2 Discriminant D = b²−4ac determines nature of roots. "
            "4.3 Sum and product of roots: −b/a and c/a. "
            "4.4 Word problems on area, speed, and consecutive integers. "
            "Example 4.1: Finding roots when D > 0. Example 4.2: No real roots when D < 0. "
            "Exercise 4.1–4.4."
        ),
    },
    {
        "doc_id": "ncert-bio-11-ch13",
        "header": "NCERT Class 11 Biology Ch.13 Photosynthesis",
        "subject": "biology", "exam_type": "cbse", "class_num": "11", "is_ncert": True,
        "document_text": (
            "13.1 Photosynthesis as anabolic process. 6CO₂+6H₂O → C₆H₁₂O₆+6O₂. "
            "13.2 Light reaction in grana: photolysis, ATP, NADPH. "
            "13.3 Calvin cycle in stroma; RuBisCO; C3 pathway. "
            "13.4 C4 pathway in maize and sugarcane; Kranz anatomy. "
            "Figure 13.4: Z-scheme of light reaction. Table 13.1: Cyclic vs non-cyclic photophosphorylation. "
            "Exercise 13.1–13.8."
        ),
    },
    {
        "doc_id": "ncert-phy-12-ch9",
        "header": "NCERT Class 12 Physics Ch.9 Ray Optics",
        "subject": "physics", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "9.1 Reflection; mirror formula 1/f = 1/v + 1/u. "
            "9.2 Refraction; Snell's law n₁ sin i = n₂ sin r. "
            "9.3 Total internal reflection; critical angle. "
            "9.4 Lens formula 1/f = 1/v − 1/u; magnification m = v/u. "
            "9.5 Prism deviation; dispersive power. "
            "Figure 9.12: Ray diagram for convex lens. Example 9.3: Image position. Exercise 9.1–9.15."
        ),
    },
    {
        "doc_id": "ncert-chem-12-ch3",
        "header": "NCERT Class 12 Chemistry Ch.3 Electrochemistry",
        "subject": "chemistry", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "3.1 Electrochemical cells. Anode oxidation; cathode reduction. "
            "3.2 Standard electrode potential E°. Cell EMF E°cell = E°cathode − E°anode. "
            "3.3 Nernst equation links EMF to concentration. "
            "3.4 Conductance and molar conductivity; Kohlrausch law. "
            "3.5 Batteries and fuel cells. Corrosion as electrochemical process. "
            "Example 3.1: Calculate Ecell at non-standard concentrations. Exercise 3.1–3.12."
        ),
    },
    {
        "doc_id": "ncert-eco-12-ch2",
        "header": "NCERT Class 12 Economics Ch.2 National Income",
        "subject": "economics", "exam_type": "cbse", "class_num": "12", "is_ncert": True,
        "document_text": (
            "2.1 Circular flow of income. Factor payments and expenditure. "
            "2.2 GDP at market prices; GNP = GDP + NFIA. "
            "2.3 NDP and NNP; depreciation. "
            "2.4 Real vs nominal GDP; GDP deflator. "
            "2.5 Methods of measuring national income: product, income, expenditure. "
            "Table 2.1: Relationship between macro aggregates. Exercise 2.1–2.8."
        ),
    },
    {
        "doc_id": "ncert-civics-10-ch3",
        "header": "NCERT Class 10 Civics Ch.3 Gender Religion and Caste",
        "subject": "civics", "exam_type": "cbse", "class_num": "10", "is_ncert": True,
        "document_text": (
            "3.1 Gender and politics. Public/private division; women's political representation. "
            "3.2 Religion communalism vs secularism in India. "
            "3.3 Caste and politics. Reservation policy; caste-based mobilisation. "
            "Case study: Women's reservation bill debate. "
            "Exercise: Analyse how social divisions affect electoral outcomes."
        ),
    },
    {
        "doc_id": "ncert-math-11-ch7",
        "header": "NCERT Class 11 Mathematics Ch.7 Permutations and Combinations",
        "subject": "mathematics", "exam_type": "cbse", "class_num": "11", "is_ncert": True,
        "document_text": (
            "7.1 Fundamental principle of counting. Multiplication rule. "
            "7.2 Permutations nPr = n!/(n−r)!. Circular permutations. "
            "7.3 Combinations nCr = n!/[(n−r)!r!]. "
            "7.4 Applications to binomial coefficients and probability. "
            "Example 7.1: Arrangements with repetition. Example 7.2: Selection problems. "
            "Exercise 7.1–7.10."
        ),
    },
]

CHUNK_SPECS: list[dict[str, Any]] = [
    {"doc_id": "ncert-phy-12-ch3", "chunk_content": "Ohm's law states that V = IR for metallic conductors when temperature remains constant. Resistivity ρ = RA/L relates material property to geometry.", "chunk_type_hint": "definition"},
    {"doc_id": "ncert-bio-11-ch16", "chunk_content": "Pepsin is activated in the acidic environment of the stomach; trypsin acts in the alkaline duodenum after pancreatic secretion.", "chunk_type_hint": "procedure"},
    {"doc_id": "ncert-chem-12-ch4", "chunk_content": "VSEPR theory predicts molecular geometry from repulsion between valence electron pairs; NH₃ has pyramidal shape with a lone pair.", "chunk_type_hint": "definition"},
    {"doc_id": "ncert-math-12-ch7", "chunk_content": "The definite integral ∫ₐᵇ f(x)dx equals F(b)−F(a) where F is an antiderivative of f, linking area to accumulation.", "chunk_type_hint": "formula"},
    {"doc_id": "ncert-bio-12-ch6", "chunk_content": "DNA replication is semiconservative: each new duplex has one parental strand and one newly synthesised strand at the replication fork.", "chunk_type_hint": "definition"},
    {"doc_id": "ncert-phy-11-ch7", "chunk_content": "Escape velocity v_e = √(2gR) is the minimum speed for an object to leave a planet's gravitational field without further propulsion.", "chunk_type_hint": "formula"},
    {"doc_id": "ncert-chem-11-ch7", "chunk_content": "Le Chatelier's principle: a system at equilibrium opposes imposed stress by shifting to partially counteract the change in concentration, pressure, or temperature.", "chunk_type_hint": "definition"},
    {"doc_id": "ncert-sci-10-ch12", "chunk_content": "In a series circuit the same current flows through each resistor; the supply voltage divides as V = V₁ + V₂ across components.", "chunk_type_hint": "argument"},
    {"doc_id": "ncert-math-10-ch4", "chunk_content": "For ax²+bx+c=0, discriminant D=b²−4ac: D>0 two distinct real roots, D=0 equal roots, D<0 no real roots.", "chunk_type_hint": "formula"},
    {"doc_id": "ncert-bio-11-ch13", "chunk_content": "The Calvin cycle in the stroma fixes CO₂ using ATP and NADPH produced by the light-dependent reactions in the grana.", "chunk_type_hint": "procedure"},
    {"doc_id": "ncert-phy-12-ch9", "chunk_content": "For a convex lens with real object, object distance u is negative; image distance v is positive for a real image on the opposite side.", "chunk_type_hint": "definition"},
    {"doc_id": "ncert-chem-12-ch3", "chunk_content": "At equilibrium of a galvanic cell, the Nernst equation E = E° − (0.0591/n)log Q relates EMF to ion concentrations at 298 K.", "chunk_type_hint": "formula"},
    {"doc_id": "ncert-eco-12-ch2", "chunk_content": "GNP equals GDP plus Net Factor Income from Abroad (NFIA), capturing income earned by residents regardless of geographic production.", "chunk_type_hint": "definition"},
    {"doc_id": "ncert-civics-10-ch3", "chunk_content": "Indian secularism implies the state has no official religion and treats all religions equally in public policy while allowing religious freedom.", "chunk_type_hint": "argument"},
    {"doc_id": "ncert-math-11-ch7", "chunk_content": "The number of ways to choose r objects from n distinct objects without order is nCr = n!/[(n−r)!r!].", "chunk_type_hint": "formula"},
]


def _split_parts(text: str, n: int = 4) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    if len(sentences) < n:
        return sentences + [text[i : i + 200] for i in range(0, min(len(text), 600), 200)][:n]
    chunk_size = max(1, len(sentences) // n)
    parts: list[str] = []
    for i in range(0, len(sentences), chunk_size):
        block = " ".join(sentences[i : i + chunk_size])
        if block:
            parts.append(block[:1200])
        if len(parts) >= n:
            break
    while len(parts) < 3:
        parts.append(sentences[min(len(parts), len(sentences) - 1)])
    return parts[: max(3, min(6, n))]


def load_bank_upload_documents(limit: int = 20) -> list[dict[str, Any]]:
    if not BANK_PATH.exists():
        return []
    bank = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    by_page: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for q in bank["questions"]:
        by_page[(q["source_key"], int(q["page"]))].append(q)

    docs: list[dict[str, Any]] = []
    for (sk, page), qs in sorted(by_page.items()):
        raw = (qs[0].get("raw_text") or "").strip()
        if len(raw) < 120:
            raw = "\n".join(q["problem_text_normalized"] for q in qs[:6])
        if len(raw) < 80:
            continue
        exam = "cbse"
        if sk.startswith("jee"):
            exam = "jee"
        elif sk.startswith("neet"):
            exam = "neet"
        subj = qs[0].get("subject", "science")
        header = f"{exam.upper()} {subj.title()} — {sk} page {page}"
        docs.append({
            "doc_id": f"upload-{sk}-p{page}",
            "header": header,
            "document_text": raw[:4000],
            "subject": subj,
            "exam_type": exam,
            "class_num": qs[0].get("class_num", "12"),
            "is_ncert": False,
            "source_key": sk,
            "page": page,
        })
        if len(docs) >= limit:
            break
    return docs


def get_document_by_id(doc_id: str) -> dict[str, Any] | None:
    for d in NCERT_CHAPTER_DOCS + load_bank_upload_documents(30):
        if d["doc_id"] == doc_id:
            return d
    return None


def all_ncert_documents() -> list[dict[str, Any]]:
    return list(NCERT_CHAPTER_DOCS)


def all_upload_documents() -> list[dict[str, Any]]:
    bank = load_bank_upload_documents(30)
    return bank[:13] if len(bank) >= 13 else bank


def chunk_entries() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, spec in enumerate(CHUNK_SPECS[:13]):
        doc = get_document_by_id(spec["doc_id"])
        if not doc:
            continue
        out.append({
            "doc_id": spec["doc_id"],
            "variation": VARIATION_SLOTS_13[i],
            "whole_document": doc["header"] + ". " + doc["document_text"][:2000],
            "chunk_content": spec["chunk_content"],
            "chunk_type_hint": spec["chunk_type_hint"],
            "target_context_tokens": 80,
            "target_summary_tokens": 40,
            "target_concept_terms": 5,
            "subject": doc["subject"],
            "exam_type": doc["exam_type"],
        })
    return out


def map_reduce_chains() -> list[dict[str, Any]]:
    chains: list[dict[str, Any]] = []
    for i, doc in enumerate(NCERT_CHAPTER_DOCS[:13]):
        parts = _split_parts(doc["document_text"], n=3 + (i % 3))
        chains.append({
            "doc_id": doc["doc_id"],
            "variation": VARIATION_SLOTS_13[i],
            "parts": parts,
            "user_message": REDUCE_USER_MESSAGES[i],
            "subject": doc["subject"],
            "exam_type": doc["exam_type"],
            "header": doc["header"],
        })
    return chains
