import { useEffect, useState, type FormEvent } from 'react'
import { AlertTriangle, CheckCircle2, LoaderCircle, Mail, MessageCircle, Send, X } from 'lucide-react'
import { getTranslations } from '../i18n/language'
import type { SupportedLanguage } from '../types/api'
import type {
  CanalDespacho,
  DespacharRoteiroRequest,
  DespacharRoteiroResponse,
  Roteiro,
} from '../types/roteiro'

interface DespachoModalProps {
  initialChannel: CanalDespacho
  roteiro: Roteiro
  guideText: string
  userName?: string
  userEmail?: string
  language: SupportedLanguage
  onClose: () => void
  onDispatch: (payload: DespacharRoteiroRequest) => Promise<DespacharRoteiroResponse>
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function isValidWhatsApp(value: string): boolean {
  const digits = value.replace(/\D/g, '')
  return digits.length >= 10 && digits.length <= 15
}

export function DespachoModal({
  initialChannel,
  roteiro,
  guideText,
  userName,
  userEmail,
  language,
  onClose,
  onDispatch,
}: DespachoModalProps) {
  const t = getTranslations(language)
  const [canal, setCanal] = useState<CanalDespacho>(initialChannel)
  const [destinatario, setDestinatario] = useState(initialChannel === 'email' ? (userEmail ?? '') : '')
  const [submitting, setSubmitting] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [errorMessageText, setErrorMessageText] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !submitting) onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, submitting])

  const selectChannel = (nextChannel: CanalDespacho) => {
    setCanal(nextChannel)
    setValidationError(null)
    setErrorMessageText(null)
    setSuccessMessage(null)
    setDestinatario(nextChannel === 'email' ? (userEmail ?? '') : '')
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = destinatario.trim()
    setValidationError(null)
    setErrorMessageText(null)
    setSuccessMessage(null)

    if (canal === 'email' && !EMAIL_PATTERN.test(trimmed)) {
      setValidationError(t.dispatchInvalidEmail)
      return
    }
    if (canal === 'whatsapp' && !isValidWhatsApp(trimmed)) {
      setValidationError(t.dispatchInvalidWhatsApp)
      return
    }

    setSubmitting(true)
    try {
      const payload: DespacharRoteiroRequest = {
        roteiro_id: roteiro.id,
        canal,
        destinatario: trimmed,
        ...(userName ? { nome_viajante: userName } : {}),
        ...(guideText ? { resumo_guia: guideText } : {}),
        roteiro,
      }
      const response = await onDispatch(payload)
      setSuccessMessage(response.mensagem)
    } catch {
      setErrorMessageText(t.dispatchErrorFriendly)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget && !submitting) onClose()
      }}
    >
      <div className="dispatch-modal" role="dialog" aria-modal="true" aria-labelledby="dispatch-modal-title">
        <div className="dispatch-modal-header">
          <div>
            <h2 id="dispatch-modal-title">{t.dispatchTitle}</h2>
            <p>{t.dispatchSubtitle}</p>
          </div>
          <button
            type="button"
            className="button button-quiet button-icon"
            onClick={onClose}
            disabled={submitting}
            aria-label={t.dispatchClose}
          >
            <X size={18} />
          </button>
        </div>

        <div className="dispatch-summary">
          <strong>{roteiro.origem.cidade} → {roteiro.destino.cidade}</strong>
          <span>{Math.round(roteiro.distancia_km)} km · {Math.floor(roteiro.duracao_minutos / 60)}h {Math.round(roteiro.duracao_minutos % 60)}min</span>
        </div>

        <div className="channel-switch" role="tablist" aria-label={t.dispatchTitle}>
          <button
            type="button"
            role="tab"
            aria-selected={canal === 'email'}
            className={`channel-tab ${canal === 'email' ? 'active' : ''}`}
            onClick={() => selectChannel('email')}
            disabled={submitting}
          >
            <Mail size={16} /> {t.dispatchChannelEmail}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={canal === 'whatsapp'}
            className={`channel-tab ${canal === 'whatsapp' ? 'active' : ''}`}
            onClick={() => selectChannel('whatsapp')}
            disabled={submitting}
          >
            <MessageCircle size={16} /> {t.dispatchChannelWhatsApp}
          </button>
        </div>

        <form onSubmit={(event) => void handleSubmit(event)} className="dispatch-form" noValidate>
          <div className="field-group">
            <label htmlFor="dispatch-destinatario">
              {canal === 'email' ? t.dispatchEmailLabel : t.dispatchWhatsAppLabel}
            </label>
            <input
              id="dispatch-destinatario"
              type={canal === 'email' ? 'email' : 'tel'}
              value={destinatario}
              onChange={(event) => setDestinatario(event.target.value)}
              placeholder={canal === 'email' ? t.dispatchEmailPlaceholder : t.dispatchWhatsAppPlaceholder}
              disabled={submitting}
              required
            />
          </div>

          {validationError && (
            <div className="dispatch-feedback dispatch-feedback-error" role="alert">
              <AlertTriangle size={16} /> <span>{validationError}</span>
            </div>
          )}

          {errorMessageText && (
            <div className="dispatch-feedback dispatch-feedback-error" role="alert">
              <AlertTriangle size={16} /> <span>{errorMessageText}</span>
            </div>
          )}

          {successMessage && (
            <div className="dispatch-feedback dispatch-feedback-success" role="status">
              <CheckCircle2 size={16} /> <span>{successMessage}</span>
            </div>
          )}

          <div className="dispatch-actions">
            <button type="button" className="button button-quiet" onClick={onClose} disabled={submitting}>
              {t.dispatchClose}
            </button>
            <button type="submit" className="button button-primary" disabled={submitting}>
              {submitting ? (
                <>
                  <LoaderCircle size={16} className="spin-icon" /> {t.dispatchSubmitting}
                </>
              ) : (
                <>
                  <Send size={16} /> {t.dispatchSubmit}
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
