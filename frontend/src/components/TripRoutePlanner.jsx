import React, { useState, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import axios from "axios";
import "leaflet/dist/leaflet.css";
import currentIconSrc from "../assets/map-pin-icon.svg";
import pickupIconSrc from "../assets/map-pin-icon.svg";
import dropoffIconSrc from "../assets/map-pin-icon.svg";
import "./TripRoutePlanner.css";

const BASE_URL = "http://localhost:8000";

const createCustomIcon = (iconSrc) =>
  new L.Icon({
    iconUrl: iconSrc,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });

const TripRoutePlanner = () => {
  const [locationType, setLocationType] = useState("current");
  const [locations, setLocations] = useState({
    current: null,
    pickup: null,
    dropoff: null,
  });
  const [routeCoordinates, setRouteCoordinates] = useState([]);
  const [routeDetails, setRouteDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const mapRef = useRef(null);

  const LocationSetter = () => {
    useMapEvents({
      click(e) {
        const { lat, lng } = e.latlng;
        setLocations((prev) => ({
          ...prev,
          [locationType]: { latitude: lat, longitude: lng },
        }));
      },
    });
    return null;
  };

  const calculateRoute = async () => {
    setLoading(true);
    try {
      const response = await axios.post(
        `${BASE_URL}/api/trips/calculate_route/`,
        {
          current_location: locations.current
            ? [locations.current.latitude, locations.current.longitude]
            : null,
          pickup_location: locations.pickup
            ? [locations.pickup.latitude, locations.pickup.longitude]
            : null,
          dropoff_location: locations.dropoff
            ? [locations.dropoff.latitude, locations.dropoff.longitude]
            : null,
        }
      );

      const routeData = response.data;
      setRouteDetails(routeData);
      const coordinates =
        routeData.route_details.routes[0].geometry.coordinates.map((coord) => [
          coord[1],
          coord[0],
        ]);
      setRouteCoordinates(coordinates);

      if (mapRef.current) {
        const map = mapRef.current;
        map.fitBounds(coordinates);
      }
    } catch (error) {
      console.error("Route calculation error:", error);
    }
    setLoading(false);
  };

  return (
    <div className="trip-route-planner">
      <div className="planner-container">
        <div className="input-section">
          <h2>Trip Route Planner</h2>
          <div className="selection-buttons">
            {["current", "pickup", "dropoff"].map((type) => (
              <button
                key={type}
                className={`location-btn ${
                  locationType === type ? "active" : ""
                }`}
                onClick={() => setLocationType(type)}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </button>
            ))}
          </div>
          <button
            className="calculate-route-btn"
            onClick={calculateRoute}
            disabled={loading}
          >
            {loading ? <span className="spinner"></span> : "Calculate Route"}
          </button>

          {routeDetails && (
            <div className="route-details">
              <h3>Route Information</h3>
              <div className="detail-grid">
                <div className="detail-item">
                  <p>Total Distance</p>
                  <strong>
                    {routeDetails.total_distance_km.toFixed(2)} km
                  </strong>
                </div>
                <div className="detail-item">
                  <p>Estimated Duration</p>
                  <strong>
                    {routeDetails.total_duration_hours.toFixed(2)} hrs
                  </strong>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="map-section">
          <MapContainer
            ref={mapRef}
            center={[39.8283, -98.5795]}
            zoom={4}
            style={{ height: "400px", width: "100%" }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />
            <LocationSetter />

            {Object.entries(locations).map(([key, value]) =>
              value ? (
                <Marker
                  key={key}
                  position={[value.latitude, value.longitude]}
                  icon={createCustomIcon(currentIconSrc)}
                >
                  <Popup>
                    {key.charAt(0).toUpperCase() + key.slice(1)} Location
                  </Popup>
                </Marker>
              ) : null
            )}

            {routeCoordinates.length > 0 && (
              <Polyline
                positions={routeCoordinates}
                color="blue"
                weight={5}
                opacity={0.7}
              />
            )}
          </MapContainer>

          <div className="location-details">
            {["current", "pickup", "dropoff"].map((type) => (
              <div key={type} className="location-detail">
                <span>{type.charAt(0).toUpperCase() + type.slice(1)}: </span>
                {locations[type] ? (
                  <strong>
                    {locations[type].latitude.toFixed(4)},{" "}
                    {locations[type].longitude.toFixed(4)}
                  </strong>
                ) : (
                  <em>Not Set</em>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TripRoutePlanner;
