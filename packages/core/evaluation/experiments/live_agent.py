"""Live LLM invocation for evaluation experiments."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, Optional, Tuple

from config.settings import settings
from packages.core.evaluation.datasets.loader import ROOT, load_manifest
from packages.core.llm import get_llm_client
from packages.core.prompts.versioned_loader import get_template_paths, load_agent_system_user, load_versioned_prompt


def _parse_llm_output(content: str) -> Any:
    text = (content or "").strip()
    if not text:
        return {}
    try:
        obj = json.loads(text)
        if isinstance(obj, (dict, list)):
            return obj
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    return {"output": text}


def _dataset_prompt_template(agent_name: str) -> Optional[str]:
    manifest = load_manifest()
    for ds in manifest.get("datasets") or []:
        if ds.get("dataset_id") == agent_name:
            path = ROOT / ds["path"]
            if path.is_file():
                doc = json.loads(path.read_text(encoding="utf-8"))
                return doc.get("agent", {}).get("prompt_template")
    return None


def _render_dataset_template(template: str, inputs: Dict[str, Any]) -> str:
    out = template
    for key, val in inputs.items():
        if val is None:
            sval = ""
        elif isinstance(val, (dict, list)):
            sval = json.dumps(val)
        else:
            sval = str(val)
        out = out.replace("{{ " + key + " }}", sval).replace("{{" + key + "}}", sval)
    return out


def _build_prompts(agent_name: str, prompt_version: str, inputs: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Return (system_prompt, user_prompt) for LLM call."""
    try:
        paths = get_template_paths(agent_name, prompt_version)
        if paths.get("system") and paths.get("user"):
            system, user = load_agent_system_user(
                agent_name,
                version=prompt_version,
                user_kwargs=inputs,
                system_kwargs=inputs,
            )
            return system, user
        if paths.get("template"):
            user = load_versioned_prompt(agent_name, prompt_version, part="template", **inputs)
            return None, user
    except FileNotFoundError:
        pass

    tmpl = _dataset_prompt_template(agent_name)
    if tmpl:
        rendered = _render_dataset_template(tmpl, inputs)
        if prompt_version == "v2":
            rendered += (
                "\n\nCRITICAL (v2): NCERT/CBSE grounding. JSON only. Reasoning ≤40 words."
            )
        return None, rendered

    user = (
        f"Agent: {agent_name}\nPrompt version: {prompt_version}\n"
        f"Inputs:\n{json.dumps(inputs, indent=2)}\n\n"
        "Respond with the best output for this evaluation example."
    )
    return None, user


async def invoke_agent_for_eval_async(
    agent_name: str,
    prompt_version: str,
    model: str,
    inputs: Dict[str, Any],
) -> Tuple[Any, int, int]:
    """Call live LLM; return (parsed_output, prompt_tokens, completion_tokens)."""
    if not (settings.OPENAI_API_KEY or "").strip():
        raise RuntimeError("OPENAI_API_KEY required for live evaluation")

    system_prompt, user_prompt = _build_prompts(agent_name, prompt_version, inputs)
    client = get_llm_client(model=model, temperature=0.0, max_tokens=2048)
    response = await client.generate(
        prompt=user_prompt,
        system_prompt=system_prompt,
        feature_tag=f"eval_{agent_name}",
        max_tokens=2048,
    )
    usage = response.usage or {}
    prompt_tok = int(usage.get("prompt_tokens") or max(50, len(user_prompt) // 4))
    completion_tok = int(usage.get("completion_tokens") or max(30, len(response.content or "") // 4))
    output = _parse_llm_output(response.content or "")
    return output, prompt_tok, completion_tok


def invoke_agent_for_eval(
    agent_name: str,
    prompt_version: str,
    model: str,
    inputs: Dict[str, Any],
) -> Tuple[Any, int, int]:
    """Sync wrapper for experiment runner."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                asyncio.run,
                invoke_agent_for_eval_async(agent_name, prompt_version, model, inputs),
            ).result()
    return asyncio.run(invoke_agent_for_eval_async(agent_name, prompt_version, model, inputs))
