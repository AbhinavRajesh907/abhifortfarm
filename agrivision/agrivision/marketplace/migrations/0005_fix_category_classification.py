from django.db import migrations


def fix_category_types(apps, schema_editor):
    Category = apps.get_model("marketplace", "Category")
    
    # 1. Update Plants parent and subcategories
    Category.objects.filter(name="Plants").update(category_type="Plants")
    Category.objects.filter(parent__name="Plants").update(category_type="Plants")
    Category.objects.filter(name__icontains="Plant").update(category_type="Plants")
    
    # 2. Update Seeds parent and subcategories
    Category.objects.filter(name="Seeds").update(category_type="Seeds")
    Category.objects.filter(parent__name="Seeds").update(category_type="Seeds")
    Category.objects.filter(name__icontains="Seed").update(category_type="Seeds")
    
    # 3. Update Tools/Fertilizers/Pesticides
    Category.objects.filter(name__in=["Fertilizers", "Pesticides", "Farming Tools"]).update(category_type="Other")


def reverse_fix(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0004_order_refund_status_alter_refundrequest_status"),
    ]

    operations = [
        migrations.RunPython(fix_category_types, reverse_fix),
    ]
