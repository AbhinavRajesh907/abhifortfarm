from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from agrivision.marketplace.models import Category, Product, Order, OrderItem, Payment
from agrivision.providers.models import Provider, ProviderRequest

User = get_user_model()


class AdminPortalTests(TestCase):
    def setUp(self):
        # 1. Admin user
        self.admin = User.objects.create_superuser(
            email="admin_test@agrivision.com",
            password="testpassword123",
            name="Test Admin",
        )
        # 2. Standard user
        self.user = User.objects.create_user(
            email="farmer_test@gmail.com",
            password="testpassword123",
            name="Test Farmer",
        )
        # 3. Provider user & profile
        self.prov_user = User.objects.create_user(
            email="nursery_test@agrivision.com",
            password="testpassword123",
            name="Nursery Owner",
        )
        self.provider = Provider.objects.create(
            user=self.prov_user,
            farm_name="Highland Flora Nursery",
            contact_person="Nursery Owner",
            phone="9876543210",
            email="nursery_test@agrivision.com",
            address="Tea County",
            city="Munnar",
            district="Idukki",
            pin_code="685612",
            is_verified=True,
        )
        # 4. Category
        self.category = Category.objects.create(
            name="Plants",
            description="All live plants and saplings",
            icon="fa-leaf",
        )
        # 5. Pending Provider Request
        self.req = ProviderRequest.objects.create(
            provider=self.provider,
            product_name="Rare Cardamom Clonal Plantlets",
            category=self.category,
            description="Disease-free high yielding cardamom plantlet",
            quantity=100,
            expected_price=Decimal("80.00"),
            status=ProviderRequest.PENDING,
        )

        self.client = Client()

    def test_admin_portal_access_denied_for_anonymous_and_standard_users(self):
        """Verify unauthenticated or non-staff users cannot access admin portal."""
        res_anon = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(res_anon.status_code, 302)

        self.client.login(email="farmer_test@gmail.com", password="testpassword123")
        res_user = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(res_user.status_code, 302)

    def test_admin_dashboard_renders_for_staff(self):
        """Verify dashboard loads with KPIs and charts for admin."""
        self.client.login(email="admin_test@agrivision.com", password="testpassword123")
        res = self.client.get(reverse("admin_portal:dashboard"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "AgriVision Control Center")
        self.assertContains(res, "Gross Revenue")

    def test_provider_request_approval_flow_creates_marketplace_product(self):
        """CRITICAL: Admin reviews pending request and approves -> Product is created in marketplace."""
        self.client.login(email="admin_test@agrivision.com", password="testpassword123")
        
        # Check detail page
        detail_res = self.client.get(reverse("admin_portal:request_detail", kwargs={"pk": self.req.pk}))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Rare Cardamom Clonal Plantlets")

        # Post Approval
        post_data = {
            "selling_price": "120.00",
            "admin_notes": "Passed quality standards.",
        }
        approve_res = self.client.post(
            reverse("admin_portal:request_approve", kwargs={"pk": self.req.pk}),
            data=post_data,
            follow=True,
        )
        self.assertEqual(approve_res.status_code, 200)

        # Refresh request
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, ProviderRequest.APPROVED)
        self.assertEqual(self.req.selling_price, Decimal("120.00"))
        self.assertIsNotNone(self.req.created_product)

        # Verify Marketplace Product Catalog
        created_prod = self.req.created_product
        self.assertEqual(created_prod.name, "Rare Cardamom Clonal Plantlets")
        self.assertEqual(created_prod.stock, 100)
        self.assertEqual(created_prod.price, Decimal("120.00"))
        self.assertEqual(created_prod.cost_price, Decimal("80.00"))
        self.assertEqual(created_prod.provider_name, "Highland Flora Nursery")
        self.assertTrue(created_prod.is_active)

    def test_provider_request_rejection_flow(self):
        """Admin rejects pending request with reason."""
        self.client.login(email="admin_test@agrivision.com", password="testpassword123")
        post_data = {
            "rejection_reason": "High price compared to market benchmark.",
            "admin_notes": "Discuss discount with vendor.",
        }
        reject_res = self.client.post(
            reverse("admin_portal:request_reject", kwargs={"pk": self.req.pk}),
            data=post_data,
            follow=True,
        )
        self.assertEqual(reject_res.status_code, 200)

        self.req.refresh_from_db()
        self.assertEqual(self.req.status, ProviderRequest.REJECTED)
        self.assertEqual(self.req.rejection_reason, "High price compared to market benchmark.")
        self.assertIsNone(self.req.created_product)

    def test_inventory_quick_stock_adjustment(self):
        """Quickly adjust stock on product (+50 units)."""
        self.client.login(email="admin_test@agrivision.com", password="testpassword123")
        prod = Product.objects.create(
            name="Bio-Compost Bag",
            category=self.category,
            price=Decimal("200.00"),
            stock=10,
        )
        adj_res = self.client.post(
            reverse("admin_portal:inventory_adjust", kwargs={"pk": prod.pk}),
            data={"adjustment_type": "add", "quantity": "50"},
            follow=True,
        )
        self.assertEqual(adj_res.status_code, 200)
        prod.refresh_from_db()
        self.assertEqual(prod.stock, 60)

    def test_csv_exports(self):
        """Verify CSV report endpoints return attachment downloads."""
        self.client.login(email="admin_test@agrivision.com", password="testpassword123")
        res_sales = self.client.get(reverse("admin_portal:export_sales_csv"))
        self.assertEqual(res_sales.status_code, 200)
        self.assertEqual(res_sales["Content-Type"], "text/csv")

        res_orders = self.client.get(reverse("admin_portal:export_orders_csv"))
        self.assertEqual(res_orders.status_code, 200)
        self.assertEqual(res_orders["Content-Type"], "text/csv")

        res_inv = self.client.get(reverse("admin_portal:export_products_csv"))
        self.assertEqual(res_inv.status_code, 200)
        self.assertEqual(res_inv["Content-Type"], "text/csv")
