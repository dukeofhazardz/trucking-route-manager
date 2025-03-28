from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from datetime import datetime, timedelta
import requests

from .models import Trip, DailyLog, StatusLog
from .serializers import (
    TripSerializer, 
    DailyLogSerializer, 
    StatusLogSerializer
)


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer

    @action(detail=False, methods=['POST'])
    def calculate_route(self, request):
        try:
            # Extract coordinates
            current_location = request.data.get('current_location')
            pickup_location = request.data.get('pickup_location')
            dropoff_location = request.data.get('dropoff_location')
            
            # Validate coordinates
            if not all([current_location, pickup_location, dropoff_location]):
                return Response(
                    {"error": "Missing location coordinates"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Format coordinates for OSRM
            def format_coords(location):
                return f"{location[1]},{location[0]}"
            
            waypoints = [
                format_coords(current_location),
                format_coords(pickup_location),
                format_coords(dropoff_location)
            ]
            
            # Call OSRM routing service
            osrm_url = "http://router.project-osrm.org/route/v1/driving/"
            coordinates = ";".join(waypoints)
            response = requests.get(f"{osrm_url}{coordinates}?overview=full&steps=true")
            
            if response.status_code != 200:
                return Response(
                    {"error": "Route calculation failed"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            route_data = response.json()
            
            # New trip
            trip_data = {
                "start_latitude": current_location[0],
                "start_longitude": current_location[1],
                "destination_latitude": dropoff_location[0],
                "destination_longitude": dropoff_location[1],
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(seconds=route_data['routes'][0]['duration']),
            }
            serializer = self.get_serializer(data=trip_data)
            serializer.is_valid(raise_exception=True)
            trip = serializer.save()

            return Response({
                'route_details': route_data,
                'total_distance_km': route_data['routes'][0]['distance'] / 1000,
                'total_duration_hours': route_data['routes'][0]['duration'] / 3600,
                'waypoints': route_data['waypoints']
            })
        
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['GET'])
    def generate_logs(self, request, pk=None):
        trip = self.get_object()
        
        # Generate daily logs
        logs = []
        for day in range(1, 4):  # Generate logs for first 3 days
            log = DailyLog.objects.create(
                trip=trip,
                date=trip.start_time.date() + timedelta(days=day-1),
                driving_hours=11,  # Max allowed driving hours per day
                on_duty_hours=14,  # Max on-duty hours
                off_duty_hours=10  # Remaining hours
            )
            logs.append(DailyLogSerializer(log).data)
        
        return Response(logs)

class StatusLogViewSet(viewsets.ModelViewSet):
    queryset = StatusLog.objects.all()
    serializer_class = StatusLogSerializer
    
    def create(self, request):
        # Close previous open status
        latest_status = StatusLog.objects.filter(
            end_time__isnull=True
        ).first()
        
        if latest_status:
            latest_status.end_time = datetime.fromisoformat(request.data['time'].replace('Z', ''))
            latest_status.save()

        # Parse the incoming time string as naive datetime
        try:
            new_time = datetime.fromisoformat(request.data['time'].replace('Z', ''))
        except (ValueError, KeyError):
            return Response(
                {"error": "Invalid time format. Expected ISO format (e.g. 2025-03-28T12:00:00)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if latest_status and latest_status.end_time > new_time:
            return Response(
                {"error": "New status time must be after the latest status end time."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update request data with naive datetime
        request.data['time'] = new_time
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def list(self, request):
        # Get statuses for the current day
        today = datetime.now().date()
        queryset = self.queryset.filter(
            time__date=today
        ).order_by('time')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)