import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { roteiroFixture } from '../test/fixtures'
import { HistoricoViagens } from './HistoricoViagens'

describe('HistoricoViagens', () => {
  it('explica o estado vazio', () => {
    render(<HistoricoViagens items={[]} loading={false} onSelect={vi.fn()} onDelete={vi.fn()} />)
    expect(screen.getByText('Nenhuma viagem ainda')).toBeInTheDocument()
  })

  it('seleciona e solicita exclusão de um roteiro', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    const onDelete = vi.fn()
    render(<HistoricoViagens items={[roteiroFixture]} loading={false} onSelect={onSelect} onDelete={onDelete} />)

    await user.click(screen.getByRole('button', { name: /Recife.*Salvador/i }))
    expect(onSelect).toHaveBeenCalledWith(roteiroFixture)
    await user.click(screen.getByRole('button', { name: /excluir roteiro para Salvador/i }))
    expect(onDelete).toHaveBeenCalledWith('rota-1')
  })
})
