import Dashboard from "./components/Dashboard";
import ELDStatusLogger from "./components/ELDLogger";
import NavBar from "./components/NavBar";
import TripRoutePlanner from "./components/TripRoutePlanner";

function App() {
  return (
    <div style={{ height: "100vh", overflowY: "scroll" }}>
      <NavBar />
      <div id="trip-planner">
        <TripRoutePlanner />
      </div>
      <div id="driver-dashboard">
        <Dashboard />
      </div>
      <div id="eld-logger">
        <ELDStatusLogger />
      </div>
    </div>
  );
}

export default App;
