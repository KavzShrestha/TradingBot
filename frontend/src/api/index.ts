import { createMockClient } from './mockClient'
import type { ApiClient } from './types'

export * from './types'

/** Mock is the default; set VITE_USE_MOCK_API=false once the real client exists. */
export function isMockApiEnabled(): boolean {
  return (import.meta.env.VITE_USE_MOCK_API as string | undefined) !== 'false'
}

export function createApiClient(): ApiClient {
  if (isMockApiEnabled())return createMockClient()
  // The real HTTP/WebSocket client is a later task (see docs/PLAN.md, M6).
  throw new Error('Real API client is not implemented yet; set VITE_USE_MOCK_API=true')
}
