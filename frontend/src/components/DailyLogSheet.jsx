import React, { useState, useEffect, useRef } from "react";
import * as d3 from "d3";
import * as Plot from "@observablehq/plot";
import axios from "axios";
import "./DailyLogSheet.css";

const BASE_URL = "https://gleaming-compassion-production.up.railway.app";

const DailyLogSheet = () => {
  const plotRef = useRef(null);
  const totalsRef = useRef(null);
  const [data, setData] = useState([]);
  const [dailyLog, setDailyLog] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch status log data
  const fetchStatusData = async () => {
    try {
      const response = await axios.get(`${BASE_URL}/api/status-logs/`);
      const resolvedData = response.data.map((log) => ({
        ...log,
        time: new Date(log.time),
        status: formatStatus(log.status),
      }));
      setData(resolvedData);
    } catch (error) {
      console.error("Error fetching status logs:", error);
    }
  };

  // Fetch today's daily log
  const fetchDailyLog = async () => {
    try {
      const response = await axios.get(
        `${BASE_URL}/api/daily-logs/generate_report/`
      );
      setDailyLog(response.data);
    } catch (error) {
      console.error("Error fetching daily log:", error);
    } finally {
      setLoading(false);
    }
  };

  // Format status for display
  const formatStatus = (status) => {
    const statusMap = {
      sleeper_berth: "Sleeper Berth",
      driving: "Driving",
      on_duty: "On Duty",
      off_duty: "Off Duty",
    };
    return statusMap[status] || status;
  };

  // Initialize data fetching
  useEffect(() => {
    fetchStatusData();
    fetchDailyLog();
  }, []);

  // Render the ELD plot
  useEffect(() => {
    if (!plotRef.current) return;

    const domain = ["Off Duty", "Sleeper Berth", "Driving", "On Duty"];

    const cleanedData = data.map((d) => {
      // Force status to match domain (case-sensitive)
      const matchedStatus =
        domain.find((item) => item.toLowerCase() === d.status.toLowerCase()) ||
        domain[0]; // Fallback to "Off Duty"

      return {
        ...d,
        status: matchedStatus, // Use the exact domain string
      };
    });

    // Get the start of the local day
    const now = new Date();
    const startOfDay = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      0,
      0,
      0
    );

    // Get the end of the local day
    const endOfDay = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate() + 1,
      0,
      0,
      0
    );

    const thirty = d3.timeHours(startOfDay, endOfDay, 1); // Hourly markers
    const fifteen = d3.timeMinutes(startOfDay, endOfDay, 15); // 15-min markers

    const dayExtent = d3.extent(data.map((d) => new Date(d.time)));

    // Calculate time totals for each status
    const statusTotals = {};
    for (let i = 0; i < data.length - 1; i++) {
      const currentStatus = data[i].status;
      const nextTime = new Date(data[i + 1].time);
      const currentTime = new Date(data[i].time);
      const duration = nextTime - currentTime;

      statusTotals[currentStatus] =
        (statusTotals[currentStatus] || 0) + duration;
    }

    const plot = Plot.plot({
      marginLeft: 60,
      marginRight: 40,
      x: {
        type: "time",
        domain: [startOfDay, endOfDay],
        axis: "top",
        ticks: d3.timeHour.every(1),
        tickFormat: (d) => {
          const hour = d3.timeFormat("%H")(d);
          if (hour === "00") return "Midnight";
          if (hour === "12") return "Noon";
          return hour;
        },
        grid: true,
        nice: false,
      },
      y: { domain, tickSize: 0, label: null },
      marks: [
        Plot.frame(),
        // time ticks every 15 and 30 minutes
        Plot.tickX(
          thirty.flatMap((time) => domain.map((status) => ({ time, status }))),
          { x: "time", y: "status", strokeWidth: 0.25 }
        ),
        Plot.tickX(
          fifteen.flatMap((time) => domain.map((status) => ({ time, status }))),
          {
            x: "time",
            y: "status",
            strokeDasharray: [0, 5, 4],
            strokeWidth: 0.25,
          }
        ),
        // data line
        Plot.line(cleanedData, {
          x: "time",
          y: "status",
          curve: "step-after",
          stroke: "blue",
          strokeWidth: 2,
        }),
      ],
      width: 800,
      height: 150,
    });

    // Clear any previous plot and append new one
    plotRef.current.innerHTML = "";
    plotRef.current.append(plot);

    // Render totals externally
    if (totalsRef.current) {
      totalsRef.current.innerHTML = domain
        .map((status) => {
          const totalMs = statusTotals[status] || 0;
          const hours = Math.floor(totalMs / 3600000);
          const minutes = Math.floor((totalMs % 3600000) / 60000);
          return `${hours}h ${minutes}m`;
        })
        .join("<br>");
    }

    // Cleanup function to remove plot when component unmounts
    return () => {
      plot.remove();
    };
  }, [data]);

  if (loading) return <div>Loading log sheet...</div>;

  return (
    <div className="log-sheet">
      <h1 className="log-title">Driver's Daily Log</h1>

      <div className="log-header">
        <div className="log-date">
          <span>Date: {new Date().toLocaleDateString()}</span>
        </div>
        <div className="log-cycle-info">
          <span>Cycle: 70 Hours / 8 Days</span>
        </div>
      </div>

      <div className="log-origin">
        <p>Original: File at home terminal.</p>
        <p>Duplicate: Driver retains in his/her possession for 8 days.</p>
      </div>

      <div className="log-section">
        <div className="log-info">
          <h2>
            From: <span>{dailyLog?.from}</span>
          </h2>
          <h2>
            To: <span>{dailyLog?.to}</span>
          </h2>
        </div>
        <table className="log-table">
          <thead>
            <tr>
              <th>Total Miles Driving Today</th>
              <th>Total Mileage Today</th>
              <th>Name of Carriers or Centers</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{dailyLog?.total_miles?.toFixed(1) || "0.0"}</td>
              <td>{dailyLog?.cumulative_mileage?.toFixed(1) || "0.0"}</td>
              <td>{dailyLog?.name_of_carriers || "Property Carrier"}</td>
            </tr>
          </tbody>
          <thead>
            <tr>
              <th>
                Truck/Tractor and Trailer Numbers or License Plate[s]/State
                (show each unit)
              </th>
              <th>Main Office Address</th>
              <th>Home Terminal Address</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{dailyLog?.vehicle_license_number || "N/A"}</td>
              <td>{dailyLog?.main_office_address || "N/A"}</td>
              <td>{dailyLog?.home_terminal_address || "N/A"}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="log-section">
        <h2>ELD Status Graph</h2>
        <div className="logger">
          <div ref={plotRef} />
          <div ref={totalsRef} className="eld-totals" />
        </div>
      </div>

      <div className="log-section">
        <h2>Hours Breakdown</h2>
        <ul className="hours-list">
          <li>
            <strong>Driving:</strong>{" "}
            {dailyLog?.driving_hours?.toFixed(1) || "0.0"} hrs
          </li>
          <li>
            <strong>On Duty (not driving):</strong>{" "}
            {dailyLog?.on_duty_hours?.toFixed(1) || "0.0"} hrs
          </li>
          <li>
            <strong>Sleeper Berth:</strong>{" "}
            {dailyLog?.sleeper_berth_hours?.toFixed(1) || "0.0"} hrs
          </li>
          <li>
            <strong>Off Duty:</strong>{" "}
            {dailyLog?.off_duty_hours?.toFixed(1) || "0.0"} hrs
          </li>
        </ul>
      </div>

      <div className="log-section">
        <h2>Remarks</h2>
        <div className="remarks-box"></div>
      </div>

      <div className="log-section">
        <h2>Shipping Documents</h2>
        <p>
          <strong>DV1 on Marathon No. 84</strong>
        </p>
        <p>
          <strong>Shipper & Commodity:</strong>
          <br />
          Enter name of place you regarded and whose collected items work and
          where and where each change of duty occurred.
        </p>
        <p>Use time standard of former terminal.</p>
      </div>
    </div>
  );
};

export default DailyLogSheet;
