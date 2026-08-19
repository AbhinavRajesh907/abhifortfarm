import random
import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from agrivision.marketplace.models import Category, Product, Order, OrderItem, Payment
from agrivision.providers.models import Provider, ProviderRequest, ProviderProduct

from allauth.account.models import EmailAddress

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds comprehensive sample data for AgriVision Admin Management testing and demonstration."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("[*] Seeding AgriVision database with Admin Management demo data..."))

        # 1. Admin Superuser
        admin_email = "admin@agrivision.com"
        admin_user, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "name": "AgriVision Admin",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
        )
        admin_user.set_password("admin123")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        EmailAddress.objects.get_or_create(user=admin_user, email=admin_email, defaults={"verified": True, "primary": True})
        self.stdout.write(self.style.SUCCESS(f"[OK] Admin account ready: {admin_email} (Password: admin123)"))

        # 2. Farmers / Customers
        customers_data = [
            {"name": "Ramesh Nair", "email": "ramesh.nair@gmail.com"},
            {"name": "Priya Varma", "email": "priya.varma@gmail.com"},
            {"name": "Anand Kumar", "email": "anand.kumar@gmail.com"},
            {"name": "Deepa Menon", "email": "deepa.menon@gmail.com"},
            {"name": "Mathew Joseph", "email": "mathew.joseph@gmail.com"},
        ]
        customer_users = []
        for c in customers_data:
            u, _ = User.objects.get_or_create(
                email=c["email"],
                defaults={"name": c["name"], "is_active": True}
            )
            u.set_password("pass123")
            u.save()
            EmailAddress.objects.get_or_create(user=u, email=c["email"], defaults={"verified": True, "primary": True})
            customer_users.append(u)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(customer_users)} regular customer/farmer accounts."))

        # 3. Providers
        providers_data = [
            {
                "email": "greenroots@agrivision.com",
                "name": "Suresh Babu",
                "farm_name": "GreenRoots Agro Nursery",
                "phone": "+91 98470 11223",
                "city": "Kalpetta",
                "district": "Wayanad",
                "address": "Green Valley, Meppadi Road",
                "pin_code": "673121",
                "is_verified": True,
            },
            {
                "email": "sahyadri.seeds@agrivision.com",
                "name": "Kavitha Pillai",
                "farm_name": "Sahyadri Organic Seed Farms",
                "phone": "+91 94471 44556",
                "city": "Thodupuzha",
                "district": "Idukki",
                "address": "Plot 14, High Range Spice & Seed Hub",
                "pin_code": "685584",
                "is_verified": True,
            },
            {
                "email": "malabar.botanics@agrivision.com",
                "name": "Abdul Rasheed",
                "farm_name": "Malabar Agri-Tech & Plants",
                "phone": "+91 97455 88990",
                "city": "Vadakara",
                "district": "Kozhikode",
                "address": "Near NH Bypass, Kakkattil",
                "pin_code": "673104",
                "is_verified": False,
            },
        ]
        provider_objs = []
        for p in providers_data:
            u, _ = User.objects.get_or_create(
                email=p["email"],
                defaults={"name": p["name"], "is_active": True}
            )
            u.set_password("provider123")
            u.save()
            EmailAddress.objects.get_or_create(user=u, email=p["email"], defaults={"verified": True, "primary": True})

            prov, _ = Provider.objects.get_or_create(
                user=u,
                defaults={
                    "farm_name": p["farm_name"],
                    "contact_person": p["name"],
                    "phone": p["phone"],
                    "email": p["email"],
                    "address": p["address"],
                    "city": p["city"],
                    "district": p["district"],
                    "pin_code": p["pin_code"],
                    "is_verified": p["is_verified"],
                    "verification_date": timezone.now() if p["is_verified"] else None,
                }
            )
            provider_objs.append(prov)
        self.stdout.write(self.style.SUCCESS(f"[OK] Created {len(provider_objs)} provider organizations."))

        # 4. Product Categories
        categories_data = [
            ("Seeds", "High germination organic & hybrid seeds for vegetable and cash crops.", "fa-seedling"),
            ("Plants", "Grafted saplings, tissue-cultured plants, and fruit tree cuttings.", "fa-leaf"),
            ("Fertilizers", "Organic compost, NPK blends, bio-fertilizers, and micronutrients.", "fa-flask"),
            ("Pesticides", "Eco-friendly botanical bio-pesticides and fungal control solutions.", "fa-shield-halved"),
            ("Farming Tools", "Ergonomic sickles, pruning shears, drip irrigation components, and sprayers.", "fa-wrench"),
        ]
        category_map = {}
        for cat_name, desc, icon in categories_data:
            cat, _ = Category.objects.get_or_create(
                name=cat_name,
                defaults={"description": desc, "icon": icon}
            )
            category_map[cat_name] = cat
        self.stdout.write(self.style.SUCCESS(f"[OK] Initialized {len(category_map)} marketplace categories."))

        # 5. Products in Marketplace
        sample_products = [
            {
                "name": "High-Yield F1 Hybrid Tomato Seeds (100g)",
                "category": "Seeds",
                "provider_name": "Sahyadri Organic Seed Farms",
                "description": "Disease-resistant indeterminate tomato seeds. Produces glossy firm fruits with 90%+ germination rate.",
                "price": Decimal("180.00"),
                "cost_price": Decimal("130.00"),
                "stock": 85,
                "image_url": "https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=600&auto=format&fit=crop&q=80",
                "is_featured": True,
            },
            {
                "name": "Malabar Extra Hot Bird's Eye Chili Seeds (50g)",
                "category": "Seeds",
                "provider_name": "Sahyadri Organic Seed Farms",
                "description": "Authentic Kanthari / Bird's Eye chili seeds with intense pungency and continuous bearing habit.",
                "price": Decimal("120.00"),
                "cost_price": Decimal("85.00"),
                "stock": 45,
                "image_url": "https://images.unsplash.com/photo-1588252303782-cb80119abd6d?w=600&auto=format&fit=crop&q=80",
                "is_featured": True,
            },
            {
                "name": "Dwarf Grafted Cavendish Banana Plantlet",
                "category": "Plants",
                "provider_name": "GreenRoots Agro Nursery",
                "description": "Hardened tissue-culture Grand Naine Cavendish banana sapling ready for field planting.",
                "price": Decimal("95.00"),
                "cost_price": Decimal("65.00"),
                "stock": 60,
                "image_url": "https://images.unsplash.com/photo-1528825871115-3581a5387919?w=600&auto=format&fit=crop&q=80",
                "is_featured": True,
            },
            {
                "name": "Wayanad Robusta Coffee Grafted Sapling",
                "category": "Plants",
                "provider_name": "GreenRoots Agro Nursery",
                "description": "High yield Robusta coffee seedling with sturdy root stock suited for high humidity zones.",
                "price": Decimal("140.00"),
                "cost_price": Decimal("100.00"),
                "stock": 8,  # LOW STOCK SAMPLE
                "image_url": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=600&auto=format&fit=crop&q=80",
                "is_featured": False,
            },
            {
                "name": "Pure Enriched Vermicompost (5kg Bag)",
                "category": "Fertilizers",
                "provider_name": "GreenRoots Agro Nursery",
                "description": "100% organic earthworm castings packed with beneficial microbes, humic acid, and macro-nutrients.",
                "price": Decimal("220.00"),
                "cost_price": Decimal("150.00"),
                "stock": 120,
                "image_url": "https://images.unsplash.com/photo-1615811361523-6bd03d7748e7?w=600&auto=format&fit=crop&q=80",
                "is_featured": False,
            },
            {
                "name": "Seaweed Extract Liquid Bio-Nutrient (1L)",
                "category": "Fertilizers",
                "provider_name": "GreenRoots Agro Nursery",
                "description": "Cold-processed marine kelp extract promoting root vigor and stress tolerance.",
                "price": Decimal("480.00"),
                "cost_price": Decimal("350.00"),
                "stock": 4,  # LOW STOCK SAMPLE
                "image_url": "https://images.unsplash.com/photo-1585314062340-f1a5a7c9328d?w=600&auto=format&fit=crop&q=80",
                "is_featured": False,
            },
            {
                "name": "Neem Oil 10000 PPM Bio-Pesticide (500ml)",
                "category": "Pesticides",
                "provider_name": "Sahyadri Organic Seed Farms",
                "description": "Cold-pressed pure Azadirachtin neem oil emulsion for organic pest management.",
                "price": Decimal("340.00"),
                "cost_price": Decimal("240.00"),
                "stock": 0,  # OUT OF STOCK SAMPLE
                "image_url": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?w=600&auto=format&fit=crop&q=80",
                "is_featured": False,
            },
            {
                "name": "Heavy-Duty Bypass Pruning Shears",
                "category": "Farming Tools",
                "provider_name": "AgriVision Direct",
                "description": "SK5 high-carbon Japanese steel blade with titanium non-stick coating and ergonomic rubber grip.",
                "price": Decimal("650.00"),
                "cost_price": Decimal("450.00"),
                "stock": 35,
                "image_url": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=600&auto=format&fit=crop&q=80",
                "is_featured": True,
            },
        ]

        created_products = []
        for pdata in sample_products:
            prod, _ = Product.objects.get_or_create(
                name=pdata["name"],
                defaults={
                    "category": category_map[pdata["category"]],
                    "provider_name": pdata["provider_name"],
                    "description": pdata["description"],
                    "price": pdata["price"],
                    "cost_price": pdata["cost_price"],
                    "stock": pdata["stock"],
                    "image_url": pdata["image_url"],
                    "is_featured": pdata["is_featured"],
                    "is_active": True,
                }
            )
            created_products.append(prod)
        self.stdout.write(self.style.SUCCESS(f"[OK] Loaded {len(created_products)} catalog products with inventory."))

        # 6. Provider Requests (Pending, Approved, Rejected)
        requests_data = [
            # PENDING REQUESTS FOR ADMIN TO REVIEW & APPROVE
            {
                "provider": provider_objs[0],
                "product_name": "Organic Black Pepper Panniyur-1 Cuttings (Pack of 10)",
                "category": category_map["Plants"],
                "description": "Certified root-rotting resistant Panniyur variety pepper cuttings with active vegetative buds.",
                "quantity": 150,
                "expected_price": Decimal("250.00"),
                "status": ProviderRequest.PENDING,
                "image_url": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=600&auto=format&fit=crop&q=80",
            },
            {
                "provider": provider_objs[1],
                "product_name": "Heirloom Red Lady Papaya Hybrid Seeds (20 Seeds)",
                "category": category_map["Seeds"],
                "description": "High sweetness Red Lady 786 papaya seeds with dwarf fruiting characteristic.",
                "quantity": 200,
                "expected_price": Decimal("110.00"),
                "status": ProviderRequest.PENDING,
                "image_url": "https://images.unsplash.com/photo-1517282009859-f000ec3b26fe?w=600&auto=format&fit=crop&q=80",
            },
            {
                "provider": provider_objs[2],
                "product_name": "Bio-Enriched Trichoderma Viride Fungal Bio-Control (1kg)",
                "category": category_map["Pesticides"],
                "description": "Antagonistic fungal culture preventing damping off and wilt in nursery beds.",
                "quantity": 75,
                "expected_price": Decimal("180.00"),
                "status": ProviderRequest.PENDING,
                "image_url": "https://images.unsplash.com/photo-1530595467537-0b5996c41f2d?w=600&auto=format&fit=crop&q=80",
            },
            # APPROVED REQUEST
            {
                "provider": provider_objs[0],
                "product_name": "Dwarf Grafted Cavendish Banana Plantlet",
                "category": category_map["Plants"],
                "description": "Hardened tissue-culture Grand Naine Cavendish banana sapling ready for field planting.",
                "quantity": 60,
                "expected_price": Decimal("65.00"),
                "selling_price": Decimal("95.00"),
                "status": ProviderRequest.APPROVED,
                "admin_notes": "Quality verified with Wayanad nursery inspection.",
                "reviewed_by": admin_user,
                "reviewed_at": timezone.now(),
                "created_product": created_products[2],
                "image_url": "https://images.unsplash.com/photo-1528825871115-3581a5387919?w=600&auto=format&fit=crop&q=80",
            },
            # REJECTED REQUEST
            {
                "provider": provider_objs[2],
                "product_name": "Unbranded Generic Chemical Fertilizer Mix (50kg)",
                "category": category_map["Fertilizers"],
                "description": "Mixed synthetic nitrogen pellets without batch analysis report.",
                "quantity": 40,
                "expected_price": Decimal("750.00"),
                "status": ProviderRequest.REJECTED,
                "admin_notes": "Safety compliance violation. AgriVision only permits certified organic and lab-tested agro inputs.",
                "rejection_reason": "Missing government quality certification and lab nitrogen content analysis report.",
                "reviewed_by": admin_user,
                "reviewed_at": timezone.now(),
                "image_url": "https://images.unsplash.com/photo-1585314062340-f1a5a7c9328d?w=600&auto=format&fit=crop&q=80",
            },
        ]

        for req_data in requests_data:
            ProviderRequest.objects.get_or_create(
                product_name=req_data["product_name"],
                provider=req_data["provider"],
                defaults=req_data,
            )
        self.stdout.write(self.style.SUCCESS("[OK] Seeded realistic Provider Requests (Pending review, Approved, and Rejected)."))

        # 7. Customer Orders & Payments
        orders_data = [
            {
                "user": customer_users[0],
                "order_number": f"AGV-{random.randint(10000, 99999)}",
                "full_name": "Ramesh Nair",
                "phone": "+91 98471 22334",
                "email": "ramesh.nair@gmail.com",
                "delivery_address": "Kovilakam House, East Fort Road",
                "city": "Thrissur",
                "district": "Thrissur",
                "pin_code": "680005",
                "payment_method": Order.ONLINE,
                "payment_status": Order.PAID,
                "order_status": Order.DELIVERED,
                "items": [
                    (created_products[0], 3),  # 3 x 180 = 540
                    (created_products[4], 2),  # 2 x 220 = 440
                ],
            },
            {
                "user": customer_users[1],
                "order_number": f"AGV-{random.randint(10000, 99999)}",
                "full_name": "Priya Varma",
                "phone": "+91 94460 77889",
                "email": "priya.varma@gmail.com",
                "delivery_address": "Lotus Villa, Infopark Expressway",
                "city": "Kochi",
                "district": "Ernakulam",
                "pin_code": "682030",
                "payment_method": Order.ONLINE,
                "payment_status": Order.PAID,
                "order_status": Order.SHIPPED,
                "items": [
                    (created_products[7], 1),  # 1 x 650 = 650
                    (created_products[1], 4),  # 4 x 120 = 480
                ],
            },
            {
                "user": customer_users[2],
                "order_number": f"AGV-{random.randint(10000, 99999)}",
                "full_name": "Anand Kumar",
                "phone": "+91 97450 33445",
                "email": "anand.kumar@gmail.com",
                "delivery_address": "Green Pastures Farm, Kanjirappally",
                "city": "Kottayam",
                "district": "Kottayam",
                "pin_code": "686507",
                "payment_method": Order.COD,
                "payment_status": Order.PENDING,
                "order_status": Order.PROCESSING,
                "items": [
                    (created_products[2], 5),  # 5 x 95 = 475
                    (created_products[4], 3),  # 3 x 220 = 660
                ],
            },
            {
                "user": customer_users[3],
                "order_number": f"AGV-{random.randint(10000, 99999)}",
                "full_name": "Deepa Menon",
                "phone": "+91 95440 99112",
                "email": "deepa.menon@gmail.com",
                "delivery_address": "Menon Nivas, Karaparamba",
                "city": "Kozhikode",
                "district": "Kozhikode",
                "pin_code": "673010",
                "payment_method": Order.COD,
                "payment_status": Order.PENDING,
                "order_status": Order.ORDER_PENDING,
                "items": [
                    (created_products[0], 2),  # 2 x 180 = 360
                ],
            },
        ]

        for odata in orders_data:
            items_list = odata.pop("items")
            total_amt = sum(prod.price * qty for prod, qty in items_list)
            order, created = Order.objects.get_or_create(
                order_number=odata["order_number"],
                defaults={
                    "total_amount": total_amt,
                    **odata,
                }
            )
            if created:
                for prod, qty in items_list:
                    OrderItem.objects.create(
                        order=order,
                        product=prod,
                        product_name=prod.name,
                        quantity=qty,
                        price=prod.price,
                        subtotal=prod.price * qty,
                    )
                # Create Payment record
                Payment.objects.create(
                    order=order,
                    user=order.user,
                    transaction_id=f"TXN-{uuid.uuid4().hex[:10].upper()}",
                    payment_method=order.get_payment_method_display(),
                    amount=total_amt,
                    status=order.payment_status,
                )

        self.stdout.write(self.style.SUCCESS("[OK] Seeded customer orders, order items, and payment transactions."))
        self.stdout.write(self.style.SUCCESS("[OK] Seeding complete! You can now log into the Admin Portal at /admin-portal/ with admin@agrivision.com / admin123."))
