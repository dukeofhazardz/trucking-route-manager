# Generated by Django 5.0.4 on 2025-03-26 08:43

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('driver_name', models.CharField(max_length=255)),
                ('current_location', models.CharField(max_length=255)),
                ('pickup_location', models.CharField(max_length=255)),
                ('dropoff_location', models.CharField(max_length=255)),
                ('current_cycle_hours', models.FloatField(default=0)),
                ('total_driving_hours', models.FloatField(default=0)),
                ('cycle_type', models.CharField(choices=[('70_8', '70 Hours / 8 Days')], default='70_8', max_length=10)),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('estimated_arrival', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DailyLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('name_of_carrier', models.CharField(max_length=255)),
                ('truck_number', models.CharField(max_length=255)),
                ('main_office_address', models.CharField(max_length=255)),
                ('home_terminal_address', models.CharField(max_length=255)),
                ('total_miles', models.FloatField(default=0)),
                ('total_millage', models.FloatField(default=0)),
                ('sleeper_berth_hours', models.FloatField(default=0)),
                ('driving_hours', models.FloatField(default=0)),
                ('on_duty_hours', models.FloatField(default=0)),
                ('off_duty_hours', models.FloatField(default=0)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trucking_app.trip')),
            ],
        ),
        migrations.CreateModel(
            name='Status',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('sleeper_berth', 'Sleeper Berth'), ('driving', 'Driving'), ('on_duty', 'On Duty'), ('off_duty', 'Off Duty')], max_length=20)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trucking_app.trip')),
            ],
            options={
                'ordering': ['timestamp'],
                'unique_together': {('trip', 'timestamp')},
            },
        ),
    ]
