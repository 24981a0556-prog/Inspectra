import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import InspectionsListPage from '@/pages/InspectionsListPage';
import NewInspectionPage from '@/pages/NewInspectionPage';
import InspectionDetailPage from '@/pages/InspectionDetailPage';
import ProductsPage from '@/pages/ProductsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected — wrapped in AppShell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/inspections" element={<InspectionsListPage />} />
            <Route path="/inspections/new" element={<NewInspectionPage />} />
            <Route path="/inspections/:id" element={<InspectionDetailPage />} />
            <Route path="/products" element={<ProductsPage />} />
          </Route>
        </Route>

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
