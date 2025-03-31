from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime


class StatusLog(models.Model):
    """
    Comprehensive status tracking for drivers with automatic time calculations.
    """
    STATUS_CHOICES = [
        ('sleeper_berth', 'Sleeper Berth'),
        ('driving', 'Driving'),
        ('on_duty', 'On Duty'),
        ('off_duty', 'Off Duty'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    time = models.DateTimeField(default=datetime.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    class Meta:
        ordering = ['-time']
        
    def save(self, *args, **kwargs):
        # Automatically calculate duration when end_time is set
        if self.time and self.end_time:
            if hasattr(self.time, 'tzinfo'):
                self.time = self.time.replace(tzinfo=None)
            if hasattr(self.end_time, 'tzinfo'):
                self.end_time = self.end_time.replace(tzinfo=None)
            self.duration = self.end_time - self.time
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.status} at ({self.time})"


class Trip(models.Model):
    """
    Comprehensive trip tracking with advanced cycle management.
    """
    CYCLE_CHOICES = [
        ('70_8', '70 Hours / 8 Days'),
        ('60_7', '60 Hours / 7 Days'),
    ]
    start_latitude = models.CharField(max_length=255)
    start_longitude = models.CharField(max_length=255)
    destination_latitude = models.CharField(max_length=255)
    destination_longitude = models.CharField(max_length=255)
    start_time = models.DateTimeField(default=datetime.now)
    end_time = models.DateTimeField(null=True, blank=True)
    total_distance_km = models.FloatField(default=0)
    total_duration_hours = models.FloatField(default=0)
    
    cycle_type = models.CharField(
        max_length=10, 
        choices=CYCLE_CHOICES, 
        default='70_8'
    )
    
    def calculate_remaining_hours(self):
        """
        Calculate remaining driving hours based on selected cycle.
        """
        cycle_limits = {
            '70_8': 70,
            '60_7': 60
        }
        max_hours = cycle_limits.get(self.cycle_type, 70)
        return max(max_hours - self.total_duration_hours, 0)
    
    def clean(self):
        if self.calculate_remaining_hours() < 0:
            raise ValidationError("This trip would exceed your available driving hours")
        
    def __str__(self):
        return f"Trip from {self.start_time} to {self.end_time}"

class DailyLog(models.Model):
    """
    Comprehensive daily log with detailed tracking and validation.
    """
    # A daily log can be associated with many trips
    trip = models.ManyToManyField(
        Trip,
        related_name='daily_logs',
        blank=True,
        help_text="Trips associated with this daily log"
        )
    date = models.DateField(default=datetime.now)
    driving_hours = models.FloatField(default=0)
    on_duty_hours = models.FloatField(default=0)
    off_duty_hours = models.FloatField(default=0)
    sleeper_berth_hours = models.FloatField(default=0)
    total_miles = models.FloatField(
        default=0,
        help_text="Miles driven today"
    )
    cumulative_mileage = models.FloatField(
        default=0,
        help_text="Total odometer reading"
    )

    def save(self, *args, **kwargs):
        """
        Automatically populate hours from associated trip and status logs.
        """
        self.full_clean()

        # First save to get a PK
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Daily Log for {self.date}"
