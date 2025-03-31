import React from "react";
import "./NavBar.css";

const NavBar = () => {
  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };
  return (
    <nav className="navbar">
      <div className="navbar-content">
        <h1 className="logo">TRP</h1>
        <div className="nav-links">
          <button className="nav-link" onClick={() => scrollToSection("trip-planner")}>Trip</button>
          <button className="nav-link" onClick={() => scrollToSection("driver-dashboard")}>Dashboard</button>
          <button className="nav-link" onClick={() => scrollToSection("eld-logger")}>Logger</button>
        </div>
      </div>
    </nav>
  );
};

export default NavBar;
