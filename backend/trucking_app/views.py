from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from datetime import datetime, timedelta
import requests
import os
from .models import Trip, DailyLog, StatusLog
from .serializers import (
    TripSerializer, 
    DailyLogSerializer, 
    StatusLogSerializer
)
import openrouteservice as ors
from openrouteservice.directions import directions
import folium


OPENROUTESERVICE_API_KEY = os.getenv('OPENROUTESERVICE_API_KEY')

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer


    @action(detail=False, methods=['POST'])
    def calculate_route(self, request):
        try:
            # Extract coordinates
            current_location = request.data.get('current_location')  # [lon, lat]
            pickup_location = request.data.get('pickup_location')    # [lon, lat]
            dropoff_location = request.data.get('dropoff_location')  # [lon, lat]
            
            # Validate coordinates
            if not all([current_location, pickup_location, dropoff_location]):
                return Response(
                    {"error": "Missing location coordinates"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initialize ORS client
            ors_client = ors.Client(key=OPENROUTESERVICE_API_KEY)
            
            # Define waypoints in ORS format (lon, lat)
            coordinates = [
                current_location,
                pickup_location,
                dropoff_location
            ]
            
            # Calculate route with driving profile (remove optimize_waypoints)
            route = directions(
                client=ors_client,
                coordinates=coordinates,
                profile='driving-car',
                format='geojson',
                instructions=True,
            )
            
            # Extract route information
            total_distance = route['features'][0]['properties']['summary']['distance'] / 1000  # km
            total_duration = route['features'][0]['properties']['summary']['duration'] / 3600  # hours
            
            # Create Folium map centered on start point
            m = folium.Map(
                location=[current_location[1], current_location[0]],
                zoom_start=12,
                tiles='cartodbpositron'
            )
            
            # Add route to map
            folium.GeoJson(
                route,
                name='Route',
                style_function=lambda x: {
                    'color': '#4285F4',
                    'weight': 5,
                    'opacity': 0.8
                }
            ).add_to(m)
            
            # Add markers for waypoints
            waypoint_names = ['Current Location', 'Pickup', 'Dropoff']
            for i, (coord, name) in enumerate(zip(coordinates, waypoint_names)):
                folium.Marker(
                    location=[coord[1], coord[0]],
                    popup=f"<b>{name}</b>",
                    icon=folium.Icon(
                        color='red' if i == 0 else 'green' if i == 1 else 'blue',
                        icon='truck' if i == 0 else 'industry' if i == 1 else 'flag'
                    )
                ).add_to(m)
            
            # Calculate rest stops (every 4 hours of driving)
            rest_stops = []
            if total_duration > 4:
                # Get detailed steps for the full route
                for step in route['features'][0]['properties']['segments'][0]['steps']:
                    if 'duration' in step and 'distance' in step:
                        rest_stops.append({
                            'location': step['way_points'][-1],
                            'duration': step['duration'],
                            'distance': step['distance']
                        })
                
                # Filter to get stops approximately every 4 hours
                filtered_rest_stops = []
                cumulative_time = 0
                rest_threshold = 4 * 3600  # 4 hours in seconds
                
                for stop in rest_stops:
                    cumulative_time += stop['duration']
                    if cumulative_time >= rest_threshold:
                        filtered_rest_stops.append(stop)
                        cumulative_time = 0
                
                rest_stops = filtered_rest_stops
            
            # Save map to HTML string
            map_html = m._repr_html_()
            
            # Create new trip record
            trip_data = {
                "start_latitude": current_location[1],
                "start_longitude": current_location[0],
                "destination_latitude": dropoff_location[1],
                "destination_longitude": dropoff_location[0],
                "start_time": datetime.now(),
                "end_time": datetime.now() + timedelta(seconds=total_duration*3600),
                "total_distance_km": total_distance,
                "total_duration_hours": total_duration,
            }
            serializer = self.get_serializer(data=trip_data)
            serializer.is_valid(raise_exception=True)
            trip = serializer.save()
            
            return Response({
                'route_geojson': route,
                'total_distance_km': total_distance,
                'total_duration_hours': total_duration,
                'waypoints': coordinates,
                'rest_stops': rest_stops,
                'map_html': map_html,
                'trip_id': trip.id
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