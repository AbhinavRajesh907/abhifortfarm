"""
Management command to seed the marketplace with:
  - 2 categories: Seeds and Plants (ONLY these two)
  - 10 sample products (5 Seeds, 5 Plants)

Usage:
    python manage.py seed_marketplace
"""

from django.core.management.base import BaseCommand

from agrivision.marketplace.models import Category
from agrivision.marketplace.models import Product


SAMPLE_PRODUCTS = [
    # Seeds
    {
        "name": "Tomato Seeds",
        "category": "Seeds",
        "description": "High-yield hybrid tomato seeds suitable for both open field and greenhouse cultivation.",
        "price": 49.00,
        "stock": 200,
    },
    {
        "name": "Chilli Seeds",
        "category": "Seeds",
        "description": "Hot and spicy chilli seeds. Grows well in tropical climates with good sunlight.",
        "price": 39.00,
        "stock": 150,
    },
    {
        "name": "Carrot Seeds",
        "category": "Seeds",
        "description": "Premium carrot seeds that produce sweet, crunchy carrots. Easy to grow in sandy soil.",
        "price": 35.00,
        "stock": 180,
    },
    {
        "name": "Spinach Seeds",
        "category": "Seeds",
        "description": "Nutritious spinach seeds. Fast-growing leafy vegetable ideal for home gardens.",
        "price": 29.00,
        "stock": 250,
    },
    {
        "name": "Brinjal Seeds",
        "category": "Seeds",
        "description": "Round brinjal (eggplant) seeds. Heavy-bearing variety suitable for warm climates.",
        "price": 45.00,
        "stock": 120,
    },
    # Plants
    {
        "name": "Tomato Plant",
        "category": "Plants",
        "description": "Ready-to-plant tomato saplings. 4-6 week old, healthy and pest-free.",
        "price": 25.00,
        "stock": 100,
    },
    {
        "name": "Chilli Plant",
        "category": "Plants",
        "description": "Healthy chilli plants ready for transplanting. Starts bearing fruit within 60 days.",
        "price": 20.00,
        "stock": 90,
    },
    {
        "name": "Rose Plant",
        "category": "Plants",
        "description": "Beautiful flowering rose plant. Available in red. Ideal for gardens and pots.",
        "price": 120.00,
        "stock": 50,
    },
    {
        "name": "Mango Plant",
        "category": "Plants",
        "description": "Grafted mango plant. Produces fruit within 2-3 years. Alphonso variety.",
        "price": 350.00,
        "stock": 30,
    },
    {
        "name": "Coconut Plant",
        "category": "Plants",
        "description": "Dwarf coconut palm plant. Fast-bearing variety, starts yielding in 3-4 years.",
        "price": 280.00,
        "stock": 40,
    },
]


class Command(BaseCommand):
    help = "Seed the marketplace with Seeds & Plants categories and sample products."

    def handle(self, *args, **options):
        # Create only Seeds and Plants categories
        for cat_name in ["Seeds", "Plants"]:
            cat, created = Category.objects.get_or_create(name=cat_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Created category: {cat_name}"))
            else:
                self.stdout.write(f"  Category already exists: {cat_name}")

        # Create sample products
        created_count = 0
        for data in SAMPLE_PRODUCTS:
            cat = Category.objects.get(name=data["category"])
            product, created = Product.objects.get_or_create(
                name=data["name"],
                defaults={
                    "category": cat,
                    "description": data["description"],
                    "price": data["price"],
                    "stock": data["stock"],
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created product: {product.name}"))
            else:
                self.stdout.write(f"  Product already exists: {product.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete. {created_count} new products added."
            )
        )
