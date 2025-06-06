# Generated by Django 5.1.3 on 2025-05-26 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('custom_design', '0002_templatepayment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producttype',
            name='default_height',
            field=models.IntegerField(default=400, help_text='Default canvas height in pixels'),
        ),
        migrations.AlterField(
            model_name='producttype',
            name='default_width',
            field=models.IntegerField(default=320, help_text='Default canvas width in pixels'),
        ),
    ]
