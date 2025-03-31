import React, { useState, useEffect, useRef } from "react";
import * as d3 from "d3";
import * as Plot from "@observablehq/plot";
import axios from "axios";
import "./ELDLogger.css";
import DailyLogSheet from "./DailyLogSheet";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

const BASE_URL = "http://localhost:8000";

const ELDStatusLogger = () => {
  const plotRef = useRef(null);
  const totalsRef = useRef(null);
  const [data, setData] = useState([]); // Store ELD log data
  const [newStatus, setNewStatus] = useState("Off Duty"); // For status update
  const [error, setError] = useState(null);
  const [showLogSheet, setShowLogSheet] = useState(false);
  const logSheetRef = useRef(null);
  const pdfRef = useRef(null);
  const [selectedTime, setSelectedTime] = useState(() => {
    const now = new Date();
    // Format as YYYY-MM-DDTHH:MM in local time
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");

    return `${year}-${month}-${day}T${hours}:${minutes}`;
  });

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
      const response = await axios.get(`${BASE_URL}/api/status-logs/`);
      const resolvedData = resolveData(response.data);
      setData(resolvedData);
      setError(null);
    } catch (error) {
      console.error("Error fetching data:", error);
      setError("Could not fetch status logs. Please try again.");
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

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

  const handleStatusUpdate = async (event) => {
    event.preventDefault();
    setError(null);
    try {
      // Format the time string to match local time without timezone conversion
      const localDate = selectedTime.replace("T", " ") + ":00";

      // Create optimistic update in the same format as server response
      const optimisticEntry = {
        status: statusChoicesReverse[newStatus],
        time: localDate,
      };

      // Optimistically update with resolved data
      setData((prevData) => [
        ...prevData,
        {
          ...optimisticEntry,
          status: newStatus, // Convert to display format
          time: new Date(localDate), // Convert to Date object
        },
      ]);

      const response = await axios.post(
        `${BASE_URL}/api/status-logs/`,
        optimisticEntry
      );
    } catch (error) {
      console.error("Error updating status:", error);
      setError("Failed to update status. Please try again.");
      fetchData();
    }
  };

  const resolveData = (data) => {
    if (!Array.isArray(data)) return [];

    return data.map((d) => {
      // Handle both server response format and optimistic update format
      const status =
        typeof d.status === "string"
          ? statusChoices[d.status] || d.status
          : d.status;

      return {
        ...d,
        time: new Date(d.time),
        status: status,
      };
    });
  };

  const handleGenerateLog = async () => {
    try {
      // Capture the log sheet as an image
      const canvas = await html2canvas(pdfRef.current);
      const imgData = canvas.toDataURL("image/png");

      // Create PDF
      const pdf = new jsPDF("p", "mm", "a4");
      const imgProps = pdf.getImageProperties(imgData);
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;

      pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
      pdf.save("daily-log.pdf");
    } catch (error) {
      console.error("Error generating PDF:", error);
    }
  };

  const toggleLogSheet = () => {
    setShowLogSheet(!showLogSheet);
  };

  return (
    <>
      <div className="eld-container">
        {error && <div className="error-message">{error}</div>}
        <h2 className="eld-title">ELD Status Logger</h2>
        <div className="logger">
          <div ref={plotRef} />
          <div ref={totalsRef} className="eld-totals" />
        </div>

        <div className="form-area">
          <form
            onSubmit={handleStatusUpdate}
            className="stat-card actions-card eld-form"
          >
            <label>
              Select Status:
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
              >
                <option value="Off Duty">Off Duty</option>
                <option value="Sleeper Berth">Sleeper Berth</option>
                <option value="On Duty">On Duty</option>
                <option value="Driving">Driving</option>
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
            <button type="submit">Update Status</button>
          </form>

          {/* Quick Actions */}
          <div className="stat-card actions-card">
            <h3>Quick Actions</h3>
            <button className="action-btn" onClick={handleGenerateLog}>
              Download Today's Log (PDF)
            </button>
            <button className="action-btn" onClick={toggleLogSheet}>
              {showLogSheet ? "Hide Today's Log" : "View Today's Log"}
            </button>
          </div>
        </div>
      </div>
      {showLogSheet && (
        <div ref={logSheetRef}>
          <DailyLogSheet />
        </div>
      )}
      {/* Hidden log sheet for PDF generation */}
      <div
        style={{ position: "absolute", left: "-9999px", top: 0 }}
        ref={pdfRef}
      >
        <DailyLogSheet />
      </div>
    </>
  );
};

export default ELDStatusLogger;
