import { useState, type FormEvent } from 'react'
import { ArrowRight, CarFront, LocateFixed, MapPin, Route, Sparkles } from 'lucide-react'
import { findNearestCity, suggestDestinationsBeyondRadius } from '../services/geolocation'
import { UFS, type Coordenada, type EstiloViagem, type PlanejamentoInput, type PreferenciaRota, type TipoVeiculo } from '../types/roteiro'

interface RoteiroFormProps {
  loading: boolean
  disabled?: boolean
  onSubmit: (values: PlanejamentoInput) => void
  onLocate: () => void
  locating: boolean
  currentPosition?: Coordenada | null
}

const INITIAL_VALUES: PlanejamentoInput = {
  origem: { cidade: '', uf: '' },
  destino: { cidade: '', uf: '' },
  estilo_viagem: 'cultural',
  dias: 3,
  preferencia_rota: 'rapida',
  veiculo: { tipo: 'gasolina', consumo: 12, autonomia_km: 500, capacidade: 50, preco_unidade: 6.2 },
  passageiros: 2,
}

export function RoteiroForm({ loading, disabled = false, onSubmit, onLocate, locating, currentPosition }: RoteiroFormProps) {
  const [values, setValues] = useState<PlanejamentoInput>(INITIAL_VALUES)

  const nearestOrigin = currentPosition ? findNearestCity(currentPosition) : null
  const destinationSuggestions = currentPosition ? suggestDestinationsBeyondRadius(currentPosition, 400, 4) : []

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!loading && !disabled) onSubmit(values)
  }

  const updatePlace = (key: 'origem' | 'destino', field: 'cidade' | 'uf', value: string) => {
    setValues((current) => ({ ...current, [key]: { ...current[key], [field]: value } }))
  }

  return (
    <section className="planner-panel" aria-labelledby="planner-title">
      <div className="section-heading">
        <span className="heading-icon"><Route size={20} /></span>
        <div><h1 id="planner-title">Planeje sua próxima rota</h1><p>Conte o essencial. Nós organizamos a viagem.</p></div>
      </div>

      <form onSubmit={submit} className="planner-form">
        <fieldset disabled={loading || disabled}>
          <legend className="sr-only">Origem e destino</legend>
          <div className="route-fields">
            <div className="field-group route-field">
              <label htmlFor="origem-cidade"><MapPin size={15} /> Origem</label>
              <div className="city-state">
                <input id="origem-cidade" value={values.origem.cidade} onChange={(event) => updatePlace('origem', 'cidade', event.target.value)} placeholder="Ex.: Recife" autoComplete="address-level2" required minLength={2} />
                <select aria-label="UF de origem" value={values.origem.uf} onChange={(event) => updatePlace('origem', 'uf', event.target.value)} required>
                  <option value="">UF</option>{UFS.map((uf) => <option key={uf}>{uf}</option>)}
                </select>
              </div>
              <div className="locate-actions">
                <button className="locate-button" type="button" onClick={onLocate} disabled={locating || loading}>
                  <LocateFixed size={15} /> {locating ? 'Localizando…' : 'Usar minha localização'}
                </button>
                {nearestOrigin && (values.origem.cidade !== nearestOrigin.cidade || values.origem.uf !== nearestOrigin.uf) && (
                  <button
                    className="locate-chip"
                    type="button"
                    onClick={() => setValues((curr) => ({ ...curr, origem: { cidade: nearestOrigin.cidade, uf: nearestOrigin.uf } }))}
                  >
                    Preencher {nearestOrigin.cidade}/{nearestOrigin.uf}
                  </button>
                )}
              </div>
            </div>
            <ArrowRight className="route-arrow" aria-hidden="true" size={20} />
            <div className="field-group route-field">
              <label htmlFor="destino-cidade"><MapPin size={15} /> Destino</label>
              <div className="city-state">
                <input id="destino-cidade" value={values.destino.cidade} onChange={(event) => updatePlace('destino', 'cidade', event.target.value)} placeholder="Ex.: Salvador" autoComplete="address-level2" required minLength={2} />
                <select aria-label="UF de destino" value={values.destino.uf} onChange={(event) => updatePlace('destino', 'uf', event.target.value)} required>
                  <option value="">UF</option>{UFS.map((uf) => <option key={uf}>{uf}</option>)}
                </select>
              </div>
              {destinationSuggestions.length > 0 && (
                <div className="haversine-suggestions" aria-label="Sugestões de destinos acima de 400 km">
                  <span><Sparkles size={12} /> Sugestões (&gt;400 km):</span>
                  {destinationSuggestions.map((dest) => (
                    <button
                      key={`${dest.cidade}-${dest.uf}`}
                      type="button"
                      className="locate-chip"
                      onClick={() => setValues((curr) => ({ ...curr, destino: { cidade: dest.cidade, uf: dest.uf } }))}
                    >
                      {dest.cidade}/{dest.uf} ({dest.distancia_km} km)
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="form-divider"><span>Preferências da viagem</span></div>
          <div className="form-grid">
            <div className="field-group"><label htmlFor="estilo">Estilo</label><select id="estilo" value={values.estilo_viagem} onChange={(event) => setValues({ ...values, estilo_viagem: event.target.value as EstiloViagem })}><option value="cultural">Cultural</option><option value="gastronomico">Gastronômico</option><option value="aventura">Ecoturismo / aventura</option><option value="familia">Em família</option><option value="romantico">Romântico</option><option value="economico">Econômico</option></select></div>
              <div className="field-group"><label htmlFor="dias">Duração</label><div className="input-suffix"><input id="dias" type="number" min="1" max="5" value={values.dias} onChange={(event) => setValues({ ...values, dias: event.target.valueAsNumber })} required /><span>dias</span></div></div>
            <div className="field-group"><label htmlFor="preferencia">Prioridade da rota</label><select id="preferencia" value={values.preferencia_rota} onChange={(event) => setValues({ ...values, preferencia_rota: event.target.value as PreferenciaRota })}><option value="rapida">Mais rápida</option><option value="economica">Mais econômica</option><option value="cenica">Mais cênica</option></select></div>
            <div className="field-group"><label htmlFor="passageiros">Viajantes</label><div className="input-suffix"><input id="passageiros" type="number" min="1" max="8" value={values.passageiros} onChange={(event) => setValues({ ...values, passageiros: event.target.valueAsNumber })} required /><span>pessoas</span></div></div>
          </div>

          <details className="vehicle-details">
            <summary><CarFront size={17} /> Dados do veículo <span>melhoram as estimativas</span></summary>
            <div className="form-grid vehicle-grid">
              <div className="field-group"><label htmlFor="veiculo">Combustível</label><select id="veiculo" value={values.veiculo.tipo} onChange={(event) => setValues({ ...values, veiculo: { ...values.veiculo, tipo: event.target.value as TipoVeiculo } })}><option value="gasolina">Gasolina</option><option value="etanol">Etanol</option><option value="diesel">Diesel</option><option value="hibrido">Híbrido</option><option value="eletrico">Elétrico</option></select></div>
              <div className="field-group"><label htmlFor="consumo">Consumo médio</label><div className="input-suffix"><input id="consumo" type="number" min="1" max="80" step="0.1" value={values.veiculo.consumo} onChange={(event) => setValues({ ...values, veiculo: { ...values.veiculo, consumo: event.target.valueAsNumber } })} required /><span>{values.veiculo.tipo === 'eletrico' ? 'km/kWh' : 'km/L'}</span></div></div>
              <div className="field-group"><label htmlFor="capacidade">{values.veiculo.tipo === 'eletrico' ? 'Capacidade da bateria' : 'Capacidade do tanque'}</label><div className="input-suffix"><input id="capacidade" type="number" min="1" max="300" step="0.1" value={values.veiculo.capacidade} onChange={(event) => setValues({ ...values, veiculo: { ...values.veiculo, capacidade: event.target.valueAsNumber } })} required /><span>{values.veiculo.tipo === 'eletrico' ? 'kWh' : 'L'}</span></div></div>
              <div className="field-group"><label htmlFor="preco-unidade">{values.veiculo.tipo === 'eletrico' ? 'Preço por kWh' : 'Preço por litro'}</label><div className="input-suffix"><input id="preco-unidade" type="number" min="0.1" max="50" step="0.01" value={values.veiculo.preco_unidade} onChange={(event) => setValues({ ...values, veiculo: { ...values.veiculo, preco_unidade: event.target.valueAsNumber } })} required /><span>R$</span></div></div>
              <div className="field-group"><label htmlFor="autonomia">Autonomia segura</label><div className="input-suffix"><input id="autonomia" type="number" min="50" max="1500" value={values.veiculo.autonomia_km} onChange={(event) => setValues({ ...values, veiculo: { ...values.veiculo, autonomia_km: event.target.valueAsNumber } })} required /><span>km</span></div></div>
            </div>
          </details>
        </fieldset>

        <button className="button button-primary plan-button" type="submit" disabled={loading || disabled}>
          {loading ? <><span className="spinner" aria-hidden="true" /> Planejando sua viagem…</> : <><Route size={19} /> Planejar viagem</>}
        </button>
      </form>
    </section>
  )
}
