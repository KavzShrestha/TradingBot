import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('renders the Overview page heading and paper banner', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByText('PAPER TRADING – SIMULATED')).toBeInTheDocument()
    expect(await screen.findByText('Total equity')).toBeInTheDocument()
  })
})
