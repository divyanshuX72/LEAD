import { Routes, Route, Navigate } from 'react-router';
import { AppLayout } from '@/layouts/AppLayout';
import { AuthGuard } from '@/components/AuthGuard';

import { LeadSearch } from '@/pages/leads/LeadSearch';
import { LeadDashboard } from '@/pages/leads/LeadDashboard';
import { BatchDetail } from '@/pages/leads/BatchDetail';

import { Login } from '@/pages/Auth/Login';
import { Register } from '@/pages/Auth/Register';

function App() {
  return (
    <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        <Route element={
          <AuthGuard>
            <AppLayout />
          </AuthGuard>
        }>
          <Route path="/" element={<Navigate to="/lead/search" replace />} />
          
          {/* Lead Agent Routes */}
          <Route path="/lead/search" element={<LeadSearch />} />
          <Route path="/lead/dashboard" element={<LeadDashboard />} />
          <Route path="/lead/dashboard/:batchId" element={<BatchDetail />} />
          
          <Route path="*" element={<Navigate to="/lead/search" replace />} />
        </Route>
    </Routes>
  );
}

export default App;
