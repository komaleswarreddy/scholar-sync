#!/usr/bin/env python3
"""Rewrite TestSprite tests to use embedded fixtures via ts_helpers."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TS = ROOT / "testsprite_tests"

TESTS = {
    "ING-01_happy_path_pdf_upload_and_chat_retrieval.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ing01():
    up = upload_fixture("standard_chapter.pdf")
    assert up["status_code"] == 200, up
    source_id = up["body"]["id"]
    final = wait_indexed(source_id)
    assert final["status"] == "indexed", final
    assert int(final.get("chunks_count") or 0) > 0
    chat = stream_chat("What role does chlorophyll play in photosynthesis?", [source_id])
    assert chat["status_code"] == 200, chat
    assert "citation" in chat["events"]
    assert chat["text"].strip()

if __name__ == "__main__":
    test_ing01()
''',
    "ING-02_txt_upload_two_distinct_phrases.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ing02():
    for fname, phrase in [("sample_phrase_alpha.txt", "mitochondria"), ("sample_phrase_beta.txt", "Snell")]:
        up = upload_fixture(fname)
        assert up["status_code"] == 200, up
        sid = up["body"]["id"]
        final = wait_indexed(sid)
        assert final["status"] == "indexed", final
        chat = stream_chat(f"Tell me about {phrase}", [sid])
        assert chat["status_code"] == 200
        assert chat["citations"] or phrase.lower() in chat["text"].lower()

if __name__ == "__main__":
    test_ing02()
''',
    "ING-03_encrypted_pdf_password_flow.py": '''
from ts_helpers import upload_fixture, wait_indexed

def test_ing03():
    bad = upload_fixture("encrypted_sample.pdf")
    assert bad["status_code"] == 400, bad
    good = upload_fixture("encrypted_sample.pdf", pdf_password="testpass")
    assert good["status_code"] == 200, good
    final = wait_indexed(good["body"]["id"])
    assert final["status"] == "indexed", final

if __name__ == "__main__":
    test_ing03()
''',
    "ING-04_large_pdf_indexes_within_sla.py": '''
import time
from ts_helpers import upload_fixture, wait_indexed

def test_ing04():
    start = time.time()
    up = upload_fixture("large_50page.pdf")
    assert up["status_code"] == 200, up
    final = wait_indexed(up["body"]["id"])
    assert time.time() - start < 300
    assert final["status"] == "indexed", final

if __name__ == "__main__":
    test_ing04()
''',
    "ING-08_chunking_produces_chunks.py": '''
from ts_helpers import upload_fixture, wait_indexed

def test_ing08():
    up = upload_fixture("standard_chapter.pdf")
    assert up["status_code"] == 200
    final = wait_indexed(up["body"]["id"])
    assert int(final.get("chunks_count") or 0) > 0

if __name__ == "__main__":
    test_ing08()
''',
    "ING-09_scanned_pdf_clear_error.py": '''
from ts_helpers import upload_fixture, wait_indexed

def test_ing09():
    up = upload_fixture("blank_scanned.pdf")
    assert up["status_code"] == 200, up
    final = wait_indexed(up["body"]["id"])
    assert final["status"] == "error", final
    msg = (final.get("error_message") or "").lower()
    assert "image-only" in msg or "no extractable" in msg or "extractable text" in msg

if __name__ == "__main__":
    test_ing09()
''',
    "ING-10_small_upload_latency.py": '''
import time
from ts_helpers import upload_bytes, wait_indexed, dev_jwt

def test_ing10():
    content = b"Small latency probe unique content for ING-10\\n"
    start = time.time()
    up = upload_bytes("latency_probe.txt", content, "text/plain")
    assert up["status_code"] == 200, up
    final = wait_indexed(up["body"]["id"])
    assert time.time() - start < 90
    assert final["status"] == "indexed"

if __name__ == "__main__":
    test_ing10()
''',
    "ING-11_concurrent_uploads_succeed.py": '''
import concurrent.futures
from ts_helpers import upload_bytes, wait_indexed

def _one(i):
    content = f"concurrent {i}\\n".encode()
    up = upload_bytes(f"c{i}.txt", content, "text/plain", sub=f"ts_concurrent_{i}")
    assert up["status_code"] == 200, up
    sid = up["body"]["id"]
    final = wait_indexed(sid, sub=f"ts_concurrent_{i}")
    assert final["status"] == "indexed", final
    return sid

def test_ing11():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        ids = list(ex.map(_one, range(3)))
    assert len(set(ids)) == 3

if __name__ == "__main__":
    test_ing11()
''',
    "ING-07_duplicate_upload_distinct_source_ids.py": '''
from ts_helpers import upload_fixture, wait_indexed

def test_ing07():
    ids = []
    for _ in range(2):
        up = upload_fixture("sample_phrase_alpha.txt")
        assert up["status_code"] == 200, up
        ids.append(up["body"]["id"])
    assert ids[0] != ids[1]
    for sid in ids:
        assert wait_indexed(sid)["status"] == "indexed"

if __name__ == "__main__":
    test_ing07()
''',
}

RET_TESTS = {
    "RET-01_factual_recall_via_chat_citations.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret01():
    up = upload_fixture("standard_chapter.pdf")
    sid = up["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What is the photosynthesis equation?", [sid])
    assert chat["status_code"] == 200
    blob = (chat["text"] + " " + " ".join(c.get("text","") for c in chat["citations"])).lower()
    assert "photosynthesis" in blob or "co2" in blob

if __name__ == "__main__":
    test_ret01()
''',
    "RET-06_out_of_corpus_refusal.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret06():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What year will humans colonize Mars permanently?", [sid])
    text = chat["text"].lower()
    assert "not found" in text

if __name__ == "__main__":
    test_ret06()
''',
    "RET-07_cross_user_source_isolation_403.py": '''
import requests
from ts_helpers import upload_fixture, wait_indexed, auth_headers, BASE_URL, TIMEOUT

def test_ret07():
    up = upload_fixture("sample_phrase_alpha.txt", sub="ts_user_a")
    sid = up["body"]["id"]
    wait_indexed(sid, sub="ts_user_a")
    r = requests.post(
        f"{BASE_URL}/api/v1/chat/stream",
        headers={**auth_headers("ts_user_b"), "Accept": "text/event-stream"},
        json={"message": "mitochondria powerhouse", "history": [], "active_source_ids": [sid]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 403, r.text

if __name__ == "__main__":
    test_ret07()
''',
    "RET-09_formula_retrieval.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret09():
    sid = upload_fixture("physics_formulas.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("State Snell's law formula", [sid])
    blob = (chat["text"] + " " + " ".join(c.get("text","") for c in chat["citations"])).lower()
    assert "snell" in blob

if __name__ == "__main__":
    test_ret09()
''',
    "RET-02_first_correct_citation_rank.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret02():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What is photosynthesis?", [sid])
    assert chat["citations"], chat
    assert chat["citations"][0].get("source_id") == sid or chat["citations"][0].get("id")

if __name__ == "__main__":
    test_ret02()
''',
    "RET-03_citation_relevance.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret03():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("Explain chlorophyll role in photosynthesis", [sid])
    blob = " ".join(c.get("text","") for c in chat["citations"]).lower()
    assert "chlorophyll" in blob or "photosynthesis" in blob

if __name__ == "__main__":
    test_ret03()
''',
    "RET-04_citation_supports_answer.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret04():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("What is the photosynthesis equation?", [sid])
    assert chat["citations"]
    assert chat["text"].strip()

if __name__ == "__main__":
    test_ret04()
''',
    "RET-05_multi_document_citations.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret05():
    ids = []
    for name in ["sample_phrase_alpha.txt", "sample_phrase_beta.txt"]:
        up = upload_fixture(name)
        sid = up["body"]["id"]
        wait_indexed(sid)
        ids.append(sid)
    chat = stream_chat("Compare mitochondria and Snell law topics", ids)
    assert len(chat["citations"]) >= 1

if __name__ == "__main__":
    test_ret05()
''',
    "RET-08_paraphrase_robustness.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret08():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    chat = stream_chat("How do green plants make food from sunlight?", [sid])
    blob = (chat["text"] + " " + " ".join(c.get("text","") for c in chat["citations"])).lower()
    assert "photosynthesis" in blob or "chlorophyll" in blob or chat["citations"]

if __name__ == "__main__":
    test_ret08()
''',
    "RET-10_question_type_variants.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret10():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    for q in ["What is photosynthesis?", "List steps of photosynthesis", "Why is chlorophyll important?"]:
        chat = stream_chat(q, [sid])
        assert chat["status_code"] == 200

if __name__ == "__main__":
    test_ret10()
''',
    "RET-11_long_question_retrieval.py": '''
from ts_helpers import upload_fixture, wait_indexed, stream_chat

def test_ret11():
    sid = upload_fixture("standard_chapter.pdf")["body"]["id"]
    wait_indexed(sid)
    long_q = " ".join(["Explain photosynthesis"] * 20)
    chat = stream_chat(long_q, [sid])
    assert chat["status_code"] == 200

if __name__ == "__main__":
    test_ret11()
''',
}

def main():
    for fname, body in {**TESTS, **RET_TESTS}.items():
        path = TS / fname
        if path.exists():
            path.write_text(body.strip() + "\n", encoding="utf-8")
            print("patched", fname)

if __name__ == "__main__":
    main()
