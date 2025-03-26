import React, { useState, useEffect, useRef } from "react";
import * as d3 from "d3";
import * as Plot from "@observablehq/plot";
import axios from "axios";

const BASE_URL = "http://localhost:8000";
const ELDStatusLogger = () => {
  const plotRef = useRef(null);

  useEffect(() => {
    if (!plotRef.current) return;

    const data = [
      { time: "2021-07-20T05:00Z", status: "Off Duty" },
      { time: "2021-07-20T06:12Z", status: "On Duty" },
      { time: "2021-07-20T06:53Z", status: "Driving" },
      { time: "2021-07-20T07:00:10Z", status: "On Duty" },
      { time: "2021-07-20T08:08Z", status: "Driving" },
      { time: "2021-07-20T09:00Z", status: "On Duty" },
      { time: "2021-07-20T09:30Z", status: "Driving" },
      { time: "2021-07-20T09:45Z", status: "On Duty" },
      { time: "2021-07-20T10:15Z", status: "Driving" },
      { time: "2021-07-20T10:30Z", status: "On Duty" },
      { time: "2021-07-20T14:14Z", status: "Driving" },
      { time: "2021-07-20T15:00Z", status: "Off Duty" },
      { time: "2021-07-20T17:00Z", status: "Off Duty" },
    ];
    const domain = ["Off Duty", "Sleeper Berth", "Driving", "On Duty"];

    const thirty = d3.timeDays(new Date(2021, 6, 20), new Date(2021, 6, 21));
    const fifteen = d3.timeMinutes(new Date(2021, 6, 20), new Date(2021, 6, 21), 15);
    const dayExtent = d3.extent(data.map((d) => new Date(d.time)));

    const plot = Plot.plot({
      marginLeft: 60,
      marginRight: 100,
      x: {
        type: "time",
        axis: "top",
        ticks: 25,
        tickFormat: "%H",
        grid: true,
        nice: true,
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

        // compute the totals
        Plot.text(
          d3.pairs(data),
          Plot.groupY(
            {
              text: (d) => new Date(d3.sum(d) + 30000).toISOString().slice(11, 16)
            },
            {
              y: ([a]) => a.status,
              text: ([a, b]) => b.time - a.time,
              x: dayExtent[1],
              textAnchor: "start",
              dx: 10
            }
          )
        )
      ],
      marginRight: 40,
      width: 800,
      height: 150,
    });

    // ✅ Clear any previous plot and append new one
    plotRef.current.innerHTML = "";
    plotRef.current.append(plot);

    // ✅ Cleanup function to remove plot when component unmounts
    return () => {
      plot.remove();
    };
  }, []);

  return (
    <>
      <div className="p-4 bg-white shadow rounded">
        <h2 className="text-xl mb-4">ELD Days of Service Logger</h2>
        <div ref={plotRef}></div>
      </div>
    </>
  );
};

export default ELDStatusLogger;
