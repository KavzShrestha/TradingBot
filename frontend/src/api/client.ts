/**
 * Minimal typed client for the backend REST API.
 *
 * Grows as backend/app/api/ gains real endpoints (positions, trades,
 * backtests, strategies). WebSocket client for live updates lands with M5.
 */

const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export interface HealthResponse {
  status: string
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return (await response.json()) as HealthResponse
}
