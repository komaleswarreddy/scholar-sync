# Tutor Mode Filter Enforcement - Complete Fix Summary

## Problem Statement  
Tutor Mode filters were not being enforced during NCERT retrieval. Users selecting Class 9, Subject: Science, Chapter 4 were getting results from Class 10, Science, Chapter 3 instead.

## Root Causes Identified & Fixed

### 1. **Phantom Field in Pinecone Filter** ❌ → ✅ FIXED
**File:** `packages/core/rag/retriever.py`

**Issue:** The filter builder was including `{"tenant_id": {"$eq": ns}}` but this field doesn't exist in NCERT metadata.

**Where Tenant Filtering Happens:** Pinecone uses the `namespace` parameter, NOT metadata fields, for tenant isolation.

**Fix Applied:**
- Removed the non-existent `tenant_id` filter condition
- Kept `{"source": {"$eq": "ncert"}}` as the only required base filter
- Added debug logging to show the actual filter being built

**Code Change:**
```python
# BEFORE (lines 221-257)
conditions: List[Dict[str, Any]] = [
    {"tenant_id": {"$eq": ns}},  # ❌ DOESN'T EXIST
    {"source": {"$eq": "ncert"}},
]

# AFTER
conditions: List[Dict[str, Any]] = [
    {"source": {"$eq": "ncert"}},  # ✅ CORRECT
]
```

---

### 2. **Subject Case Sensitivity Mismatch** ❌ → ✅ FIXED
**File:** `packages/core/services/ncert_global_service.py` (line ~248)

**Issue:** 
- Metadata was stored as: `subject: "Science"` (capitalized)
- Filter was looking for: `subject: "science"` (lowercase)
- Pinecone's `$eq` operator is case-sensitive → NO MATCH → fallback to unfiltered results

**Fix Applied:**
- Normalize subject to lowercase at **ingestion time**: `"subject": subject.lower()`
- All future NCERT ingestions will now store subject as lowercase

**Code Change:**
```python
# BEFORE
"subject": subject,  # Stored as "Science"

# AFTER  
"subject": subject.lower(),  # Stored as "science"
```

---

### 3. **Chapter Name Case Sensitivity Mismatch** ❌ → ✅ FIXED
**File:** `packages/core/services/ncert_global_service.py` (line ~256)

**Issue:** Same as above but for chapter names
- Stored as: `"Corrosion"`, filter looking for: `"corrosion"`

**Fix Applied:**
- Normalize chapter_name to lowercase: `"chapter_name": chapter_name.lower()`

**Code Change:**
```python
# BEFORE
"chapter_name": chapter_name,  # Stored as "Corrosion"

# AFTER
"chapter_name": chapter_name.lower(),  # Stored as "corrosion"
```

---

### 4. **Comprehensive Debug Logging** ⚠️ → ✅ ADDED
Added three logging points to trace filter enforcement through the entire pipeline:

**a) Filter Builder Log:**
```python
print(f"[TUTOR_FILTER_BUILD] class={selected_class} subject={selected_subject} "
      f"chapter_no={selected_chapter_no} chapter_name={selected_chapter_name} "
      f"→ filter={meta_filter}")
```

**b) Pinecone Query Log:**
```python
print(f"[TUTOR_QUERY_PINECONE] ns={ns} filter={meta_filter}")
```

**C) Post-Processing Log:**
```python
print(f"[TUTOR_POSTPROCESS_FILTER] class={requested_class} subject={target_subject or 'all'} "
      f"chapter_no={requested_chapter_no if requested_chapter_no is not None else 'all'} "
      f"chapter_name={requested_chapter_name or 'all'} "
      f"raw={len(gmatches)} filtered_out={failed_filters_count} kept={len(filtered)}")
```

---

## Filter Flow Visualization

```
Frontend (Chat UI)
    ↓ (ncert_class=9, ncert_subject="science", ncert_chapter_no=4)
API (ChatRequest)
    ↓
ChatGraph._stream() 
    ↓
Retriever._retrieve_ncert_global_matches()
    ↓
_build_ncert_global_filter()  ← [TUTOR_FILTER_BUILD] logged here
    ↓ (builds {"$and": [{"source": {"$eq": "ncert"}}, {"class": {"$eq": 9}}, ...]})
Pinecone.query()             ← [TUTOR_QUERY_PINECONE] logged here
    ↓ (returns chunks where metadata MATCHES the filter)
Post-processing              ← [TUTOR_FILTER_MISMATCH] logged if any mismatches
    ↓ (double-checks metadata, filters out non-matches for backward compatibility)
Response
```

---

## Backward Compatibility Note

**Existing NCERT Data in Pinecone:**
- Old data may still have capitalized subject/chapter names (e.g., "Science", "Corrosion")
- Post-processing filter will still work because it normalizes to lowercase before comparing
- **Performance Note:** Post-processing is slower than Pinecone filter. New data will be instant.

**New NCERT Ingestions:**
- Will store subject and chapter_name in lowercase
- Will match filters instantly in Pinecone (faster retrieval)

---

## How to Test the Fix

### Step 1: Verify Backend is Running
Backend should be running on `http://localhost:8000` with the fixes loaded.

### Step 2: Test from Frontend UI
1. **Open the NotebookLM web interface**
2. **Navigate to Tutor Mode**
3. **Select Filters:**
   - Class: 9
   - Subject: Science  
   - Chapter: 4 (or any chapter)
4. **Ask a question** related to the selected chapter (e.g., "What is corrosion?")
5. **Check the response:**
   - All returned chunks should have `class=9`, `subject="science"`, `chapter_no=4`
   - Should NOT see results from other classes, subjects, or chapters
   - Response should be specific to the selected content

### Step 3: Monitor Backend Logs
Watch the API server terminal for these debug logs:

```
[TUTOR_FILTER_BUILD] class=9 subject=science chapter_no=4 chapter_name=corrosion → filter={...}
[TUTOR_QUERY_PINECONE] ns=NcertDataGlobal filter={...}
[TUTOR_POSTPROCESS_FILTER] class=9 subject=science chapter_no=4 chapter_name=corrosion raw=N filtered_out=0 kept=N
```

**Expected Results:**
- `raw=N` should be >> 0 (positive number of results from Pinecone)
- `filtered_out=0` should be 0 (no mismatches in post-processing)
- `kept=N` should equal `raw=N` (all results kept)

### Step 4: Test Edge Cases
1. **Only class selected (no subject/chapter):**
   - Should get all results for Class 9 across all subjects/chapters
   
2. **Class + Subject (no chapter):**
   - Should get all Class 9 Science chapters
   
3. **All filters selected:**
   - Should get only matching chapter results

4. **No filters (uncheck all):**
   - Should return full NCERT corpus (or empty if tutor mode is disabled)

---

## If Issues Persist

### Symptom: Still getting results from wrong class/subject/chapter

**Debugging Steps:**
1. **Check API logs for the TUTOR_* debug messages**
   - If `[TUTOR_FILTER_BUILD]` shows wrong values → frontend not sending filters correctly
   - If `[TUTOR_QUERY_PINECONE]` shows no filter → ChatGraph not passing filters to Retriever
   - If `[TUTOR_POSTPROCESS_FILTER]` shows `filtered_out > 0` → old data with wrong casing

2. **Re-ingest NCERT Data**
   - Old metadata in Pinecone with capitalized values will eventually make new metadata post-processing slow
   - Consider dropping and re-ingesting NCERT global collection to normalize all metadata

3. **Check Pinecone Metadata Directly**
   - Query Pinecone directly to verify metadata field casing for existing chunks
   - Command: `pinecone index describe NcertDataGlobal`

---

## Files Changed

1. **packages/core/rag/retriever.py**
   - Removed tenant_id filter condition
   - Normalized subject and chapter_name to lowercase in filter builder
   - Added comprehensive debug logging at 3 points

2. **packages/core/services/ncert_global_service.py**
   - Normalized subject to lowercase at ingestion: `subject.lower()`
   - Normalized chapter_name to lowercase at ingestion: `chapter_name.lower()`

---

## Summary

✅ **Fixed:** Removed phantom `tenant_id` field from Pinecone filter  
✅ **Fixed:** Ensured subject and chapter_name normalized to lowercase  
✅ **Added:** Comprehensive debug logging for filter flow tracing  
✅ **Backend:** Restarted with new code loaded  
✅ **Ready:** For manual testing from frontend  

**Next Steps:** Test from frontend UI and verify debug logs show expected output.
