import React, { useState } from "react";
import logo from "./logo.svg";
import HomeScreen from "./Homescreen";
import "./App.css";

import CounterComponent from "./components/counterComponent";

function App() {
  const [currentView, setCurrentView] = useState<"home" | "counter">("home");

  return <div className="App">
    {currentView === "home" && <HomeScreen setCurrentView={setCurrentView}/>}
    {currentView === "counter" && <CounterComponent setCurrentView={setCurrentView} />}
    </div>;
}

export default App;
