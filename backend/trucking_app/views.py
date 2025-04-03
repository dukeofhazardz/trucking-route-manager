from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db.models import Sum
from datetime import datetime, timedelta
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
import geopy.distance


OPENROUTESERVICE_API_KEY = os.getenv('OPENROUTESERVICE_API_KEY')

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer


    @action(detail=False, methods=['POST'])
    def calculate_route(self, request):
        try:
            current_location = request.data.get('current_location')  # [lon, lat]
            pickup_location = request.data.get('pickup_location')    # [lon, lat]
            dropoff_location = request.data.get('dropoff_location')  # [lon, lat]

            if not all([current_location, pickup_location, dropoff_location]):
                return Response(
                    {"error": "Missing location coordinates"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            ors_client = ors.Client(key=OPENROUTESERVICE_API_KEY)
            
            # Define waypoints in the ORS format (lon, lat)
            coordinates = [
                current_location,
                pickup_location,
                dropoff_location
            ]

            route = directions(
                client=ors_client,
                coordinates=coordinates,
                profile='driving-car',
                format='geojson',
                instructions=True,
            )

            total_distance = route['features'][0]['properties']['summary']['distance'] / 1000  # km
            total_duration = route['features'][0]['properties']['summary']['duration'] / 3600  # hours

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

            rest_stops = []
            if total_duration > 4:  # Only calculate rest stops for trips that is over 4 hours
                route_coordinates = route['features'][0]['geometry']['coordinates']
                
                # Get distance along route for each coordinate
                distances = []
                running_dist = 0
                prev_coord = None
                
                for coord in route_coordinates:
                    if prev_coord:
                        # This will calculate distance between consecutive points
                        point1 = (prev_coord[1], prev_coord[0])  # lat, lon
                        point2 = (coord[1], coord[0])  # lat, lon
                        segment_dist = geopy.distance.geodesic(point1, point2).kilometers
                        running_dist += segment_dist
                        distances.append(running_dist)
                    else:
                        distances.append(0)
                    prev_coord = coord
                
                # Calculate rest stop positions (every 4 hours of driving)
                avg_speed = total_distance / total_duration  # km/h
                distance_per_rest = 4 * avg_speed  # The distance covered in 4 hours
                
                # Find coordinates for rest stops
                next_rest_distance = distance_per_rest
                for i, distance in enumerate(distances):
                    if distance >= next_rest_distance:
                        rest_stops.append({
                            'location': route_coordinates[i],  # [lon, lat]
                            'distance_km': distance
                        })
                        next_rest_distance += distance_per_rest

                # Add rest stops to map
                for i, stop in enumerate(rest_stops):
                    folium.Marker(
                        location=[stop['location'][1], stop['location'][0]],  # [lat, lon]
                        popup=f"<b>Rest Stop {i+1}</b><br>Distance: {stop['distance_km']:.1f} km",
                        icon=folium.Icon(color='orange', icon='bed')
                    ).add_to(m)
            map_html = m._repr_html_()

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
        
        # Only check driving hours if this is a new driving status
        if request.data.get('status') == 'driving':
            today = datetime.now().date()
            driving_hours = StatusLog.objects.filter(
                time__date=today,
                status='driving'
            ).aggregate(total=Sum('duration'))['total'] or timedelta()
            
            if isinstance(driving_hours, timedelta):
                driving_hours = driving_hours.total_seconds() / 3600
            
            if driving_hours > 11:
                return Response(
                    {"error": "Exceeded maximum driving hours for today."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        request.data['time'] = new_time
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def list(self, request):
        today = datetime.now().date()
        queryset = self.queryset.filter(
            time__date=today
        ).order_by('time')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class DailyLogViewSet(viewsets.ModelViewSet):
    queryset = DailyLog.objects.all().order_by('-date')
    serializer_class = DailyLogSerializer

    def _calculate_hours(self, date, status):
        """Helper to calculate hours for a given status and date"""
        result = StatusLog.objects.filter(
            time__date=date,
            status=status
        ).aggregate(total=Sum('duration'))['total']
        return result.total_seconds() / 3600 if result else 0

    def _calculate_mileage(self, date):
        """Helper to calculate mileage data for a given date"""
        today_trips = Trip.objects.filter(start_time__date=date)
        total_miles = sum(
            trip.total_distance_km * 0.621371
            for trip in today_trips
        ) if today_trips.exists() else 0

        previous_log = DailyLog.objects.filter(
            date__lt=date
        ).order_by('-date').first()
        previous_mileage = previous_log.cumulative_mileage if previous_log else 0
        
        return {
            'total_miles': total_miles,
            'cumulative_mileage': previous_mileage + total_miles,
            'trips': today_trips
        }

    def _get_daily_log_data(self, date):
        """Generate complete daily log data for a given date"""
        mileage_data = self._calculate_mileage(date)
        
        return {
            "date": date,
            "driving_hours": self._calculate_hours(date, 'driving'),
            "on_duty_hours": self._calculate_hours(date, 'on_duty'),
            "off_duty_hours": self._calculate_hours(date, 'off_duty'),
            "sleeper_berth_hours": self._calculate_hours(date, 'sleeper_berth'),
            "total_miles": mileage_data['total_miles'],
            "cumulative_mileage": mileage_data['cumulative_mileage'],
            "trips": mileage_data['trips']
        }

    def get_queryset(self):
        """Optionally filter by date if provided in query params"""
        queryset = super().get_queryset()
        date_param = self.request.query_params.get('date', None)
        
        if date_param:
            try:
                date = datetime.strptime(date_param, '%Y-%m-%d').date()
                daily_log_data = self._get_daily_log_data(date)
                daily_log = queryset.filter(date=date).first()
                
                if daily_log:
                    for key, value in daily_log_data.items():
                        if key != 'trips':  # Handle trips separately
                            setattr(daily_log, key, value)
                    daily_log.trip.set(daily_log_data['trips'])
                    daily_log.save()
                    
            except ValueError:
                pass
                
        return queryset

    def create(self, request, *args, **kwargs):
        """Create a daily log with validation"""
        try:
            date = request.data.get('date', datetime.now().date())
            if isinstance(date, str):
                date = datetime.strptime(date, '%Y-%m-%d').date()

            daily_log_data = self._get_daily_log_data(date)
            
            # Remove trips from data before serialization
            trips = daily_log_data.pop('trips')
            
            serializer = self.get_serializer(data=daily_log_data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            # Associate trips after creation
            daily_log = serializer.instance
            daily_log.trip.set(trips)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['GET'])
    def generate_report(self, request, pk=None):
        """Generate a detailed daily log report"""
        today = datetime.now().date()
        
        try:
            daily_logs = DailyLog.objects.filter(date=today).order_by('-id')
            
            if daily_logs.exists():
                daily_log = daily_logs.first()
                created = False
            else:
                daily_log, created = DailyLog.objects.get_or_create(date=today)
            report_data = {
                'name': f'Daily Log for {daily_log.date}',
                'date': daily_log.date,
                'vehicle_license_number': 'ABC123',
                'from': 'N/A',
                'to': 'N/A',
                'name_of_carriers': 'Property Carrier',
                'main_office_address': '123 Main St, City, State, Zip',
                'home_terminal_address': '456 Elm St, City, State, Zip',
                'driver_name': 'John Doe',
                'driving_hours': daily_log.driving_hours,
                'on_duty_hours': daily_log.on_duty_hours,
                'off_duty_hours': daily_log.off_duty_hours,
                'sleeper_berth_hours': daily_log.sleeper_berth_hours,
                'total_miles': daily_log.total_miles,
                'cumulative_mileage': daily_log.cumulative_mileage,
                'trips': [{
                    'start_time': trip.start_time,
                    'end_time': trip.end_time,
                    'distance': trip.total_distance_km * 0.621371,  # Conversion to miles
                    'duration': trip.total_duration_hours
                } for trip in daily_log.trip.all()]
            }
            
            return Response(report_data)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to generate report: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )