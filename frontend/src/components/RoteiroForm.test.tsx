import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { RoteiroForm } from './RoteiroForm'

describe('RoteiroForm', () => {
  it('envia origem, destino e preferências tipadas', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<RoteiroForm loading={false} onSubmit={onSubmit} onLocate={vi.fn()} locating={false} />)

    await user.type(screen.getByLabelText(/^origem$/i), 'Recife')
    await user.selectOptions(screen.getByLabelText('UF de origem'), 'PE')
    await user.type(screen.getByLabelText(/^destino$/i), 'Salvador')
    await user.selectOptions(screen.getByLabelText('UF de destino'), 'BA')
    await user.click(screen.getByRole('button', { name: /planejar viagem/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      origem: { cidade: 'Recife', uf: 'PE' },
      destino: { cidade: 'Salvador', uf: 'BA' },
      dias: 3,
      passageiros: 2,
    }))
  })

  it('bloqueia um segundo envio durante o planejamento', () => {
    render(<RoteiroForm loading onSubmit={vi.fn()} onLocate={vi.fn()} locating={false} />)
    expect(screen.getByRole('button', { name: /planejando sua viagem/i })).toBeDisabled()
    expect(screen.getByRole('group', { name: /origem e destino/i })).toBeDisabled()
  })
})
