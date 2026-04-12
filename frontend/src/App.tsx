import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProfileProvider } from "./context/ProfileContext";
import { ToastProvider } from "./context/ToastContext";
import { CreateOfferPage } from "./pages/CreateOfferPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { OrderBookPage } from "./pages/OrderBookPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TradeDetailPage } from "./pages/TradeDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <ProfileProvider>
        <ToastProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<OrderBookPage />} />
              <Route path="/create-offer" element={<CreateOfferPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/trade/:tradeId" element={<TradeDetailPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ToastProvider>
      </ProfileProvider>
    </BrowserRouter>
  );
}
