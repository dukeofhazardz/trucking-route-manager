import ELDStatusLogger from "./components/ELDLogger";
import NavBar from "./components/NavBar";
import TripRoutePlanner from "./components/TripRoutePlanner";

function App() {
  return (
    <>
      <NavBar />
      <TripRoutePlanner />
      <ELDStatusLogger />
    </>
  );
}

export default App;
