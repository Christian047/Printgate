# Generated by Django 5.1.3 on 2025-02-25 17:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_alter_product_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, default='A.png', null=True, upload_to='products/'),
        ),
    ]
