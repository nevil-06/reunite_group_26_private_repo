# Generated by Django 5.0.7 on 2024-07-13 14:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20200510_2016'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='size',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
