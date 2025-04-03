import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Dashboard.css';

const BASE_URL = "https://gleaming-compassion-production.up.railway.app";

const Dashboard = () => {
  const [stats, setStats] = useState({
    cycleUsed: 0,
    cycleRemaining: 70,
    drivingHours: 0,
    onDutyHours: 0,
    sleeperBerth: 0,
    offDuty: 0,
    totalMiles: 0,
    totalMileage: 0,
    isLoading: true
  });
  const [tripId, setTripId] = useState(localStorage.getItem("TripID"));

  useEffect(() => {
    const createDailyLog = async () => {
      try {
        // First check if a daily log already exists for today
        const today = new Date().toISOString().split('T')[0];
        const response = await axios.get(`${BASE_URL}/api/daily-logs/?date=${today}`);
        
        if (response.data.length === 0) {
          // Create new daily log if none exists
          await axios.post(`${BASE_URL}/api/daily-logs/`, {
            date: today
          });
        }
        
        // Then fetch the current stats
        fetchDashboardData();
      } catch (error) {
        console.error("Error creating/fetching daily log:", error);
        setStats(prev => ({ ...prev, isLoading: false }));
      }
    };

    const fetchDashboardData = async () => {
      try {
        const today = new Date().toISOString().split('T')[0];
        const [dailyLogRes, tripsRes] = await Promise.all([
          axios.get(`${BASE_URL}/api/daily-logs/?date=${today}`),
          axios.get(`${BASE_URL}/api/trips/`)
        ]);

        const dailyLog = dailyLogRes.data.length > 0 ? dailyLogRes.data[0] : null;
        const trips = tripsRes.data;

        if (dailyLog) {
          setStats({
            cycleUsed: dailyLog.driving_hours + dailyLog.on_duty_hours,
            cycleRemaining: Math.max(70 - (dailyLog.driving_hours + dailyLog.on_duty_hours), 0),
            drivingHours: dailyLog.driving_hours,
            onDutyHours: dailyLog.on_duty_hours,
            sleeperBerth: dailyLog.sleeper_berth_hours,
            offDuty: dailyLog.off_duty_hours,
            totalMiles: dailyLog.total_miles,
            totalMileage: dailyLog.cumulative_mileage,
            isLoading: false
          });
        } else {
          // Set default values if no daily log exists
          setStats(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        setStats(prev => ({ ...prev, isLoading: false }));
      }
    };

    createDailyLog();
  }, [tripId]);

  return (
    <div className="dashboard">
      <h1 className="dashboard-title">Driver Dashboard</h1>
      
      <div className="stats-grid">
        {/* Cycle Stats - Always shown */}
        <div className="stat-card cycle-card">
          <h3>Cycle Status</h3>
          {stats.isLoading ? (
            <div className="loading-placeholder">Loading...</div>
          ) : (
            <>
              <div className="cycle-progress">
                <div 
                  className="progress-bar"
                  style={{ width: `${(stats.cycleUsed / 70) * 100}%` }}
                ></div>
              </div>
              <div className="cycle-numbers">
                <span className="used">{stats.cycleUsed.toFixed(1)} hrs</span>
                <span className="remaining">{stats.cycleRemaining.toFixed(1)} hrs remaining</span>
              </div>
            </>
          )}
        </div>

        {/* Hours Breakdown - Always shown */}
        <div className="stat-card hours-card">
          <h3>Hours Breakdown</h3>
          {stats.isLoading ? (
            <div className="loading-placeholder">Loading...</div>
          ) : (
            <div className="hours-grid">
              {[
                { label: 'Driving', value: stats.drivingHours },
                { label: 'On Duty', value: stats.onDutyHours },
                { label: 'Sleeper Berth', value: stats.sleeperBerth },
                { label: 'Off Duty', value: stats.offDuty }
              ].map((item, index) => (
                <div key={index} className="hour-item">
                  <span className="hour-label">{item.label}</span>
                  <span className="hour-value">{item.value.toFixed(1)} hrs</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Mileage Stats - Always shown */}
        <div className="stat-card mileage-card">
          <h3>Mileage</h3>
          {stats.isLoading ? (
            <div className="loading-placeholder">Loading...</div>
          ) : (
            <>
              <div className="mileage-item">
                <span className="mileage-label">Current Trip</span>
                <span className="mileage-value">{stats.totalMiles.toLocaleString()} mi</span>
              </div>
              <div className="mileage-item">
                <span className="mileage-label">Total Mileage</span>
                <span className="mileage-value">{stats.totalMileage.toLocaleString()} mi</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;