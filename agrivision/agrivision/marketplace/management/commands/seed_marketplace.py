"""
Management command to seed the marketplace with:
  - 2 categories: Seeds and Plants
  - Sample products (5 Seeds, 5 Plants)

Usage:
    python manage.py seed_marketplace
"""

from django.core.management.base import BaseCommand

from agrivision.marketplace.models import Category, Product
from agrivision.providers.models import ProviderProfile


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
        "name": "Cucumber Seeds",
        "category": "Seeds",
        "description": "Crisp and refreshing cucumber seeds. Fast germination and disease-resistant variety.",
        "price": 45.00,
        "stock": 120,
    },
    # Plants
    {
        "name": "Neem Sapling",
        "category": "Plants",
        "description": "Hardy medicinal neem tree sapling (1-2 ft). Naturally repels pests and purifies air.",
        "price": 79.00,
        "stock": 60,
    },
    {
        "name": "Tulsi (Holy Basil)",
        "category": "Plants",
        "description": "Aromatic and sacred Holy Basil plant in a nursery pot. Ready to plant in your garden.",
        "price": 49.00,
        "stock": 90,
    },
    {
        "name": "Aloe Vera Plant",
        "category": "Plants",
        "description": "Succulent Aloe Vera plant. Requires minimal watering; excellent for skin and health.",
        "price": 69.00,
        "stock": 75,
    },
    {
        "name": "Money Plant (Pothos)",
        "category": "Plants",
        "description": "Lush green air-purifying money plant. Grows in water or soil, indoors or outdoors.",
        "price": 99.00,
        "stock": 45,
    },
    {
        "name": "Curry Leaf Plant",
        "category": "Plants",
        "description": "Fresh culinary curry leaf sapling. A kitchen garden essential for everyday cooking.",
        "price": 59.00,
        "stock": 80,
    },
]


class Command(BaseCommand):
    help = "Seeds the marketplace with default categories and sample products."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding marketplace categories..."))

        seeds_cat, _ = Category.objects.get_or_create(name="Seeds", defaults={"description": "Seeds for agriculture"})
        plants_cat, _ = Category.objects.get_or_create(name="Plants", defaults={"description": "Plants and saplings"})

        cat_map = {
            "Seeds": seeds_cat,
            "Plants": plants_cat,
        }

        first_provider = ProviderProfile.objects.first()

        self.stdout.write(self.style.NOTICE("Seeding sample products..."))
        created_count = 0
        for data in SAMPLE_PRODUCTS:
            category = cat_map[data["category"]]
            product, created = Product.objects.get_or_create(
                name=data["name"],
                defaults={
                    "category": category,
                    "description": data["description"],
                    "price": data["price"],
                    "stock": data["stock"],
                    "provider": first_provider,
                    "provider_name": getattr(first_provider, "farm_name", "AgriFarm Direct"),
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + Created: {product.name} ({category.name})"))
            else:
                self.stdout.write(f"  - Already exists: {product.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete! {created_count} product(s) added."
            )
        )
