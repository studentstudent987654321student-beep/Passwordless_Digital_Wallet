"""
Performance tests using Locust.
Load testing for authentication and wallet endpoints.

Run with:
    locust -f tests/locustfile.py --host=https://localhost

Or headless:
    locust -f tests/locustfile.py --host=https://localhost --headless -u 100 -r 10 -t 60s
"""
import random
import string
from locust import HttpUser, task, between, tag


def random_email():
    """Generate a random email address for testing."""
    chars = string.ascii_lowercase + string.digits
    username = ''.join(random.choice(chars) for _ in range(10))
    return f"{username}@loadtest.example.com"


class WebsiteUser(HttpUser):
    """Simulates a regular website visitor."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    @tag('homepage')
    @task(10)
    def view_homepage(self):
        """View the homepage."""
        self.client.get("/")
    
    @tag('about')
    @task(3)
    def view_about(self):
        """View the about page."""
        self.client.get("/about")
    
    @tag('static')
    @task(5)
    def load_static_assets(self):
        """Load static assets."""
        self.client.get("/static/css/style.css")
        self.client.get("/static/js/main.js")
    
    @tag('registration')
    @task(2)
    def view_registration_page(self):
        """View the registration page."""
        self.client.get("/register")
    
    @tag('login')
    @task(2)
    def view_login_page(self):
        """View the login page."""
        self.client.get("/login")


class AuthenticatingUser(HttpUser):
    """Simulates a user attempting to authenticate."""
    
    wait_time = between(2, 8)
    
    @tag('auth', 'registration')
    @task(3)
    def registration_options(self):
        """Request registration options (WebAuthn challenge)."""
        email = random_email()
        with self.client.post("/auth/register/options",
            json={
                "email": email,
                "display_name": "Load Test User"
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @tag('auth', 'login')
    @task(5)
    def login_options(self):
        """Request login options (WebAuthn challenge)."""
        with self.client.post("/auth/login/options",
            json={"email": "test@example.com"},
            catch_response=True
        ) as response:
            # 400/404 expected for non-existent user
            if response.status_code in [200, 400, 404]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class WalletUser(HttpUser):
    """Simulates an authenticated user accessing wallet features."""
    
    wait_time = between(1, 3)
    
    # Note: These tests will fail without proper authentication
    # In a real load test, you'd need to implement session handling
    
    @tag('wallet')
    @task(5)
    def get_balance(self):
        """Get wallet balance."""
        with self.client.get("/wallet/balance", catch_response=True) as response:
            # Expect 401 without authentication
            if response.status_code in [200, 401, 302]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @tag('wallet', 'transactions')
    @task(3)
    def get_transactions(self):
        """Get transaction history."""
        with self.client.get("/wallet/transactions", catch_response=True) as response:
            if response.status_code in [200, 401, 302]:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")


class StressTestUser(HttpUser):
    """Aggressive user for stress testing."""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    @tag('stress')
    @task(1)
    def rapid_homepage(self):
        """Rapidly request homepage."""
        self.client.get("/")
    
    @tag('stress', 'auth')
    @task(1)
    def rapid_auth_options(self):
        """Rapidly request auth options."""
        self.client.post("/auth/login/options",
            json={"email": "stress@test.com"}
        )


class ApiEndpointUser(HttpUser):
    """Tests specific API endpoints."""
    
    wait_time = between(1, 2)
    
    @tag('api', 'health')
    @task(10)
    def health_check(self):
        """Check health endpoint if available."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 404:
                response.success()  # Endpoint might not exist
            elif response.status_code == 200:
                response.success()
    
    @tag('api', 'error')
    @task(1)
    def trigger_404(self):
        """Test 404 handling."""
        with self.client.get("/nonexistent-endpoint", catch_response=True) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(f"Expected 404, got {response.status_code}")
    
    @tag('api', 'validation')
    @task(2)
    def test_invalid_registration(self):
        """Test registration validation."""
        with self.client.post("/auth/register/options",
            json={"email": "invalid-email"},  # Missing display_name, invalid email
            catch_response=True
        ) as response:
            if response.status_code == 400:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Expected 400, got {response.status_code}")


# Custom events for detailed metrics
from locust import events

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, **kwargs):
    """Log request details for analysis."""
    if response_time > 2000:  # Over 2 seconds
        print(f"SLOW REQUEST: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("=" * 50)
    print("Load Test Starting")
    print("Target: Passwordless Digital Wallet")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("=" * 50)
    print("Load Test Complete")
    print("=" * 50)
