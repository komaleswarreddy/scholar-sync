"""Curated NCERT-aligned tutor scopes and exchanges for Agents 23–24 eval pool."""

from __future__ import annotations

from typing import Any

# class, subject_label, subject_key, chapter_no, chapter_title, concept, ncert_context, variation
TUTOR_BOOTSTRAP_SCOPES: list[dict[str, Any]] = [
    {
        "class_num": 10, "subject_label": "Science", "subject_key": "science",
        "chapter_no": 12, "chapter_title": "Electricity", "concept": "Ohm's law and resistance",
        "ncert_context": (
            "NCERT Class 10 Science Ch.12: Ohm's law V=IR at constant temperature. "
            "Resistance R=ρL/A. Resistors in series add; in parallel reciprocals add. "
            "Electric power P=VI=I²R. Household circuits use 220 V AC."
        ),
        "variation": "numerical",
    },
    {
        "class_num": 11, "subject_label": "Biology", "subject_key": "biology",
        "chapter_no": 16, "chapter_title": "Digestion and Absorption", "concept": None,
        "ncert_context": (
            "NCERT Class 11 Biology Ch.16: Salivary amylase in mouth. Stomach: HCl and pepsin. "
            "Pancreatic juice: trypsin, lipase, amylase. Absorption in small intestine villi and microvilli."
        ),
        "variation": "conversational",
    },
    {
        "class_num": 12, "subject_label": "Physics", "subject_key": "physics",
        "chapter_no": 9, "chapter_title": "Ray Optics and Optical Instruments", "concept": "Lens formula",
        "ncert_context": (
            "NCERT Class 12 Physics Ch.9: Lens formula 1/f=1/v-1/u. Magnification m=v/u. "
            "Power P=1/f (f in metres). Sign convention: object distance u negative for real objects."
        ),
        "variation": "diagram",
    },
    {
        "class_num": 10, "subject_label": "Mathematics", "subject_key": "mathematics",
        "chapter_no": 4, "chapter_title": "Quadratic Equations", "concept": None,
        "ncert_context": (
            "NCERT Class 10 Maths Ch.4: ax²+bx+c=0 roots via quadratic formula. "
            "Discriminant D=b²-4ac determines nature of roots. Sum of roots=-b/a; product=c/a."
        ),
        "variation": "cbse",
    },
    {
        "class_num": 12, "subject_label": "Chemistry", "subject_key": "chemistry",
        "chapter_no": 4, "chapter_title": "Chemical Bonding and Molecular Structure", "concept": "VSEPR theory",
        "ncert_context": (
            "NCERT Class 12 Chemistry Ch.4: Ionic, covalent, and metallic bonds. "
            "VSEPR predicts geometry from electron pairs. Hybridisation sp, sp², sp³."
        ),
        "variation": "neet",
    },
    {
        "class_num": 12, "subject_label": "Physics", "subject_key": "physics",
        "chapter_no": 3, "chapter_title": "Current Electricity", "concept": "Kirchhoff's laws",
        "ncert_context": (
            "NCERT Class 12 Physics Ch.3: Ohm's law V=IR. Resistivity ρ=RA/L. "
            "Kirchhoff junction rule: ΣI_in=ΣI_out. Loop rule: ΣΔV=0. Wheatstone bridge for unknown R."
        ),
        "variation": "jee",
    },
    {
        "class_num": 11, "subject_label": "Chemistry", "subject_key": "chemistry",
        "chapter_no": 7, "chapter_title": "Equilibrium", "concept": "Le Chatelier's principle",
        "ncert_context": (
            "NCERT Class 11 Chemistry Ch.7: Kc=[products]/[reactants]. "
            "Le Chatelier: system opposes stress. Catalyst does not change K. Ionic equilibrium Ka, Kb, Kw."
        ),
        "variation": "multi_part",
    },
    {
        "class_num": 12, "subject_label": "Biology", "subject_key": "biology",
        "chapter_no": 6, "chapter_title": "Molecular Basis of Inheritance", "concept": "DNA replication",
        "ncert_context": (
            "NCERT Class 12 Biology Ch.6: DNA double helix A-T, G-C. Semiconservative replication. "
            "Central dogma: DNA→RNA→protein. Genetic code is triplet, degenerate."
        ),
        "variation": "conceptual",
    },
    {
        "class_num": 10, "subject_label": "Civics", "subject_key": "civics-polity",
        "chapter_no": 3, "chapter_title": "Gender, Religion and Caste", "concept": None,
        "ncert_context": (
            "NCERT Class 10 Civics Ch.3: Gender division is social, not biological. "
            "Secularism: state has no official religion. Caste inequalities persist; reservation policies."
        ),
        "variation": "case_study",
    },
    {
        "class_num": 12, "subject_label": "Economics", "subject_key": "economics",
        "chapter_no": 2, "chapter_title": "National Income Accounting", "concept": "GDP vs GNP",
        "ncert_context": (
            "NCERT Class 12 Economics Ch.2: GDP at market prices. GNP=GDP+NFIA. "
            "Circular flow of income. Depreciation deducted for NDP."
        ),
        "variation": "ncert_strict",
    },
    {
        "class_num": 11, "subject_label": "Physics", "subject_key": "physics",
        "chapter_no": 7, "chapter_title": "Gravitation", "concept": "Kepler's laws",
        "ncert_context": (
            "NCERT Class 11 Physics Ch.7: Universal gravitation F=Gm₁m₂/r². "
            "g=GM/R². Kepler's laws for planetary motion. Escape velocity v_e=√(2gR)."
        ),
        "variation": "typo",
    },
    {
        "class_num": 12, "subject_label": "Mathematics", "subject_key": "mathematics",
        "chapter_no": 7, "chapter_title": "Integrals", "concept": "Definite integrals",
        "ncert_context": (
            "NCERT Class 12 Maths Ch.7: ∫x^n dx=x^(n+1)/(n+1)+C, n≠-1. "
            "Fundamental theorem links definite integral to antiderivative. Area under curve."
        ),
        "variation": "proof",
    },
    {
        "class_num": 10, "subject_label": "Geography", "subject_key": "geography",
        "chapter_no": 1, "chapter_title": "Resources and Development", "concept": None,
        "ncert_context": (
            "NCERT Class 10 Geography Ch.1: Resource types: renewable, non-renewable. "
            "Sustainable development balances present and future needs. Soil erosion and conservation."
        ),
        "variation": "conversational",
    },
    {
        "class_num": 11, "subject_label": "Biology", "subject_key": "biology",
        "chapter_no": 13, "chapter_title": "Photosynthesis in Higher Plants", "concept": "Calvin cycle",
        "ncert_context": (
            "NCERT Class 11 Biology Ch.13: Light reaction in grana produces ATP, NADPH. "
            "Calvin cycle in stroma fixes CO₂. C3, C4 pathways differ in carbon fixation."
        ),
        "variation": "diagram",
    },
    {
        "class_num": 12, "subject_label": "Chemistry", "subject_key": "chemistry",
        "chapter_no": 3, "chapter_title": "Electrochemistry", "concept": "Nernst equation",
        "ncert_context": (
            "NCERT Class 12 Chemistry Ch.3: Galvanic cell: anode oxidation, cathode reduction. "
            "E°cell=E°cathode-E°anode. Nernst equation links EMF to concentration."
        ),
        "variation": "numerical",
    },
]

TUTOR_FOLLOWUP_EXCHANGES: list[dict[str, Any]] = [
    {
        "user_message": "In a series circuit with two 4Ω resistors and a 12V battery, why is current the same through both resistors but voltage splits?",
        "assistant_message": "In series, charge has one path so current I is identical. Each resistor drops V=IR; total 12V splits as 4I + 4I = 8I, giving I = 1.5 A.",
        "concept": "Ohm's law",
        "variation": "typo",
    },
    {
        "user_message": "How does gastric pH affect pepsinogen activation, and what happens if antacid raises stomach pH too much?",
        "assistant_message": "HCl converts pepsinogen to active pepsin near pH 2. Excess antacid raises pH, reducing pepsin activity and slowing protein digestion in the stomach.",
        "concept": None,
        "variation": "conversational",
    },
    {
        "user_message": "For a convex lens with u = −30 cm and f = +15 cm, why must we use the sign convention before applying 1/f = 1/v − 1/u?",
        "assistant_message": "Real objects are on the incoming-light side, so u is negative. Using magnitudes without signs gives wrong v and mislabels image as real or virtual.",
        "concept": "Lens formula",
        "variation": "diagram",
    },
    {
        "user_message": "If a quadratic has D = 0 but coefficients are not proportional to a perfect square, how do we still know roots are equal?",
        "assistant_message": "D = b² − 4ac = 0 means the quadratic touches the x-axis once. The repeated root is −b/(2a), even if factorisation is not obvious.",
        "concept": None,
        "variation": "cbse",
    },
    {
        "user_message": "Why does NH₃ have pyramidal geometry while BF₃ is trigonal planar despite both having three bonded atoms?",
        "assistant_message": "NH₃ has one lone pair on nitrogen; four electron domains → tetrahedral electron geometry, pyramidal shape. BF₃ has three domains only → trigonal planar.",
        "concept": "VSEPR theory",
        "variation": "neet",
    },
    {
        "user_message": "In a Wheatstone bridge, why can't we apply the loop rule to only one branch when finding the unknown resistor?",
        "assistant_message": "Kirchhoff's loop rule needs a closed path with consistent sign for each IR drop. A single branch is not a closed loop, so ΣΔV = 0 cannot be applied there alone.",
        "concept": "Kirchhoff's laws",
        "variation": "jee",
    },
    {
        "user_message": "If we add an inert gas at constant volume to an equilibrium A ⇌ B, does Q change or only total pressure?",
        "assistant_message": "At constant V, partial pressures of A and B are unchanged, so Q = [B]/[A] stays the same. Equilibrium position does not shift; only total P rises.",
        "concept": "Le Chatelier's principle",
        "variation": "multi_part",
    },
    {
        "user_message": "During DNA replication, why is the leading strand continuous but the lagging strand made of Okazaki fragments?",
        "assistant_message": "DNA polymerase moves 5′→3′. At the fork, one template strand runs 3′→5′ relative to synthesis, forcing discontinuous short fragments on the lagging side.",
        "concept": "DNA replication",
        "variation": "conceptual",
    },
    {
        "user_message": "How can caste-based mobilisation both strengthen democracy and deepen social divisions at the same time?",
        "assistant_message": "It increases political participation and representation of marginal groups, but can also harden identity voting and reduce cross-community coalitions on policy issues.",
        "concept": None,
        "variation": "case_study",
    },
    {
        "user_message": "Why is GDP at market prices not the same as national income, and where does depreciation enter?",
        "assistant_message": "National income (NNP at factor cost) adjusts GDP for net indirect taxes and depreciation. Ignoring depreciation overstates income available for consumption and investment.",
        "concept": "GDP vs GNP",
        "variation": "ncert_strict",
    },
    {
        "user_message": "Why does escape velocity depend on planet radius and g but not on the mass of the escaping object?",
        "assistant_message": "Escape speed balances kinetic and gravitational potential per unit mass: ½v² = GM/R. The object's mass cancels; only the field strength at the surface matters.",
        "concept": "Kepler's laws",
        "variation": "typo",
    },
    {
        "user_message": "For ∫₀¹ x√(1−x²) dx, why is substitution u = 1−x² more natural than integration by parts?",
        "assistant_message": "The derivative of 1−x² is −2x, matching the x factor outside the root. Parts would couple x with arcsin-type terms and add unnecessary steps.",
        "concept": "Definite integrals",
        "variation": "proof",
    },
    {
        "user_message": "If contour ploughing reduces erosion on slopes, why might terrace farming be needed on steeper hills?",
        "assistant_message": "Contour ploughing slows runoff on moderate slopes. Steeper gradients still concentrate water; terraces break slope length and reduce velocity before soil is washed away.",
        "concept": None,
        "variation": "conversational",
    },
    {
        "user_message": "In C₄ plants, why is the Calvin cycle still in bundle-sheath cells if initial CO₂ fixation happens in mesophyll?",
        "assistant_message": "Mesophyll cells fix CO₂ into a 4-carbon acid that shuttles to bundle sheath, where CO₂ is released internally, raising local concentration and cutting photorespiration.",
        "concept": "Calvin cycle",
        "variation": "diagram",
    },
    {
        "user_message": "For a galvanic cell with E°cell = +0.76 V, how do we use the Nernst equation when [Zn²⁺] doubles at 298 K?",
        "assistant_message": "Write Q from the cell reaction, then E = E° − (0.0591/n) log Q. Changing [Zn²⁺] alters Q and therefore the cell EMF from standard conditions.",
        "concept": "Nernst equation",
        "variation": "numerical",
    },
    {
        "user_message": "Three identical resistors in parallel share 12 V. Why is branch current I/3 but total power not simply P/3?",
        "assistant_message": "Each resistor gets full 12 V, so each dissipates V²/R. Three paths triple total current and total power becomes 3V²/R, not one-third of a single resistor's power.",
        "concept": "Ohm's law",
        "variation": "cbse",
    },
    {
        "user_message": "Why does trypsin act in the alkaline duodenum but not in the acidic stomach?",
        "assistant_message": "Trypsin is secreted as inactive trypsinogen and needs enterokinase and pH ~8. Gastric HCl would denature or fail to activate it, so activity is localised to the small intestine.",
        "concept": None,
        "variation": "neet",
    },
    {
        "user_message": "For total internal reflection, why is the critical angle defined only when light goes from denser to rarer medium?",
        "assistant_message": "TIR needs the refracted ray bent beyond 90°. That happens when n₁ sin i = n₂ sin r cannot be solved for real r with n₁ > n₂ beyond the critical angle.",
        "concept": "Lens formula",
        "variation": "jee",
    },
    {
        "user_message": "Without solving x² − 5x + 6 = 0, how can sum and product of roots verify the factorisation (x−2)(x−3)?",
        "assistant_message": "For ax²+bx+c, sum = −b/a = 5 and product = c/a = 6. If roots are 2 and 3, both checks match, confirming the factorisation without expansion errors.",
        "concept": None,
        "variation": "numerical",
    },
    {
        "user_message": "Why is sp³ hybridisation in methane consistent with four equivalent C−H bonds, not three bonds plus one lone pair?",
        "assistant_message": "Carbon promotes one 2s electron to 3p, mixes to four sp³ orbitals. Each overlaps with H 1s, giving four identical σ bonds and tetrahedral 109.5° angles.",
        "concept": "VSEPR theory",
        "variation": "neet",
    },
    {
        "user_message": "In a balanced Wheatstone bridge, why is the galvanometer current zero even though P and Q carry different currents?",
        "assistant_message": "At balance, potential at the midpoints of both arms is equal, so no PD across the galvanometer. Current divides in the arms but the junction potentials match.",
        "concept": None,
        "variation": "multi_part",
    },
    {
        "user_message": "Why is the genetic code called degenerate if each codon still codes for only one amino acid?",
        "assistant_message": "Degenerate means multiple codons can specify the same amino acid (e.g. leucine has six). It does not mean one codon maps to many amino acids—that would break translation fidelity.",
        "concept": "DNA replication",
        "variation": "conceptual",
    },
    {
        "user_message": "How does Indian secularism differ from Western separation when the state funds religious schools and personal laws coexist?",
        "assistant_message": "Indian secularism emphasises equal respect and principled distance, not strict church–state separation. The state may reform personal laws and subsidise education without adopting a state religion.",
        "concept": None,
        "variation": "case_study",
    },
    {
        "user_message": "If NFIA is positive, does GNP exceed GDP or fall below it, and what does that imply about net factor income abroad?",
        "assistant_message": "GNP = GDP + NFIA. Positive NFIA means residents earn more abroad than foreigners earn domestically, so GNP > GDP.",
        "concept": None,
        "variation": "ncert_strict",
    },
    {
        "user_message": "Using Kepler's third law, why do planets farther from the Sun have longer years but not necessarily lower orbital speed?",
        "assistant_message": "T² ∝ r³ gives longer periods, but v ≈ √(GM/r) decreases only as 1/√r. Outer planets move slower, yet the much longer path increases the year dramatically.",
        "concept": "Kepler's laws",
        "variation": "jee",
    },
    {
        "user_message": "To prove ∫ₐᵇ f(x) dx = F(b) − F(a), what must we show about F beyond finding an antiderivative?",
        "assistant_message": "F must be continuous on [a,b] and differentiable with F′(x)=f(x) almost everywhere on the interval. The FTC links accumulation to net change of that antiderivative.",
        "concept": "Definite integrals",
        "variation": "proof",
    },
    {
        "user_message": "Why can afforestation reduce soil erosion but not fix salinisation caused by over-irrigation?",
        "assistant_message": "Tree cover cuts wind and water erosion by binding soil. Salinisation needs drainage and better irrigation scheduling; roots alone cannot leach accumulated salts from the root zone.",
        "concept": None,
        "variation": "conversational",
    },
    {
        "user_message": "In hot climates, why do C₄ plants outperform C₃ plants even though both use the Calvin cycle?",
        "assistant_message": "C₄ concentrates CO₂ before Calvin cycle, keeping RuBisCO on carboxylation and lowering photorespiration when stomata close to reduce water loss in heat.",
        "concept": "Calvin cycle",
        "variation": "diagram",
    },
    {
        "user_message": "Not found in provided sources for Nernst equation worked example at non-standard concentrations.",
        "assistant_message": "Not found in provided sources for this question.",
        "concept": "Nernst equation",
        "variation": "edge_not_found",
    },
    {
        "user_message": "For a projectile launched at 45° on level ground, why is range maximum at 45° only when air resistance is neglected?",
        "assistant_message": "R = u²sin2θ/g assumes level ground and no drag. With air resistance, optimal angle shifts below 45° because horizontal speed decays faster than in the vacuum model.",
        "concept": None,
        "variation": "numerical",
    },
]
