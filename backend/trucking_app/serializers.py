from rest_framework import serializers
from .models import Trip, DailyLog, Status

class TripSerializer(serializers.ModelSerializer):
    remaining_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Trip
        fields = '__all__'
    
    def get_remaining_hours(self, obj):
        return obj.calculate_remaining_hours()

class DailyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyLog
        fields = '__all__'


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Status
        fields = '__all__'


