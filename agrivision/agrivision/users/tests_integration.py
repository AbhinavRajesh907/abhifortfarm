from decimal import Decimal
import io
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from agrivision.marketplace.models import Category, Product
from agrivision.providers.models import ProviderProfile, ProviderRequest

User = get_user_model()


class AgriFarmFullIntegrationTests(TestCase):
    """
    End-to-End Integration Tests covering all 9 required verification points:
    1. User Registration & Login Flow
    2. Provider Registration & Verification Submission
    3. Provider Login Before Approval (Pending Status Enforcement)
    4. Admin Login & Dashboard Access
    5. Admin Provider Verification Review
    6. Admin Approves Provider
    7. Approved Provider Login & Dashboard Access
    8. Access Control & Cross-Role Permissions Enforcement
    9. Logout Flow
    """

    def setUp(self):
        # Initial Category setup
        self.cat_seeds = Category.objects.create(name=Category.SEEDS, description="Seed catalog")
        self.cat_plants = Category.objects.create(name=Category.PLANTS, description="Plant catalog")

        # Create Admin Account
        self.admin_user = User.objects.create_superuser(
            username="admin@agrifarm.com",
            email="admin@agrifarm.com",
            password="AdminPassword123!",
            name="AgriFarm Admin",
            role=User.Role.ADMIN,
        )

        self.client = Client()

    def test_01_user_registration_and_login_flow(self):
        """Test 1: User Registration, DB persistence, unauthenticated state, login and redirection to User Dashboard."""
        # Registration submission
        user_reg_data = {
            "username": "rajesh_farmer",
            "name": "Rajesh Kumar",
            "email": "rajesh@gmail.com",
            "phone": "9847123456",
            "address": "Kovilakam House, Main Road",
            "city": "Thrissur",
            "state": "Kerala",
            "pincode": "680001",
            "password": "FarmerPassword123!",
            "confirm_password": "FarmerPassword123!",
        }
        response = self.client.post(reverse("users:register_user"), data=user_reg_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

        # Verify DB persistence
        user = User.objects.get(username="rajesh_farmer")
        self.assertEqual(user.name, "Rajesh Kumar")
        self.assertEqual(user.email, "rajesh@gmail.com")
        self.assertEqual(user.role, User.Role.USER)
        self.assertFalse(hasattr(user, "provider_profile"))

        # Verify not automatically logged in
        home_res = self.client.get(reverse("home"))
        self.assertNotContains(home_res, "Sign Out")

        # Login with credentials
        login_res = self.client.post(
            reverse("users:login"),
            data={"username": "rajesh_farmer", "password": "FarmerPassword123!"},
        )
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse("marketplace:dashboard"))

        # Verify marketplace dashboard accessible
        dash_res = self.client.get(reverse("marketplace:dashboard"))
        self.assertEqual(dash_res.status_code, 200)

    def test_02_provider_registration_flow(self):
        """Test 2: Provider Registration with 3-section data, license upload, and PENDING status."""
        license_file = SimpleUploadedFile(
            "agri_license.pdf",
            b"%PDF-1.4 dummy license content",
            content_type="application/pdf",
        )

        prov_reg_data = {
            "username": "greenroots_nursery",
            "name": "Suresh Babu",
            "email": "suresh@greenroots.com",
            "phone": "9847011223",
            "address": "Green Valley, Meppadi Road",
            "city": "Kalpetta",
            "state": "Kerala",
            "pincode": "673121",
            "farm_name": "GreenRoots Agro Nursery",
            "farm_address": "Facility 1, Meppadi, Wayanad",
            "provider_type": "Plant Nursery",
            "experience_years": "8 Years",
            "description": "Specialized in fruit saplings and organic seeds.",
            "license_number": "KER-AGRI-2026-99",
            "license_type": "Nursery Trade License",
            "issuing_authority": "Dept of Agriculture Kerala",
            "issue_date": "2024-01-15",
            "expiry_date": "2028-01-15",
            "license_document": license_file,
            "password": "ProviderPassword123!",
            "confirm_password": "ProviderPassword123!",
        }

        response = self.client.post(reverse("users:register_provider"), data=prov_reg_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("home"))

        # Verify User and ProviderProfile in DB
        prov_user = User.objects.get(username="greenroots_nursery")
        self.assertEqual(prov_user.role, User.Role.PROVIDER)
        profile = prov_user.provider_profile
        self.assertEqual(profile.farm_name, "GreenRoots Agro Nursery")
        self.assertEqual(profile.license_number, "KER-AGRI-2026-99")
        self.assertEqual(profile.verification_status, ProviderProfile.VerificationStatus.PENDING)
        self.assertTrue(profile.is_pending)
        self.assertFalse(profile.is_approved)
        self.assertTrue(bool(profile.license_document))

    def test_03_provider_login_before_approval(self):
        """Test 3: Provider login before approval -> blocked from Joyal's Dashboard and shown status."""
        prov_user = User.objects.create_user(
            username="pending_provider",
            email="pending@farm.com",
            password="ProviderPassword123!",
            name="Pending Farmer",
            role=User.Role.PROVIDER,
        )
        ProviderProfile.objects.create(
            user=prov_user,
            farm_name="Pending Agro",
            phone_number="9847000000",
            license_number="LIC-PENDING-01",
            license_type="Trade License",
            issuing_authority="Agri Dept",
            verification_status=ProviderProfile.VerificationStatus.PENDING,
        )

        # Log in
        login_res = self.client.post(
            reverse("users:login"),
            data={"username": "pending_provider", "password": "ProviderPassword123!"},
        )
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse("providers:status"))

        # Direct access to provider dashboard must be blocked & redirected to status
        dash_res = self.client.get(reverse("providers:dashboard"))
        self.assertEqual(dash_res.status_code, 302)
        self.assertRedirects(dash_res, reverse("providers:status"))

        # Status page must load cleanly
        status_res = self.client.get(reverse("providers:status"))
        self.assertEqual(status_res.status_code, 200)
        self.assertContains(status_res, "Pending")

    def test_04_admin_login_and_dashboard_access(self):
        """Test 4: Admin login -> reaches Santhana's Admin Dashboard."""
        login_res = self.client.post(
            reverse("users:login"),
            data={"username": "admin@agrifarm.com", "password": "AdminPassword123!"},
        )
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse("admin_portal:dashboard"))

        dash_res = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "AgriVision Control Center")

    def test_05_and_06_admin_reviews_and_approves_provider(self):
        """Test 5 & 6: Admin views pending provider details/license and approves provider."""
        prov_user = User.objects.create_user(
            username="kavitha_seeds",
            email="kavitha@sahyadri.com",
            password="ProviderPassword123!",
            name="Kavitha Pillai",
            role=User.Role.PROVIDER,
        )
        profile = ProviderProfile.objects.create(
            user=prov_user,
            farm_name="Sahyadri Organic Seed Farms",
            phone_number="9447144556",
            city="Thodupuzha",
            district="Idukki",
            license_number="LIC-IDK-2026",
            license_type="Seed Certification",
            issuing_authority="Kerala State Seed Authority",
            verification_status=ProviderProfile.VerificationStatus.PENDING,
        )

        # Log in as Admin
        self.client.login(username="admin@agrifarm.com", password="AdminPassword123!")

        # 5. Check provider in admin provider list and view details
        list_res = self.client.get(reverse("admin_portal:provider_list"))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Sahyadri Organic Seed Farms")

        detail_res = self.client.get(reverse("admin_portal:provider_detail", kwargs={"pk": profile.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "LIC-IDK-2026")
        self.assertContains(detail_res, "Kerala State Seed Authority")

        # 6. Admin approves provider
        approve_res = self.client.post(
            reverse("admin_portal:provider_approve", kwargs={"pk": profile.pk}),
            follow=True,
        )
        self.assertEqual(approve_res.status_code, 200)

        # Verify DB status updated
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, ProviderProfile.VerificationStatus.APPROVED)
        self.assertTrue(profile.is_approved)
        self.assertIsNotNone(profile.verification_date)

    def test_07_provider_login_after_approval(self):
        """Test 7: Approved provider logs in -> automatically reaches Joyal's Provider Dashboard."""
        prov_user = User.objects.create_user(
            username="approved_farmer",
            email="approved@farm.com",
            password="FarmerPassword123!",
            name="Approved Farmer",
            role=User.Role.PROVIDER,
        )
        ProviderProfile.objects.create(
            user=prov_user,
            farm_name="Approved Green Valley Farm",
            phone_number="9876543210",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )

        login_res = self.client.post(
            reverse("users:login"),
            data={"username": "approved_farmer", "password": "FarmerPassword123!"},
        )
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse("providers:dashboard"))

        dash_res = self.client.get(reverse("providers:dashboard"))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Approved Green Valley Farm")

    def test_08_access_control_and_permissions(self):
        """Test 8: Strict access control between Normal User, Provider, and Admin."""
        # 1. Normal User
        user = User.objects.create_user(
            username="norm_user",
            email="user@test.com",
            password="Password123!",
            role=User.Role.USER,
        )
        self.client.login(username="norm_user", password="Password123!")

        # Normal user blocked from Provider Dashboard
        res = self.client.get(reverse("providers:dashboard"))
        self.assertEqual(res.status_code, 302)

        # Normal user blocked from Admin Portal
        res_admin = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(res_admin.status_code, 302)
        self.client.logout()

        # 2. Approved Provider blocked from Admin Portal
        prov_user = User.objects.create_user(
            username="prov_user",
            email="prov@test.com",
            password="Password123!",
            role=User.Role.PROVIDER,
        )
        ProviderProfile.objects.create(
            user=prov_user,
            farm_name="Test Prov Farm",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )
        self.client.login(username="prov_user", password="Password123!")

        res_prov_to_admin = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(res_prov_to_admin.status_code, 302)
        self.client.logout()

        # 3. Unauthenticated access blocked on all protected routes
        for protected_url in [
            reverse("marketplace:dashboard"),
            reverse("providers:dashboard"),
            reverse("admin_portal:dashboard"),
        ]:
            unauth_res = self.client.get(protected_url)
            self.assertEqual(unauth_res.status_code, 302)
            self.assertIn("login", unauth_res.url)

    def test_09_logout_flow(self):
        """Test 9: Logout clears session and redirects to Home page."""
        user = User.objects.create_user(
            username="logout_user",
            email="logout@test.com",
            password="Password123!",
            role=User.Role.USER,
        )
        self.client.login(username="logout_user", password="Password123!")

        # Perform logout
        logout_res = self.client.get(reverse("users:logout"))
        self.assertEqual(logout_res.status_code, 302)
        self.assertRedirects(logout_res, reverse("home"))

        # Verify session cleared
        dash_res = self.client.get(reverse("marketplace:dashboard"))
        self.assertEqual(dash_res.status_code, 302)
        self.assertIn("login", dash_res.url)
