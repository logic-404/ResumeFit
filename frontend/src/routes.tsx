import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { AnalysePage } from "@/pages/Analyse";
import { DashboardPage } from "@/pages/Dashboard";
import { ResultsPage } from "@/pages/Results";
import { UploadPage } from "@/pages/Upload";

export const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <Layout>
        <Outlet />
      </Layout>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "upload", element: <UploadPage /> },
      { path: "analyse", element: <AnalysePage /> },
      { path: "results/:appId", element: <ResultsPage /> },
      { path: "dashboard", element: <DashboardPage /> },
    ],
  },
]);
