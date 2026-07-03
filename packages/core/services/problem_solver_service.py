"""Problem Solver orchestration service."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models.notebook import Notebook
from packages.core.database.models.problem_solver import ProblemSolverSession, ProblemSolverStep
from packages.core.llm import get_llm_client, get_model_for_task
from packages.core.processing.help_me_solve_cumulative import enrich_help_me_solve_response
from packages.core.prompts import load_prompt
from packages.core.rag.whole_file_map_reduce import fetch_all_chunks_for_sources, _chunk_text
from packages.core.security.answer_leak_guard import answer_leak_guard
from packages.core.services.problem_solver_chat_bridge import persist_ps_assistant_turn
from packages.core.services.problem_subject_inference import (
    infer_problem_subject,
    normalize_dna_subject,
)

SOLVING_MODES = frozenset(
    {
        "EXPLAIN_FROM_BASICS",
        "HELP_ME_SOLVE_IT",
        "SHOW_MISSING_IDEA",
        "SHOW_BEST_APPROACH",
    }
)

MODE_TEMPLATES = {
    "EXPLAIN_FROM_BASICS": "problem_solver/explain_from_basics.j2",
    "HELP_ME_SOLVE_IT": "problem_solver/help_me_solve_it.j2",
    "SHOW_MISSING_IDEA": "problem_solver/show_missing_idea.j2",
    "SHOW_BEST_APPROACH": "problem_solver/show_best_approach.j2",
}

# Follow-up pill actions that should run a full mode template instead of follow_up.j2
FOLLOW_UP_MODE_ACTIONS = frozenset({"SHOW_BEST_APPROACH"})

VALID_TRANSITIONS: Dict[str, frozenset[str]] = {
    "created": frozenset({"extracting", "dna_ready"}),
    "extracting": frozenset({"dna_ready"}),
    "dna_ready": frozenset({"mode_selected"}),
    "mode_selected": frozenset({"responding", "completed"}),
    "responding": frozenset({"completed", "follow_up"}),
    "follow_up": frozenset({"completed", "follow_up"}),
    "completed": frozenset({"created"}),
}


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _normalize_problem_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


DEFAULT_CHECKPOINT_OPTIONS = [
    {"id": "A", "label": "Convert units first, then use v = u + at"},
    {"id": "B", "label": "Use distance formula before finding acceleration"},
    {"id": "C", "label": "Plug 72 km/h directly into m/s² formulas"},
    {"id": "D", "label": "Skip setup and guess from the answer choices"},
]

DEFAULT_CHECKPOINT_OPTIONS_2 = [
    {"id": "A", "label": "Use s = ut + ½at² after finding acceleration"},
    {"id": "B", "label": "Use s = (u + v)t / 2"},
    {"id": "C", "label": "Multiply speed by time without converting units"},
    {"id": "D", "label": "Use only the average-speed shortcut without checking units"},
]


def normalize_checkpoint(
    checkpoint: Any,
    *,
    checkpoint_number: int = 1,
) -> Optional[Dict[str, Any]]:
    """Ensure checkpoint MCQ shape is always valid for the UI."""
    data: Dict[str, Any] = checkpoint if isinstance(checkpoint, dict) else {}
    prompt = (
        data.get("prompt")
        or data.get("question")
        or ("Which equation should we use next?" if checkpoint_number > 1 else "Which idea should we use first?")
    )
    number = data.get("number") or data.get("checkpoint_number") or checkpoint_number

    raw_options = data.get("options") or data.get("choices") or data.get("answers") or []
    options: List[Dict[str, str]] = []
    if isinstance(raw_options, list):
        for i, opt in enumerate(raw_options):
            if isinstance(opt, dict):
                opt_id = str(opt.get("id") or opt.get("key") or chr(65 + i))
                label = str(opt.get("label") or opt.get("text") or opt.get("value") or "").strip()
                if label:
                    options.append({"id": opt_id, "label": label})
            elif isinstance(opt, str) and opt.strip():
                options.append({"id": chr(65 + i), "label": opt.strip()})

    if not options:
        fallback = DEFAULT_CHECKPOINT_OPTIONS_2 if int(number) >= 2 else DEFAULT_CHECKPOINT_OPTIONS
        options = [dict(opt) for opt in fallback]

    return {
        "number": int(number),
        "prompt": str(prompt).strip(),
        "options": options[:4],
    }


def normalize_mode_response(
    response: Dict[str, Any],
    *,
    solving_mode: Optional[str],
    interaction_count: int,
) -> Dict[str, Any]:
    """Normalize sections and checkpoint fields on mode responses."""
    out = dict(response or {})
    sections = out.get("sections")
    if not isinstance(sections, list):
        out["sections"] = []
    else:
        out["sections"] = [
            {
                "heading": str(s.get("heading") or "Section"),
                "bodyMarkdown": str(s.get("bodyMarkdown") or s.get("body") or ""),
            }
            for s in sections
            if isinstance(s, dict)
        ]

    buttons = out.get("followUpButtons") or out.get("follow_up_buttons") or []
    if not isinstance(buttons, list):
        buttons = []
    normalized_buttons: List[Dict[str, str]] = []
    for btn in buttons:
        if not isinstance(btn, dict):
            continue
        action = btn.get("action") or btn.get("id")
        label = btn.get("label") or btn.get("text") or action
        if action:
            normalized_buttons.append({"label": str(label), "action": str(action)})
    out["followUpButtons"] = normalized_buttons

    if solving_mode == "HELP_ME_SOLVE_IT":
        if interaction_count < 2 and (interaction_count == 0 or out.get("checkpoint")):
            out["checkpoint"] = normalize_checkpoint(
                out.get("checkpoint"),
                checkpoint_number=interaction_count + 1,
            )
        else:
            out.pop("checkpoint", None)
        if interaction_count == 0 and "checkpointHistory" not in out:
            out["checkpointHistory"] = []
        if "interactionCount" not in out:
            out["interactionCount"] = interaction_count
    elif out.get("checkpoint") is not None:
        normalized = normalize_checkpoint(out.get("checkpoint"), checkpoint_number=interaction_count + 1)
        out["checkpoint"] = normalized if normalized and normalized.get("options") else None

    return out


def _format_prior_response(prior: Optional[Dict[str, Any]]) -> Optional[str]:
    """Serialize prior coach turn for multi-step Help Me Solve It prompts."""
    if not prior or not isinstance(prior, dict):
        return None
    try:
        return json.dumps(prior, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return None


def _response_end_state(session: ProblemSolverSession, response: Dict[str, Any]) -> str:
    if (
        session.solving_mode == "HELP_ME_SOLVE_IT"
        and response.get("checkpoint")
        and session.interaction_count < 2
    ):
        return "follow_up"
    return "completed"


def _session_to_public(session: ProblemSolverSession) -> Dict[str, Any]:
    dna = session.problem_dna or {}
    return {
        "session_id": str(session.id),
        "notebook_id": str(session.notebook_id),
        "state": session.state,
        "problem_text": session.problem_text,
        "problem_text_normalized": session.problem_text_normalized,
        "input_type": session.input_type,
        "source_refs": session.source_refs or [],
        "problem_dna": dna,
        "solving_mode": session.solving_mode,
        "interaction_count": session.interaction_count,
        "last_response": session.last_response,
        "assistant_message_id": (
            (session.last_response or {}).get("assistant_message_id")
            if isinstance(session.last_response, dict)
            else None
        ),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


class ProblemSolverService:
    def __init__(self, db: AsyncSession, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def _get_notebook(self, notebook_id: str) -> Notebook:
        result = await self.db.execute(
            select(Notebook).where(
                Notebook.id == uuid.UUID(notebook_id),
                Notebook.tenant_id == uuid.UUID(self.tenant_id),
                Notebook.user_id == self.user_id,
            )
        )
        notebook = result.scalar_one_or_none()
        if not notebook:
            raise HTTPException(status_code=404, detail="Notebook not found")
        if notebook.mode != "problem_solver":
            raise HTTPException(status_code=400, detail="Notebook is not a problem solver workspace")
        return notebook

    async def _get_session(self, session_id: str) -> ProblemSolverSession:
        result = await self.db.execute(
            select(ProblemSolverSession).where(
                ProblemSolverSession.id == uuid.UUID(session_id),
                ProblemSolverSession.tenant_id == uuid.UUID(self.tenant_id),
                ProblemSolverSession.user_id == self.user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def _scope_from_notebook(self, notebook: Notebook) -> Dict[str, Any]:
        settings_json = notebook.settings if isinstance(notebook.settings, dict) else {}
        return settings_json.get("problem_solver_scope") or {}

    async def _append_step(
        self,
        session: ProblemSolverSession,
        step_type: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        step = ProblemSolverStep(
            session_id=session.id,
            step_type=step_type,
            content=content,
            step_metadata=metadata or {},
        )
        self.db.add(step)

    async def _persist_assistant_message(
        self,
        session: ProblemSolverSession,
        response: Dict[str, Any],
    ) -> None:
        try:
            await persist_ps_assistant_turn(
                self.db,
                session,
                response,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
            )
        except Exception as exc:
            print(f"[PS_CHAT_BRIDGE] persist failed: {exc}")

    def _transition(self, session: ProblemSolverSession, new_state: str) -> None:
        allowed = VALID_TRANSITIONS.get(session.state, frozenset())
        if new_state not in allowed and session.state != new_state:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid transition {session.state} -> {new_state}",
            )
        session.state = new_state

    async def _retrieve_ncert_context(
        self,
        query: str,
        scope: Dict[str, Any],
        dna: Optional[Dict[str, Any]] = None,
        *,
        subject_key_hint: Optional[str] = None,
    ) -> str:
        """Problem Solver uses LLM-only grounding — no live NCERT retrieval."""
        return ""

    async def _llm_json(self, prompt: str, task: str = "problem_solver_dna") -> Dict[str, Any]:
        provider, model = get_model_for_task(task)
        llm = get_llm_client(provider=provider, model=model, temperature=0.3)
        gen_kwargs: Dict[str, Any] = {"response_format": {"type": "json_object"}}
        resp = await llm.generate(prompt, **gen_kwargs)
        parsed = _parse_json_object(resp.content)
        if not parsed:
            raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
        return parsed

    async def create_session(
        self,
        *,
        notebook_id: str,
        problem_text: str,
        input_type: str = "text",
        source_refs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        notebook = await self._get_notebook(notebook_id)
        scope = self._scope_from_notebook(notebook)
        normalized = _normalize_problem_text(problem_text)
        if len(normalized) < 10:
            raise HTTPException(status_code=400, detail="Problem text is too short")

        session = ProblemSolverSession(
            tenant_id=uuid.UUID(self.tenant_id),
            user_id=self.user_id,
            notebook_id=notebook.id,
            problem_text=problem_text,
            problem_text_normalized=normalized,
            input_type=input_type or "text",
            source_refs=source_refs or [],
            state="created",
            trace_id=str(uuid.uuid4()),
        )
        self.db.add(session)
        await self.db.flush()

        await self._append_step(session, "intake", content=normalized)
        self._transition(session, "dna_ready")

        subject_keys = list(scope.get("subject_keys") or [])
        subject_labels = list(scope.get("subject_labels") or [])
        inference = infer_problem_subject(normalized, subject_keys)
        ncert_context = await self._retrieve_ncert_context(
            normalized,
            scope,
            subject_key_hint=inference.get("subject_key"),
        )
        inferred_hint = (
            f"{inference['subject']} (NCERT key: {inference['subject_key']}, "
            f"confidence: {inference['confidence']})"
        )
        dna_prompt = load_prompt(
            "problem_solver/dna.j2",
            problem_text_normalized=normalized,
            ncert_context=ncert_context,
            subject_keys=subject_keys,
            subject_labels=subject_labels,
            class_num=scope.get("class_num") or 12,
            inferred_subject_hint=inferred_hint,
        )
        dna = await self._llm_json(dna_prompt, task="problem_solver_dna")
        dna = normalize_dna_subject(dna, normalized, scope)
        expert = dna.pop("expert_solution_internal", None)
        session.problem_dna = dna
        session.expert_solution = expert
        await self._append_step(session, "dna", metadata=dna)
        await self.db.commit()
        await self.db.refresh(session)
        return _session_to_public(session)

    async def set_extracted_text(self, session_id: str, normalized_text: str) -> Dict[str, Any]:
        session = await self._get_session(session_id)
        if session.state not in ("created", "extracting"):
            raise HTTPException(status_code=409, detail="Cannot extract in current state")
        session.problem_text_normalized = _normalize_problem_text(normalized_text)
        session.problem_text = normalized_text
        self._transition(session, "dna_ready")
        notebook = await self._get_notebook(str(session.notebook_id))
        scope = self._scope_from_notebook(notebook)
        subject_keys = list(scope.get("subject_keys") or [])
        subject_labels = list(scope.get("subject_labels") or [])
        inference = infer_problem_subject(session.problem_text_normalized or "", subject_keys)
        ncert_context = await self._retrieve_ncert_context(
            session.problem_text_normalized or "",
            scope,
            subject_key_hint=inference.get("subject_key"),
        )
        inferred_hint = (
            f"{inference['subject']} (NCERT key: {inference['subject_key']}, "
            f"confidence: {inference['confidence']})"
        )
        dna_prompt = load_prompt(
            "problem_solver/dna.j2",
            problem_text_normalized=session.problem_text_normalized,
            ncert_context=ncert_context,
            subject_keys=subject_keys,
            subject_labels=subject_labels,
            class_num=scope.get("class_num") or 12,
            inferred_subject_hint=inferred_hint,
        )
        dna = await self._llm_json(dna_prompt, task="problem_solver_dna")
        dna = normalize_dna_subject(dna, session.problem_text_normalized or "", scope)
        expert = dna.pop("expert_solution_internal", None)
        session.problem_dna = dna
        session.expert_solution = expert
        await self._append_step(session, "dna", metadata=dna)
        await self.db.commit()
        await self.db.refresh(session)
        return _session_to_public(session)

    async def select_mode(self, session_id: str, solving_mode: str) -> Dict[str, Any]:
        if solving_mode not in SOLVING_MODES:
            raise HTTPException(status_code=400, detail="Invalid solving mode")
        session = await self._get_session(session_id)
        if session.state != "dna_ready":
            raise HTTPException(status_code=409, detail="DNA not ready")
        session.solving_mode = solving_mode
        self._transition(session, "mode_selected")
        await self._append_step(session, "mode_selected", metadata={"solving_mode": solving_mode})
        await self.db.commit()
        await self.db.refresh(session)
        return _session_to_public(session)

    async def _build_mode_response(self, session: ProblemSolverSession) -> Dict[str, Any]:
        notebook = await self._get_notebook(str(session.notebook_id))
        scope = self._scope_from_notebook(notebook)
        dna = session.problem_dna or {}
        ncert_context = await self._retrieve_ncert_context(
            session.problem_text_normalized or "",
            scope,
            dna=dna,
        )
        template = MODE_TEMPLATES.get(session.solving_mode or "")
        if not template:
            raise HTTPException(status_code=400, detail="Solving mode not set")

        prior_response = None
        if session.solving_mode == "HELP_ME_SOLVE_IT" and session.interaction_count > 0:
            prior_response = _format_prior_response(session.last_response)

        prompt = load_prompt(
            template,
            problem_text_normalized=session.problem_text_normalized,
            ncert_context=ncert_context,
            interaction_count=session.interaction_count,
            checkpoint_number=session.interaction_count + 1 if session.solving_mode == "HELP_ME_SOLVE_IT" else None,
            student_choice=None,
            prior_response=prior_response,
        )
        response = await self._llm_json(prompt, task="problem_solver_mode")
        allow_reveal = session.solving_mode in ("EXPLAIN_FROM_BASICS", "SHOW_BEST_APPROACH")
        if session.solving_mode == "HELP_ME_SOLVE_IT" and session.interaction_count >= 2:
            allow_reveal = True
        response = answer_leak_guard(
            response,
            expert_solution=session.expert_solution,
            allow_reveal=allow_reveal,
        )
        response = normalize_mode_response(
            response,
            solving_mode=session.solving_mode,
            interaction_count=session.interaction_count,
        )
        if session.solving_mode == "HELP_ME_SOLVE_IT":
            response = enrich_help_me_solve_response(
                response,
                interaction_count=session.interaction_count,
                student_choice=None,
                prior_response=None,
            )
        response["mode"] = session.solving_mode
        return response

    async def respond(self, session_id: str) -> Dict[str, Any]:
        session = await self._get_session(session_id)
        if session.state not in ("mode_selected", "responding", "follow_up"):
            raise HTTPException(status_code=409, detail="Cannot respond in current state")
        self._transition(session, "responding")
        response = await self._build_mode_response(session)
        session.last_response = response
        self._transition(session, _response_end_state(session, response))
        await self._persist_assistant_message(session, response)
        await self._append_step(session, "mode_response", metadata=response)
        await self.db.commit()
        await self.db.refresh(session)
        return _session_to_public(session)

    async def stream_respond(self, session_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        session = await self._get_session(session_id)
        if session.state not in ("mode_selected", "responding", "follow_up"):
            raise HTTPException(status_code=409, detail="Cannot respond in current state")
        self._transition(session, "responding")
        response = await self._build_mode_response(session)
        session.last_response = response
        self._transition(session, _response_end_state(session, response))
        await self._persist_assistant_message(session, response)
        await self._append_step(session, "mode_response", metadata=response)
        await self.db.commit()

        yield {"event": "start", "data": {"title": response.get("title"), "mode": response.get("mode")}}
        for i, section in enumerate(response.get("sections") or []):
            yield {"event": "section", "data": {"index": i, **section}}
        yield {
            "event": "done",
            "data": {
                "followUpButtons": response.get("followUpButtons") or [],
                "revealLevel": response.get("revealLevel"),
                "checkpoint": response.get("checkpoint"),
                "finalAnswer": response.get("finalAnswer"),
                "session_id": str(session.id),
                "assistant_message_id": response.get("assistant_message_id"),
            },
        }

    async def submit_checkpoint(
        self,
        session_id: str,
        checkpoint_number: int,
        selected_option: str,
    ) -> Dict[str, Any]:
        session = await self._get_session(session_id)
        if session.solving_mode != "HELP_ME_SOLVE_IT":
            raise HTTPException(status_code=400, detail="Checkpoints only for Help Me Solve It mode")
        if session.interaction_count >= 2:
            raise HTTPException(status_code=409, detail="Maximum checkpoints reached")
        prior_dict = session.last_response if isinstance(session.last_response, dict) else None
        prior_response = _format_prior_response(prior_dict)
        session.interaction_count += 1
        await self._append_step(
            session,
            "checkpoint",
            content=selected_option,
            metadata={"checkpoint_number": checkpoint_number, "selected_option": selected_option},
        )
        notebook = await self._get_notebook(str(session.notebook_id))
        scope = self._scope_from_notebook(notebook)
        dna = session.problem_dna or {}
        ncert_context = await self._retrieve_ncert_context(
            session.problem_text_normalized or "",
            scope,
            dna=dna,
        )
        prompt = load_prompt(
            "problem_solver/help_me_solve_it.j2",
            problem_text_normalized=session.problem_text_normalized,
            ncert_context=ncert_context,
            interaction_count=session.interaction_count,
            checkpoint_number=checkpoint_number,
            student_choice=selected_option,
            prior_response=prior_response,
        )
        response = await self._llm_json(prompt, task="problem_solver_mode")
        allow_reveal = session.interaction_count >= 2
        response = answer_leak_guard(
            response,
            expert_solution=session.expert_solution,
            allow_reveal=allow_reveal,
        )
        response = normalize_mode_response(
            response,
            solving_mode=session.solving_mode,
            interaction_count=session.interaction_count,
        )
        response = enrich_help_me_solve_response(
            response,
            interaction_count=session.interaction_count,
            student_choice=selected_option,
            prior_response=prior_dict,
        )
        response["mode"] = session.solving_mode
        session.last_response = response
        session.state = _response_end_state(session, response)
        await self._persist_assistant_message(session, response)
        await self._append_step(session, "mode_response", metadata=response)
        await self.db.commit()
        await self.db.refresh(session)
        return _session_to_public(session)

    async def follow_up(
        self,
        session_id: str,
        action: str,
        user_follow_up: Optional[str] = None,
    ) -> Dict[str, Any]:
        session = await self._get_session(session_id)
        if action == "START_TUTOR_SESSION":
            dna = session.problem_dna or {}
            return {
                "action": action,
                "redirect": "/tutor",
                "query": {
                    "class": dna.get("ncert_class") or 12,
                    "subject": dna.get("subject"),
                    "chapter": dna.get("chapter"),
                },
            }

        if action in FOLLOW_UP_MODE_ACTIONS and action in SOLVING_MODES:
            session.solving_mode = action
            response = await self._build_mode_response(session)
        elif action == "REVEAL_SOLUTION" and session.solving_mode == "HELP_ME_SOLVE_IT":
            session.interaction_count = max(session.interaction_count, 2)
            response = await self._build_mode_response(session)
        else:
            notebook = await self._get_notebook(str(session.notebook_id))
            scope = self._scope_from_notebook(notebook)
            dna = session.problem_dna or {}
            ncert_context = await self._retrieve_ncert_context(
                session.problem_text_normalized or "",
                scope,
                dna=dna,
            )
            if action == "REVEAL_SOLUTION":
                session.interaction_count = max(session.interaction_count, 2)

            prompt = load_prompt(
                "problem_solver/follow_up.j2",
                action=action,
                user_follow_up=user_follow_up or "",
                problem_text_normalized=session.problem_text_normalized,
                solving_mode=session.solving_mode,
                ncert_context=ncert_context,
            )
            response = await self._llm_json(prompt, task="problem_solver_mode")

        allow_reveal = action in ("REVEAL_SOLUTION", "SHOW_BEST_APPROACH") or session.solving_mode in (
            "EXPLAIN_FROM_BASICS",
            "SHOW_BEST_APPROACH",
        )
        response = answer_leak_guard(
            response,
            expert_solution=session.expert_solution,
            allow_reveal=allow_reveal or session.interaction_count >= 2,
        )
        response = normalize_mode_response(
            response,
            solving_mode=session.solving_mode,
            interaction_count=session.interaction_count,
        )
        response["mode"] = session.solving_mode
        response["interactionCount"] = session.interaction_count
        session.last_response = response
        session.state = "follow_up"
        await self._persist_assistant_message(session, response)
        await self._append_step(session, "follow_up_action", metadata={"action": action, "response": response})
        await self.db.commit()
        await self.db.refresh(session)
        return _session_to_public(session)

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        session = await self._get_session(session_id)
        return _session_to_public(session)

    _RESUMABLE_STATES = frozenset(
        {"created", "extracting", "dna_ready", "mode_selected", "responding", "follow_up"}
    )

    async def extract_text_from_source(self, source_id: str) -> str:
        from packages.core.database.models.source import Source
        from packages.core.processing.problem_solver_extraction import detect_corruption
        from packages.core.processing.problem_solver_source_text import extract_problem_text_from_bytes
        from packages.core.storage.s3 import S3Storage

        result = await self.db.execute(
            select(Source).where(
                Source.id == uuid.UUID(source_id),
                Source.tenant_id == uuid.UUID(self.tenant_id),
            )
        )
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        chunks = await fetch_all_chunks_for_sources(
            self.tenant_id, [source_id], user_id=self.user_id
        )
        texts = [_chunk_text(c) for c in chunks]
        combined = "\n".join(t for t in texts if t).strip()

        if len(combined) >= 20 and not detect_corruption(combined):
            return combined[:12000]

        storage = S3Storage(self.tenant_id)
        try:
            file_content = await storage.download_file(source.s3_key)
        except Exception as exc:
            if len(combined) >= 10:
                return combined[:12000]
            raise HTTPException(
                status_code=400,
                detail=f"Could not download source file: {exc}",
            ) from exc

        enriched = await extract_problem_text_from_bytes(
            file_content,
            s3_key=source.s3_key or "",
            title=source.title or "",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            indexed_chunks=combined,
        )
        if len(enriched) < 10:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough text from the uploaded file",
            )
        return enriched[:12000]

    async def get_active_for_notebook(self, notebook_id: str) -> Optional[Dict[str, Any]]:
        await self._get_notebook(notebook_id)
        result = await self.db.execute(
            select(ProblemSolverSession)
            .where(
                ProblemSolverSession.notebook_id == uuid.UUID(notebook_id),
                ProblemSolverSession.tenant_id == uuid.UUID(self.tenant_id),
                ProblemSolverSession.user_id == self.user_id,
            )
            .order_by(ProblemSolverSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if not session or session.state not in self._RESUMABLE_STATES:
            return None
        return _session_to_public(session)

    async def reset_session(self, notebook_id: str) -> Dict[str, Any]:
        await self._get_notebook(notebook_id)
        result = await self.db.execute(
            select(ProblemSolverSession)
            .where(
                ProblemSolverSession.notebook_id == uuid.UUID(notebook_id),
                ProblemSolverSession.tenant_id == uuid.UUID(self.tenant_id),
                ProblemSolverSession.user_id == self.user_id,
                ProblemSolverSession.state.in_(tuple(self._RESUMABLE_STATES)),
            )
            .order_by(ProblemSolverSession.created_at.desc())
            .limit(1)
        )
        session = result.scalar_one_or_none()
        if session:
            session.state = "completed"
            await self.db.commit()
        return {"notebook_id": notebook_id, "reset": True}
