# Generated by Django 5.1.3 on 2025-03-15 08:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0023_alter_pendingorder_design_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='variant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='store.productvariant'),
        ),
    ]
