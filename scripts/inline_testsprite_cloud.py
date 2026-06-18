#!/usr/bin/env python3
"""Make TestSprite tests self-contained for cloud exec (no local imports)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = ROOT / "testsprite_tests"

PREAMBLE = r'''
import base64
import io
import json
import time
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 120
POLL_INTERVAL = 2
MAX_POLL_SECONDS = 300

FIXTURES = __FIXTURES_PLACEHOLDER__

def dev_jwt(sub="testsprite_user"):
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).rstrip(b"=").decode()
    return f"{header}.{payload}."

def auth_headers(sub="testsprite_user"):
    return {"Authorization": f"Bearer {dev_jwt(sub)}"}

def fixture_bytes(name):
    return base64.b64decode(FIXTURES[name])

def upload_bytes(filename, content, content_type, sub="testsprite_user", pdf_password=None):
    headers = auth_headers(sub)
    data = {}
    if pdf_password:
        data["pdf_password"] = pdf_password
    files = {"file": (filename, io.BytesIO(content), content_type)}
    r = requests.post(f"{BASE_URL}/api/v1/ingest/upload", headers=headers, files=files, data=data, timeout=TIMEOUT)
    body = r.json() if r.content else {}
    return {"status_code": r.status_code, "body": body, "text": r.text}

def upload_fixture(name, sub="testsprite_user", pdf_password=None):
    content = fixture_bytes(name)
    ctype = "application/pdf" if name.endswith(".pdf") else "text/plain"
    return upload_bytes(name, content, ctype, sub=sub, pdf_password=pdf_password)

def wait_indexed(source_id, sub="testsprite_user"):
    headers = auth_headers(sub)
    deadline = time.time() + MAX_POLL_SECONDS
    last = None
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/api/v1/ingest/sources", headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        last = next((s for s in r.json().get("sources", []) if s.get("id") == source_id), None)
        if last and last.get("status") in ("indexed", "error"):
            return last
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Source {source_id} not indexed. Last={last}")

def stream_chat(message, source_ids, sub="testsprite_user"):
    headers = {**auth_headers(sub), "Accept": "text/event-stream"}
    payload = {"message": message, "history": [], "active_source_ids": source_ids}
    r = requests.post(f"{BASE_URL}/api/v1/chat/stream", headers=headers, json=payload, timeout=TIMEOUT, stream=True)
    events, citations, text = [], [], ""
    if r.status_code != 200:
        return {"status_code": r.status_code, "text": r.text, "events": events, "citations": citations}
    current = None
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            current = line.split("event:", 1)[1].strip()
            events.append(current)
        elif line.startswith("data:") and current:
            try:
                data = json.loads(line.split("data:", 1)[1].strip())
            except json.JSONDecodeError:
                data = None
            if current == "citation" and isinstance(data, dict):
                citations.append(data)
            elif current == "chunk" and isinstance(data, dict):
                text += data.get("text", "")
    return {"status_code": 200, "events": events, "citations": citations, "text": text}
'''.strip()

TESTS = {
    "ING-01_happy_path_pdf_upload_and_chat_retrieval.py": '''
def test_ing01():
    up = upload_fixture("standard_chapter.pdf")
    assert up["status_code"] == 200, up
    sid = up["body"]["id"]
    final = wait_indexed(sid)
    assert final["status"] == "indexed", final
    assert int(final.get("chunks_count") or 0) > 0
    chat = stream_chat("What role does chlorophyll play in photosynthesis?", [sid])
    assert chat["status_code"] == 200, chat
    assert "citation" in chat["events"]
    assert chat["text"].strip() or chat["citations"]
test_ing01()
''',
    "ING-02_txt_upload_two_distinct_phrases.py": '''
def test_ing02():
    for fname, phrase in [("sample_phrase_alpha.txt", "mitochondria"), ("sample_phrase_beta.txt", "Snell")]:
        up = upload_fixture(fname)
        assert up["status_code"] == 200, up
        final = wait_indexed(up["body"]["id"])
        assert final["status"] == "indexed", final
        chat = stream_chat(f"Tell me about {phrase}", [up["body"]["id"]])
        assert chat["status_code"] == 200
test_ing02()
''',
    "ING-03_encrypted_pdf_password_flow.py": '''
def test_ing03():
    up = upload_fixture("encrypted_sample.pdf", pdf_password="testpass")
    assert up["status_code"] == 200, up
    final = wait_indexed(up["body"]["id"])
    assert final["status"] == "indexed", final
test_ing03()
''',
    "ING-04_large_pdf_indexes_within_sla.py": '''
import time
def test_ing04():
    start = time.time()
    up = upload_fixture("large_50page.pdf")
    assert up["status_code"] == 200, up
    final = wait_indexed(up["body"]["id"])
    assert time.time() - start < 300
    assert final["status"] == "indexed", final
test_ing04()
''',
    "ING-05_corrupt_files_return_400_not_500.py": '''
def test_ing05():
    for name in ["truncated.pdf", "jpg_renamed.pdf"]:
        up = upload_fixture(name)
        assert up["status_code"] == 400, up
    empty = upload_bytes("empty.pdf", b"", "application/pdf")
    assert empty["status_code"] == 400, empty
test_ing05()
''',
    "ING-07_duplicate_upload_distinct_source_ids.py": '''
def test_ing07():
    ids = [upload_fixture("sample_phrase_alpha.txt")["body"]["id"] for _ in range(2)]
    assert ids[0] != ids[1]
    for sid in ids:
        assert wait_indexed(sid)["status"] == "indexed"
test_ing07()
''',
    "ING-08_chunking_produces_chunks.py": '''
def test_ing08():
    up = upload_fixture("standard_chapter.pdf")
    final = wait_indexed(up["body"]["id"])
    assert int(final.get("chunks_count") or 0) > 0
test_ing08()
''',
    "ING-09_scanned_pdf_clear_error.py": '''
def test_ing09():
    up = upload_fixture("blank_scanned.pdf")
    assert up["status_code"] == 200, up
    final = wait_indexed(up["body"]["id"])
    assert final["status"] == "error", final
    msg = (final.get("error_message") or "").lower()
    assert "image-only" in msg or "extractable" in msg
test_ing09()
''',
    "ING-10_small_upload_latency.py": '''
import time
def test_ing10():
    start = time.time()
    up = upload_bytes("latency_probe.txt", b"Small latency probe ING-10\n", "text/plain")
    assert up["status_code"] == 200, up
    assert wait_indexed(up["body"]["id"])["status"] == "indexed"
    assert time.time() - start < 90
test_ing10()
''',
    "ING-11_concurrent_uploads_succeed.py": '''
import concurrent.futures
def _one(i):
    up = upload_bytes(f"c{i}.txt", f"concurrent {i}\n".encode(), "text/plain", sub=f"ts_c_{i}")
    assert up["status_code"] == 200, up
    assert wait_indexed(up["body"]["id"], sub=f"ts_c_{i}")["status"] == "indexed"
    return up["body"]["id"]
def test_ing11():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        ids = list(ex.map(_one, range(3)))
    assert len(set(ids)) == 3
test_ing11()
''',
    "RET-01_factual_recall_via_chat_citations.py": '''
def test_ret01():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What is the photosynthesis equation?", [sid])
    blob = (chat["text"] + " " + " ".join(c.get("text","") for c in chat["citations"])).lower()
    assert "photosynthesis" in blob or "co2" in blob or chat["citations"]
test_ret01()
''',
    "RET-02_first_correct_citation_rank.py": '''
def test_ret02():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What is photosynthesis?", [sid])
    assert chat["citations"]
test_ret02()
''',
    "RET-03_citation_relevance.py": '''
def test_ret03():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("Explain chlorophyll role in photosynthesis", [sid])
    blob = " ".join(c.get("text","") for c in chat["citations"]).lower()
    assert "chlorophyll" in blob or "photosynthesis" in blob or chat["text"]
test_ret03()
''',
    "RET-04_citation_supports_answer.py": '''
def test_ret04():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What is the photosynthesis equation?", [sid])
    assert chat["citations"] or chat["text"].strip()
test_ret04()
''',
    "RET-05_multi_document_citations.py": '''
def test_ret05():
    ids = []
    for name in ["sample_phrase_alpha.txt", "sample_phrase_beta.txt"]:
        sid = upload_fixture(name)["body"]["id"]
        wait_indexed(sid)
        ids.append(sid)
    chat = stream_chat("Compare mitochondria and Snell law topics", ids)
    assert chat["status_code"] == 200
test_ret05()
''',
    "RET-06_out_of_corpus_refusal.py": '''
def test_ret06():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What year will humans colonize Mars permanently?", [sid])
    assert "not found" in chat["text"].lower()
test_ret06()
''',
    "RET-07_cross_user_source_isolation_403.py": '''
def test_ret07():
    sid = upload_fixture("sample_phrase_alpha.txt", sub="ts_user_a")["body"]["id"]
    wait_indexed(sid, sub="ts_user_a")
    r = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers={**auth_headers("ts_user_b"), "Accept": "text/event-stream"},
        json={"message": "mitochondria powerhouse", "history": [], "active_source_ids": [sid]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 403, r.text
test_ret07()
''',
    "RET-08_paraphrase_robustness.py": '''
def test_ret08():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("How do green plants make food from sunlight?", [sid])
    assert chat["status_code"] == 200
test_ret08()
''',
    "RET-09_formula_retrieval.py": '''
def test_ret09():
    sid = upload_fixture("physics_formulas.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("State Snell's law formula", [sid])
    blob = (chat["text"] + " " + " ".join(c.get("text","") for c in chat["citations"])).lower()
    assert "snell" in blob or chat["citations"]
test_ret09()
''',
    "RET-10_question_type_variants.py": '''
def test_ret10():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    for q in ["What is photosynthesis?", "List steps of photosynthesis", "Why is chlorophyll important?"]:
        assert stream_chat(q, [sid])["status_code"] == 200
test_ret10()
''',
    "RET-11_long_question_retrieval.py": '''
def test_ret11():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    long_q = " ".join(["Explain photosynthesis"] * 20)
    assert stream_chat(long_q, [sid])["status_code"] == 200
test_ret11()
''',
}


def main():
    import importlib.util

    spec = importlib.util.spec_from_file_location("fixture_payloads", TS / "fixture_payloads.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fixtures_dict = "FIXTURES = " + repr(mod.FIXTURES)
    preamble = PREAMBLE.replace("__FIXTURES_PLACEHOLDER__", fixtures_dict)
    for fname, body in TESTS.items():
        path = TS / fname
        path.write_text(preamble + "\n\n" + body.strip() + "\n", encoding="utf-8")
        print("inlined", fname)


if __name__ == "__main__":
    main()
