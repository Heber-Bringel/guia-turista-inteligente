import { useState, type FormEvent } from 'react'
import { Bot, LoaderCircle, Send, Sparkles, UserRound } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import type { SupportedLanguage } from '../types/api'
import type {
  ChatMensagem,
  ChatRoteiroRequest,
  ChatRoteiroResponse,
  EstiloViagem,
  RitmoViagem,
  Roteiro,
} from '../types/roteiro'

interface ChatRoteiroProps {
  roteiro: Roteiro
  language: SupportedLanguage
  diasEstadia?: number
  estiloViagem?: EstiloViagem
  onSendMessage: (payload: ChatRoteiroRequest) => Promise<ChatRoteiroResponse>
  onSummaryUpdated?: (summary: string) => void
}

let nextChatMessageId = 1

function createMessageId(prefix: 'user' | 'assistant'): string {
  nextChatMessageId += 1
  return `${prefix}-${nextChatMessageId}`
}

export function ChatRoteiro({
  roteiro,
  language,
  diasEstadia = 3,
  estiloViagem = 'cultural',
  onSendMessage,
  onSummaryUpdated,
}: ChatRoteiroProps) {
  const t = getTranslations(language)
  const [ritmo, setRitmo] = useState<RitmoViagem>('moderado')
  const [acompanhantes, setAcompanhantes] = useState('Casal')
  const [gastronomia, setGastronomia] = useState('Culinária típica regional')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMensagem[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendText = async (rawText: string) => {
    const trimmed = rawText.trim()
    if (!trimmed || sending) return

    const userMsg: ChatMensagem = {
      id: createMessageId('user'),
      role: 'user',
      content: trimmed,
      criado_em: new Date().toISOString(),
    }

    const historico = messages.map((msg) => ({ role: msg.role, content: msg.content }))
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setError(null)
    setSending(true)

    try {
      const payload: ChatRoteiroRequest = {
        destino: `${roteiro.destino.cidade} - ${roteiro.destino.uf}`,
        dias_estadia: diasEstadia,
        estilo_viagem: estiloViagem,
        ritmo_viagem: ritmo,
        acompanhantes: acompanhantes.trim() || 'Casal',
        preferencias_gastronomia: gastronomia.trim() || 'Culinária típica regional',
        mensagem: trimmed,
        historico,
        ...(roteiro.clima ? { clima_info: roteiro.clima } : {}),
        roteiro_id: roteiro.id,
      }
      const response = await onSendMessage(payload)
      const assistantMsg: ChatMensagem = {
        id: createMessageId('assistant'),
        role: 'assistant',
        content: response.resposta,
        criado_em: new Date().toISOString(),
        ...(response.patrimonios_preservados && response.patrimonios_preservados.length > 0
          ? { patrimonios_preservados: response.patrimonios_preservados }
          : {}),
        ...(response.sugestoes_proximos_passos && response.sugestoes_proximos_passos.length > 0
          ? { sugestoes_proximos_passos: response.sugestoes_proximos_passos }
          : {}),
      }
      setMessages((prev) => [...prev, assistantMsg])
      const updatedSummary = response.roteiro_personalizado ?? response.resposta
      if (updatedSummary && onSummaryUpdated) {
        onSummaryUpdated(updatedSummary)
      }
    } catch {
      setError(t.chatErrorFriendly)
    } finally {
      setSending(false)
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void sendText(input)
  }

  return (
    <section className="chat-panel" aria-labelledby="chat-roteiro-title">
      <div className="section-heading compact">
        <span className="heading-icon"><Sparkles size={19} /></span>
        <div>
          <h3 id="chat-roteiro-title">{t.chatTitle}</h3>
          <p>{t.chatSubtitle}</p>
        </div>
      </div>

      <div className="chat-prefs">
        <div className="field-group">
          <label htmlFor="chat-ritmo">{t.chatPaceLabel}</label>
          <select
            id="chat-ritmo"
            value={ritmo}
            onChange={(event) => setRitmo(event.target.value as RitmoViagem)}
            disabled={sending}
          >
            <option value="tranquilo">{t.chatPaceRelaxed}</option>
            <option value="moderado">{t.chatPaceModerate}</option>
            <option value="intenso">{t.chatPaceIntense}</option>
          </select>
        </div>

        <div className="field-group">
          <label htmlFor="chat-acompanhantes">{t.chatCompanionsLabel}</label>
          <input
            id="chat-acompanhantes"
            type="text"
            value={acompanhantes}
            onChange={(event) => setAcompanhantes(event.target.value)}
            placeholder={t.chatCompanionsPlaceholder}
            disabled={sending}
          />
        </div>

        <div className="field-group">
          <label htmlFor="chat-gastronomia">{t.chatGastronomyLabel}</label>
          <input
            id="chat-gastronomia"
            type="text"
            value={gastronomia}
            onChange={(event) => setGastronomia(event.target.value)}
            placeholder={t.chatGastronomyPlaceholder}
            disabled={sending}
          />
        </div>
      </div>

      <div className="chat-messages" role="log" aria-live="polite" aria-busy={sending}>
        {messages.length === 0 ? (
          <p className="chat-empty">{t.chatEmpty}</p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`chat-bubble ${message.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-assistant'}`}
            >
              <span className="chat-avatar" aria-hidden="true">
                {message.role === 'user' ? <UserRound size={15} /> : <Bot size={15} />}
              </span>
              <div className="chat-bubble-body">
                <p>{message.content}</p>
                {message.patrimonios_preservados && message.patrimonios_preservados.length > 0 && (
                  <div className="chat-heritage">
                    <small>{t.chatPreservedHeritage}:</small>
                    <div>
                      {message.patrimonios_preservados.map((item) => (
                        <span key={item} className="heritage-chip">{item}</span>
                      ))}
                    </div>
                  </div>
                )}
                {message.sugestoes_proximos_passos && message.sugestoes_proximos_passos.length > 0 && (
                  <div className="chat-suggestions">
                    {message.sugestoes_proximos_passos.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        className="locate-chip"
                        disabled={sending}
                        onClick={() => void sendText(suggestion)}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {sending && (
          <div className="chat-loading">
            <LoaderCircle size={15} />
            <span>{t.chatSending}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="notice notice-warning chat-error" role="alert">
          <span>{error}</span>
        </div>
      )}

      <form className="chat-composer" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={t.chatInputPlaceholder}
          aria-label={t.chatInputPlaceholder}
          disabled={sending}
        />
        <button className="button button-primary" type="submit" disabled={sending || !input.trim()}>
          <Send size={15} /> {sending ? t.chatSending : t.chatSend}
        </button>
      </form>
    </section>
  )
}
