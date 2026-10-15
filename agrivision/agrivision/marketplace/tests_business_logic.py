import uuid
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from agrivision.marketplace.models import (
    Category,
    Product,
    Cart,
    CartItem,
    Order,
    OrderItem,
    StockHistory,
    RefundRequest,
)
from agrivision.providers.models import ProviderProfile

User = get_user_model()


class BusinessLogicTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin_user = User.objects.create_superuser(
            email="admin_test@agrivision.com",
            password="adminpassword123",
            name="Platform Admin",
        )

        # Provider user & profile
        self.provider_user = User.objects.create_user(
            email="provider1@farm.com",
            password="providerpassword123",
            name="Green Valley Nursery",
        )
        self.provider_profile = ProviderProfile.objects.create(
            user=self.provider_user,
            farm_name="Green Valley Organic Farms",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
            phone_number="9876543210",
            address="Village 10, Green Road",
            city="Pune",
            district="Pune",
            state="Maharashtra",
            pincode="411001",
        )

        # Second provider for isolation tests
        self.provider_user2 = User.objects.create_user(
            email="provider2@farm.com",
            password="providerpassword123",
            name="Sunshine Agro",
        )
        self.provider_profile2 = ProviderProfile.objects.create(
            user=self.provider_user2,
            farm_name="Sunshine Agro Nursery",
            verification_status=ProviderProfile.VerificationStatus.APPROVED,
            phone_number="9876543211",
            address="Village 20, Sunshine Road",
            city="Nashik",
            district="Nashik",
            state="Maharashtra",
            pincode="422001",
        )

        # Customer user
        self.customer = User.objects.create_user(
            email="customer@agrivision.com",
            password="customerpassword123",
            name="Ramesh Farmer",
        )

        # Categories Hierarchy
        self.seeds_parent = Category.objects.create(
            name="Seeds",
            category_type=Category.SEEDS,
            icon="fa-seedling",
        )
        self.veg_seeds = Category.objects.create(
            name="Vegetable Seeds",
            parent=self.seeds_parent,
            category_type=Category.SEEDS,
            icon="fa-carrot",
        )
        self.plants_parent = Category.objects.create(
            name="Plants & Saplings",
            category_type=Category.PLANTS,
            icon="fa-leaf",
        )

        # Products
        self.product1 = Product.objects.create(
            name="Hybrid Tomato F1 Seeds (100g)",
            category=self.veg_seeds,
            provider=self.provider_profile,
            provider_name=self.provider_profile.farm_name,
            provider_user=self.provider_user,
            price=Decimal("250.00"),
            cost_price=Decimal("180.00"),
            stock=100,
            is_active=True,
        )
        # Log initial stock
        StockHistory.objects.create(
            product=self.product1,
            provider=self.provider_profile,
            previous_stock=0,
            quantity_changed=100,
            new_stock=100,
            change_type=StockHistory.ChangeType.INITIAL,
            reason="Initial stock listing",
            created_by=self.provider_user,
        )

        self.product2 = Product.objects.create(
            name="Sunshine Alphonso Mango Grafted Plant",
            category=self.plants_parent,
            provider=self.provider_profile2,
            provider_name=self.provider_profile2.farm_name,
            provider_user=self.provider_user2,
            price=Decimal("450.00"),
            cost_price=Decimal("300.00"),
            stock=50,
            is_active=True,
        )

    def _setup_cart_and_session(self, product, quantity):
        cart, _ = Cart.objects.get_or_create(user=self.customer)
        cart.items.all().delete()
        CartItem.objects.create(cart=cart, product=product, quantity=quantity)

        session = self.client.session
        session["checkout_data"] = {
            "full_name": "Ramesh Farmer",
            "phone": "9876543210",
            "email": "customer@agrivision.com",
            "delivery_address": "12 Farm Lane, Pune",
            "city": "Pune",
            "district": "Pune",
            "pin_code": "411001",
        }
        session.save()

    def test_01_category_hierarchy(self):
        """Test parent-child subcategory relationship."""
        self.assertEqual(self.veg_seeds.parent, self.seeds_parent)
        self.assertEqual(self.seeds_parent.subcategories.count(), 1)
        self.assertEqual(self.seeds_parent.subcategories.first().name, "Vegetable Seeds")

    def test_02_stock_adjustments_and_history(self):
        """Test provider manual stock adjustment and audit trail."""
        self.client.force_login(self.provider_user)
        # Add 30 units
        url = reverse("providers:stock_adjust", kwargs={"pk": self.product1.pk})
        resp = self.client.post(url, {
            "adjustment_type": "add",
            "quantity": 30,
            "reason": "Fresh harvest restock",
        })
        self.assertEqual(resp.status_code, 302)

        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 130)

        latest_hist = StockHistory.objects.filter(product=self.product1).order_by("-created_at").first()
        self.assertEqual(latest_hist.previous_stock, 100)
        self.assertEqual(latest_hist.quantity_changed, 30)
        self.assertEqual(latest_hist.new_stock, 130)
        self.assertEqual(latest_hist.change_type, StockHistory.ChangeType.ADDED)
        self.assertEqual(latest_hist.reason, "Fresh harvest restock")

    def test_03_payment_tier_full_online(self):
        """Test 100% full online payment option with provider confirmation."""
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 2)

        resp = self.client.post(reverse("marketplace:place_order"), {
            "payment_method": Order.ONLINE,
        })
        self.assertEqual(resp.status_code, 302)

        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment_method, Order.ONLINE)
        self.assertEqual(order.order_status, Order.ORDER_PENDING)
        self.assertEqual(order.payment_status, Order.PENDING)
        self.assertEqual(order.total_amount, Decimal("500.00"))
        self.assertEqual(order.online_paid_amount, Decimal("500.00"))
        self.assertEqual(order.cod_amount_due, Decimal("0.00"))

        # Provider confirms the order -> payment status activates to PAID
        self.client.force_login(self.provider_user)
        self.client.post(reverse("providers:order_status_update", kwargs={"order_id": order.id}), {
            "order_status": Order.CONFIRMED,
        })
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.CONFIRMED)
        self.assertEqual(order.payment_status, Order.PAID)

        # Check stock deduction
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 98)

        # Check StockHistory
        hist = StockHistory.objects.filter(product=self.product1, change_type=StockHistory.ChangeType.ORDER).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.quantity_changed, -2)

    def test_04_payment_tier_split_50_50(self):
        """Test 50% Online + 50% COD split payment option with provider confirmation."""
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 1)

        resp = self.client.post(reverse("marketplace:place_order"), {
            "payment_method": Order.HALF_COD,
        })
        self.assertEqual(resp.status_code, 302)

        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment_method, Order.HALF_COD)
        self.assertEqual(order.order_status, Order.ORDER_PENDING)
        self.assertEqual(order.payment_status, Order.PENDING)
        self.assertEqual(order.total_amount, Decimal("250.00"))
        self.assertEqual(order.online_paid_amount, Decimal("125.00"))
        self.assertEqual(order.cod_amount_due, Decimal("125.00"))

        # Provider confirms the order -> 50% advance activates to PARTIALLY_PAID
        self.client.force_login(self.provider_user)
        self.client.post(reverse("providers:order_status_update", kwargs={"order_id": order.id}), {
            "order_status": Order.CONFIRMED,
        })
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.CONFIRMED)
        self.assertEqual(order.payment_status, Order.PARTIALLY_PAID)

    def test_05_payment_tier_full_cod(self):
        """Test 100% Cash on Delivery payment option."""
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 1)

        resp = self.client.post(reverse("marketplace:place_order"), {
            "payment_method": Order.COD,
        })
        self.assertEqual(resp.status_code, 302)

        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment_method, Order.COD)
        self.assertEqual(order.payment_status, Order.PENDING)
        self.assertEqual(order.online_paid_amount, Decimal("0.00"))
        self.assertEqual(order.cod_amount_due, Decimal("250.00"))

    def test_06_order_cancellation_and_automatic_restock(self):
        """Test pre-dispatch order cancellation automatically restores stock."""
        initial_stock = self.product1.stock
        order = Order.objects.create(
            user=self.customer,
            order_number=f"ORD-TEST-004",
            full_name="Ramesh Farmer",
            email="customer@agrivision.com",
            phone="9876543210",
            delivery_address="12 Farm Lane",
            city="Pune",
            district="Pune",
            pin_code="411001",
            total_amount=Decimal("1000.00"),
            payment_method=Order.ONLINE,
            payment_status=Order.PAID,
            order_status=Order.CONFIRMED,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            product_name=self.product1.name,
            provider=self.provider_profile,
            price=self.product1.price,
            quantity=4,
            subtotal=Decimal("1000.00"),
        )
        # Deduct stock for order placement
        self.product1.stock -= 4
        self.product1.save()

        # Customer cancels before dispatch
        self.client.force_login(self.customer)
        cancel_url = reverse("marketplace:cancel_order", kwargs={"order_number": order.order_number})
        resp = self.client.post(cancel_url, {"cancellation_reason": "Bought from local store by mistake"})
        self.assertEqual(resp.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.CANCELLED)

        # Stock restored
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock)

        # Stock history logged
        hist = StockHistory.objects.filter(product=self.product1, change_type=StockHistory.ChangeType.CANCELLATION).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.quantity_changed, 4)

    def test_07_refund_request_and_admin_approval_with_restock(self):
        """Test customer refund request submission and Admin approval with inventory restock."""
        order = Order.objects.create(
            user=self.customer,
            order_number=f"ORD-TEST-005",
            full_name="Ramesh Farmer",
            email="customer@agrivision.com",
            phone="9876543210",
            delivery_address="12 Farm Lane",
            city="Pune",
            district="Pune",
            pin_code="411001",
            total_amount=Decimal("500.00"),
            payment_method=Order.ONLINE,
            payment_status=Order.PAID,
            order_status=Order.DELIVERED,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product1,
            product_name=self.product1.name,
            provider=self.provider_profile,
            price=self.product1.price,
            quantity=2,
            subtotal=Decimal("500.00"),
        )
        current_stock = self.product1.stock

        # Customer requests refund
        self.client.force_login(self.customer)
        refund_submit_url = reverse("marketplace:request_refund", kwargs={"order_number": order.order_number})
        resp = self.client.post(refund_submit_url, {
            "reason": RefundRequest.RefundReason.WRONG_PRODUCT,
            "custom_reason": "Received chili seeds instead of tomato seeds. Pack is unopened and sealed.",
        })
        self.assertEqual(resp.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.refund_status, Order.REFUND_REQUESTED)
        refund_req = RefundRequest.objects.get(order=order)
        self.assertEqual(refund_req.status, RefundRequest.RefundStatus.PENDING)
        self.assertEqual(refund_req.reason, RefundRequest.RefundReason.WRONG_PRODUCT)

        # Admin approves with restocking (undamaged, sealed)
        self.client.force_login(self.admin_user)
        process_url = reverse("admin_portal:refund_process", kwargs={"pk": refund_req.pk})
        resp = self.client.post(process_url, {
            "decision": RefundRequest.RefundStatus.APPROVED,
            "refund_amount": "500.00",
            "is_restocked": True,
            "admin_notes": "Pack verified unopened; restocked to nursery inventory.",
        })
        self.assertEqual(resp.status_code, 302)

        refund_req.refresh_from_db()
        self.assertEqual(refund_req.status, RefundRequest.RefundStatus.APPROVED)
        self.assertTrue(refund_req.is_restocked)

        # Inventory increased by 2
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, current_stock + 2)

        # StockHistory created
        hist = StockHistory.objects.filter(product=self.product1, change_type=StockHistory.ChangeType.REFUND_RESTOCK).first()
        self.assertIsNotNone(hist)
        self.assertEqual(hist.quantity_changed, 2)

    def test_08_provider_isolation(self):
        """Test provider can only see and manage their own products and orders."""
        self.client.force_login(self.provider_user)

        # Provider 1 visits stock management
        resp = self.client.get(reverse("providers:stock_management"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.product1.name)
        self.assertNotContains(resp, self.product2.name)

        # Provider 1 cannot adjust Provider 2's product
        resp = self.client.post(reverse("providers:stock_adjust", kwargs={"pk": self.product2.pk}), {
            "adjustment_type": "add",
            "quantity": 50,
            "reason": "Hacking attempt",
        })
        self.assertEqual(resp.status_code, 404)

    def test_09_order_tracking_and_delivery_balance_settlement(self):
        """Test Live Order Tracking and 50% COD balance auto-settlement on delivery completion."""
        # 1. Customer places 50% Online + 50% COD order (starts as ORDER_PENDING awaiting provider confirmation)
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 2)
        resp = self.client.post(reverse("marketplace:place_order"), {
            "payment_method": Order.HALF_COD,
        })
        self.assertEqual(resp.status_code, 302)

        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertEqual(order.payment_method, Order.HALF_COD)
        self.assertEqual(order.order_status, Order.ORDER_PENDING)
        self.assertEqual(order.payment_status, Order.PENDING)
        self.assertEqual(order.online_paid_amount, Decimal("250.00"))
        self.assertEqual(order.cod_amount_due, Decimal("250.00"))

        # 2. Provider confirms the order
        self.client.force_login(self.provider_user)
        self.client.post(reverse("providers:order_status_update", kwargs={"order_id": order.id}), {
            "order_status": Order.CONFIRMED,
        })
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.CONFIRMED)
        self.assertEqual(order.payment_status, Order.PARTIALLY_PAID)

        # 3. Customer views Live Tracking page
        self.client.force_login(self.customer)
        track_url = reverse("marketplace:track_order", kwargs={"order_number": order.order_number})
        track_resp = self.client.get(track_url)
        self.assertEqual(track_resp.status_code, 200)
        self.assertContains(track_resp, "Live Product &amp; Shipment Tracking")
        self.assertContains(track_resp, "50% Cash on Delivery Balance")
        self.assertContains(track_resp, "₹250.00")

        # 4. Provider marks order as DELIVERED upon doorstep handover
        self.client.force_login(self.provider_user)
        update_url = reverse("providers:order_status_update", kwargs={"order_id": order.id})
        resp = self.client.post(update_url, {
            "order_status": Order.DELIVERED,
        })
        self.assertEqual(resp.status_code, 302)

        # 5. Verify order is DELIVERED and 50% balance is automatically marked PAID (settled)
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.DELIVERED)
        self.assertEqual(order.payment_status, Order.PAID)

        # 6. Customer checks Live Tracking page after delivery completion
        self.client.force_login(self.customer)
        track_resp2 = self.client.get(track_url)
        self.assertEqual(track_resp2.status_code, 200)
        self.assertContains(track_resp2, "Delivered &amp; Balance Settled")
        self.assertContains(track_resp2, "Doorstep Settlement Completed")

    def test_10_provider_order_management_lifecycle(self):
        """Test provider receiving incoming orders, filtering, viewing detail/slip, and progressing fulfillment."""
        # 1. Customer places Full COD order for provider1's product
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 3)
        self.client.post(reverse("marketplace:place_order"), {
            "payment_method": Order.COD,
        })
        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.order_status, Order.ORDER_PENDING)

        # 2. Provider logs in and checks incoming orders
        self.client.force_login(self.provider_user)
        orders_url = reverse("providers:orders")
        resp = self.client.get(orders_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, order.order_number)
        self.assertContains(resp, self.product1.name)
        self.assertContains(resp, "Confirm Order")

        # 3. Provider views order detail page
        detail_url = reverse("providers:order_detail", kwargs={"order_id": order.id})
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, order.order_number)
        self.assertContains(detail_resp, "Print Packing Slip")
        self.assertContains(detail_resp, self.customer.name or self.customer.email)

        # 4. Provider confirms the order (Pending -> Confirmed)
        status_url = reverse("providers:order_status_update", kwargs={"order_id": order.id})
        self.client.post(status_url, {"order_status": Order.CONFIRMED})
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.CONFIRMED)

        # 5. Provider marks as Packing (Confirmed -> Processing)
        self.client.post(status_url, {"order_status": Order.PROCESSING})
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.PROCESSING)

        # 6. Provider dispatches (Processing -> Shipped)
        self.client.post(status_url, {"order_status": Order.SHIPPED})
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.SHIPPED)

        # 7. Provider marks delivered -> balance settles to PAID
        self.client.post(status_url, {"order_status": Order.DELIVERED})
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.DELIVERED)
        self.assertEqual(order.payment_status, Order.PAID)

    def test_checkout_validation_failures_and_success(self):
        """Test strict validation of phone, pin code, and successful checkout session setup."""
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 2)
        checkout_url = reverse("marketplace:checkout")

        # 1. Invalid phone number (too short or letters)
        resp = self.client.post(checkout_url, {
            "full_name": "Ramesh Farmer",
            "phone": "12345",
            "email": "customer@agrivision.com",
            "delivery_address": "Farm House 12, Green Way",
            "city": "Pune",
            "district": "Maharashtra",
            "pin_code": "411001",
        })
        self.assertEqual(resp.status_code, 200)  # Rendered with error
        self.assertContains(resp, "valid 10-digit mobile number")

        # 2. Invalid PIN code (not 6 digits)
        resp = self.client.post(checkout_url, {
            "full_name": "Ramesh Farmer",
            "phone": "9876543210",
            "email": "customer@agrivision.com",
            "delivery_address": "Farm House 12, Green Way",
            "city": "Pune",
            "district": "Maharashtra",
            "pin_code": "4110",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PIN code must be exactly 6 digits")

        # 3. Valid submission
        resp = self.client.post(checkout_url, {
            "full_name": "Ramesh Farmer",
            "phone": "9876543210",
            "email": "customer@agrivision.com",
            "delivery_address": "Farm House 12, Green Way",
            "city": "Pune",
            "district": "Maharashtra",
            "pin_code": "411001",
        })
        self.assertRedirects(resp, reverse("marketplace:payment"))
        self.assertEqual(self.client.session.get("checkout_data")["phone"], "9876543210")

    def test_post_order_success_navigation_links(self):
        """Test that order_success page provides Back to Dashboard, Profile & Orders, and Live Tracking."""
        self.client.force_login(self.customer)
        self._setup_cart_and_session(self.product1, 1)

        place_resp = self.client.post(reverse("marketplace:place_order"), {
            "payment_method": Order.COD,
        })
        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertIsNotNone(order)
        self.assertRedirects(place_resp, reverse("marketplace:order_success", kwargs={"order_number": order.order_number}))

        success_resp = self.client.get(reverse("marketplace:order_success", kwargs={"order_number": order.order_number}))
        self.assertEqual(success_resp.status_code, 200)
        self.assertContains(success_resp, "Order Placed Successfully!")
        self.assertContains(success_resp, "Back to Dashboard")
        self.assertContains(success_resp, "My Profile &amp; Orders")
        self.assertContains(success_resp, "Track Order Live")
        self.assertContains(success_resp, reverse("marketplace:dashboard"))
        self.assertContains(success_resp, reverse("marketplace:my_orders"))

    def test_unauthenticated_access_protection(self):
        """Test that protected pages require login and redirect anonymous users."""
        self.client.logout()

        protected_urls = [
            reverse("marketplace:dashboard"),
            reverse("marketplace:cart"),
            reverse("marketplace:checkout"),
            reverse("marketplace:my_orders"),
            reverse("providers:dashboard"),
            reverse("admin_portal:dashboard"),
        ]

        for url in protected_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertTrue(resp.url.startswith("/users/login") or resp.url.startswith("/accounts/login") or "login" in resp.url)

    def test_category_classification_seeds_and_plants(self):
        """Test that products are correctly classified and filtered into Seeds vs Plants."""
        self.client.force_login(self.customer)

        # Create explicit plant product
        plant_cat = Category.objects.create(name="Medicinal Plants", category_type=Category.PLANTS, parent=self.plants_parent)
        plant_prod = Product.objects.create(
            name="Aloe Vera Nursery Sapling",
            category=plant_cat,
            price=Decimal("45.00"),
            stock=20,
            is_active=True,
        )

        # 1. Seeds Filter: must include Tomato seeds, but exclude Aloe Vera plant
        seeds_resp = self.client.get(reverse("marketplace:product_list") + "?category=Seeds")
        self.assertEqual(seeds_resp.status_code, 200)
        seeds_products = seeds_resp.context["products"]
        self.assertIn(self.product1, seeds_products)
        self.assertNotIn(plant_prod, seeds_products)

        # 2. Plants Filter: must include Aloe Vera plant, but exclude Tomato seeds
        plants_resp = self.client.get(reverse("marketplace:product_list") + "?category=Plants")
        self.assertEqual(plants_resp.status_code, 200)
        plants_products = plants_resp.context["products"]
        self.assertIn(plant_prod, plants_products)
        self.assertNotIn(self.product1, plants_products)

        # 3. All Products: must include both
        all_resp = self.client.get(reverse("marketplace:product_list"))
        self.assertEqual(all_resp.status_code, 200)
        all_products = all_resp.context["products"]
        self.assertIn(self.product1, all_products)
        self.assertIn(plant_prod, all_products)



