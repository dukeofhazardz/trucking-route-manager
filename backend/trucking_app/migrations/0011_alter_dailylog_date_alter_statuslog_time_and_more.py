# Generated by Django 5.0.4 on 2025-03-28 19:54

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trucking_app', '0010_alter_dailylog_date_alter_statuslog_time_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailylog',
            name='date',
            field=models.DateField(default=datetime.datetime(2025, 3, 28, 19, 54, 57, 527387)),
        ),
        migrations.AlterField(
            model_name='statuslog',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2025, 3, 28, 19, 54, 57, 522323)),
        ),
        migrations.AlterField(
            model_name='trip',
            name='start_time',
            field=models.DateTimeField(default=datetime.datetime(2025, 3, 28, 19, 54, 57, 524338)),
        ),
    ]
