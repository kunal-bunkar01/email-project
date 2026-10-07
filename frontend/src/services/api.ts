import axios from "axios";
import type {
  ActivityPage,
  AuthStatus,
  DashboardStats,
  EmailDetail,
  EmailPage,
  ReviewItem,
  Settings,
  SyncResult,
} from "../types";

const configured = import.meta.env.VITE_API_URL?.replace(/\/$/, "") ?? "";

export const api = axios.create({
  baseURL: configured,
});

export const backendOrigin = configured || "http://localhost:8000";

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    if (error.code === "ERR_NETWORK") return "The assistant is not reachable. Start the backend and try again.";
    return "Something went wrong. Please try again.";
  }
  return "Something went wrong. Please try again.";
}

export const getHealth = () => api.get("/api/health");
export const getAuthStatus = () => api.get<AuthStatus>("/api/auth/status").then((response) => response.data);
export const logout = () => api.post<AuthStatus>("/api/auth/logout").then((response) => response.data);
export const syncEmails = () => api.post<SyncResult>("/api/emails/sync").then((response) => response.data);

export function listEmails(params: Record<string, string | number | undefined>) {
  return api.get<EmailPage>("/api/emails", { params }).then((response) => response.data);
}

export const getEmail = (id: number) => api.get<EmailDetail>(`/api/emails/${id}`).then((response) => response.data);
export const processEmail = (id: number) => api.post<EmailDetail>(`/api/emails/${id}/process`).then((response) => response.data);
export const regenerateEmail = (id: number) =>
  api.post<EmailDetail>(`/api/emails/${id}/regenerate`).then((response) => response.data);

export const getReviews = () => api.get<ReviewItem[]>("/api/reviews").then((response) => response.data);
export const getReview = (draftId: number) => api.get<EmailDetail>(`/api/reviews/${draftId}`).then((response) => response.data);
export const getStats = () => api.get<DashboardStats>("/api/dashboard/stats").then((response) => response.data);
export const getActivity = (page = 1) =>
  api.get<ActivityPage>("/api/activity", { params: { page, page_size: 40 } }).then((response) => response.data);

export const getSettings = () => api.get<Settings>("/api/settings").then((response) => response.data);
export const saveSettings = (payload: Partial<Settings>) =>
  api.put<Settings>("/api/settings", payload).then((response) => response.data);

export const updateDraft = (id: number, current_draft: string) =>
  api.put(`/api/drafts/${id}`, { current_draft }).then((response) => response.data);

export const sendDraft = (id: number, current_draft: string) =>
  api.post<EmailDetail>(`/api/drafts/${id}/send`, { current_draft }).then((response) => response.data);

export const rejectDraft = (id: number, current_draft: string) =>
  api.post<EmailDetail>(`/api/drafts/${id}/reject`, { current_draft }).then((response) => response.data);
