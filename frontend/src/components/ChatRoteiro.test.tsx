import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { roteiroFixture } from '../test/fixtures'
import { ChatRoteiro } from './ChatRoteiro'

describe('ChatRoteiro', () => {
  it('envia ritmo, acompanhantes, gastronomia e mensagem e exibe resposta preservando patrimônios', async () => {
    const user = userEvent.setup()
    const onSendMessage = vi.fn().mockResolvedValue({
      resposta: 'Manhã no Parque Nacional de Sete Cidades e jantar regional.',
      idioma: 'pt-BR',
      destino: 'Salvador - BA',
      roteiro_personalizado: 'Roteiro atualizado com Parque Nacional de Sete Cidades.',
      patrimonios_preservados: ['Parque Nacional de Sete Cidades'],
      sugestoes_proximos_passos: ['Incluir parada na BR-343'],
    })
    const onSummaryUpdated = vi.fn()

    render(
      <ChatRoteiro
        roteiro={roteiroFixture}
        language="pt-BR"
        onSendMessage={onSendMessage}
        onSummaryUpdated={onSummaryUpdated}
      />,
    )

    await user.selectOptions(screen.getByLabelText(/ritmo de viagem/i), 'tranquilo')
    const compInput = screen.getByLabelText(/acompanhantes/i)
    await user.clear(compInput)
    await user.type(compInput, 'Família com crianças')
    const gastroInput = screen.getByLabelText(/gastronomia/i)
    await user.clear(gastroInput)
    await user.type(gastroInput, 'Frutos do mar e doces regionais')
    await user.type(screen.getByPlaceholderText(/peça ajustes/i), 'Inclua paradas culturais pela manhã')
    await user.click(screen.getByRole('button', { name: /enviar/i }))

    expect(onSendMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        ritmo_viagem: 'tranquilo',
        acompanhantes: 'Família com crianças',
        preferencias_gastronomia: 'Frutos do mar e doces regionais',
        mensagem: 'Inclua paradas culturais pela manhã',
      }),
    )
    expect(await screen.findByText(/Manhã no Parque Nacional de Sete Cidades/i)).toBeInTheDocument()
    expect(screen.getByText('Parque Nacional de Sete Cidades')).toBeInTheDocument()
    expect(onSummaryUpdated).toHaveBeenCalledWith('Roteiro atualizado com Parque Nacional de Sete Cidades.')
  })

  it('exibe mensagem amigável sem detalhes técnicos quando o chat falha', async () => {
    const user = userEvent.setup()
    const onSendMessage = vi.fn().mockRejectedValue(new Error('Internal 500 stack trace'))

    render(
      <ChatRoteiro
        roteiro={roteiroFixture}
        language="pt-BR"
        onSendMessage={onSendMessage}
      />,
    )

    await user.type(screen.getByPlaceholderText(/peça ajustes/i), 'Sugira um café da manhã')
    await user.click(screen.getByRole('button', { name: /enviar/i }))

    const alert = await screen.findByRole('alert')
    expect(alert.textContent).not.toMatch(/500|stack trace/i)
    expect(alert.textContent).toMatch(/tente enviar sua mensagem novamente/i)
  })
})
