# Generated by Django 5.1.3 on 2025-03-25 06:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0026_orderitem_designer_service'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='base_price',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
