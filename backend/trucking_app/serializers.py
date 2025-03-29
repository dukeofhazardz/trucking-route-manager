from rest_framework import serializers
from .models import Trip, DailyLog, StatusLog


class StatusLogSerializer(serializers.ModelSerializer):
    duration_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = StatusLog
        fields = '__all__'
        extra_kwargs = {
            'duration': {'read_only': True},
        }

class TripSerializer(serializers.ModelSerializer):
    remaining_hours = serializers.SerializerMethodField()
    status_logs = StatusLogSerializer(many=True, read_only=True)
    
    class Meta:
        model = Trip
        fields = '__all__'
        extra_kwargs = {
            'total_driving_hours': {'read_only': True},
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
            'total_miles': {'read_only': True},
            'cumulative_mileage': {'read_only': True},
        }
