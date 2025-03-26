from django.db import models
from django.utils import timezone


class Trip(models.Model):
    CYCLE_CHOICES = [
        ('70_8', '70 Hours / 8 Days'),
    ]

    driver_name = models.CharField(max_length=255)
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    
    current_cycle_hours = models.FloatField(default=0)
    total_driving_hours = models.FloatField(default=0)
    
    cycle_type = models.CharField(
        max_length=10, 
        choices=CYCLE_CHOICES, 
        default='70_8'
    )
    
    start_time = models.DateTimeField(default=timezone.now)
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    
    def calculate_remaining_hours(self):
        # Logic to calculate remaining driving hours in 8-day cycle
        return max(70 - self.total_driving_hours, 0)


class Status(models.Model):
    STATUS_CHOICES = [
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty', 'On Duty'),
        ('off_duty', 'Off Duty'),
    ]
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    time = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['time']
        unique_together = ['trip', 'time']


class DailyLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    name_of_carrier = models.CharField(max_length=255)
    truck_number = models.CharField(max_length=255)
    main_office_address = models.CharField(max_length=255)
    home_terminal_address = models.CharField(max_length=255)
    total_miles = models.FloatField(default=0)
    total_millage = models.FloatField(default=0)
    sleeper_berth_hours = models.FloatField(default=0)
    driving_hours = models.FloatField(default=0)
    on_duty_hours = models.FloatField(default=0)
    off_duty_hours = models.FloatField(default=0)
    
    def validate_hours(self):
        # Ensure total hours don't exceed 24
        total_hours = self.driving_hours + self.on_duty_hours + self.off_duty_hours
        return total_hours <= 24

