import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { createMockClient } from '../api/mockClient'
import type { ApiClient } from '../api'
import { Overview } from './Overview'

describe('Overview', () => {
  it('shows a loading state first', () => {
    render(<Overview client={createMockClient()} />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
  })

  it('shows totals, chart and one card per strategy', async () => {
    render(<Overview client={createMockClient()} />)
    expect(await screen.findByText('Total equity')).toBeInTheDocument()
    // 10450 + 9800 + 10000 from the mock fixtures
    const card = screen.getByText('Total equity').parentElement as HTMLElement
    expect(within(card).getByText('$30,250.00')).toBeInTheDocument()
    expect(screen.getByText('P&L today')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Combined equity curve' })).toBeInTheDocument()

    const sma = screen.getByRole('region', { name: 'sma_crossover' })
    expect(within(sma).getByText('$10,450.00')).toBeInTheDocument()
    expect(within(sma).getByText('+4.50%')).toBeInTheDocument()
    expect(within(sma).getByText('−6.00%')).toBeInTheDocument()
    const rsi = screen.getByRole('region', { name: 'rsi_mean_reversion' })
    expect(within(rsi).getByText('−2.00%')).toBeInTheDocument()
    expect(screen.getAllByRole('region')).toHaveLength(3)
  })

  it('shows an empty state with no strategies', async () => {
    const client: ApiClient = { ...createMockClient(), listStrategies: () => Promise.resolve([]) }
    render(<Overview client={client} />)
    expect(await screen.findByText('No strategies yet.')).toBeInTheDocument()
  })

  it('shows an error state when the client fails', async () => {
    const client: ApiClient = {
      ...createMockClient(),
      listStrategies: () => Promise.reject(new Error('boom')),
    }
    render(<Overview client={client} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('boom')
  })
})
