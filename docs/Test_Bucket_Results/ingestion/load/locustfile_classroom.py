"""
ING-11 classroom load test — sustained concurrent chat + uploads.

Mirrors ~40 students: 35 streaming chat (shared pre-indexed chapter), 5 uploading.

The production gate seeds CLASSROOM_CHAT_SOURCE_ID before Locust starts so chat
users do not all upload at spawn (which overwhelms ingest/DB pool).

Usage:
  locust -f tests/load/locustfile_classroom.py --host http://127.0.0.1:8000 \\
    --users 40 --spawn-rate 5 --run-time 10m --headless

Set GATE_CLASSROOM_SHORT=1 for a 2-minute smoke (local dev only).
"""

from __future__ import annotations

import json
import os
import time
import uuid

from locust import HttpUser, between, task

from tests.helpers.auth import make_dev_jwt

_SHORT = os.getenv("GATE_CLASSROOM_SHORT", "").strip().lower() in {"1", "true", "yes"}

CHAT_QUESTIONS = [
    "What is photosynthesis?",
    "Explain the Calvin cycle briefly.",
    "What role does chlorophyll play?",
    "How do plants convert light energy?",
    "What are the reactants in photosynthesis?",
]


class ChatStudentUser(HttpUser):
    """Student asking questions against a shared indexed chapter (gate-seeded)."""

    weight = 12 if _SHORT else 35
    wait_time = between(2, 8)

    def on_start(self) -> None:
        shared_source = os.environ.get("CLASSROOM_CHAT_SOURCE_ID", "").strip()
        shared_user = os.environ.get("CLASSROOM_CHAT_USER", "classroom_chat_shared").strip()
        if shared_source:
            self.token = make_dev_jwt(shared_user)
            self.source_id = shared_source
            return

        # Manual Locust runs without gate seed: per-user upload (not recommended at 35 users).
        self.token = make_dev_jwt(f"classroom_chat_{uuid.uuid4().hex[:10]}")
        self.source_id = None
        content = (
            f"Classroom chat fixture {uuid.uuid4()}\n"
            "Photosynthesis converts light energy into chemical energy in plants.\n"
            "Chlorophyll absorbs red and blue light.\n"
        )
        files = {"file": (f"chat_{uuid.uuid4().hex}.txt", content.encode("utf-8"), "text/plain")}
        data = {"title": "classroom_chat_source"}
        with self.client.post(
            "/api/v1/ingest/upload",
            headers={"Authorization": f"Bearer {self.token}"},
            files=files,
            data=data,
            catch_response=True,
            name="/api/v1/ingest/upload (chat setup)",
        ) as response:
            if response.status_code != 200:
                response.failure(f"setup upload HTTP {response.status_code}")
                return
            self.source_id = response.json().get("id")
            response.success()

        if self.source_id:
            self._wait_indexed(self.source_id)

    def _wait_indexed(self, source_id: str, timeout_s: float = 120.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            response = self.client.get(
                "/api/v1/ingest/sources",
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/v1/ingest/sources (poll)",
            )
            if response.status_code == 200:
                for src in response.json().get("sources", []):
                    if src.get("id") == source_id and src.get("status") in (
                        "indexed",
                        "ready",
                        "completed",
                    ):
                        return True
            time.sleep(2)
        return False

    @task
    def stream_chat(self) -> None:
        if not self.source_id:
            return
        question = CHAT_QUESTIONS[int(uuid.uuid4().int % len(CHAT_QUESTIONS))]
        payload = {
            "message": question,
            "history": [],
            "active_source_ids": [self.source_id],
        }
        with self.client.post(
            "/api/v1/chat/stream",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "text/event-stream",
            },
            json=payload,
            stream=True,
            catch_response=True,
            timeout=180,
            name="/api/v1/chat/stream",
        ) as response:
            if response.status_code >= 500:
                response.failure(f"Server error {response.status_code}")
                return
            if response.status_code != 200:
                detail = ""
                try:
                    detail = str(response.json().get("detail", ""))[:120]
                except Exception:  # noqa: BLE001
                    detail = response.text[:120]
                response.failure(f"HTTP {response.status_code}: {detail}")
                return
            saw_done = False
            saw_chunk = False
            for line in response.iter_lines(decode_unicode=True):
                if line and line.startswith("event:") and "done" in line:
                    saw_done = True
                    break
                if line and line.startswith("data:"):
                    try:
                        data = json.loads(line.split("data:", 1)[1].strip())
                        if isinstance(data, dict) and data.get("error"):
                            response.failure(data.get("error", "stream error")[:200])
                            return
                    except json.JSONDecodeError:
                        pass
                    saw_chunk = True
            if saw_done or saw_chunk:
                response.success()
            else:
                response.failure("stream ended without data")


class UploadStudentUser(HttpUser):
    """Students uploading new materials during class."""

    weight = 0 if _SHORT else 5
    wait_time = between(5, 15)

    def on_start(self) -> None:
        self.token = make_dev_jwt(f"classroom_upload_{uuid.uuid4().hex[:10]}")

    @task
    def upload_document(self) -> None:
        content = (
            f"Classroom upload {uuid.uuid4()}\n"
            "Photosynthesis converts light energy into chemical energy in plants.\n"
            "Chlorophyll absorbs red and blue light most effectively.\n"
            "Carbon dioxide and water are reactants in the Calvin cycle.\n"
            "The equation 6CO2 + 6H2O -> C6H12O6 + 6O2 summarizes photosynthesis.\n"
            "Glucose is the sugar produced during photosynthesis.\n"
        )
        files = {"file": (f"upload_{uuid.uuid4().hex}.txt", content.encode("utf-8"), "text/plain")}
        data = {"title": "classroom_upload"}
        with self.client.post(
            "/api/v1/ingest/upload",
            headers={"Authorization": f"Bearer {self.token}"},
            files=files,
            data=data,
            catch_response=True,
            name="/api/v1/ingest/upload",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code >= 500:
                response.failure(f"Server error {response.status_code}")
            else:
                response.failure(f"HTTP {response.status_code}")
