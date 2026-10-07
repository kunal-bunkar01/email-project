import { Navigate, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import { AppLayout } from "./layouts/AppLayout";
import { ActivityPage } from "./pages/ActivityPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EmailDetailPage } from "./pages/EmailDetailPage";
import { EmailsPage } from "./pages/EmailsPage";
import { ReviewPage } from "./pages/ReviewPage";
import { SettingsPage } from "./pages/SettingsPage";

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/emails" element={<EmailsPage />} />
            <Route path="/emails/:id" element={<EmailDetailPage />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/review/:draftId" element={<ReviewPage />} />
            <Route path="/sent" element={<EmailsPage title="Sent" description="Replies that were sent automatically or after you approved them." lockedStatus="sent,auto_sent" />} />
            <Route path="/activity" element={<ActivityPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ToastProvider>
    </ErrorBoundary>
  );
}
