# Generated by Django 5.1.3 on 2025-02-27 05:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='products',
            name='category',
        ),
        migrations.DeleteModel(
            name='Categories',
        ),
        migrations.DeleteModel(
            name='Products',
        ),
    ]
