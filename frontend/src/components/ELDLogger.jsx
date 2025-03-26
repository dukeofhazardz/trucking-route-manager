import React, { useState, useEffect, useRef } from "react";
import * as d3 from "d3";
import * as Plot from "@observablehq/plot";
import axios from "axios";
import "./ELDLogger.css";

const BASE_URL = "http://localhost:8000";

const ELDStatusLogger = () => {
  const plotRef = useRef(null);
  const totalsRef = useRef(null);
  const [data, setData] = useState([]); // Store ELD log data
  const [newStatus, setNewStatus] = useState("Off Duty"); // For status update
  const [selectedTime, setSelectedTime] = useState(
    new Date().toISOString().slice(0, 16)
  );

  const statusChoices = {
    sleeper_berth: "Sleeper Berth",
    driving: "Driving",
    on_duty: "On Duty",
    off_duty: "Off Duty",
  };

  const statusChoicesReverse = {
    "Sleeper Berth": "sleeper_berth",
    Driving: "driving",
    "On Duty": "on_duty",
    "Off Duty": "off_duty",
  };

  const fetchData = async () => {
    try {
      const response = await axios.get(`${BASE_URL}/api/status/`);
      const resolvedData = resolveData(response.data);
      setData(resolvedData);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (!plotRef.current) return;

    const domain = ["Off Duty", "Sleeper Berth", "Driving", "On Duty"];

    const now = new Date();
    const startOfDay = new Date(
      Date.UTC(
        now.getUTCFullYear(),
        now.getUTCMonth(),
        now.getUTCDate(),
        0,
        0,
        0
      )
    );
    const endOfDay = new Date(
      Date.UTC(
        now.getUTCFullYear(),
        now.getUTCMonth(),
        now.getUTCDate() + 1,
        0,
        0,
        0
      )
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
        domain: [startOfDay, endOfDay], // Force UTC
        axis: "top",
        ticks: d3.timeHour.every(1),
        tickFormat: (d) => {
          const hour = d3.utcFormat("%H")(d);
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
        Plot.line(data, {
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

  const handleStatusUpdate = async (event) => {
    event.preventDefault();
    try {
      const response = await axios.post(`${BASE_URL}/api/status/`, {
        status: statusChoicesReverse[newStatus],
        time: new Date(selectedTime).toISOString(), // Use user-selected time
        trip: 1, // Default
      });

      if (response.status === 200) {
        await fetchData();
      }
    } catch (error) {
      console.error("Error updating status:", error);
    }
  };

  const resolveData = (data) => {
    if (!Array.isArray(data)) return [];

    return data.map((d) => ({
      ...d,
      time: new Date(d.time).toISOString().slice(0, 16) + "Z",
      status: statusChoices[d.status],
    }));
  };

  return (
    <>
      <div className="eld-container">
        <div>
          <h2 className="eld-title">ELD Days of Service Logger</h2>
          <div ref={plotRef} />
        </div>
        <div ref={totalsRef} className="eld-totals" />
      </div>
      <form onSubmit={handleStatusUpdate} className="eld-form">
        <label>
          Update Status:
          <select
            value={newStatus}
            onChange={(e) => setNewStatus(e.target.value)}
          >
            <option value="Off Duty">Off Duty</option>
            <option value="Sleeper Berth">Sleeper Berth</option>
            <option value="Driving">Driving</option>
            <option value="On Duty">On Duty</option>
          </select>
        </label>
        <label>
          Select Time:
          <input
            type="datetime-local"
            value={selectedTime}
            onChange={(e) => setSelectedTime(e.target.value)}
            required
          />
        </label>

        <button type="submit">Submit</button>
      </form>
    </>
  );
};

export default ELDStatusLogger;
