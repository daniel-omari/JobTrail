import { BrowserRouter, Route, Routes } from "react-router";
import { Banners } from "./components/Banners";
import { NavBar } from "./components/NavBar";
import { ScanToast } from "./components/ScanToast";
import { Overview } from "./pages/Overview";
import { Placeholder } from "./pages/Placeholder";
import { Privacy } from "./pages/Privacy";
import { Quarantine } from "./pages/Quarantine";
import { Settings } from "./pages/Settings";
import { Tracker } from "./pages/Tracker";
import { ScanProvider } from "./scan-context";

export default function App() {
  return (
    <BrowserRouter>
      <ScanProvider>
        <NavBar />
        <Banners />
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/review" element={<Placeholder title="Review" />} />
          <Route path="/quarantine" element={<Quarantine />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/export" element={<Placeholder title="Export" />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
        <ScanToast />
      </ScanProvider>
    </BrowserRouter>
  );
}
