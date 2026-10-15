from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from agrivision.marketplace.models import Category, Product, Cart, CartItem, Order, OrderItem

User = get_user_model()


class StockValidationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="buyer@example.com",
            email="buyer@example.com",
            password="testpassword123",
            name="Buyer Farmer",
        )
        self.client.login(username="buyer@example.com", password="testpassword123")

        self.category = Category.objects.create(name="Seeds", description="Quality seeds")
        self.product = Product.objects.create(
            name="Hybrid Tomato Seeds",
            category=self.category,
            price=Decimal("150.00"),
            cost_price=Decimal("100.00"),
            stock=5,
            is_active=True,
        )

    def test_add_to_cart_within_stock(self):
        """User adding quantity <= available stock should succeed."""
        response = self.client.post(
            reverse("marketplace:add_to_cart", kwargs={"pk": self.product.pk}),
            {"quantity": "3"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.get(product=self.product)
        self.assertEqual(cart_item.quantity, 3)

    def test_add_to_cart_exceeding_stock_rejected(self):
        """User requesting quantity > available stock should be rejected with exact error message."""
        response = self.client.post(
            reverse("marketplace:add_to_cart", kwargs={"pk": self.product.pk}),
            {"quantity": "7"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        cart = Cart.objects.filter(user=self.user).first()
        if cart:
            self.assertFalse(cart.items.filter(product=self.product).exists())
        messages = list(response.context["messages"])
        self.assertTrue(any("Only 5 units are available" in str(m) for m in messages))

    def test_add_to_cart_invalid_quantity_rejected(self):
        """Zero, negative numbers, decimals, or text should be rejected."""
        for invalid_val in ["0", "-2", "3.5", "abc", ""]:
            response = self.client.post(
                reverse("marketplace:add_to_cart", kwargs={"pk": self.product.pk}),
                {"quantity": invalid_val},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)
            messages = list(response.context["messages"])
            self.assertTrue(any("positive whole number" in str(m) for m in messages))

    def test_add_to_cart_incremental_exceeding_stock(self):
        """Adding 3 units first, then attempting to add 3 more when stock is 5 should be blocked."""
        # First add 3
        self.client.post(
            reverse("marketplace:add_to_cart", kwargs={"pk": self.product.pk}),
            {"quantity": "3"},
        )
        # Try to add 3 more (total 6 > 5)
        response = self.client.post(
            reverse("marketplace:add_to_cart", kwargs={"pk": self.product.pk}),
            {"quantity": "3"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        cart = Cart.objects.get(user=self.user)
        cart_item = cart.items.get(product=self.product)
        # Quantity should remain 3
        self.assertEqual(cart_item.quantity, 3)
        messages = list(response.context["messages"])
        self.assertTrue(any("at most 2 more" in str(m) for m in messages))

    def test_update_cart_exceeding_stock(self):
        """Updating cart quantity beyond available stock should be rejected."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        cart_item = CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(
            reverse("marketplace:update_cart", kwargs={"pk": cart_item.pk}),
            {"quantity": "8"},
            follow=True,
        )
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        messages = list(response.context["messages"])
        self.assertTrue(any("Only 5 units are available" in str(m) for m in messages))

    def test_checkout_blocks_insufficient_stock(self):
        """If stock drops after adding to cart, checkout view should redirect with alert."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=4)

        # Stock is reduced by another transaction to 2
        self.product.stock = 2
        self.product.save()

        response = self.client.get(reverse("marketplace:checkout"), follow=True)
        self.assertRedirects(response, reverse("marketplace:cart"))
        messages = list(response.context["messages"])
        self.assertTrue(any("Only 2 units are available" in str(m) for m in messages))

    def test_place_order_deducts_stock_atomically(self):
        """Placing order should successfully create order and decrement stock atomically."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)

        # Set session checkout data
        session = self.client.session
        session["checkout_data"] = {
            "full_name": "Buyer Farmer",
            "phone": "9876543210",
            "email": "buyer@example.com",
            "delivery_address": "123 Farm House",
            "city": "Kochi",
            "district": "Ernakulam",
            "pin_code": "682001",
        }
        session.save()

        response = self.client.post(
            reverse("marketplace:place_order"),
            {"payment_method": "cod"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        # Verify stock decremented
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)  # 5 - 3 = 2

        # Verify order exists
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 3)

        # Verify cart is empty
        self.assertEqual(cart.items.count(), 0)

    def test_place_order_insufficient_stock_rollback(self):
        """If stock is 1 and user tries to place order for 3, transaction should rollback."""
        cart, _ = Cart.objects.get_or_create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=3)

        # Simulate another user bought items so only 1 is left
        self.product.stock = 1
        self.product.save()

        session = self.client.session
        session["checkout_data"] = {
            "full_name": "Buyer Farmer",
            "phone": "9876543210",
            "email": "buyer@example.com",
            "delivery_address": "123 Farm House",
            "city": "Kochi",
            "district": "Ernakulam",
            "pin_code": "682001",
        }
        session.save()

        response = self.client.post(
            reverse("marketplace:place_order"),
            {"payment_method": "cod"},
            follow=True,
        )
        self.assertRedirects(response, reverse("marketplace:cart"))

        # Stock should remain 1 (untouched)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

        # No order created
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)
