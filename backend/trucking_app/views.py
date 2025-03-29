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
            total_distance_km = route_data['routes'][0]['distance'] / 1000,
            total_duration_hours = route_data['routes'][0]['duration'] / 3600,

            # New trip
            trip_data = {
                "start_latitude": current_location[0],
                "start_longitude": current_location[1],
                "destination_latitude": dropoff_location[0],
                "destination_longitude": dropoff_location[1],
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(seconds=route_data['routes'][0]['duration']),
                "total_distance_km": total_distance_km,
                "total_duration_hours": total_duration_hours,
            }
            serializer = self.get_serializer(data=trip_data)
            serializer.is_valid(raise_exception=True)
            trip = serializer.save()

            return Response({
                'route_details': route_data,
                'total_distance_km': total_distance_km,
                'total_duration_hours': total_duration_hours,
                'waypoints': route_data['waypoints']
            })
        
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
            
        # Get today's date and check driving hours
        today = datetime.now().date()
        driving_hours = StatusLog.objects.filter(
            time__date=today,
            status='driving'
        ).aggregate(Sum('duration'))['duration__sum'] or timedelta()
        if driving_hours.total_seconds() / 3600 > 11:
            return Response(
                {"error": "Exceeded maximum driving hours for today."},
                status=status.HTTP_400_BAD_REQUEST
            )

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


class DailyLogViewSet(viewsets.ModelViewSet):
    queryset = DailyLog.objects.all()
    serializer_class = DailyLogSerializer

    def create(self, request):
        # Validate daily log data
        try:
            trips_today = Trip.objects.filter(
                start_time__date=datetime.now().date()
            ).exists()
            trip_ids = [trip.id for trip in trips_today]
            if not trip_ids:
                return Response(
                    {"error": "No trips found for today."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = request.data.copy()
            data['trip'] = trip_ids
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def list(self, request):
        # Get daily logs for the current day
        today = datetime.now().date()
        queryset = self.queryset.filter(
            date=today
        ).order_by('date')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def generate_daily_log(self, request):
        # Generate daily log for the current day
        today = datetime.now().date()
        daily_logs = self.queryset.filter(
            date=today
        ).first()
        
        if not daily_logs.exists():
            return Response(
                {"error": "No daily logs found for today."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(daily_logs, many=True)
        serializer['name'] = 'Daily Log for ' + str(today)
        serializer['vehicle_license_number']  = 'ABC1234'
        serializer['from'] = 'Location A'
        serializer['to'] = 'Location B'
        serializer['name_of_carriers'] = 'Property carrier'
        serializer['main_office_address'] = '123 Main St, City, State, Zip'
        serializer['home_terminal_address'] = '456 Elm St, City, State, Zip'
        serializer['driver_name'] = 'John Doe'
        return Response(serializer.data)