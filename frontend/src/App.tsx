import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { DashboardPage } from './pages/DashboardPage';
import { ChannelsPage } from './pages/ChannelsPage';
import { DriveBrowserPage } from './pages/DriveBrowserPage';
import { VideoLibraryPage } from './pages/VideoLibraryPage';
import { SchedulesPage } from './pages/SchedulesPage';
import { CalendarPage } from './pages/CalendarPage';
import { UploadHistoryPage } from './pages/UploadHistoryPage';
import { FailedJobsPage } from './pages/FailedJobsPage';
import { LogsPage } from './pages/LogsPage';
import { SettingsPage } from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="channels" element={<ChannelsPage />} />
          <Route path="drive" element={<DriveBrowserPage />} />
          <Route path="videos" element={<VideoLibraryPage />} />
          <Route path="schedules" element={<SchedulesPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="uploads" element={<UploadHistoryPage />} />
          <Route path="failed-jobs" element={<FailedJobsPage />} />
          <Route path="logs" element={<LogsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
