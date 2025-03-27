from rest_framework import serializers
from .models import Driver, Vehicle, Trip, DailyLog, StatusLog


class DriverSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Driver
        fields = [
            'id', 'first_name', 'last_name', 'license_number', 
            'full_name'
        ]
        extra_kwargs = {
            'license_number': {'validators': []},  # Disable unique validation
        }

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class StatusLogSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = StatusLog
        fields = '__all__'
    
    def get_duration_hours(self, obj):
        return obj.duration.total_seconds() / 3600 if obj.duration else None

class TripSerializer(serializers.ModelSerializer):
    remaining_hours = serializers.SerializerMethodField()
    status_logs = StatusLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = '__all__'
        extra_kwargs = {
            'total_driving_hours': {'read_only': True},
            'total_on_duty_hours': {'read_only': True},
        }
    
    def get_remaining_hours(self, obj):
        return obj.calculate_remaining_hours()

class DailyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = '__all__'
        extra_kwargs = {
            'driving_hours': {'read_only': True},
            'on_duty_hours': {'read_only': True},
            'off_duty_hours': {'read_only': True},
            'sleeper_berth_hours': {'read_only': True},
        }

class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusLog
        fields = '__all__'