#!/usr/bin/env python3
"""Build eval pool JSON for Agent 14 (studio_slide_deck) from locked inputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from generate_agents_8_16_studio import CTX  # noqa: E402

OUT = SCRIPTS / "studio_slide_deck_eval_pool.json"

# Locked inputs — same 22 examples as gen_agent14 deck_data
ITEMS = [
    ("001", "per_concept", ["cbse", "physics", "scope_mode:per_concept"], "current_electricity",
     "6 slides, medium, focus Ohm's law and series circuits only", "per_concept"),
    ("002", "per_concept", ["neet", "biology"], "digestion",
     "5 slides, hard NEET style, digestive enzymes only", "per_concept"),
    ("003", "per_concept", ["cbse", "chemistry"], "coordination",
     "4 slides, easy, coordination number concept", "per_concept"),
    ("004", "per_concept", ["cbse", "mathematics"], "probability",
     "5 slides, medium, independent events focus", "per_concept"),
    ("005", "multi_concept", ["cbse", "biology"], "photosynthesis_mitosis",
     "6 slides, full chapter breadth, no narrow topic", "multi_concept"),
    ("006", "multi_concept", ["cbse", "chemistry"], "equilibrium_hydrocarbons",
     "5 slides, medium, all topics in context", "multi_concept"),
    ("007", "multi_concept", ["cbse", "mathematics"], "binomial_lp",
     "5 slides, medium, full breadth", "multi_concept"),
    ("008", "per_source", ["cbse", "physics"], "ray_optics",
     "6 slides, CBSE Ray Optics chapter", "per_source"),
    ("009", "per_source", ["cbse", "biology"], "dna",
     "5 slides, molecular inheritance", "per_source"),
    ("010", "per_source", ["cbse", "chemistry"], "electrochemistry",
     "4 slides, galvanic cells", "per_source"),
    ("011", "per_source", ["cbse", "mathematics"], "3d_geometry",
     "5 slides, 3D geometry", "per_source"),
    ("012", "multi_source", ["cbse", "physics"], "multi_phys_chem",
     "6 slides, integrate electricity and electrochemistry sources", "multi_source"),
    ("013", "multi_source", ["cbse", "biology"], "multi_bio",
     "5 slides, photosynthesis + cell division", "multi_source"),
    ("014", "multi_source", ["cbse", "mathematics"], "multi_math",
     "5 slides, probability + binomial", "multi_source"),
    ("015", "multi_source", ["cbse", "physics"], "ray_current",
     "7 slides, optics and circuits selected sources", "multi_source"),
    ("016", "multi_source", ["neet", "biology"], "digestion_photosynthesis",
     "6 slides, NEET cross-topic", "multi_source"),
    ("017", "no_source", ["edge_case", "scope_mode:no_source"], "",
     "4 slides, general study skills — no source", "no_source"),
    ("018", "no_source", ["edge_case"], "",
     "3 slides, minimal generic science outline", "no_source"),
    ("019", "custom_slides", ["cbse", "physics"], "rotational",
     "8 slides, hard difficulty, include torque numerical examples", "per_concept"),
    ("020", "custom_language", ["cbse", "chemistry"], "aldehydes",
     "5 slides, explain in simple English — aldehyde tests only", "per_concept"),
    ("021", "thin_source", ["cbse", "mathematics"], "binomial",
     "3 slides, thin excerpt — minimum viable deck", "per_source"),
    ("022", "chapter_scope", ["cbse", "biology"], "anatomy_plants",
     "6 slides, whole chapter revision — root anatomy", "multi_concept"),
]

CTX_KEYS = {
    "photosynthesis_mitosis": CTX["photosynthesis"] + " " + CTX["mitosis_meiosis"],
    "equilibrium_hydrocarbons": CTX["equilibrium"] + " " + CTX["hydrocarbons"],
    "binomial_lp": CTX["binomial"] + " " + CTX["linear_ineq"],
    "ray_current": CTX["ray_optics"] + "\n\n" + CTX["current_electricity"],
    "digestion_photosynthesis": CTX["digestion"] + "\n\n" + CTX["photosynthesis"],
}


def resolve_context(key: str) -> str:
    if not key:
        return ""
    if key in CTX_KEYS:
        return CTX_KEYS[key]
    return CTX.get(key, "")


def main() -> int:
    items = []
    for sid, var, tags, ctx_key, instr, scope in ITEMS:
        ctx = resolve_context(ctx_key)
        items.append({
            "example_id": f"studio_slide_deck-{sid}",
            "variation": var,
            "tags": tags,
            "scope_mode": scope,
            "context": ctx,
            "custom_instructions": instr,
        })
    payload = {"version": "1.0.0", "total": len(items), "items": items}
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
