from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime, timedelta
import requests

from .models import Driver, Vehicle, Trip, DailyLog, StatusLog
from .serializers import (
    DriverSerializer, 
    VehicleSerializer, 
    TripSerializer, 
    DailyLogSerializer, 
    StatusLogSerializer,
    StatusSerializer
)


class DriverViewSet(viewsets.ModelViewSet):
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    
    @action(detail=True, methods=['GET'])
    def trip_history(self, request, pk=None):
        driver = self.get_object()
        trips = Trip.objects.filter(driver=driver)
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['GET'])
    def current_status(self, request, pk=None):
        driver = self.get_object()
        current_status = StatusLog.objects.filter(
            driver=driver
        ).order_by('-start_time').first()
        
        if not current_status:
            return Response({"status": "No current status"})
        
        serializer = StatusLogSerializer(current_status)
        return Response(serializer.data)

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    
    @action(detail=True, methods=['GET'])
    def trip_history(self, request, pk=None):
        vehicle = self.get_object()
        trips = Trip.objects.filter(vehicle=vehicle)
        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    def create(self, request):
        # Validate and save the trip with associated data
        driver_id = request.data.get('driver')
        vehicle_id = request.data.get('vehicle')
        
        try:
            driver = Driver.objects.get(id=driver_id)
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except (Driver.DoesNotExist, Vehicle.DoesNotExist):
            return Response(
                {"error": "Invalid driver or vehicle"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trip = serializer.save()
        
        # Create initial status log
        StatusLog.objects.create(
            driver=driver,
            status='off_duty',
            start_time=timezone.now()
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
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
            
            return Response({
                'route_details': route_data,
                'total_distance_km': route_data['routes'][0]['distance'] / 1000,
                'total_duration_hours': route_data['routes'][0]['duration'] / 3600,
                'waypoints': waypoints
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
                driver=trip.driver,
                vehicle=trip.vehicle,
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
        driver_id = request.data.get('driver')
        status = request.data.get('status')
        
        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            return Response(
                {"error": "Invalid driver"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Close previous open status log
        open_status = StatusLog.objects.filter(
            driver=driver, 
            end_time=None
        ).first()
        
        if open_status:
            open_status.end_time = timezone.now()
            open_status.save()
        
        # Create new status log
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class StatusViewSet(viewsets.ModelViewSet):
    queryset = StatusLog.objects.all()
    serializer_class = StatusSerializer
    
    def list(self, request):
        # Get statuses for the current day
        today = timezone.now().date()
        queryset = self.queryset.filter(
            time__date=today
        ).order_by('time')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        # Validate status creation with 70-hour rule
        new_status = request.data.get("status")
        new_time = datetime.fromisoformat(
            request.data.get("time").replace("Z", "+00:00")
        )
        
        # Define 8-day period for hours calculation
        eight_days_ago = timezone.now() - timedelta(days=8)
        
        # Calculate total driving + on-duty hours in the last 8 days
        logs = StatusLog.objects.filter(time__gte=eight_days_ago)
        total_seconds = sum(
            (logs[i+1].time - logs[i].time).total_seconds()
            for i in range(len(logs) - 1)
            if logs[i].status in ["driving", "on_duty"]
        )
        
        total_hours = total_seconds / 3600
        
        # Reject status if 70-hour limit is reached
        if total_hours >= 70 and new_status in ["driving", "on_duty"]:
            return Response(
                {"error": "70-hour limit reached for the past 8 days."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Standard serializer validation and creation
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)