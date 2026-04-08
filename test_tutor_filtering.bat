@echo off
REM Test script to verify Tutor Mode metadata filtering
REM This script makes HTTP requests to the chat API with NCERT filters enabled

echo =========================================================================
echo TUTOR MODE METADATA FILTERING TEST
echo =========================================================================
echo.

REM Note: Replace USER_ID_TOKEN with an actual valid auth token from your Supabase
REM For testing, you might need to get this from your browser's localStorage

set AUTH_TOKEN=YOUR_AUTH_TOKEN_HERE
set API_URL=http://127.0.0.1:8000
set CONTENT_TYPE=application/json

REM Test Case 1: Class 10, Science, Chapter 3 - "What is corrosion?"
echo TEST CASE 1: Class 10, Science, Chapter 3 - "What is corrosion?"
echo =========================================================================
echo.

curl -X POST "%API_URL%/api/v1/chat/stream" ^
  -H "Content-Type: %CONTENT_TYPE%" ^
  -H "Authorization: Bearer %AUTH_TOKEN%" ^
  -d "{ ^
    \"messages\": [{\"role\": \"user\", \"content\": \"What is corrosion?\"}], ^
    \"active_source_ids\": [], ^
    \"include_ncert\": true, ^
    \"ncert_class\": 10, ^
    \"ncert_subject\": \"Science\", ^
    \"ncert_chapter_no\": 3, ^
    \"ncert_chapter_name\": \"Metals and Non-metals\" ^
  }"

echo.
echo.
echo =========================================================================
echo TEST CASE 2: Same filters - "What is photosynthesis?"
echo =========================================================================
echo.

curl -X POST "%API_URL%/api/v1/chat/stream" ^
  -H "Content-Type: %CONTENT_TYPE%" ^
  -H "Authorization: Bearer %AUTH_TOKEN%" ^
  -d "{ ^
    \"messages\": [{\"role\": \"user\", \"content\": \"What is photosynthesis?\"}], ^
    \"active_source_ids\": [], ^
    \"include_ncert\": true, ^
    \"ncert_class\": 10, ^
    \"ncert_subject\": \"Science\", ^
    \"ncert_chapter_no\": 3, ^
    \"ncert_chapter_name\": \"Metals and Non-metals\" ^
  }"

echo.
echo =========================================================================
echo Check the backend terminal for detailed debug logs
echo =========================================================================
