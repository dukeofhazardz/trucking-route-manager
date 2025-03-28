from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum
from datetime import timedelta, datetime


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
    time = models.DateTimeField(default=datetime.now())
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
        return f"{self.get_status_display()} ({self.time})"


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
    start_time = models.DateTimeField(default=datetime.now())
    end_time = models.DateTimeField(null=True, blank=True)
    
    cycle_type = models.CharField(
        max_length=10, 
        choices=CYCLE_CHOICES, 
        default='70_8'
    )
    
    total_driving_hours = models.FloatField(default=0)
    total_on_duty_hours = models.FloatField(default=0)
    
    def calculate_remaining_hours(self):
        """
        Calculate remaining driving hours based on selected cycle.
        """
        cycle_limits = {
            '70_8': 70,
            '60_7': 60
        }
        max_hours = cycle_limits.get(self.cycle_type, 70)
        return max(max_hours - self.total_driving_hours, 0)
    
    def update_hours(self):
        """
        Automatically update driving and on-duty hours from status logs.
        """
        # Calculate hours from status logs within this trip
        status_logs = StatusLog.objects.filter(
            start_time__gte=self.start_time,
            end_time__lte=self.end_time or datetime.now()
        )
        
        driving_duration = status_logs.filter(status='driving').aggregate(
            total_driving=Sum('duration')
        )['total_driving'] or timedelta()
        
        on_duty_duration = status_logs.filter(status='on_duty').aggregate(
            total_on_duty=Sum('duration')
        )['total_on_duty'] or timedelta()
        
        self.total_driving_hours = driving_duration.total_seconds() / 3600
        self.total_on_duty_hours = on_duty_duration.total_seconds() / 3600
        self.save()
    
    def __str__(self):
        return f"Trip from {self.start_location} to {self.destination}"

class DailyLog(models.Model):
    """
    Comprehensive daily log with detailed tracking and validation.
    """
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    date = models.DateField(default=datetime.now())

    driving_hours = models.FloatField(default=0)
    on_duty_hours = models.FloatField(default=0)
    off_duty_hours = models.FloatField(default=0)
    sleeper_berth_hours = models.FloatField(default=0)
    
    def clean(self):
        """
        Validate daily hours and ensure they don't exceed 24 hours.
        """
        total_hours = sum([
            self.driving_hours,
            self.on_duty_hours,
            self.off_duty_hours,
            self.sleeper_berth_hours
        ])
        
        if total_hours > 24:
            raise ValidationError("Total daily hours cannot exceed 24 hours")
    
    def save(self, *args, **kwargs):
        """
        Automatically populate hours from associated trip and status logs.
        """
        self.full_clean()
        
        # Automatically calculate hours from trip and status logs
        status_logs = StatusLog.objects.filter(
            start_time__date=self.date
        )
        
        self.driving_hours = status_logs.filter(status='driving').aggregate(
            total=Sum('duration')
        )['total'].total_seconds() / 3600 if status_logs else 0
        
        self.on_duty_hours = status_logs.filter(status='on_duty').aggregate(
            total=Sum('duration')
        )['total'].total_seconds() / 3600 if status_logs else 0
        
        self.off_duty_hours = status_logs.filter(status='off_duty').aggregate(
            total=Sum('duration')
        )['total'].total_seconds() / 3600 if status_logs else 0
        
        self.sleeper_berth_hours = status_logs.filter(status='sleeper_berth').aggregate(
            total=Sum('duration')
        )['total'].total_seconds() / 3600 if status_logs else 0
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Daily Log for {self.date}"