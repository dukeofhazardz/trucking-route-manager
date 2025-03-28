import React from "react";
import "./NavBar.css";

const NavBar = () => {
  return (
    <nav className="navbar">
      <div className="navbar-content">
        <h1 className="logo">TRP</h1>
        <div className="nav-links">
          <a href="/map">Map</a>
          <a href="/eld">ELD Logger</a>
          <a href="/history">Daily Log</a>
        </div>
      </div>
    </nav>
  );
};

export default NavBar;
