# Generated by Django 5.0.4 on 2025-03-31 18:26

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StatusLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('sleeper_berth', 'Sleeper Berth'), ('driving', 'Driving'), ('on_duty', 'On Duty'), ('off_duty', 'Off Duty')], max_length=20)),
                ('time', models.DateTimeField(default=datetime.datetime.now)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('duration', models.DurationField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-time'],
            },
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_latitude', models.CharField(max_length=255)),
                ('start_longitude', models.CharField(max_length=255)),
                ('destination_latitude', models.CharField(max_length=255)),
                ('destination_longitude', models.CharField(max_length=255)),
                ('start_time', models.DateTimeField(default=datetime.datetime.now)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('total_distance_km', models.FloatField(default=0)),
                ('total_duration_hours', models.FloatField(default=0)),
                ('cycle_type', models.CharField(choices=[('70_8', '70 Hours / 8 Days'), ('60_7', '60 Hours / 7 Days')], default='70_8', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='DailyLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=datetime.datetime.now)),
                ('driving_hours', models.FloatField(default=0)),
                ('on_duty_hours', models.FloatField(default=0)),
                ('off_duty_hours', models.FloatField(default=0)),
                ('sleeper_berth_hours', models.FloatField(default=0)),
                ('total_miles', models.FloatField(default=0, help_text='Miles driven today')),
                ('cumulative_mileage', models.FloatField(default=0, help_text='Total odometer reading')),
                ('trip', models.ManyToManyField(blank=True, help_text='Trips associated with this daily log', related_name='daily_logs', to='trucking_app.trip')),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.AddConstraint(
            model_name='dailylog',
            constraint=models.UniqueConstraint(fields=('date',), name='unique_daily_log_date'),
        ),
    ]
