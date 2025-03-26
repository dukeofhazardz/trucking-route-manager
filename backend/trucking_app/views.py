from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import requests  # For making HTTP requests to OSRM
from .models import Trip, DailyLog, Status
from .serializers import TripSerializer, DailyLogSerializer, StatusSerializer
from django.utils import timezone


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    def create(self, request):
        # Prepare trip data from request
        trip_data = {
            'driver_name': request.data.get('driver_name'),
            'current_location': request.data.get('current_location'),
            'pickup_location': request.data.get('pickup_location'),
            'dropoff_location': request.data.get('dropoff_location'),
            'current_cycle_hours': request.data.get('current_cycle_hours', 0),
            'total_driving_hours': request.data.get('total_driving_hours', 0),
            'cycle_type': request.data.get('cycle_type', '70_8'),
            'estimated_arrival': request.data.get('estimated_arrival')
        }
        
        # Validate and save the trip
        serializer = self.get_serializer(data=trip_data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        
        # Optionally, create an initial status for the trip
        Status.objects.create(
            trip=trip,
            status='off_duty',  # Default initial status
            timestamp=timezone.now()
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['POST'])
    def calculate_route(self, request):
        current_location = request.data.get('current_location')
        pickup_location = request.data.get('pickup_location')
        dropoff_location = request.data.get('dropoff_location')
        
        # OSRM expects coordinates in format "longitude,latitude"
        # Assuming locations are provided as [lat, lon]
        def format_coords(location):
            return f"{location[1]},{location[0]}"
        
        # Create waypoints string for OSRM
        waypoints = [
            format_coords(current_location),
            format_coords(pickup_location),
            format_coords(dropoff_location)
        ]
        
        # Call OSRM service
        osrm_url = "http://router.project-osrm.org/route/v1/driving/"
        coordinates = ";".join(waypoints)
        response = requests.get(f"{osrm_url}{coordinates}?overview=full&steps=true")
        
        if response.status_code != 200:
            return Response(
                {"error": "Failed to calculate route"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        route_data = response.json()
        
        # Extract distance (in meters) and duration (in seconds)
        total_distance = route_data['routes'][0]['distance']
        total_duration = route_data['routes'][0]['duration']
        
        return Response({
            'route_details': route_data,
            'total_distance_km': total_distance / 1000,
            'total_duration_hours': total_duration / 3600,
            'waypoints': waypoints
        })
    
    @action(detail=True, methods=['GET'])
    def generate_logs(self, request, pk=None):
        trip = self.get_object()
        
        # Logic to generate daily logs based on route and hours
        logs = []
        for day in range(1, 3):  # Generate logs for first 3 days
            log = DailyLog.objects.create(
                trip=trip,
                driving_hours=11,  # Max allowed driving hours per day
                on_duty_hours=14,  # Max on-duty hours
                off_duty_hours=10  # Remaining hours
            )
            logs.append(DailyLogSerializer(log).data)
        
        return Response(logs)

class DailyLogViewSet(viewsets.ModelViewSet):
    queryset = DailyLog.objects.all()
    serializer_class = DailyLogSerializer


class DriverStatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = StatusSerializer
    
    def list(self, request):
        # Get statuses for the current day
        today = timezone.now().date()
        queryset = self.queryset.filter(
            timestamp__date=today
        ).order_by('timestamp')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        # Validate and save new status
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure status doesn't overlap with existing statuses
        self.validate_status_time(serializer.validated_data)
        
        self.perform_create(serializer)
        return Response(serializer.data, status=201)
    
    def validate_status_time(self, validated_data):
        # Custom validation logic for status times
        existing_statuses = self.queryset.filter(
            timestamp__date=validated_data['timestamp'].date()
        )