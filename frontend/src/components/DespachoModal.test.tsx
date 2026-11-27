import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { roteiroFixture } from '../test/fixtures'
import { DespachoModal } from './DespachoModal'

describe('DespachoModal', () => {
  it('valida e envia roteiro por E-mail e permite alternar para WhatsApp', async () => {
    const user = userEvent.setup()
    const onDispatch = vi.fn().mockResolvedValue({
      status: 'agendado',
      protocolo: 'dsp_999',
      canal: 'email',
      mensagem: 'Roteiro agendado para envio por E-mail.',
    })

    render(
      <DespachoModal
        initialChannel="email"
        roteiro={roteiroFixture}
        guideText="Guia personalizado de Recife para Salvador"
        userName="Héber"
        language="pt-BR"
        onClose={vi.fn()}
        onDispatch={onDispatch}
      />,
    )

    // E-mail inválido bloqueia envio
    await user.type(screen.getByLabelText(/endereço de e-mail/i), 'invalido')
    await user.click(screen.getByRole('button', { name: /enviar roteiro/i }))
    expect(screen.getByRole('alert')).toHaveTextContent(/e-mail válido/i)
    expect(onDispatch).not.toHaveBeenCalled()

    // E-mail válido dispara o despacho
    await user.clear(screen.getByLabelText(/endereço de e-mail/i))
    await user.type(screen.getByLabelText(/endereço de e-mail/i), 'heber@exemplo.com')
    await user.click(screen.getByRole('button', { name: /enviar roteiro/i }))

    expect(onDispatch).toHaveBeenCalledWith(
      expect.objectContaining({
        roteiro_id: roteiroFixture.id,
        canal: 'email',
        destinatario: 'heber@exemplo.com',
        resumo_guia: 'Guia personalizado de Recife para Salvador',
      }),
    )
    expect(await screen.findByRole('status')).toHaveTextContent(/agendado/i)

    // Alternar para WhatsApp
    await user.click(screen.getByRole('tab', { name: /whatsapp/i }))
    await user.type(screen.getByLabelText(/número do whatsapp/i), '+55 (86) 99999-8888')
    await user.click(screen.getByRole('button', { name: /enviar roteiro/i }))

    expect(onDispatch).toHaveBeenLastCalledWith(
      expect.objectContaining({
        canal: 'whatsapp',
        destinatario: '+55 (86) 99999-8888',
      }),
    )
  })

  it('mostra erro amigável quando o envio falha', async () => {
    const user = userEvent.setup()
    const onDispatch = vi.fn().mockRejectedValue(new Error('Webhook 502 Bad Gateway'))

    render(
      <DespachoModal
        initialChannel="email"
        roteiro={roteiroFixture}
        guideText="Guia"
        userEmail="heber@exemplo.com"
        language="pt-BR"
        onClose={vi.fn()}
        onDispatch={onDispatch}
      />,
    )

    await user.click(screen.getByRole('button', { name: /enviar roteiro/i }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).not.toMatch(/502|Bad Gateway|Webhook/i)
    expect(alert.textContent).toMatch(/tente novamente/i)
  })
})
