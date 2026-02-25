import type { SignUpPayload, SummaryResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `${response.status} ${response.statusText}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function fetchSummary(): Promise<SummaryResponse> {
  return request<SummaryResponse>("/api/v1/healthcare/summary");
}

export async function signUp(payload: SignUpPayload): Promise<void> {
  await request<void>("/api/v1/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
