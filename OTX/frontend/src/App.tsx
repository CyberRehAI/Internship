import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DashboardPage } from './pages/DashboardPage'
import { ExportHistoryPage } from './pages/ExportHistoryPage'
import { IocDumperPage } from './pages/IocDumperPage'
import { PulseViewerPage } from './pages/PulseViewerPage'
import { SearchPage } from './pages/SearchPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/pulses" element={<PulseViewerPage />} />
        <Route path="/dumper" element={<IocDumperPage />} />
        <Route path="/export-history" element={<ExportHistoryPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
