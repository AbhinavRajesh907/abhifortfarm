from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from agrivision.marketplace.models import Category, Product, Order, OrderItem
from agrivision.providers.models import ProviderProfile, ProviderRequest

User = get_user_model()


class ProviderWorkflowTests(TestCase):
    def setUp(self):
        # Create Categories
        self.category_seeds = Category.objects.create(name=Category.SEEDS)
        self.category_plants = Category.objects.create(name=Category.PLANTS)

        # Create Normal User 1 (Applicant / Provider A)
        self.user_a = User.objects.create_user(
            email="provider_a@example.com",
            password="testpassword123",
            name="Alice Farmer",
        )

        # Create Normal User 2 (Provider B)
        self.user_b = User.objects.create_user(
            email="provider_b@example.com",
            password="testpassword123",
            name="Bob Nursery",
        )

        # Create Normal Buyer User
        self.buyer_user = User.objects.create_user(
            email="buyer@example.com",
            password="testpassword123",
            name="Charlie Buyer",
        )

        # Create Admin
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword123",
            name="Admin User",
        )

    def test_unauthenticated_access_redirects(self):
        """Unauthenticated user accessing protected provider URLs is redirected to login."""
        urls = [
            reverse("providers:dashboard"),
            reverse("providers:profile_edit"),
            reverse("providers:product_list"),
            reverse("providers:product_add"),
            reverse("providers:orders"),
            reverse("providers:apply"),
            reverse("providers:status"),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("accounts/login", response.url)

    def test_provider_application_flow(self):
        """A normal registered user can apply to become a Provider and status starts as PENDING."""
        self.client.login(email="provider_a@example.com", password="testpassword123")

        # Submit application
        apply_data = {
            "farm_name": "Green Acres Organic Farm",
            "provider_type": "Seed Producer",
            "description": "Growing heirloom tomato and pepper seeds.",
            "phone_number": "+91 9876543210",
            "address": "123 Farm Road",
            "city": "Kochi",
            "district": "Ernakulam",
            "state": "Kerala",
            "experience_years": "5+ Years",
            "license_number": "LIC-2026-001",
            "license_type": "FSSAI Agri",
        }
        response = self.client.post(reverse("providers:apply"), data=apply_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("providers:status"))

        # Verify profile created and status is PENDING
        profile = ProviderProfile.objects.get(user=self.user_a)
        self.assertEqual(profile.farm_name, "Green Acres Organic Farm")
        self.assertEqual(profile.verification_status, ProviderProfile.VerificationStatus.PENDING)
        self.assertTrue(profile.is_pending)
        self.assertFalse(profile.is_approved)

    def test_pending_provider_cannot_access_dashboard_or_management(self):
        """A user with a PENDING application cannot access dashboard, product list, add, or orders."""
        ProviderProfile.objects.create(
            user=self.user_a,
            farm_name="Pending Farm",
            phone_number="1234567890",
            verification_status=ProviderProfile.VerificationStatus.PENDING,
        )
        self.client.login(email="provider_a@example.com", password="testpassword123")

        # Dashboard redirects to status
        response = self.client.get(reverse("providers:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("providers:status"))

        # Product add redirects to status
        response = self.client.get(reverse("providers:product_add"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("providers:status"))

        # Status page renders pending notice
        status_res = self.client.get(reverse("providers:status"))
        self.assertEqual(status_res.status_code, 200)
        self.assertContains(status_res, "Application Pending Review")

    def test_rejected_provider_cannot_access_dashboard(self):
        """A REJECTED provider cannot access dashboard and sees rejection reason on status page."""
        ProviderProfile.objects.create(
            user=self.user_a,
            farm_name="Rejected Nursery",
            phone_number="1234567890",
            verification_status=ProviderProfile.VerificationStatus.REJECTED,
            rejection_reason="Invalid license documentation provided.",
        )
        self.client.login(email="provider_a@example.com", password="testpassword123")

        # Protected pages redirect to status
        response = self.client.get(reverse("providers:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("providers:status"))

        # Status page shows rejection
        status_res = self.client.get(reverse("providers:status"))
        self.assertEqual(status_res.status_code, 200)
        self.assertContains(status_res, "Application Not Approved")
        self.assertContains(status_res, "Invalid license documentation provided.")

    def test_approved_provider_can_access_dashboard_and_edit_profile(self):
        """An APPROVED provider can access the dashboard and update their profile details."""
        profile = ProviderProfile.objects.create(
            user=self.user_a,
            farm_name="Approved Agro Farm",
            phone_number="9876543210",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )
        self.client.login(email="provider_a@example.com", password="testpassword123")

        # Can view dashboard
        response = self.client.get(reverse("providers:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved Agro Farm")
        self.assertContains(response, "Approved Provider")

        # Can update profile
        edit_data = {
            "farm_name": "Approved Agro Farm (Updated)",
            "provider_type": "Certified Organic Nursery",
            "description": "High quality saplings and organic seeds.",
            "phone_number": "9998887776",
            "city": "Ernakulam",
            "district": "Ernakulam",
            "state": "Kerala",
            "experience_years": "8+ Years",
        }
        edit_res = self.client.post(reverse("providers:profile_edit"), data=edit_data)
        self.assertEqual(edit_res.status_code, 302)
        self.assertRedirects(edit_res, reverse("providers:dashboard"))

        profile.refresh_from_db()
        self.assertEqual(profile.farm_name, "Approved Agro Farm (Updated)")
        self.assertEqual(profile.phone_number, "9998887776")

    def test_provider_product_submission_and_validation(self):
        """An approved provider can submit products with validation for positive price and quantity."""
        profile = ProviderProfile.objects.create(
            user=self.user_a,
            farm_name="Sunshine Seeds",
            phone_number="9876543210",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )
        self.client.login(email="provider_a@example.com", password="testpassword123")

        # Invalid: 0 quantity, negative price
        invalid_data = {
            "category": "Seeds",
            "item_name": "Tomato Seeds",
            "description": "Hybrid variety",
            "quantity": 0,
            "expected_price": "-10.00",
        }
        res_invalid = self.client.post(reverse("providers:product_add"), data=invalid_data)
        self.assertEqual(res_invalid.status_code, 200)
        self.assertFalse(ProviderRequest.objects.filter(item_name="Tomato Seeds").exists())

        # Valid submission
        valid_data = {
            "category": "Seeds",
            "item_name": "Tomato Seeds (Hybrid 50g)",
            "description": "High yield tomato seeds for summer season.",
            "quantity": 50,
            "expected_price": "120.00",
        }
        res_valid = self.client.post(reverse("providers:product_add"), data=valid_data)
        self.assertEqual(res_valid.status_code, 302)

        req = ProviderRequest.objects.get(item_name="Tomato Seeds (Hybrid 50g)")
        self.assertEqual(req.provider, profile)
        self.assertEqual(req.quantity, 50)
        self.assertEqual(req.expected_price, Decimal("120.00"))
        self.assertEqual(req.status, ProviderRequest.Status.PENDING)

    def test_product_ownership_isolation(self):
        """Provider A cannot edit or delete Provider B's products."""
        # Provider A
        profile_a = ProviderProfile.objects.create(
            user=self.user_a,
            farm_name="Farm A",
            phone_number="111",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )
        # Provider B
        profile_b = ProviderProfile.objects.create(
            user=self.user_b,
            farm_name="Farm B",
            phone_number="222",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )

        # Product belonging to Provider B
        prod_b = Product.objects.create(
            name="Mango Sapling",
            category=self.category_plants,
            description="Alphonso variety",
            price=Decimal("250.00"),
            stock=15,
            provider=profile_b,
        )

        # Log in as Provider A and attempt to edit/delete Provider B's product
        self.client.login(email="provider_a@example.com", password="testpassword123")

        # Edit attempt -> 404 (not found in Provider A's queryset)
        edit_res = self.client.get(reverse("providers:product_edit", kwargs={"pk": prod_b.pk}))
        self.assertEqual(edit_res.status_code, 404)

        # Delete attempt -> 404
        del_res = self.client.post(reverse("providers:product_delete", kwargs={"pk": prod_b.pk}))
        self.assertEqual(del_res.status_code, 404)

        # Product B is untouched
        prod_b.refresh_from_db()
        self.assertTrue(prod_b.is_active)

    def test_provider_orders_visibility_isolation(self):
        """Provider A sees only orders for Provider A's products, not Provider B's products."""
        profile_a = ProviderProfile.objects.create(
            user=self.user_a,
            farm_name="Provider A Farm",
            phone_number="111",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )
        profile_b = ProviderProfile.objects.create(
            user=self.user_b,
            farm_name="Provider B Nursery",
            phone_number="222",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )

        # Products
        prod_a = Product.objects.create(
            name="Tomato Seeds",
            category=self.category_seeds,
            description="Quality seeds",
            price=Decimal("100.00"),
            stock=50,
            provider=profile_a,
        )
        prod_b = Product.objects.create(
            name="Rose Plant",
            category=self.category_plants,
            description="Flowering rose",
            price=Decimal("150.00"),
            stock=20,
            provider=profile_b,
        )

        # Order 1: Buyer orders Product A (from Provider A)
        order_1 = Order.objects.create(
            user=self.buyer_user,
            order_number="AGV-TEST-001",
            total_amount=Decimal("200.00"),
            full_name="Charlie Buyer",
            phone="9876543210",
            email="buyer@example.com",
            delivery_address="456 Buyer St",
            city="Kochi",
            district="Ernakulam",
            pin_code="682001",
        )
        OrderItem.objects.create(
            order=order_1,
            product=prod_a,
            quantity=2,
            price=Decimal("100.00"),
            subtotal=Decimal("200.00"),
        )

        # Order 2: Buyer orders Product B (from Provider B)
        order_2 = Order.objects.create(
            user=self.buyer_user,
            order_number="AGV-TEST-002",
            total_amount=Decimal("150.00"),
            full_name="Charlie Buyer",
            phone="9876543210",
            email="buyer@example.com",
            delivery_address="456 Buyer St",
            city="Kochi",
            district="Ernakulam",
            pin_code="682001",
        )
        OrderItem.objects.create(
            order=order_2,
            product=prod_b,
            quantity=1,
            price=Decimal("150.00"),
            subtotal=Decimal("150.00"),
        )

        # Log in as Provider A
        self.client.login(email="provider_a@example.com", password="testpassword123")
        res_a = self.client.get(reverse("providers:orders"))
        self.assertEqual(res_a.status_code, 200)
        self.assertContains(res_a, "AGV-TEST-001")
        self.assertContains(res_a, "Tomato Seeds")
        self.assertNotContains(res_a, "AGV-TEST-002")
        self.assertNotContains(res_a, "Rose Plant")

        # Log in as Provider B
        self.client.login(email="provider_b@example.com", password="testpassword123")
        res_b = self.client.get(reverse("providers:orders"))
        self.assertEqual(res_b.status_code, 200)
        self.assertContains(res_b, "AGV-TEST-002")
        self.assertContains(res_b, "Rose Plant")
        self.assertNotContains(res_b, "AGV-TEST-001")
        self.assertNotContains(res_b, "Tomato Seeds")
