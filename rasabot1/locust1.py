from locust import HttpUser, between, task

class LoadTest(HttpUser):
    wait_time = between(1, 5)

    @task
    def load_homepage(self):
        self.client.get("http://192.168.85.234:8000/chat")

if __name__ == "__main__":
    import os
    os.system("locust -f locust1.py --headless -u 1000 -r 10")