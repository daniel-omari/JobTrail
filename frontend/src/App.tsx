import { BrowserRouter, Route, Routes } from "react-router";
import { NavBar } from "./components/NavBar";
import { ScanToast } from "./components/ScanToast";
import { Overview } from "./pages/Overview";
import { Placeholder } from "./pages/Placeholder";
import { Privacy } from "./pages/Privacy";
import { Tracker } from "./pages/Tracker";
import { ScanProvider } from "./scan-context";

export default function App() {
  return (
    <BrowserRouter>
      <ScanProvider>
        <NavBar />
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/review" element={<Placeholder title="Review" />} />
          <Route path="/quarantine" element={<Placeholder title="Quarantine" />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/export" element={<Placeholder title="Export" />} />
          <Route path="/settings" element={<Placeholder title="Settings" />} />
        </Routes>
        <ScanToast />
      </ScanProvider>
    </BrowserRouter>
  );
}
