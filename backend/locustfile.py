from locust import HttpUser, task, between

class EduNavigatorUser(HttpUser):
    # Wait between 0.1 to 0.5 seconds between tasks to simulate high concurrency
    wait_time = between(0.1, 0.5)

    @task(5)
    def check_health(self):
        self.client.get("/health")

    @task(1)
    def ask_question(self):
        # Simple query to evaluate ask endpoint overhead
        self.client.post("/ask", json={
            "question": "hello",
            "history": []
        })
