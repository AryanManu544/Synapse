import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import { DashboardLayout } from './components/DashboardLayout'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { PullRequestsPage } from './pages/PullRequestsPage'
import { RuleConfigurationPage } from './pages/RuleConfigurationPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<DashboardLayout />}>
          <Route index element={<Navigate to="/pull-requests" replace />} />
          <Route path="pull-requests" element={<PullRequestsPage />} />
          <Route path="rules" element={<RuleConfigurationPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
