import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { Shell } from "@/components/Shell";
import PowerMonitoring from "@/pages/PowerMonitoring";
import StagePlaceholder from "@/pages/StagePlaceholder";

document.documentElement.classList.add("dark");

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Navigate to="/power" replace />} />
            <Route path="/power" element={<PowerMonitoring />} />
            <Route path="/heat-monitoring" element={<StagePlaceholder stage="Chennai Heat Monitoring" />} />
            <Route path="/heat-risk" element={<StagePlaceholder stage="Heat Risk Analysis" />} />
            <Route path="/emergency" element={<StagePlaceholder stage="Emergency Priority Planning" />} />
            <Route path="*" element={<Navigate to="/power" replace />} />
          </Routes>
        </Shell>
      </BrowserRouter>
      <Toaster theme="dark" position="bottom-right" />
    </div>
  );
}

export default App;
