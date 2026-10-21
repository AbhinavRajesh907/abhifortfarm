from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from agrivision.marketplace.models import Category, Order, OrderItem, Product, StockHistory
from agrivision.providers.models import ProviderProfile, ProviderRequest

User = get_user_model()


class TargetedUpdatesTests(TestCase):
    """
    Verification tests covering all 5 requested features:
    1. Admin product edit removal and direct URL protection
    2. License issue date future rejection & validation
    3. Proper session, logout, and no-cache security across roles
    4. Mandatory cancellation reason, stock restoration, and order security
    5. Plant and Seed product type creation and category mapping
    """

    def setUp(self):
        self.client = Client()

        # Seed categories
        self.cat_plants, _ = Category.objects.get_or_create(
            name="Plants", defaults={"category_type": Category.PLANTS, "description": "Live plants"}
        )
        self.cat_seeds, _ = Category.objects.get_or_create(
            name="Seeds", defaults={"category_type": Category.SEEDS, "description": "Certified seeds"}
        )

        # Admin User
        self.admin = User.objects.create_superuser(
            username="admin_test",
            email="admin_test@agrifarm.com",
            password="Password123!",
            name="Admin User",
            role=User.Role.ADMIN,
        )

        # Provider User & Profile
        self.prov_user = User.objects.create_user(
            username="provider_test",
            email="provider_test@agrifarm.com",
            password="Password123!",
            name="Test Nursery Provider",
            role=User.Role.PROVIDER,
        )
        self.provider = ProviderProfile.objects.create(
            user=self.prov_user,
            farm_name="Kerala Green Nursery",
            phone_number="9847012345",
            license_number="LIC-12345",
            issue_date=timezone.now().date() - timedelta(days=365),
            expiry_date=timezone.now().date() + timedelta(days=365),
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
        )

        # Buyer User 1
        self.buyer1 = User.objects.create_user(
            username="buyer1_test",
            email="buyer1_test@agrifarm.com",
            password="Password123!",
            name="Buyer One",
            role=User.Role.USER,
        )

        # Buyer User 2 (for isolation check)
        self.buyer2 = User.objects.create_user(
            username="buyer2_test",
            email="buyer2_test@agrifarm.com",
            password="Password123!",
            name="Buyer Two",
            role=User.Role.USER,
        )

        # Sample Product
        self.product = Product.objects.create(
            name="Cardamom Sapling",
            category=self.cat_plants,
            provider=self.provider,
            provider_user=self.prov_user,
            description="Healthy nursery plant",
            price=Decimal("150.00"),
            cost_price=Decimal("100.00"),
            stock=50,
            is_active=True,
        )

    # =========================================================================
    # 1. ADMIN PRODUCT EDIT REMOVAL & PROTECTION
    # =========================================================================

    def test_admin_cannot_edit_product_via_direct_url(self):
        """Admin direct access to /admin-portal/products/<pk>/update/ is blocked and redirected."""
        self.client.login(username="admin_test", password="Password123!")

        url = reverse("admin_portal:product_update", kwargs={"pk": self.product.pk})
        response = self.client.get(url, follow=True)

        # Must redirect back to admin product list with an error message
        self.assertRedirects(response, reverse("admin_portal:product_list"))
        messages = list(response.context["messages"])
        self.assertTrue(any("restricted to the respective provider" in str(m) for m in messages))

        # Direct POST attempt must also be blocked
        post_response = self.client.post(url, {"name": "Hacked Product Name"}, follow=True)
        self.assertRedirects(post_response, reverse("admin_portal:product_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Cardamom Sapling")

    def test_provider_can_still_edit_own_product(self):
        """Provider editing is preserved at /providers/products/<pk>/edit/."""
        self.client.login(username="provider_test", password="Password123!")

        url = reverse("providers:product_edit", kwargs={"pk": self.product.pk})
        edit_data = {
            "name": "Cardamom Sapling (Updated)",
            "description": "Updated care details with sunlight and watering guidance.",
            "price": "175.00",
            "stock": 45,
            "is_active": True,
        }
        response = self.client.post(url, edit_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Cardamom Sapling (Updated)")
        self.assertEqual(self.product.price, Decimal("175.00"))
        self.assertEqual(self.product.stock, 45)

    # =========================================================================
    # 2. PROVIDER LICENSE ISSUE DATE VALIDATION
    # =========================================================================

    def test_provider_registration_rejects_future_issue_date(self):
        """Provider registration fails if issue_date is in the future."""
        tomorrow = (timezone.now().date() + timedelta(days=1)).isoformat()
        next_year = (timezone.now().date() + timedelta(days=365)).isoformat()

        dummy_doc = SimpleUploadedFile("license.pdf", b"%PDF-1.4 dummy", content_type="application/pdf")
        form_data = {
            "username": "future_provider",
            "name": "Future Provider",
            "email": "future@farm.com",
            "phone": "9847111222",
            "address": "Green Lane",
            "city": "Kochi",
            "state": "Kerala",
            "pincode": "682001",
            "farm_name": "Future Farm",
            "farm_address": "Farm Lane",
            "provider_type": "Plant Nursery",
            "experience_years": "3 Years",
            "license_number": "LIC-999",
            "license_type": "Trade License",
            "issuing_authority": "Dept of Agri",
            "issue_date": tomorrow,  # Future date!
            "expiry_date": next_year,
            "license_document": dummy_doc,
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        response = self.client.post(reverse("users:register_provider"), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "issue_date",
            "License issue date cannot be in the future. Please select today's date or an earlier date.",
        )
        self.assertFalse(User.objects.filter(username="future_provider").exists())

    def test_provider_registration_accepts_today_and_past_issue_date(self):
        """Provider registration succeeds when issue_date is today or a past date."""
        today = timezone.now().date().isoformat()
        next_year = (timezone.now().date() + timedelta(days=365)).isoformat()

        dummy_doc = SimpleUploadedFile("license.pdf", b"%PDF-1.4 dummy", content_type="application/pdf")
        form_data = {
            "username": "valid_provider",
            "name": "Valid Provider",
            "email": "valid@farm.com",
            "phone": "9847222333",
            "address": "Green Lane",
            "city": "Kochi",
            "state": "Kerala",
            "pincode": "682001",
            "farm_name": "Valid Farm",
            "farm_address": "Farm Lane",
            "provider_type": "Plant Nursery",
            "experience_years": "5 Years",
            "license_number": "LIC-1000",
            "license_type": "Trade License",
            "issuing_authority": "Dept of Agri",
            "issue_date": today,  # Today is valid!
            "expiry_date": next_year,
            "license_document": dummy_doc,
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        response = self.client.post(reverse("users:register_provider"), data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="valid_provider").exists())

    # =========================================================================
    # 3. SESSION AND LOGOUT SECURITY ACROSS ALL ROLES
    # =========================================================================

    def test_cache_control_headers_on_authenticated_dashboards(self):
        """Authenticated dashboards must return no-cache headers."""
        # 1. Admin Dashboard
        self.client.login(username="admin_test", password="Password123!")
        res_admin = self.client.get(reverse("admin_portal:dashboard"))
        self.assertIn("no-cache", res_admin.headers.get("Cache-Control", ""))
        self.assertIn("no-store", res_admin.headers.get("Cache-Control", ""))
        self.client.logout()

        # 2. Provider Dashboard
        self.client.login(username="provider_test", password="Password123!")
        res_prov = self.client.get(reverse("providers:dashboard"))
        self.assertIn("no-cache", res_prov.headers.get("Cache-Control", ""))
        self.client.logout()

        # 3. User Dashboard
        self.client.login(username="buyer1_test", password="Password123!")
        res_user = self.client.get(reverse("marketplace:dashboard"))
        self.assertIn("no-cache", res_user.headers.get("Cache-Control", ""))

    def test_logout_terminates_session_and_blocks_back_navigation(self):
        """Logging out flushes session; direct navigation to protected page redirects to login."""
        self.client.login(username="buyer1_test", password="Password123!")

        # Logout
        res_logout = self.client.get(reverse("users:logout"), follow=True)
        self.assertEqual(res_logout.status_code, 200)

        # Subsequent direct visit to protected dashboard must redirect to login
        res_dashboard = self.client.get(reverse("marketplace:dashboard"))
        self.assertEqual(res_dashboard.status_code, 302)
        self.assertIn("/users/login/", res_dashboard.url)

    # =========================================================================
    # 4. ORDER CANCELLATION BY USERS
    # =========================================================================

    def _create_test_order(self, buyer, status=Order.ORDER_PENDING):
        order = Order.objects.create(
            user=buyer,
            order_number=f"ORD-TEST-{buyer.pk}-{timezone.now().timestamp()}",
            total_amount=Decimal("300.00"),
            online_paid_amount=Decimal("0.00"),
            cod_amount_due=Decimal("300.00"),
            full_name=buyer.name,
            phone="9876543210",
            email=buyer.email,
            delivery_address="Main Street",
            city="Kochi",
            district="Ernakulam",
            pin_code="682001",
            payment_method=Order.COD,
            payment_status=Order.PENDING,
            order_status=status,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            provider=self.provider,
            provider_user=self.prov_user,
            product_name=self.product.name,
            quantity=2,
            price=self.product.price,
            subtotal=Decimal("300.00"),
        )
        return order

    def test_user_can_cancel_own_order_with_mandatory_reason(self):
        """User successfully cancels eligible order with a valid reason, restoring stock."""
        order = self._create_test_order(self.buyer1, status=Order.ORDER_PENDING)
        initial_stock = self.product.stock

        self.client.login(username="buyer1_test", password="Password123!")
        cancel_url = reverse("marketplace:cancel_order", kwargs={"order_number": order.order_number})

        response = self.client.post(cancel_url, {"cancellation_reason": "Found better price elsewhere"}, follow=True)
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.CANCELLED)
        self.assertEqual(order.cancellation_reason, "Found better price elsewhere")
        self.assertIsNotNone(order.cancelled_at)

        # Stock must be restored (+2 units)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock + 2)

        # StockHistory audit log must be created
        log = StockHistory.objects.filter(related_order=order, change_type=StockHistory.ChangeType.CANCELLATION).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.quantity_changed, 2)

    def test_cancellation_fails_when_reason_is_empty_or_whitespace(self):
        """Cancellation fails and order remains pending if reason is blank."""
        order = self._create_test_order(self.buyer1, status=Order.ORDER_PENDING)
        initial_stock = self.product.stock

        self.client.login(username="buyer1_test", password="Password123!")
        cancel_url = reverse("marketplace:cancel_order", kwargs={"order_number": order.order_number})

        # Submit empty string
        res_empty = self.client.post(cancel_url, {"cancellation_reason": "   "}, follow=True)
        self.assertEqual(res_empty.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.ORDER_PENDING)  # Must remain pending!
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)  # Stock unchanged!

        messages = list(res_empty.context["messages"])
        self.assertTrue(any("Reason for cancellation is required" in str(m) for m in messages))

    def test_user_cannot_cancel_another_users_order(self):
        """Buyer 2 cannot cancel Buyer 1's order (isolation check)."""
        order = self._create_test_order(self.buyer1, status=Order.ORDER_PENDING)

        self.client.login(username="buyer2_test", password="Password123!")
        cancel_url = reverse("marketplace:cancel_order", kwargs={"order_number": order.order_number})

        response = self.client.post(cancel_url, {"cancellation_reason": "Malicious attempt"})
        self.assertEqual(response.status_code, 404)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.ORDER_PENDING)

    def test_cannot_cancel_already_cancelled_or_dispatched_order(self):
        """Repeated cancellation or cancellation of shipped order is rejected."""
        # 1. Already cancelled
        order_cancelled = self._create_test_order(self.buyer1, status=Order.CANCELLED)
        self.client.login(username="buyer1_test", password="Password123!")
        cancel_url = reverse("marketplace:cancel_order", kwargs={"order_number": order_cancelled.order_number})
        res_repeat = self.client.post(cancel_url, {"cancellation_reason": "Again"}, follow=True)
        messages = list(res_repeat.context["messages"])
        self.assertTrue(any("already been cancelled" in str(m) for m in messages))

        # 2. Shipped order
        order_shipped = self._create_test_order(self.buyer1, status=Order.SHIPPED)
        cancel_shipped_url = reverse("marketplace:cancel_order", kwargs={"order_number": order_shipped.order_number})
        res_shipped = self.client.post(cancel_shipped_url, {"cancellation_reason": "Cancel shipped"}, follow=True)
        messages_shipped = list(res_shipped.context["messages"])
        self.assertTrue(any("cannot be cancelled as it has already been processed" in str(m) for m in messages_shipped))
        order_shipped.refresh_from_db()
        self.assertEqual(order_shipped.order_status, Order.SHIPPED)

    # =========================================================================
    # 5. PLANT AND SEED PRODUCT TYPES
    # =========================================================================

    def test_provider_creates_plant_product_default(self):
        """Creating product with product_type='Plants' maps to Plants category."""
        self.client.login(username="provider_test", password="Password123!")

        plant_data = {
            "product_type": "Plants",
            "item_name": "Areca Palm Indoor Plant",
            "description": "Thrives in indirect bright sunlight. Water twice a week.",
            "quantity": 25,
            "expected_price": "350.00",
        }
        res = self.client.post(reverse("providers:product_add"), data=plant_data, follow=True)
        self.assertEqual(res.status_code, 200)

        product = Product.objects.get(name="Areca Palm Indoor Plant")
        self.assertEqual(product.category.name, "Plants")
        self.assertEqual(product.category.category_type, Category.PLANTS)
        self.assertEqual(product.stock, 25)
        self.assertEqual(product.provider, self.provider)

    def test_provider_creates_seed_product_with_details(self):
        """Creating product with product_type='Seeds' maps to Seeds category and enriches description."""
        self.client.login(username="provider_test", password="Password123!")

        seed_data = {
            "product_type": "Seeds",
            "item_name": "Organic Sweet Corn F1",
            "seed_variety": "Golden Bantam Heirloom",
            "germination_rate": "90% Germination",
            "sowing_season": "Kharif and Summer",
            "harvest_duration": "70 Days",
            "description": "High sweetness organic sweet corn seeds certified organic.",
            "available_packets": 100,
            "expected_price": "95.00",
        }
        res = self.client.post(reverse("providers:product_add"), data=seed_data, follow=True)
        self.assertEqual(res.status_code, 200)

        product = Product.objects.get(name="Organic Sweet Corn F1")
        self.assertEqual(product.category.name, "Seeds")
        self.assertEqual(product.category.category_type, Category.SEEDS)
        self.assertEqual(product.stock, 100)
        self.assertIn("Golden Bantam Heirloom", product.description)
        self.assertIn("90% Germination", product.description)
        self.assertIn("70 Days", product.description)

    def test_provider_creates_seed_product_with_valid_packet_quantity_and_contents(self):
        """Seed product creation succeeds with valid packet count and seeds-per-packet in description."""
        self.client.login(username="provider_test", password="Password123!")

        seed_data = {
            "product_type": "Seeds",
            "item_name": "Hybrid Sunflower Seeds",
            "available_packets": 50,
            "expected_price": "45.00",
            "description": "Hybrid sunflower seeds suitable for garden and agricultural cultivation. Each packet contains 25 seeds. Sow in well-drained soil with adequate sunlight.",
        }
        res = self.client.post(reverse("providers:product_add"), data=seed_data, follow=True)
        self.assertEqual(res.status_code, 200)

        product = Product.objects.get(name="Hybrid Sunflower Seeds")
        self.assertEqual(product.stock, 50)
        self.assertEqual(product.category.name, "Seeds")
        self.assertIn("Each packet contains 25 seeds", product.description)

        # Verify presentation on marketplace product details page
        detail_res = self.client.get(reverse("marketplace:product_detail", kwargs={"pk": product.pk}))
        self.assertEqual(detail_res.status_code, 200)
        content = detail_res.content.decode("utf-8")
        self.assertIn("Available Packets:", content)
        self.assertIn("50", content)
        self.assertIn("packets", content)

    def test_seed_product_rejects_missing_zero_negative_decimal_packet_quantities(self):
        """Seed product rejects missing, zero, negative, decimal, and invalid text for available_packets."""
        self.client.login(username="provider_test", password="Password123!")

        base_data = {
            "product_type": "Seeds",
            "item_name": "Test Packet Validation Seeds",
            "expected_price": "30.00",
            "description": "Each packet contains 50 seeds. Suitable for all soils.",
        }

        # 1. Missing available_packets
        res_missing = self.client.post(reverse("providers:product_add"), data=base_data)
        self.assertEqual(res_missing.status_code, 200)
        self.assertTrue(res_missing.context["form"].has_error("available_packets"))

        # 2. Zero packets
        data_zero = {**base_data, "available_packets": 0}
        res_zero = self.client.post(reverse("providers:product_add"), data=data_zero)
        self.assertEqual(res_zero.status_code, 200)
        self.assertTrue(res_zero.context["form"].has_error("available_packets"))

        # 3. Negative packets
        data_neg = {**base_data, "available_packets": -15}
        res_neg = self.client.post(reverse("providers:product_add"), data=data_neg)
        self.assertEqual(res_neg.status_code, 200)
        self.assertTrue(res_neg.context["form"].has_error("available_packets"))

        # 4. Decimal packets
        data_dec = {**base_data, "available_packets": "25.5"}
        res_dec = self.client.post(reverse("providers:product_add"), data=data_dec)
        self.assertEqual(res_dec.status_code, 200)
        self.assertTrue(res_dec.context["form"].has_error("available_packets"))

        # 5. Invalid text
        data_text = {**base_data, "available_packets": "fifty_packets"}
        res_text = self.client.post(reverse("providers:product_add"), data=data_text)
        self.assertEqual(res_text.status_code, 200)
        self.assertTrue(res_text.context["form"].has_error("available_packets"))

    def test_plant_product_does_not_require_available_packets(self):
        """Plant products use standard quantity and do not require or display available_packets."""
        self.client.login(username="provider_test", password="Password123!")

        plant_data = {
            "product_type": "Plants",
            "item_name": "Golden Pothos Hanging Vine",
            "quantity": 18,
            "expected_price": "180.00",
            "description": "Lush indoor foliage plant in hanging basket. Low light tolerant.",
        }
        res = self.client.post(reverse("providers:product_add"), data=plant_data, follow=True)
        self.assertEqual(res.status_code, 200)

        product = Product.objects.get(name="Golden Pothos Hanging Vine")
        self.assertEqual(product.stock, 18)
        self.assertEqual(product.category.name, "Plants")

        detail_res = self.client.get(reverse("marketplace:product_detail", kwargs={"pk": product.pk}))
        self.assertEqual(detail_res.status_code, 200)
        content = detail_res.content.decode("utf-8")
        self.assertIn("Available Stock:", content)
        self.assertIn("18 units", content)

