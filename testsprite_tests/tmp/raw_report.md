
# TestSprite AI Testing Report(MCP)

---

## 1️⃣ Document Metadata
- **Project Name:** NotebookLM
- **Date:** 2026-06-10
- **Prepared by:** TestSprite AI Team

---

## 2️⃣ Requirement Validation Summary

#### Test TC001 health_check_endpoint_returns_service_status
- **Test Code:** [TC001_health_check_endpoint_returns_service_status.py](./TC001_health_check_endpoint_returns_service_status.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/789318c6-a9c1-493a-9982-424b1dd5bebb
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-01 happy_path_pdf_upload_and_chat_retrieval
- **Test Code:** [ING-01_happy_path_pdf_upload_and_chat_retrieval.py](./ING-01_happy_path_pdf_upload_and_chat_retrieval.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/e2077c7e-f050-4087-94c4-1207eb84260d
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-02 txt_upload_two_distinct_phrases
- **Test Code:** [ING-02_txt_upload_two_distinct_phrases.py](./ING-02_txt_upload_two_distinct_phrases.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/cd6b3152-1f65-4acc-ade4-cbfca518936f
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-03 encrypted_pdf_password_flow
- **Test Code:** [ING-03_encrypted_pdf_password_flow.py](./ING-03_encrypted_pdf_password_flow.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 93, in <module>
  File "<string>", line 56, in test_encrypted_pdf_password_flow
AssertionError: Expected 400 but got 200

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/220a2a18-3f10-42c4-bed3-caf94046960e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-04 large_pdf_indexes_within_sla
- **Test Code:** [ING-04_large_pdf_indexes_within_sla.py](./ING-04_large_pdf_indexes_within_sla.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 40, in <module>
ModuleNotFoundError: No module named 'fixture_payloads'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/73256823-c345-47f5-a1fd-2750feeb300a
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-05 corrupt_files_return_400_not_500
- **Test Code:** [ING-05_corrupt_files_return_400_not_500.py](./ING-05_corrupt_files_return_400_not_500.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 43, in <module>
  File "<string>", line 38, in test_corrupt_files_return_400_not_500
AssertionError: Expected 400 for truncated.pdf upload but got 401 with content: {"detail":"Invalid or expired authentication token: Invalid or expired token: Not enough segments","error_code":"INVALID_TOKEN"}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/591f982c-4862-4f3a-95b8-194e83e956ed
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-06 unsupported_file_types_rejected
- **Test Code:** [ING-06_unsupported_file_types_rejected.py](./ING-06_unsupported_file_types_rejected.py)
- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/95df058d-15f0-48fa-8491-58d581ef634a
- **Status:** ✅ Passed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-07 duplicate_upload_distinct_source_ids
- **Test Code:** [ING-07_duplicate_upload_distinct_source_ids.py](./ING-07_duplicate_upload_distinct_source_ids.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/fab06c52-9b55-42cf-b091-c22872609f03
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-08 chunking_produces_chunks
- **Test Code:** [ING-08_chunking_produces_chunks.py](./ING-08_chunking_produces_chunks.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 3, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/765b40a4-04b6-4543-8b39-a5a0d811373a
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-09 scanned_pdf_clear_error
- **Test Code:** [ING-09_scanned_pdf_clear_error.py](./ING-09_scanned_pdf_clear_error.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 99, in <module>
  File "<string>", line 58, in test_scanned_pdf_clear_error
AssertionError: Upload failed: {"detail":"Failed to read PDF: negative seek value -1"}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/96bd6704-6f37-44bc-ae48-a215a6442065
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-10 small_upload_latency
- **Test Code:** [ING-10_small_upload_latency.py](./ING-10_small_upload_latency.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 3, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/52a44bfd-b179-4972-9473-a5cb9afb4e50
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test ING-11 concurrent_uploads_succeed
- **Test Code:** [ING-11_concurrent_uploads_succeed.py](./ING-11_concurrent_uploads_succeed.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 3, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/b5a07101-98da-4c70-855b-327e18128d50
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-01 factual_recall_via_chat_citations
- **Test Code:** [RET-01_factual_recall_via_chat_citations.py](./RET-01_factual_recall_via_chat_citations.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 3, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/d9c1ace9-468b-4cd4-af6a-9b2d4a5c3e75
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-02 first_correct_citation_rank
- **Test Code:** [RET-02_first_correct_citation_rank.py](./RET-02_first_correct_citation_rank.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 132, in <module>
  File "<string>", line 57, in test_RET_02_first_correct_citation_rank
AssertionError: Upload failed: {"detail":"PDF file appears to be corrupted or invalid: Stream has ended unexpectedly"}

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/1b174887-614d-4306-8d0a-c2d45ae559da
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-03 citation_relevance
- **Test Code:** [RET-03_citation_relevance.py](./RET-03_citation_relevance.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 138, in <module>
  File "<string>", line 90, in test_ret_03_citation_relevance
AssertionError: Upload failed with 400

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/758411d5-1380-4c5f-b575-e9a77b1fbf5e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-04 citation_supports_answer
- **Test Code:** [RET-04_citation_supports_answer.py](./RET-04_citation_supports_answer.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/e1e2ac49-7322-486f-98d3-a25e653f582c
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-05 multi_document_citations
- **Test Code:** [RET-05_multi_document_citations.py](./RET-05_multi_document_citations.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/50298380-21eb-434b-9504-065647137d0e
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-06 out_of_corpus_refusal
- **Test Code:** [RET-06_out_of_corpus_refusal.py](./RET-06_out_of_corpus_refusal.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 3, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/dcdf11c3-01f2-443f-8411-7ab0d3c1c521
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-07 cross_user_source_isolation_403
- **Test Code:** [RET-07_cross_user_source_isolation_403.py](./RET-07_cross_user_source_isolation_403.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/02882ded-3edf-4012-86d2-64cc7c4b5e72
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-08 paraphrase_robustness
- **Test Code:** [RET-08_paraphrase_robustness.py](./RET-08_paraphrase_robustness.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 143, in <module>
  File "<string>", line 89, in test_RET_08_paraphrase_robustness
AssertionError: Upload failed with status 400

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/8866b7a5-b3ff-4ec3-9e7d-372baad78df9
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-09 formula_retrieval
- **Test Code:** [RET-09_formula_retrieval.py](./RET-09_formula_retrieval.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 2, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/b61197b3-1a08-4799-a8f8-a050396f7c43
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-10 question_type_variants
- **Test Code:** [RET-10_question_type_variants.py](./RET-10_question_type_variants.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 3, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/196ee172-7abc-4cd9-9385-6e5708c00e35
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---

#### Test RET-11 long_question_retrieval
- **Test Code:** [RET-11_long_question_retrieval.py](./RET-11_long_question_retrieval.py)
- **Test Error:** Traceback (most recent call last):
  File "/var/task/handler.py", line 258, in run_with_retry
    exec(code, exec_env)
  File "<string>", line 4, in <module>
ModuleNotFoundError: No module named 'ts_helpers'

- **Test Visualization and Result:** https://www.testsprite.com/dashboard/mcp/tests/8d88a466-aebf-4865-a0a9-ef53b4ebb096/92aadfd0-dabf-4515-8b6c-337ba4abba39
- **Status:** ❌ Failed
- **Analysis / Findings:** {{TODO:AI_ANALYSIS}}.
---


## 3️⃣ Coverage & Matching Metrics

- **8.70** of tests passed

| Requirement        | Total Tests | ✅ Passed | ❌ Failed  |
|--------------------|-------------|-----------|------------|
| ...                | ...         | ...       | ...        |
---


## 4️⃣ Key Gaps / Risks
{AI_GNERATED_KET_GAPS_AND_RISKS}
---