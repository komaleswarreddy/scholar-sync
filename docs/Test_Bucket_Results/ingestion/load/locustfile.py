"""

ING-11 concurrent upload load test.



Mirrors the pytest burst pattern: each simulated user performs one upload at

start-up; Locust keeps the run alive without hammering the DB connection pool.



Usage:

  pip install locust

  locust -f tests/load/locustfile.py --host http://127.0.0.1:8000 --users 5 --spawn-rate 5 --run-time 60s

"""



from __future__ import annotations



import uuid



from locust import HttpUser, constant, task



from tests.helpers.auth import make_dev_jwt





class IngestionUser(HttpUser):

    wait_time = constant(30)



    def on_start(self) -> None:

        self.token = make_dev_jwt(f"locust_{uuid.uuid4().hex[:8]}")

        self._upload_once()



    def _upload_once(self) -> None:

        content = f"Locust concurrent upload {uuid.uuid4()}\n"

        files = {"file": (f"load_{uuid.uuid4().hex}.txt", content.encode("utf-8"), "text/plain")}

        data = {"title": "locust_upload"}

        with self.client.post(

            "/api/v1/ingest/upload",

            headers={"Authorization": f"Bearer {self.token}"},

            files=files,

            data=data,

            catch_response=True,

        ) as response:

            if response.status_code == 200:

                response.success()

            elif response.status_code >= 500:

                response.failure(f"Server error {response.status_code}")

            else:

                detail = ""

                try:

                    detail = response.json().get("detail", "")[:120]

                except Exception:  # noqa: BLE001

                    detail = response.text[:120]

                response.failure(f"HTTP {response.status_code}: {detail}")



    @task

    def idle(self) -> None:

        """Hold the user session open without additional uploads."""

        return


