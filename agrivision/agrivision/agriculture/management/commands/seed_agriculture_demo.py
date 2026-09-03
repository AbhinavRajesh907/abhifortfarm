"""Management command to seed comprehensive agricultural demo data.

Seeds:
1. Agronomic crop profiles with soil, season, N-P-K, pH, temperature, and rainfall ranges.
2. Plant pathology data with symptoms, treatments, and preventive measures.
3. Regional agricultural commodity market prices.
4. Sample user recommendations and disease detections.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from agrivision.agriculture.models import (
    CropInformation,
    CropRecommendation,
    DiseaseInformation,
    MarketPrice,
)
from agrivision.users.models import User

CROPS = [
    {
        "name": "Rice",
        "description": "Primary staple cereal crop suited to warm, humid tropical and sub-tropical regions with high water-retention soils.",
        "cultivation_information": "Puddle fields thoroughly before transplanting 20-25 day old seedlings. Maintain 2-5 cm standing water during vegetative stage and drain before harvest. Apply nitrogen in splits (basal, tillering, and panicle initiation).",
        "soil_types": "Clay,Loam,Alluvial",
        "seasons": "Kharif,Monsoon",
        "locations": "Kerala,Tamil Nadu,West Bengal,Andhra Pradesh,Punjab",
        "min_temp": Decimal("20.00"),
        "max_temp": Decimal("38.00"),
        "min_ph": Decimal("5.00"),
        "max_ph": Decimal("7.50"),
        "min_rainfall": Decimal("1000.00"),
        "max_rainfall": Decimal("2500.00"),
        "optimal_n": Decimal("80.00"),
        "optimal_p": Decimal("40.00"),
        "optimal_k": Decimal("40.00"),
    },
    {
        "name": "Wheat",
        "description": "Essential cool-season rabi cereal crop requiring moderate temperatures and well-drained loamy soils.",
        "cultivation_information": "Sow in lines using seed drill during November at 20 cm row spacing. Critical irrigation stages: Crown Root Initiation (CRI at 21 days), Tillering, Flowering, and Milking stages.",
        "soil_types": "Loam,Clay loam,Alluvial",
        "seasons": "Rabi,Winter",
        "locations": "Punjab,Haryana,Uttar Pradesh,Madhya Pradesh,Rajasthan",
        "min_temp": Decimal("10.00"),
        "max_temp": Decimal("25.00"),
        "min_ph": Decimal("6.00"),
        "max_ph": Decimal("7.80"),
        "min_rainfall": Decimal("350.00"),
        "max_rainfall": Decimal("800.00"),
        "optimal_n": Decimal("120.00"),
        "optimal_p": Decimal("60.00"),
        "optimal_k": Decimal("40.00"),
    },
    {
        "name": "Tomato",
        "description": "High-value solanaceous vegetable crop that thrives in rich, well-drained loam with bright sunny days.",
        "cultivation_information": "Transplant sturdy seedlings onto raised beds with drip fertigation and plastic mulching. Provide bamboo staking for indeterminate varieties. Prune lower suckers to promote air circulation.",
        "soil_types": "Loam,Sandy loam,Red",
        "seasons": "Winter,Spring,Kharif",
        "locations": "Karnataka,Maharashtra,Kerala,Andhra Pradesh,Himachal Pradesh",
        "min_temp": Decimal("18.00"),
        "max_temp": Decimal("32.00"),
        "min_ph": Decimal("6.00"),
        "max_ph": Decimal("7.00"),
        "min_rainfall": Decimal("500.00"),
        "max_rainfall": Decimal("1200.00"),
        "optimal_n": Decimal("100.00"),
        "optimal_p": Decimal("60.00"),
        "optimal_k": Decimal("60.00"),
    },
    {
        "name": "Maize",
        "description": "High-yielding grain and fodder cereal adaptable to varied agro-climatic conditions with moderate moisture.",
        "cultivation_information": "Plant seeds 4-5 cm deep with 60x20 cm spacing. Ensure critical moisture at knee-high, tasseling, and silking stages. Keep fields free of weeds for the first 30 days.",
        "soil_types": "Loam,Sandy loam,Black,Alluvial",
        "seasons": "Kharif,Rabi,Summer",
        "locations": "Karnataka,Bihar,Andhra Pradesh,Madhya Pradesh,Maharashtra",
        "min_temp": Decimal("18.00"),
        "max_temp": Decimal("35.00"),
        "min_ph": Decimal("5.80"),
        "max_ph": Decimal("7.50"),
        "min_rainfall": Decimal("500.00"),
        "max_rainfall": Decimal("1100.00"),
        "optimal_n": Decimal("120.00"),
        "optimal_p": Decimal("60.00"),
        "optimal_k": Decimal("40.00"),
    },
    {
        "name": "Cotton",
        "description": "Premier fiber cash crop suited to deep, moisture-retentive black cotton soils with long frost-free periods.",
        "cultivation_information": "Sow with onset of monsoon in black cotton soil. Maintain 90x60 cm or 120x45 cm spacing. Monitor for bollworm and sucking pests using pheromone traps and integrated pest management.",
        "soil_types": "Black,Alluvial,Loam",
        "seasons": "Kharif,Monsoon",
        "locations": "Gujarat,Maharashtra,Telangana,Andhra Pradesh,Punjab",
        "min_temp": Decimal("21.00"),
        "max_temp": Decimal("37.00"),
        "min_ph": Decimal("6.50"),
        "max_ph": Decimal("8.50"),
        "min_rainfall": Decimal("600.00"),
        "max_rainfall": Decimal("1200.00"),
        "optimal_n": Decimal("100.00"),
        "optimal_p": Decimal("50.00"),
        "optimal_k": Decimal("50.00"),
    },
    {
        "name": "Potato",
        "description": "Crucial tuber cash crop requiring cool climate during tuber formation and loose, fertile sandy loam.",
        "cultivation_information": "Plant disease-free, sprouted seed tubers 7-10 cm deep in furrows. Perform earthing-up operations at 30 and 45 days after planting to prevent greening of tubers.",
        "soil_types": "Sandy loam,Loam,Alluvial",
        "seasons": "Rabi,Winter",
        "locations": "Uttar Pradesh,West Bengal,Bihar,Gujarat,Punjab",
        "min_temp": Decimal("12.00"),
        "max_temp": Decimal("24.00"),
        "min_ph": Decimal("5.20"),
        "max_ph": Decimal("6.80"),
        "min_rainfall": Decimal("400.00"),
        "max_rainfall": Decimal("800.00"),
        "optimal_n": Decimal("150.00"),
        "optimal_p": Decimal("80.00"),
        "optimal_k": Decimal("100.00"),
    },
]

DISEASES = [
    {
        "name": "Tomato early blight",
        "description": "Caused by the fungus Alternaria solani, producing concentric brown rings (target-board lesions) on older lower leaves.",
        "symptoms": "Dark brown circular spots with concentric rings on lower leaves, yellow chlorotic halo around spots, premature leaf drop, and stem collar rot.",
        "treatment": "Spray copper oxychloride (3g/L) or Mancozeb (2.5g/L) upon first sign of lesions. Repeat at 10-14 day intervals if humid conditions persist.",
        "prevention": "Avoid overhead sprinkler irrigation, practice 3-year crop rotation with non-solanaceous crops, remove infected crop residues, and stake plants for ventilation.",
        "severity": "medium",
    },
    {
        "name": "Tomato late blight",
        "description": "Devastating disease caused by oomycete Phytophthora infestans, rapidly turning foliage into water-soaked brown rot during cool, wet weather.",
        "symptoms": "Water-soaked irregular lesions on leaves that rapidly turn dark brown to purplish-black with white fuzzy fungal growth on the underside during humid mornings.",
        "treatment": "Apply systemic fungicides such as Metalaxyl + Mancozeb (2g/L) or Cymoxanil immediately upon detection.",
        "prevention": "Ensure good field drainage, plant certified disease-free seeds, maintain wide plant spacing, and destroy cull piles.",
        "severity": "high",
    },
    {
        "name": "Rice blast",
        "description": "Major fungal disease caused by Magnaporthe oryzae affecting rice leaves, nodes, and panicle necks.",
        "symptoms": "Spindle-shaped or diamond-like lesions with grey centers and brown/reddish margins on leaves; rotting of panicle neck causing empty grains.",
        "treatment": "Spray Tricyclazole 75% WP (0.6g/L) or Isoprothiolane 40% EC (1.5ml/L) at boot leaf or early flowering stage.",
        "prevention": "Avoid excessive basal nitrogen fertilizers, use blast-resistant cultivars, treat seeds with carbendazim (2g/kg seed), and manage field water levels.",
        "severity": "high",
    },
    {
        "name": "Rice brown spot",
        "description": "Fungal infection caused by Bipolaris oryzae, prevalent in nutrient-deficient and water-stressed soils.",
        "symptoms": "Numerous small circular to oval brown spots with yellow halos across leaf blades and grains.",
        "treatment": "Apply Propiconazole 25% EC (1ml/L) or Mancozeb (2g/L) alongside balanced potash and nitrogen fertilization.",
        "prevention": "Ensure balanced soil nutrition (especially potassium and silicon), avoid soil water stress, and use treated certified seeds.",
        "severity": "medium",
    },
    {
        "name": "Wheat leaf rust",
        "description": "Airborne fungal disease caused by Puccinia triticina producing orange-brown powdery pustules on wheat leaves.",
        "symptoms": "Small, round to oval orange-brown powdery pustules scattered randomly across upper leaf surfaces.",
        "treatment": "Foliar spray of Propiconazole 25% EC (0.1%) or Tebuconazole (1ml/L) at the appearance of first pustules.",
        "prevention": "Sow rust-resistant wheat varieties, adhere to recommended sowing dates, and eradicate volunteer wheat plants.",
        "severity": "medium",
    },
    {
        "name": "Potato late blight",
        "description": "Phytophthora infestans infection causing rapid foliage destruction and tuber rot.",
        "symptoms": "Dark brown water-soaked blotches on leaf tips and margins; white downy mildew on underside in humid air.",
        "treatment": "Foliar application of Dimethomorph + Mancozeb (2.5g/L) or Fenamidone + Mancozeb.",
        "prevention": "Use certified seed tubers, practice proper earthing-up to protect tubers, and avoid planting near tomato fields.",
        "severity": "high",
    },
]

PRICES = [
    ("Rice", "Kochi APMC Market", "Kerala", Decimal("2650.00")),
    ("Rice", "Karnal Grain Mandi", "Haryana", Decimal("2480.00")),
    ("Wheat", "Azadpur Mandi", "Delhi", Decimal("2320.00")),
    ("Wheat", "Khanna Grain Market", "Punjab", Decimal("2280.00")),
    ("Tomato", "Kolar APMC Yard", "Karnataka", Decimal("1950.00")),
    ("Tomato", "Vashi Market", "Maharashtra", Decimal("2100.00")),
    ("Maize", "Davangere Mandi", "Karnataka", Decimal("2150.00")),
    ("Maize", "Gulabbagh Mandi", "Bihar", Decimal("2050.00")),
    ("Cotton", "Rajkot Cotton Yard", "Gujarat", Decimal("7350.00")),
    ("Cotton", "Warangal Market", "Telangana", Decimal("7100.00")),
    ("Potato", "Agra Mandi", "Uttar Pradesh", Decimal("1650.00")),
    ("Potato", "Hooghly Market", "West Bengal", Decimal("1580.00")),
]


class Command(BaseCommand):
    help = "Seed comprehensive agronomic crop profiles, plant diseases, treatments, and market prices."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            help="Optional existing user email to seed sample recommendations and history records for.",
        )

    def handle(self, *args, **options):
        crops_map = {}
        for crop_data in CROPS:
            crop, created = CropInformation.objects.update_or_create(
                name=crop_data["name"],
                defaults=crop_data,
            )
            crops_map[crop.name] = crop
            status_str = "Created" if created else "Updated"
            self.stdout.write(f"  {status_str} crop: {crop.name}")

        for disease_data in DISEASES:
            disease, created = DiseaseInformation.objects.update_or_create(
                name=disease_data["name"],
                defaults=disease_data,
            )
            status_str = "Created" if created else "Updated"
            self.stdout.write(f"  {status_str} disease: {disease.name}")

        observed_at = timezone.now()
        for crop_name, market, region, price in PRICES:
            if crop_name in crops_map:
                MarketPrice.objects.update_or_create(
                    crop=crops_map[crop_name],
                    market=market,
                    region=region,
                    defaults={
                        "price": price,
                        "unit": "quintal",
                        "currency": "INR",
                        "observed_at": observed_at,
                        "data_source": MarketPrice.SAMPLE,
                    },
                )

        email = options.get("email")
        if email:
            user = User.objects.filter(email=email).first()
            if user:
                # Seed a sample crop recommendation
                sample_crop = crops_map.get("Rice")
                CropRecommendation.objects.update_or_create(
                    user=user,
                    soil_type="Clay",
                    season="Kharif",
                    location="Kerala",
                    defaults={
                        "temperature": Decimal("28.50"),
                        "rainfall": Decimal("1450.00"),
                        "ph": Decimal("6.20"),
                        "n": Decimal("85.00"),
                        "p": Decimal("40.00"),
                        "k": Decimal("45.00"),
                        "input_params": {"soil_type": "Clay", "season": "Kharif", "location": "Kerala", "temperature": 28.5, "rainfall": 1450},
                        "recommended_crop": sample_crop,
                        "recommended_crops_list": [
                            {"crop_name": "Rice", "percentage": 96, "explanation": "Optimal clay soil and Kharif moisture."},
                            {"crop_name": "Maize", "percentage": 78, "explanation": "Good warm season growth."},
                        ],
                        "explanation": "Rice is highly recommended for your high-rainfall, clay soil profile in Kerala during the Kharif season.",
                    },
                )
                self.stdout.write(self.style.SUCCESS(f"Sample recommendations created for user: {email}"))
            else:
                self.stdout.write(self.style.WARNING(f"User '{email}' not found, skipped user-specific sample history."))

        self.stdout.write(self.style.SUCCESS("AI & Agriculture demo data seeded successfully!"))
