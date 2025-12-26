"""
End-to-end tests using Playwright.
Tests complete user flows including registration, login, and wallet operations.
"""
import pytest
from playwright.sync_api import Page, expect


# Base URL for tests - adjust for your environment
BASE_URL = "https://localhost"


class TestHomePage:
    """Test homepage and navigation."""
    
    def test_homepage_loads(self, page: Page):
        """Test homepage loads successfully."""
        page.goto(BASE_URL)
        expect(page).to_have_title("Passwordless Digital Wallet")
    
    def test_homepage_has_hero_section(self, page: Page):
        """Test homepage displays hero section."""
        page.goto(BASE_URL)
        expect(page.locator(".hero")).to_be_visible()
        expect(page.locator(".hero h1")).to_contain_text("Passwordless")
    
    def test_homepage_has_get_started_button(self, page: Page):
        """Test homepage has get started button."""
        page.goto(BASE_URL)
        expect(page.get_by_role("link", name="Get Started")).to_be_visible()
    
    def test_homepage_has_login_button(self, page: Page):
        """Test homepage has login button."""
        page.goto(BASE_URL)
        expect(page.get_by_role("link", name="Login")).to_be_visible()
    
    def test_navigation_works(self, page: Page):
        """Test navigation links work."""
        page.goto(BASE_URL)
        
        # Click About link
        page.get_by_role("link", name="About").click()
        expect(page).to_have_url(f"{BASE_URL}/about")


class TestRegistrationPage:
    """Test registration page and flow."""
    
    def test_registration_page_loads(self, page: Page):
        """Test registration page loads successfully."""
        page.goto(f"{BASE_URL}/register")
        expect(page).to_have_title("Register")
        expect(page.locator("#register-form")).to_be_visible()
    
    def test_registration_form_has_required_fields(self, page: Page):
        """Test registration form has all required fields."""
        page.goto(f"{BASE_URL}/register")
        
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#display-name")).to_be_visible()
        expect(page.locator("#gdpr-consent")).to_be_visible()
        expect(page.locator("#register-btn")).to_be_visible()
    
    def test_registration_shows_privacy_info(self, page: Page):
        """Test registration page shows privacy information."""
        page.goto(f"{BASE_URL}/register")
        expect(page.locator(".info-box")).to_be_visible()
        expect(page.locator(".info-box")).to_contain_text("Privacy")
    
    def test_registration_requires_consent(self, page: Page):
        """Test registration requires GDPR consent."""
        page.goto(f"{BASE_URL}/register")
        
        # Fill form without consent
        page.fill("#email", "test@example.com")
        page.fill("#display-name", "Test User")
        
        # Try to submit
        page.click("#register-btn")
        
        # Form should not submit due to required checkbox
        expect(page).to_have_url(f"{BASE_URL}/register")
    
    def test_registration_email_validation(self, page: Page):
        """Test registration validates email format."""
        page.goto(f"{BASE_URL}/register")
        
        # Fill form with invalid email
        page.fill("#email", "invalid-email")
        page.fill("#display-name", "Test User")
        page.check("#gdpr-consent")
        
        # HTML5 validation should prevent submission
        page.click("#register-btn")
        
        # Should still be on registration page
        expect(page).to_have_url(f"{BASE_URL}/register")


class TestLoginPage:
    """Test login page and flow."""
    
    def test_login_page_loads(self, page: Page):
        """Test login page loads successfully."""
        page.goto(f"{BASE_URL}/login")
        expect(page).to_have_title("Login")
        expect(page.locator("#login-form")).to_be_visible()
    
    def test_login_form_has_email_field(self, page: Page):
        """Test login form has email field."""
        page.goto(f"{BASE_URL}/login")
        expect(page.locator("#email")).to_be_visible()
        expect(page.locator("#login-btn")).to_be_visible()
    
    def test_login_has_register_link(self, page: Page):
        """Test login page has register link."""
        page.goto(f"{BASE_URL}/login")
        expect(page.get_by_role("link", name="Register here")).to_be_visible()
    
    def test_login_shows_how_it_works(self, page: Page):
        """Test login page shows how it works info."""
        page.goto(f"{BASE_URL}/login")
        expect(page.locator(".info-box")).to_be_visible()


class TestAboutPage:
    """Test about page."""
    
    def test_about_page_loads(self, page: Page):
        """Test about page loads successfully."""
        page.goto(f"{BASE_URL}/about")
        expect(page).to_have_title("About")
    
    def test_about_has_project_overview(self, page: Page):
        """Test about page has project overview."""
        page.goto(f"{BASE_URL}/about")
        expect(page.locator("text=Project Overview")).to_be_visible()
    
    def test_about_has_technology_stack(self, page: Page):
        """Test about page shows technology stack."""
        page.goto(f"{BASE_URL}/about")
        expect(page.locator("text=Technology Stack")).to_be_visible()
    
    def test_about_has_security_features(self, page: Page):
        """Test about page shows security features."""
        page.goto(f"{BASE_URL}/about")
        expect(page.locator("text=Security Features")).to_be_visible()


class TestDashboardAccess:
    """Test dashboard access control."""
    
    def test_dashboard_redirects_unauthenticated(self, page: Page):
        """Test unauthenticated user is redirected from dashboard."""
        page.goto(f"{BASE_URL}/dashboard")
        
        # Should redirect to login
        expect(page).not_to_have_url(f"{BASE_URL}/dashboard")


class TestErrorPages:
    """Test error pages."""
    
    def test_404_page(self, page: Page):
        """Test 404 page displays correctly."""
        page.goto(f"{BASE_URL}/nonexistent-page")
        expect(page.locator("text=404")).to_be_visible()
    
    def test_404_has_home_link(self, page: Page):
        """Test 404 page has link to home."""
        page.goto(f"{BASE_URL}/nonexistent-page")
        expect(page.get_by_role("link", name="Go Home")).to_be_visible()


class TestResponsiveDesign:
    """Test responsive design on different viewports."""
    
    def test_mobile_viewport(self, page: Page):
        """Test page renders correctly on mobile."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(BASE_URL)
        
        expect(page.locator(".hero")).to_be_visible()
        # Navigation should be collapsed on mobile
        expect(page.locator(".nav-toggle")).to_be_visible()
    
    def test_tablet_viewport(self, page: Page):
        """Test page renders correctly on tablet."""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(BASE_URL)
        
        expect(page.locator(".hero")).to_be_visible()
    
    def test_desktop_viewport(self, page: Page):
        """Test page renders correctly on desktop."""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(BASE_URL)
        
        expect(page.locator(".hero")).to_be_visible()


class TestAccessibility:
    """Test accessibility features."""
    
    def test_page_has_main_landmark(self, page: Page):
        """Test page has main landmark."""
        page.goto(BASE_URL)
        expect(page.locator("main")).to_be_visible()
    
    def test_page_has_navigation_landmark(self, page: Page):
        """Test page has navigation landmark."""
        page.goto(BASE_URL)
        expect(page.locator("nav")).to_be_visible()
    
    def test_page_has_footer_landmark(self, page: Page):
        """Test page has footer landmark."""
        page.goto(BASE_URL)
        expect(page.locator("footer")).to_be_visible()
    
    def test_images_have_alt_text(self, page: Page):
        """Test images have alt text."""
        page.goto(BASE_URL)
        
        # All images should have alt attribute
        images = page.locator("img").all()
        for img in images:
            expect(img).to_have_attribute("alt")
    
    def test_form_labels_exist(self, page: Page):
        """Test form inputs have labels."""
        page.goto(f"{BASE_URL}/register")
        
        # Check email field has label
        expect(page.locator("label[for='email']")).to_be_visible()
        expect(page.locator("label[for='display-name']")).to_be_visible()


# Pytest fixtures for Playwright
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context for tests."""
    return {
        **browser_context_args,
        "ignore_https_errors": True,  # For self-signed certificates
    }


@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test."""
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    yield page
    page.close()
    context.close()
