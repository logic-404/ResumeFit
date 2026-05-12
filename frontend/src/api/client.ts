import axios from "axios";
import type {
  AnalyseResponse,
  ApplicationDetail,
  ApplicationSummary,
  DashboardStats,
  Profile,
  Status,
} from "./types";

export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 60_000,
});

export async function uploadResume(files: File[]): Promise<Profile> {
  const fd = new FormData();
  for (const f of files) {
    fd.append("files", f, (f as any).webkitRelativePath || f.name);
  }
  const { data } = await api.post<Profile>("/profile/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getProfile(): Promise<Profile | null> {
  try {
    const { data } = await api.get<Profile>("/profile");
    return data;
  } catch (e: any) {
    if (e?.response?.status === 404) return null;
    throw e;
  }
}

export async function updateProfile(patch: Partial<Profile>): Promise<Profile> {
  const { data } = await api.put<Profile>("/profile", patch);
  return data;
}

export interface JDPreview {
  company: string | null;
  role: string | null;
  location: string | null;
  jd_text: string;
}

export async function previewJd(url: string): Promise<JDPreview> {
  const { data } = await api.post<JDPreview>("/jd/preview", { url });
  return data;
}

export async function startAnalyse(payload: {
  jd_text?: string;
  jd_url?: string;
  company_name?: string;
  role_title?: string;
  job_url?: string;
}): Promise<AnalyseResponse> {
  const { data } = await api.post<AnalyseResponse>("/analyse", payload);
  return data;
}

export async function listApplications(params?: {
  status?: Status;
  q?: string;
  limit?: number;
  offset?: number;
}): Promise<ApplicationSummary[]> {
  const { data } = await api.get<ApplicationSummary[]>("/applications", { params });
  return data;
}

export async function getApplication(id: string): Promise<ApplicationDetail> {
  const { data } = await api.get<ApplicationDetail>(`/applications/${id}`);
  return data;
}

export async function patchApplication(
  id: string,
  patch: { status?: Status; applied_date?: string; response_date?: string; notes?: string },
): Promise<ApplicationSummary> {
  const { data } = await api.patch<ApplicationSummary>(`/applications/${id}`, patch);
  return data;
}

export async function deleteApplication(id: string): Promise<void> {
  await api.delete(`/applications/${id}`);
}

export async function regenerate(
  id: string,
  output_type: "cover_letter" | "gap_analysis" | "tailored_resume",
): Promise<{ job_id: string }> {
  const { data } = await api.post(`/applications/${id}/regenerate`, { output_type });
  return data;
}

export function downloadTailoredResumeUrl(id: string): string {
  return `/api/v1/applications/${id}/tailored-resume/download`;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/dashboard/stats");
  return data;
}
