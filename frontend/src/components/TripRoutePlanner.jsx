import React, { useState, useRef, useEffect } from "react";
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
import "./TripRoutePlanner.css";

const BASE_URL = "http://localhost:8000";

// Create custom icons for each location type
const createCustomIcon = (iconSrc, iconColor = null) => {
  const icon = new L.Icon({
    iconUrl: iconSrc,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });

  if (iconColor) {
    icon.options.className = `custom-icon-${iconColor}`;
  }

  return icon;
};

const locationIcons = {
  current: createCustomIcon(currentIconSrc),
  pickup: createCustomIcon(currentIconSrc, "green"),
  dropoff: createCustomIcon(currentIconSrc, "blue"),
};

const TripRoutePlanner = () => {
  const [locationType, setLocationType] = useState("current");
  const [locations, setLocations] = useState({
    current: null,
    pickup: null,
    dropoff: null,
  });
  const [calculatedRoute, setCalculatedRoute] = useState({
    waypoints: [],
    coordinates: [],
    details: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
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
    const selectedLocations = Object.values(locations).filter(Boolean);
    if (selectedLocations.length < 2) {
      setError("Please set at least two locations to calculate a route");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.post(
        `${BASE_URL}/api/trips/calculate_route/`,
        {
          current_location: locations.current
            ? [locations.current.longitude, locations.current.latitude]
            : null,
          pickup_location: locations.pickup
            ? [locations.pickup.longitude, locations.pickup.latitude]
            : null,
          dropoff_location: locations.dropoff
            ? [locations.dropoff.longitude, locations.dropoff.latitude]
            : null,
        }
      );

      const routeData = response.data;
      if (routeData.error) {
        setError(routeData.error);
        return;
      }
      localStorage.setItem("TripID", routeData.trip_id)

      // Extract coordinates from GeoJSON response
      const coordinates =
        routeData.route_geojson?.features?.[0]?.geometry?.coordinates?.map(
          (coord) => [coord[1], coord[0]] // Convert [lon, lat] to [lat, lon]
        ) || [];

      // Create waypoints with proper icons
      const waypoints = [
        locations.current && {
          id: "current",
          name: "Current Location",
          position: [locations.current.latitude, locations.current.longitude],
          type: "current",
        },
        locations.pickup && {
          id: "pickup",
          name: "Pickup Location",
          position: [locations.pickup.latitude, locations.pickup.longitude],
          type: "pickup",
        },
        locations.dropoff && {
          id: "dropoff",
          name: "Dropoff Location",
          position: [locations.dropoff.latitude, locations.dropoff.longitude],
          type: "dropoff",
        },
        ...(routeData.rest_stops?.map((stop, index) => ({
          id: `rest_${index}`,
          name: `Rest Stop ${index + 1}`,
          position: [stop.location[1], stop.location[0]],
          type: "rest",
          duration: stop.duration,
          distance: stop.distance,
        })) || []),
      ].filter(Boolean);

      setCalculatedRoute({
        waypoints,
        coordinates,
        details: routeData,
      });

      // Fit map to route bounds
      if (mapRef.current && coordinates.length > 0) {
        const map = mapRef.current;
        const bounds = L.latLngBounds(coordinates);
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    } catch (error) {
      console.error("Route calculation error:", error);
      setError(error.response?.data?.error || "Failed to calculate route");
    } finally {
      setLoading(false);
    }
  };

  // Reset calculated route when locations change
  useEffect(() => {
    setCalculatedRoute({
      waypoints: [],
      coordinates: [],
      details: null,
    });
  }, [locations]);

  return (
    <div className="trip-route-planner">
      <div className="planner-container">
        <div className="input-section">
          <h1 className="title">Trip Route Planner</h1>
          {error && <div className="error-message">{error}</div>}

          <div className="location-selection">
            <p>Select Locations</p>
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

            <div className="location-coordinates">
              {Object.entries(locations).map(([type, loc]) => (
                <div key={type} className="coordinate-display">
                  <span className="location-label">
                    {type.charAt(0).toUpperCase() + type.slice(1)}:
                  </span>
                  {loc ? (
                    <span className="coordinates">
                      {loc.latitude.toFixed(6)}, {loc.longitude.toFixed(6)}
                    </span>
                  ) : (
                    <span className="not-set">Not set</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          <button
            className="calculate-route-btn"
            onClick={calculateRoute}
            disabled={
              loading || Object.values(locations).filter(Boolean).length < 2
            }
          >
            {loading ? <span className="spinner"></span> : "Calculate Route"}
          </button>

          <div className="route-details">
            <h3>Route Information</h3>
            <div className="detail-grid">
              <div className="detail-item">
                <p>Total Distance</p>
                <strong>
                  {calculatedRoute.details?.total_distance_km
                    ? `${calculatedRoute.details.total_distance_km.toFixed(
                        2
                      )} km`
                    : "--"}
                </strong>
              </div>
              <div className="detail-item">
                <p>Estimated Duration</p>
                <strong>
                  {calculatedRoute.details?.total_duration_hours
                    ? `${calculatedRoute.details.total_duration_hours.toFixed(
                        2
                      )} hrs`
                    : "--"}
                </strong>
              </div>
            </div>

            {calculatedRoute.details?.rest_stops?.length > 0 && (
              <div className="rest-stops">
                <h4>Recommended Rest Stops</h4>
                <ul>
                  {calculatedRoute.details.rest_stops.map((stop, index) => (
                    <li key={index}>
                      Stop {index + 1}: {(stop.duration / 3600).toFixed(2)} hrs
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="map-section">
          <MapContainer
            ref={mapRef}
            center={[39.8283, -98.5795]}
            zoom={4}
            style={{ height: "100%", width: "100%" }}
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution="&copy; OpenStreetMap contributors"
            />
            <LocationSetter />

            {/* Show user-selected locations before calculation */}
            {!calculatedRoute.details &&
              Object.entries(locations).map(
                ([type, loc]) =>
                  loc && (
                    <Marker
                      key={`selected-${type}`}
                      position={[loc.latitude, loc.longitude]}
                      icon={locationIcons[type]}
                    >
                      <Popup>
                        <strong>
                          {type.charAt(0).toUpperCase() + type.slice(1)}{" "}
                          Location
                        </strong>
                        <div>Lat: {loc.latitude.toFixed(6)}</div>
                        <div>Lon: {loc.longitude.toFixed(6)}</div>
                      </Popup>
                    </Marker>
                  )
              )}

            {/* Show calculated route and waypoints */}
            {calculatedRoute.details && (
              <>
                {/* Route line */}
                {calculatedRoute.coordinates.length > 1 && (
                  <Polyline
                    positions={calculatedRoute.coordinates}
                    color="#4285F4"
                    weight={4}
                    opacity={0.8}
                  />
                )}

                {/* Waypoints */}
                {calculatedRoute.waypoints.map((wp) => (
                  <Marker
                    key={wp.id}
                    position={wp.position}
                    icon={
                      wp.type === "rest"
                        ? createCustomIcon(currentIconSrc, "orange")
                        : locationIcons[wp.type]
                    }
                  >
                    <Popup>
                      <strong>{wp.name}</strong>
                      <div>Lat: {wp.position[0].toFixed(6)}</div>
                      <div>Lon: {wp.position[1].toFixed(6)}</div>
                      {wp.duration && (
                        <div>
                          Duration: {(wp.duration / 3600).toFixed(2)} hrs
                        </div>
                      )}
                      {wp.distance && (
                        <div>
                          Distance: {(wp.distance / 1000).toFixed(2)} km
                        </div>
                      )}
                    </Popup>
                  </Marker>
                ))}
              </>
            )}
          </MapContainer>
        </div>
      </div>
    </div>
  );
};

export default TripRoutePlanner;
