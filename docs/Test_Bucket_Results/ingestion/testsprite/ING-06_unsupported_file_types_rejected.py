import requests
import base64
import json
import time
import hmac
import hashlib

BASE_URL = "http://localhost:8000"
UPLOAD_PATH = "/api/v1/ingest/upload"
TIMEOUT = 30

# Since ts_helpers is missing, define a simple dev JWT and auth headers inline
# For the dev token, we'll create a simple unsigned JWT with a 'sub' claim

def dev_jwt():
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip('=')
    payload = base64.urlsafe_b64encode(json.dumps({"sub": "test-user"}).encode()).decode().rstrip('=')
    # JWT with alg none requires no signature
    token = f"{header}.{payload}."
    return token

def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_unsupported_file_types_rejected():
    token = dev_jwt()
    headers = auth_headers(token)

    unsupported_files = {
        "file.exe": b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00",
        "video.mp4": b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42mp41",
        "archive.zip": b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
    }

    for filename, content_bytes in unsupported_files.items():
        files = {
            "file": (filename, content_bytes, "application/octet-stream")
        }
        response = requests.post(
            f"{BASE_URL}{UPLOAD_PATH}",
            headers=headers,
            files=files,
            timeout=TIMEOUT,
        )
        try:
            assert response.status_code == 400, (
                f"Upload of {filename} should return 400, got {response.status_code} with body: {response.text}"
            )
        except AssertionError:
            # Attempt to print response body for debugging in test logs
            print(f"Upload {filename} response body: {response.text}")
            raise

test_unsupported_file_types_rejected()
