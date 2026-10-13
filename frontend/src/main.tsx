import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { queryClient } from "./lib/query";
import { Shell } from "./components/Shell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Loading } from "./components/ui";
import { AuthPage } from "./features/auth/AuthPage";
import "./styles.css";

const DashboardPage = lazy(() =>
  import("./features/dashboard/DashboardPage").then((m) => ({
    default: m.DashboardPage,
  })),
);
const ExplorePage = lazy(() =>
  import("./features/exploration/ExplorePage").then((m) => ({
    default: m.ExplorePage,
  })),
);
const ProfilePage = lazy(() =>
  import("./features/profiles/ProfilePage").then((m) => ({
    default: m.ProfilePage,
  })),
);
const PrivacyPage = lazy(() =>
  import("./features/profiles/PrivacyPage").then((m) => ({
    default: m.PrivacyPage,
  })),
);
const PublicProfilePage = lazy(() =>
  import("./features/profiles/PublicProfilePage").then((m) => ({
    default: m.PublicProfilePage,
  })),
);
const JobsPage = lazy(() =>
  import("./features/jobs/JobsPage").then((m) => ({ default: m.JobsPage })),
);
const JobDetailPage = lazy(() =>
  import("./features/jobs/JobDetailPage").then((m) => ({
    default: m.JobDetailPage,
  })),
);
const NetworkPage = lazy(() =>
  import("./features/network/NetworkPage").then((m) => ({
    default: m.NetworkPage,
  })),
);
const PathsPage = lazy(() =>
  import("./features/network/PathsPage").then((m) => ({
    default: m.PathsPage,
  })),
);
const ReferralCreatePage = lazy(() =>
  import("./features/referrals/ReferralCreatePage").then((m) => ({
    default: m.ReferralCreatePage,
  })),
);
const ReferralsPage = lazy(() =>
  import("./features/referrals/ReferralsPage").then((m) => ({
    default: m.ReferralsPage,
  })),
);
const ReferralDetailPage = lazy(() =>
  import("./features/referrals/ReferralDetailPage").then((m) => ({
    default: m.ReferralDetailPage,
  })),
);
const NotificationsPage = lazy(() =>
  import("./features/notifications/NotificationsPage").then((m) => ({
    default: m.NotificationsPage,
  })),
);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route path="/login" element={<AuthPage />} />
              <Route path="/register" element={<AuthPage register />} />
              <Route element={<Shell />}>
                <Route index element={<DashboardPage />} />
                <Route path="explore" element={<ExplorePage />} />
                <Route path="explore/:tab" element={<ExplorePage />} />
                <Route path="explore/jobs/:jobId" element={<ExplorePage />} />
                <Route path="profile" element={<ProfilePage />} />
                <Route path="profile/privacy" element={<PrivacyPage />} />
                <Route path="people/:userId" element={<PublicProfilePage />} />
                <Route path="jobs" element={<JobsPage />} />
                <Route path="jobs/:jobId" element={<JobDetailPage />} />
                <Route path="jobs/:jobId/paths" element={<PathsPage />} />
                <Route
                  path="jobs/:jobId/referral"
                  element={<ReferralCreatePage />}
                />
                <Route path="network" element={<NetworkPage />} />
                <Route path="referrals" element={<ReferralsPage />} />
                <Route
                  path="referrals/:referralId"
                  element={<ReferralDetailPage />}
                />
                <Route path="notifications" element={<NotificationsPage />} />
                <Route
                  path="*"
                  element={
                    <div className="state">
                      <h1>Không tìm thấy trang</h1>
                      <p>Đường dẫn này không còn khả dụng.</p>
                      <Link to="/" className="button primary">
                        Về tổng quan
                      </Link>
                    </div>
                  }
                />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
