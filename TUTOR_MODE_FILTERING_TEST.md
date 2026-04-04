# Tutor Mode Metadata Filtering - Comprehensive Test & Validation

## Summary of Changes

I've added **comprehensive debug logging** to verify metadata filtering at every step:

### 1. **Filter Construction** 
The filter is built with:
- `class`: converted to integer (e.g., `10`)
- `subject`: normalized to lowercase (e.g., `"science"`)
- `chapter_no`: converted to integer (e.g., `3`)
- `chapter_name`: normalized to lowercase (e.g., `"metals and non-metals"`)

### 2. **Raw Pinecone Results**
After querying Pinecone, we log the metadata of every chunk retrieved:
```
[DEBUG] Raw Pinecone Results - Metadata of each chunk:
  [1] class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals, score=0.8234
  [2] class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals, score=0.7891
```

### 3. **Filter Criteria Logged**
Before post-processing, we show the exact criteria:
```
[DEBUG] FILTER CRITERIA:
  requested_class=10 (type=<class 'int'>)
  target_subject=science (type=<class 'str'>)
  requested_chapter_no=3 (type=<class 'int'>)
  requested_chapter_name=metals and non-metals (type=<class 'str'>)
```

### 4. **Post-Processing Validation**
Each chunk is validated:
```
[DEBUG] POST-PROCESSING FILTER VALIDATION:
  [1] ✅ ACCEPTED: class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals
  [2] ✅ ACCEPTED: class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals
  [3] ❌ REJECTED: class mismatch (requested=10, got=9)
  [4] ❌ REJECTED: subject mismatch (requested='science', got='math')
  [5] ❌ REJECTED: chapter_no mismatch (requested=3, got=1)
```

---

## Manual Testing Steps

### Prerequisites
1. **Server Running**: Confirm `python -u -m uvicorn apps.api.main:app --reload` is running
2. **Frontend Ready**: Navigate to `http://localhost:3000`
3. **Terminal Visible**: Have the backend terminal window open to see logs

### Test Configuration
Set these values in the Tutor Mode UI:
- ✅ Enable **"NCERT Global"** checkbox
- Set **Class** = `10`
- Set **Subject** = Select `Science` from dropdown  
- Set **Chapter** = Select `Ch. 3 - Metals and Non-metals`

### Test Queries

#### Query 1: "What is corrosion?"
**Expected**: Should find chunks (corrosion is in Ch. 3)
**What to look for in logs**:
- All accepted chunks must have `class=10`, `subject=science`, `chapter_no=3`
- Should see mostly ✅ ACCEPTED logs, few or no ❌ REJECTED

#### Query 2: "What is photosynthesis?"
**Expected**: Should find ZERO chunks (photosynthesis is Biology, not in Ch. 3)
**What to look for in logs**:
- Either `[TUTOR_RETRIEVAL_COMPLETE] No NCERT matches found`
- OR if any results appear, they must be from Ch. 3 (you'll see rejection logs for others)

#### Query 3: "What are isotopes?"
**Expected**: Should find ZERO chunks (isotopes are typically in Ch. 4 "Structure of Atom")
**What to look for in logs**:
- Either `[TUTOR_RETRIEVAL_COMPLETE] No NCERT matches found`
- OR if results appear, validate they're from Ch. 3

#### Query 4: "What is the law of conservation of mass?"
**Expected**: Should find ZERO chunks (this is in Ch. 1 "Chemical Reactions")
**What to look for in logs**:
- Either no matches
- OR see REJECTED logs for any that come from other chapters

---

## Validation Checklist

### ✅ PASS Conditions
1. **Query 1 (Corrosion)**: All results are from Class=10, Subject=Science, Chapter_no=3
2. **Query 2-4 (O, Isotopes, Conservation)**: Either:
   - Zero results returned (best case)
   - OR all returned results are still from Chapter 3
3. **Log Format**: Debug logs appear in clean, readable format with ✅✅ and ❌ symbols
4. **Type Correctness**: 
   - `class` is always int (e.g., `10`, not `"10"`)
   - `subject` is always lowercase string (e.g., `"science"`)
   - `chapter_no` is always int (e.g., `3`, not `"3"`)
   - `chapter_name` is always lowercase string

### ❌ FAIL Conditions
1. **Wrong Class**: A result shows `class=9` or `class=11`
2. **Wrong Subject**: A result shows `subject=math` or `subject=english`
3. **Wrong Chapter**: A result shows `chapter_no=1`, `chapter_no=2`, or `chapter_no=4`
4. **Type Mismatch**: 
   - Class shown as string `class="10"`
   - Chapter_no shown as string `chapter_no="3"`
   - Subject shown as uppercase `subject="Science"`

---

## Log Examples - What You'll See

### Example 1: CORRECT Filtering
```
[TUTOR_MODE_REQUEST] ncert_class=10
[TUTOR_MODE_REQUEST] ncert_subject=Science
[TUTOR_MODE_REQUEST] ncert_chapter_no=3
[TUTOR_MODE_REQUEST] ncert_chapter_name=Metals and Non-metals

[TUTOR_FILTER_BUILD] class=10 subject=Science chapter_no=3 chapter_name=Metals and Non-metals → filter={'$and': [{'source': {'$eq': 'ncert'}}, {'class': {'$eq': 10}}, {'subject': {'$eq': 'science'}}, {'chapter_no': {'$eq': 3}}, {'chapter_name': {'$eq': 'metals and non-metals'}}]}

[TUTOR_QUERY_PINECONE] Querying NcertDataGlobal with filter=...
[TUTOR_QUERY_PINECONE_RESULT] Got 24 raw matches from Pinecone

[DEBUG] Raw Pinecone Results - Metadata of each chunk:
  [1] class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals, score=0.8934
  [2] class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals, score=0.8712
  [3] class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals, score=0.8456

[DEBUG] FILTER CRITERIA:
  requested_class=10 (type=<class 'int'>)
  target_subject=science (type=<class 'str'>)
  requested_chapter_no=3 (type=<class 'int'>)
  requested_chapter_name=metals and non-metals (type=<class 'str'>)

[DEBUG] POST-PROCESSING FILTER VALIDATION:
  [1] ✅ ACCEPTED: class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals
  [2] ✅ ACCEPTED: class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals
  [3] ✅ ACCEPTED: class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals

[TUTOR_POSTPROCESS_FILTER] Total matches: 24, Rejected: 0, Kept: 3

[TUTOR_RETRIEVAL_COMPLETE] Retrieved 3 NCERT matches, now applying hybrid scoring
[TUTOR_HYBRID_SCORE] Hybrid scoring complete: 3 matches after reranking
```

### Example 2: INCORRECT Filtering (What to Fix)
```
[DEBUG] RAW PINECONE RESULTS:
  [1] class=10, subject=science, chapter_no=3, chapter_name=metals and non-metals, score=0.89
  [2] class=9, subject=science, chapter_no=3, chapter_name..., score=0.85  ❌ WRONG CLASS!
  [3] class=10, subject=physics, chapter_no=3, ..., score=0.82  ❌ WRONG SUBJECT!

[DEBUG] POST-PROCESSING FILTER VALIDATION:
  [1] ✅ ACCEPTED: class=10, subject=science, chapter_no=3, ...
  [2] ❌ REJECTED: class mismatch (requested=10, got=9)  ← PINECONE FILTER NOT WORKING
  [3] ❌ REJECTED: subject mismatch (requested='science', got='physics') ← PINECONE FILTER NOT WORKING
```

---

## If Filtering is NOT Working Correctly

If you see chunks being REJECTED with mismatches, the Pinecone namespace filter isn't working.

**Potential fixes needed**:

1. **Verify Pinecone Namespace**: Check if data is in the correct namespace ("NcertDataGlobal")
2. **Verify Metadata Format**: Ensure metadata keys are exactly:
   - `class` (not `class_num` or `className`)
   - `subject` (lowercase)
   - `chapter_no` (not `chapterNo` or `chapter_number`)
   - `chapter_name` (lowercase, not `chapterName`)
3. **Filter Syntax**: Ensure filter is properly constructed with `$and` and `$eq`

---

## Next Steps

1. **Open the backend terminal** where the server is running
2. **Go to http://localhost:3000** in your browser
3. **Enable Tutor Mode** with: Class 10, Science, Ch. 3
4. **Ask one of the test questions** (e.g., "What is corrosion?")
5. **Watch the terminal** for the debug logs
6. **Share the complete terminal output** with me

Once you run these tests and share the logs, I can:
- Verify filtering is 100% correct
- Identify any data inconsistencies
- Fix any issues found

