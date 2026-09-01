"""
Management command to seed the marketplace with:
  - 2 categories: Seeds and Plants (ONLY these two)
  - 3 sample Providers
  - 10 sample products (5 Seeds, 5 Plants)

Usage:
    python manage.py seed_marketplace
"""

from django.core.management.base import BaseCommand

from agrivision.marketplace.models import Category
from agrivision.marketplace.models import Product
from agrivision.marketplace.models import LocalProvider

PROVIDERS_DATA = [
    {
        "name": "Provider A",
        "business_name": "Green Valley Seeds",
        "phone": "9876543210",
        "email": "contact@greenvalley.com",
        "branch_name": "Kottayam Branch",
        "branch_location": "Kottayam, Kerala",
        "branch_address": "123 Green Valley Road, Kottayam",
    },
    {
        "name": "Provider B",
        "business_name": "Kerala Plant Nursery",
        "phone": "8765432109",
        "email": "info@keralaplantnursery.com",
        "branch_name": "Ernakulam Branch",
        "branch_location": "Ernakulam, Kerala",
        "branch_address": "456 Main Street, Ernakulam",
    },
    {
        "name": "Provider C",
        "business_name": "Farm Fresh Plants",
        "phone": "7654321098",
        "email": "hello@farmfreshplants.com",
        "branch_name": "Thrissur Branch",
        "branch_location": "Thrissur, Kerala",
        "branch_address": "789 Farm Road, Thrissur",
    },
]

SAMPLE_PRODUCTS = [
    # Seeds -> Provider A and B
    {
        "name": "Tomato Seeds",
        "category": "Seeds",
        "provider": "Provider A",
        "description": "High-yield hybrid tomato seeds suitable for both open field and greenhouse cultivation.",
        "price": 49.00,
        "stock": 200,
    },
    {
        "name": "Chilli Seeds",
        "category": "Seeds",
        "provider": "Provider A",
        "description": "Hot and spicy chilli seeds. Grows well in tropical climates with good sunlight.",
        "price": 39.00,
        "stock": 150,
    },
    {
        "name": "Carrot Seeds",
        "category": "Seeds",
        "provider": "Provider B",
        "description": "Premium carrot seeds that produce sweet, crunchy carrots. Easy to grow in sandy soil.",
        "price": 35.00,
        "stock": 180,
    },
    {
        "name": "Spinach Seeds",
        "category": "Seeds",
        "provider": "Provider B",
        "description": "Nutritious spinach seeds. Fast-growing leafy vegetable ideal for home gardens.",
        "price": 29.00,
        "stock": 250,
    },
    {
        "name": "Brinjal Seeds",
        "category": "Seeds",
        "provider": "Provider A",
        "description": "Round brinjal (eggplant) seeds. Heavy-bearing variety suitable for warm climates.",
        "price": 45.00,
        "stock": 120,
    },
    # Plants -> Provider B and C
    {
        "name": "Tomato Plant",
        "category": "Plants",
        "provider": "Provider C",
        "description": "Ready-to-plant tomato saplings. 4-6 week old, healthy and pest-free.",
        "price": 25.00,
        "stock": 100,
    },
    {
        "name": "Chilli Plant",
        "category": "Plants",
        "provider": "Provider B",
        "description": "Healthy chilli plants ready for transplanting. Starts bearing fruit within 60 days.",
        "price": 20.00,
        "stock": 90,
    },
    {
        "name": "Rose Plant",
        "category": "Plants",
        "provider": "Provider C",
        "description": "Beautiful flowering rose plant. Available in red. Ideal for gardens and pots.",
        "price": 120.00,
        "stock": 50,
    },
    {
        "name": "Mango Plant",
        "category": "Plants",
        "provider": "Provider B",
        "description": "Grafted mango plant. Produces fruit within 2-3 years. Alphonso variety.",
        "price": 350.00,
        "stock": 30,
    },
    {
        "name": "Coconut Plant",
        "category": "Plants",
        "provider": "Provider C",
        "description": "Dwarf coconut palm plant. Fast-bearing variety, starts yielding in 3-4 years.",
        "price": 280.00,
        "stock": 40,
    },
]


class Command(BaseCommand):
    help = "Seed the marketplace with Seeds & Plants and sample providers/products."

    def handle(self, *args, **options):
        # Clear existing
        Product.objects.all().delete()
        Category.objects.all().delete()
        LocalProvider.objects.all().delete()
        
        self.stdout.write("Cleared existing marketplace data.")

        # Create Providers
        providers = {}
        for pd in PROVIDERS_DATA:
            prov = LocalProvider.objects.create(**pd)
            providers[prov.name] = prov
            self.stdout.write(self.style.SUCCESS(f"  Created Provider: {prov.name} - {prov.business_name}"))

        # Create Categories
        for cat_name in ["Seeds", "Plants"]:
            cat, created = Category.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created category: {cat_name}"))

        # Create Products
        created_count = 0
        for data in SAMPLE_PRODUCTS:
            cat = Category.objects.get(name=data["category"])
            prov = providers[data["provider"]]
            product, created = Product.objects.get_or_create(
                name=data["name"],
                defaults={
                    "category": cat,
                    "provider": prov,
                    "description": data["description"],
                    "price": data["price"],
                    "stock": data["stock"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created product: {product.name} (Provider: {prov.business_name})"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete. {created_count} new products added with providers."
            )
        )
