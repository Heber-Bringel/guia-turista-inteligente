import type { SupportedLanguage } from '../types/api'

export interface LanguageOption {
  code: SupportedLanguage
  label: string
  nativeLabel: string
  dir: 'ltr' | 'rtl'
}

export const LANGUAGE_OPTIONS: readonly LanguageOption[] = [
  { code: 'pt-BR', label: 'Português', nativeLabel: 'Português (BR)', dir: 'ltr' },
  { code: 'en', label: 'English', nativeLabel: 'English', dir: 'ltr' },
  { code: 'es', label: 'Español', nativeLabel: 'Español', dir: 'ltr' },
  { code: 'fr', label: 'Français', nativeLabel: 'Français', dir: 'ltr' },
  { code: 'zh', label: 'Mandarim', nativeLabel: '中文', dir: 'ltr' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी', dir: 'ltr' },
  { code: 'ar', label: 'Árabe', nativeLabel: 'العربية', dir: 'rtl' },
  { code: 'ru', label: 'Russo', nativeLabel: 'Русский', dir: 'ltr' },
] as const

export interface TranslationKeys {
  brandTitle: string
  brandSubtitle: string
  languageSelectorLabel: string
  visitorSession: string
  visitorModeButton: string
  restoreGooglePrefix: string
  themeToDark: string
  themeToLight: string
  logout: string
  logoutAria: string
  continueVisitor: string
  signingIn: string
  offlineBanner: string
  introMark: string
  introHeading: string
  introBody: string
  introOrigin: string
  introDestination: string
  signinHeading: string
  signinBody: string
  signinButton: string
  signinLoading: string
  plannerTitle: string
  plannerSubtitle: string
  originLabel: string
  destinationLabel: string
  useLocation: string
  locating: string
  planButton: string
  planningButton: string
  calculatedRoute: string
  mapsButton: string
  sendEmailButton: string
  sendWhatsAppButton: string
  elevationSummary: string
  maxAltitude: string
  ascentDescent: string
  consumptionImpact: string
  historyTitle: string
  historySubtitle: string
  historyEmptyTitle: string
  historyEmptyBody: string
  deleteConfirm: string
  footerLeft: string
  footerRight: string
  metricDistance: string
  metricDuration: string
  metricWeather: string
  metricElevation: string
  metricTotalCost: string
  metricPerTraveler: string
  unavailable: string
  mapHintAnp: string
  mapDeparture: string
  mapDestination: string
  mapRouteOptions: string
  anpBadge: string
  anpCorporateName: string
  anpCnpj: string
  anpRating: string
  anpAuthTime: string
  anpFuels: string
  anpRanking: string
  anpEstimatedStop: string
  notInformed: string
  yearsSuffix: string
  weatherUnavailable: string
  weatherFallbackHint: string
  guideTitle: string
  guideSubtitle: string
  guidePending: string
  guideStreaming: string
  attractionsTitle: string
  visited: string
  markVisited: string
  chatTitle: string
  chatSubtitle: string
  chatPaceLabel: string
  chatPaceRelaxed: string
  chatPaceModerate: string
  chatPaceIntense: string
  chatCompanionsLabel: string
  chatCompanionsPlaceholder: string
  chatGastronomyLabel: string
  chatGastronomyPlaceholder: string
  chatInputPlaceholder: string
  chatSend: string
  chatSending: string
  chatEmpty: string
  chatPreservedHeritage: string
  chatErrorFriendly: string
  dispatchTitle: string
  dispatchSubtitle: string
  dispatchChannelEmail: string
  dispatchChannelWhatsApp: string
  dispatchEmailLabel: string
  dispatchEmailPlaceholder: string
  dispatchWhatsAppLabel: string
  dispatchWhatsAppPlaceholder: string
  dispatchInvalidEmail: string
  dispatchInvalidWhatsApp: string
  dispatchSubmit: string
  dispatchSubmitting: string
  dispatchClose: string
  dispatchErrorFriendly: string
  errorSessionExpired: string
  errorConflict: string
  errorValidation: string
  errorServiceFriendly: string
  errorCancelled: string
  errorGenericFriendly: string
  locationSaved: string
  farOriginWarning: string
  guideWarningFriendly: string
  sessionExpiredNotice: string
}

const ptBR: TranslationKeys = {
  brandTitle: 'Guia do Turista',
  brandSubtitle: 'Inteligente',
  languageSelectorLabel: 'Idioma da interface e do roteiro',
  visitorSession: 'Sessão de visitante',
  visitorModeButton: 'Modo visitante',
  restoreGooglePrefix: 'Voltar para',
  themeToDark: 'Usar tema escuro',
  themeToLight: 'Usar tema claro',
  logout: 'Sair',
  logoutAria: 'Sair da conta',
  continueVisitor: 'Continuar como visitante',
  signingIn: 'Entrando…',
  offlineBanner: 'Você está offline. O planejamento será liberado quando a conexão voltar.',
  introMark: 'Brasil de ponta a ponta',
  introHeading: 'Sua viagem começa com um plano que faz sentido.',
  introBody: 'Rota, autonomia, postos regulados, conversa com IA e entrega direta no seu E-mail ou WhatsApp.',
  introOrigin: 'Origem',
  introDestination: 'Destino',
  signinHeading: 'Entre para abrir o planejador',
  signinBody: 'Use sua conta Google ou continue como visitante por até duas horas. Seus roteiros ficam separados por usuário.',
  signinButton: 'Explorar como visitante',
  signinLoading: 'Preparando sessão…',
  plannerTitle: 'Planeje sua próxima rota',
  plannerSubtitle: 'Conte o essencial. Nós organizamos a viagem.',
  originLabel: 'Origem',
  destinationLabel: 'Destino',
  useLocation: 'Usar minha localização',
  locating: 'Localizando…',
  planButton: 'Planejar viagem',
  planningButton: 'Planejando sua viagem…',
  calculatedRoute: 'Roteiro calculado',
  mapsButton: 'Maps',
  sendEmailButton: 'Enviar por E-mail',
  sendWhatsAppButton: 'Enviar por WhatsApp',
  elevationSummary: 'Topografia e relevo',
  maxAltitude: 'Altitude máxima',
  ascentDescent: 'Subida / descida',
  consumptionImpact: 'Impacto no consumo',
  historyTitle: 'Viagens salvas',
  historySubtitle: 'Seu histórico acompanha a sessão.',
  historyEmptyTitle: 'Nenhuma viagem ainda',
  historyEmptyBody: 'Seu primeiro roteiro aparecerá aqui depois do planejamento.',
  deleteConfirm: 'Excluir este roteiro do seu histórico?',
  footerLeft: 'Guia do Turista Inteligente · V3',
  footerRight: 'React 19 + FastAPI + n8n',
  metricDistance: 'Distância',
  metricDuration: 'Tempo estimado',
  metricWeather: 'Clima no destino',
  metricElevation: 'Ganho de elevação',
  metricTotalCost: 'Custo total',
  metricPerTraveler: 'Por viajante',
  unavailable: 'Indisponível',
  mapHintAnp: 'Clique em um marcador de posto no mapa para consultar os dados regulatórios da ANP.',
  mapDeparture: 'Partida',
  mapDestination: 'Destino',
  mapRouteOptions: 'Opções de rota',
  anpBadge: 'Posto regulado ANP',
  anpCorporateName: 'Razão Social',
  anpCnpj: 'CNPJ',
  anpRating: 'Avaliação',
  anpAuthTime: 'Tempo de autorização ANP',
  anpFuels: 'Combustíveis',
  anpRanking: 'Ranking ANP',
  anpEstimatedStop: 'Parada estimada ao longo da rota',
  notInformed: 'Não informado',
  yearsSuffix: 'anos',
  weatherUnavailable: 'Clima temporariamente indisponível',
  weatherFallbackHint: 'Planeje com uma margem para mudanças no tempo.',
  guideTitle: 'Guia do viajante',
  guideSubtitle: 'Uma síntese objetiva, criada enquanto você acompanha.',
  guidePending: 'O guia começará assim que a rota estiver pronta.',
  guideStreaming: 'Gerando recomendações…',
  attractionsTitle: 'Atrativos e sabores locais',
  visited: 'Visitado',
  markVisited: 'Marcar visita',
  chatTitle: 'Personalize seu roteiro com a IA',
  chatSubtitle: 'Informe seu ritmo de viagem, acompanhantes e preferências gastronômicas para ajustar cada detalhe.',
  chatPaceLabel: 'Ritmo de viagem',
  chatPaceRelaxed: 'Tranquilo',
  chatPaceModerate: 'Moderado',
  chatPaceIntense: 'Intenso',
  chatCompanionsLabel: 'Acompanhantes',
  chatCompanionsPlaceholder: 'Ex.: Família com crianças, casal, amigos',
  chatGastronomyLabel: 'Gastronomia',
  chatGastronomyPlaceholder: 'Ex.: Culinária regional, frutos do mar, vegetariana',
  chatInputPlaceholder: 'Peça ajustes no roteiro, paradas culturais ou dicas locais…',
  chatSend: 'Enviar',
  chatSending: 'Consultando…',
  chatEmpty: 'Envie uma mensagem para começar o diálogo e construir seu roteiro sob medida.',
  chatPreservedHeritage: 'Patrimônios locais preservados',
  chatErrorFriendly: 'Nosso assistente está reorganizando as sugestões no momento. Tente enviar sua mensagem novamente em instantes.',
  dispatchTitle: 'Receber roteiro completo',
  dispatchSubtitle: 'Escolha como prefere receber seu roteiro personalizado.',
  dispatchChannelEmail: 'E-mail (HTML)',
  dispatchChannelWhatsApp: 'WhatsApp',
  dispatchEmailLabel: 'Endereço de e-mail',
  dispatchEmailPlaceholder: 'viajante@exemplo.com',
  dispatchWhatsAppLabel: 'Número do WhatsApp (com DDD)',
  dispatchWhatsAppPlaceholder: '+55 (86) 99999-9999',
  dispatchInvalidEmail: 'Informe um endereço de e-mail válido.',
  dispatchInvalidWhatsApp: 'Informe um número de WhatsApp válido com DDD (mínimo 10 dígitos).',
  dispatchSubmit: 'Enviar roteiro',
  dispatchSubmitting: 'Enviando roteiro…',
  dispatchClose: 'Fechar',
  dispatchErrorFriendly: 'Não conseguimos concluir o envio agora. Verifique os dados e tente novamente em instantes.',
  errorSessionExpired: 'Sua sessão expirou. Entre novamente para continuar.',
  errorConflict: 'Este roteiro já está sendo calculado. Aguarde a conclusão.',
  errorValidation: 'Revise os campos preenchidos e tente novamente.',
  errorServiceFriendly: 'Estamos ajustando alguns detalhes por aqui. Tente novamente em instantes.',
  errorCancelled: 'Operação cancelada.',
  errorGenericFriendly: 'Não foi possível concluir sua solicitação agora. Tente novamente em instantes.',
  locationSaved: 'Localização registrada. Vamos comparar a distância assim que a origem for localizada.',
  farOriginWarning: 'Você parece estar a mais de 400 km da origem informada. Confirme a cidade antes de seguir.',
  guideWarningFriendly: 'Sua rota está pronta. As sugestões extras serão exibidas assim que estiverem disponíveis.',
  sessionExpiredNotice: 'Sua sessão de visitante expirou. Entre novamente para continuar.',
}

const en: TranslationKeys = {
  ...ptBR,
  brandTitle: 'Smart Tourist',
  brandSubtitle: 'Guide',
  languageSelectorLabel: 'Interface and itinerary language',
  visitorSession: 'Visitor session',
  visitorModeButton: 'Visitor mode',
  restoreGooglePrefix: 'Back to',
  themeToDark: 'Switch to dark theme',
  themeToLight: 'Switch to light theme',
  logout: 'Sign out',
  logoutAria: 'Sign out of account',
  continueVisitor: 'Continue as visitor',
  signingIn: 'Signing in…',
  offlineBanner: 'You are offline. Route planning will resume once your connection returns.',
  introMark: 'Across Brazil',
  introHeading: 'Your journey starts with a plan that makes sense.',
  introBody: 'Route, range, regulated fuel stations, AI itinerary chat, and direct delivery via Email or WhatsApp.',
  introOrigin: 'Origin',
  introDestination: 'Destination',
  signinHeading: 'Sign in to open the planner',
  signinBody: 'Use your Google account or continue as a visitor for up to two hours. Your trips stay separated per user.',
  signinButton: 'Explore as visitor',
  signinLoading: 'Preparing session…',
  plannerTitle: 'Plan your next route',
  plannerSubtitle: 'Share the essentials. We organize the trip.',
  originLabel: 'Origin',
  destinationLabel: 'Destination',
  useLocation: 'Use my location',
  locating: 'Locating…',
  planButton: 'Plan trip',
  planningButton: 'Planning your trip…',
  calculatedRoute: 'Planned itinerary',
  mapsButton: 'Maps',
  sendEmailButton: 'Send via Email',
  sendWhatsAppButton: 'Send via WhatsApp',
  elevationSummary: 'Topography & elevation',
  maxAltitude: 'Max altitude',
  ascentDescent: 'Ascent / descent',
  consumptionImpact: 'Consumption impact',
  historyTitle: 'Saved trips',
  historySubtitle: 'Your history follows your session.',
  historyEmptyTitle: 'No trips yet',
  historyEmptyBody: 'Your first itinerary will appear here after planning.',
  deleteConfirm: 'Delete this itinerary from your history?',
  footerLeft: 'Smart Tourist Guide · V3',
  metricDistance: 'Distance',
  metricDuration: 'Estimated time',
  metricWeather: 'Destination weather',
  metricElevation: 'Elevation gain',
  metricTotalCost: 'Total cost',
  metricPerTraveler: 'Per traveler',
  unavailable: 'Unavailable',
  mapHintAnp: 'Click a fuel station marker on the map to view ANP regulatory details.',
  mapDeparture: 'Departure',
  mapDestination: 'Destination',
  mapRouteOptions: 'Route options',
  anpBadge: 'ANP regulated station',
  anpCorporateName: 'Corporate Name',
  anpCnpj: 'CNPJ',
  anpRating: 'Rating',
  anpAuthTime: 'ANP authorization time',
  anpFuels: 'Fuels',
  anpRanking: 'ANP Ranking',
  anpEstimatedStop: 'Estimated stop along the route',
  notInformed: 'Not informed',
  yearsSuffix: 'years',
  weatherUnavailable: 'Weather temporarily unavailable',
  weatherFallbackHint: 'Plan ahead for weather changes along the way.',
  guideTitle: 'Traveler guide',
  guideSubtitle: 'A concise overview tailored to your route.',
  guidePending: 'Your guide will appear as soon as the route is ready.',
  guideStreaming: 'Generating recommendations…',
  attractionsTitle: 'Attractions & local flavors',
  visited: 'Visited',
  markVisited: 'Mark visited',
  chatTitle: 'Personalize your itinerary with AI',
  chatSubtitle: 'Tell us your travel pace, companions, and food preferences to refine every detail.',
  chatPaceLabel: 'Travel pace',
  chatPaceRelaxed: 'Relaxed',
  chatPaceModerate: 'Moderate',
  chatPaceIntense: 'Intense',
  chatCompanionsLabel: 'Companions',
  chatCompanionsPlaceholder: 'e.g. Family with kids, couple, friends',
  chatGastronomyLabel: 'Gastronomy',
  chatGastronomyPlaceholder: 'e.g. Regional cuisine, seafood, vegetarian',
  chatInputPlaceholder: 'Ask for itinerary adjustments, cultural stops, or local tips…',
  chatSend: 'Send',
  chatSending: 'Thinking…',
  chatEmpty: 'Send a message to start building your custom itinerary.',
  chatPreservedHeritage: 'Preserved local heritage',
  chatErrorFriendly: 'Our travel assistant is organizing suggestions right now. Please try again shortly.',
  dispatchTitle: 'Receive complete itinerary',
  dispatchSubtitle: 'Choose how you want to receive your personalized itinerary.',
  dispatchChannelEmail: 'Email (HTML)',
  dispatchChannelWhatsApp: 'WhatsApp',
  dispatchEmailLabel: 'Email address',
  dispatchEmailPlaceholder: 'traveler@example.com',
  dispatchWhatsAppLabel: 'WhatsApp number (with country/area code)',
  dispatchWhatsAppPlaceholder: '+55 (86) 99999-9999',
  dispatchInvalidEmail: 'Please enter a valid email address.',
  dispatchInvalidWhatsApp: 'Please enter a valid WhatsApp number (at least 10 digits).',
  dispatchSubmit: 'Send itinerary',
  dispatchSubmitting: 'Sending itinerary…',
  dispatchClose: 'Close',
  dispatchErrorFriendly: 'We could not complete the delivery right now. Please try again shortly.',
  errorSessionExpired: 'Your session expired. Sign in again to continue.',
  errorConflict: 'This itinerary is already being calculated. Please wait.',
  errorValidation: 'Please check the highlighted fields and try again.',
  errorServiceFriendly: 'We are fine-tuning a few details. Please try again in a moment.',
  errorCancelled: 'Operation cancelled.',
  errorGenericFriendly: 'We could not complete your request right now. Please try again shortly.',
  locationSaved: 'Location recorded. We will compare distances once the origin is located.',
  farOriginWarning: 'You appear to be more than 400 km from the chosen origin. Confirm the city before departing.',
  guideWarningFriendly: 'Your route is ready. Extra guide suggestions will appear as soon as available.',
  sessionExpiredNotice: 'Your visitor session expired. Sign in again to continue.',
}

const es: TranslationKeys = {
  ...en,
  brandTitle: 'Guía del Turista',
  brandSubtitle: 'Inteligente',
  languageSelectorLabel: 'Idioma de la interfaz y del itinerario',
  visitorSession: 'Sesión de visitante',
  visitorModeButton: 'Modo visitante',
  restoreGooglePrefix: 'Volver a',
  logout: 'Salir',
  logoutAria: 'Cerrar sesión',
  continueVisitor: 'Continuar como visitante',
  signingIn: 'Ingresando…',
  offlineBanner: 'Estás sin conexión. La planificación volverá cuando regrese internet.',
  introMark: 'Brasil de punta a punta',
  introHeading: 'Tu viaje comienza con un plan que tiene sentido.',
  introBody: 'Ruta, autonomía, estaciones reguladas ANP, chat con IA y envío directo por Correo o WhatsApp.',
  introOrigin: 'Origen',
  introDestination: 'Destino',
  signinHeading: 'Inicia sesión para abrir el planificador',
  signinButton: 'Explorar como visitante',
  plannerTitle: 'Planifica tu próxima ruta',
  plannerSubtitle: 'Cuéntanos lo esencial. Organizamos el viaje.',
  originLabel: 'Origen',
  destinationLabel: 'Destino',
  useLocation: 'Usar mi ubicación',
  planButton: 'Planificar viaje',
  planningButton: 'Planificando tu viaje…',
  calculatedRoute: 'Itinerario calculado',
  sendEmailButton: 'Enviar por Correo',
  sendWhatsAppButton: 'Enviar por WhatsApp',
  historyTitle: 'Viajes guardados',
  historySubtitle: 'Tu historial acompaña la sesión.',
  historyEmptyTitle: 'Aún no hay viajes',
  footerLeft: 'Guía del Turista Inteligente · V3',
  metricDistance: 'Distancia',
  metricDuration: 'Tiempo estimado',
  metricWeather: 'Clima en destino',
  metricElevation: 'Desnivel positivo',
  metricTotalCost: 'Costo total',
  metricPerTraveler: 'Por viajero',
  mapHintAnp: 'Haz clic en un marcador de estación en el mapa para ver los datos regulatorios de la ANP.',
  mapDeparture: 'Salida',
  mapDestination: 'Destino',
  anpBadge: 'Estación regulada ANP',
  anpCorporateName: 'Razón Social',
  anpCnpj: 'CNPJ',
  anpRating: 'Calificación',
  anpAuthTime: 'Tiempo de autorización ANP',
  anpFuels: 'Combustibles',
  anpRanking: 'Ranking ANP',
  anpEstimatedStop: 'Parada estimada en la ruta',
  yearsSuffix: 'años',
  guideTitle: 'Guía del viajero',
  chatTitle: 'Personaliza tu itinerario con IA',
  chatSubtitle: 'Indica tu ritmo de viaje, acompañantes y preferencias gastronómicas.',
  chatPaceLabel: 'Ritmo de viaje',
  chatPaceRelaxed: 'Tranquilo',
  chatPaceModerate: 'Moderado',
  chatPaceIntense: 'Intenso',
  chatCompanionsLabel: 'Acompañantes',
  chatGastronomyLabel: 'Gastronomía',
  chatInputPlaceholder: 'Pide ajustes en el itinerario o consejos locales…',
  chatSend: 'Enviar',
  chatSending: 'Consultando…',
  chatPreservedHeritage: 'Patrimonios locales preservados',
  chatErrorFriendly: 'Nuestro asistente está organizando las sugerencias. Intenta de nuevo en unos instantes.',
  dispatchTitle: 'Recibir itinerario completo',
  dispatchSubtitle: 'Elige cómo prefieres recibir tu itinerario personalizado.',
  dispatchChannelEmail: 'Correo (HTML)',
  dispatchEmailLabel: 'Correo electrónico',
  dispatchWhatsAppLabel: 'Número de WhatsApp',
  dispatchSubmit: 'Enviar itinerario',
  dispatchSubmitting: 'Enviando itinerario…',
  dispatchClose: 'Cerrar',
  dispatchErrorFriendly: 'No pudimos completar el envío ahora. Intenta nuevamente en unos instantes.',
  errorServiceFriendly: 'Estamos ajustando algunos detalles. Intenta nuevamente en unos instantes.',
}

const fr: TranslationKeys = {
  ...en,
  brandTitle: 'Guide Touristique',
  brandSubtitle: 'Intelligent',
  languageSelectorLabel: 'Langue de l’interface et de l’itinéraire',
  visitorSession: 'Session visiteur',
  logout: 'Déconnexion',
  continueVisitor: 'Continuer en visiteur',
  introHeading: 'Votre voyage commence par un plan clair.',
  plannerTitle: 'Planifiez votre prochain itinéraire',
  originLabel: 'Origine',
  destinationLabel: 'Destination',
  planButton: 'Planifier le voyage',
  calculatedRoute: 'Itinéraire calculé',
  sendEmailButton: 'Envoyer par E-mail',
  sendWhatsAppButton: 'Envoyer par WhatsApp',
  historyTitle: 'Voyages enregistrés',
  footerLeft: 'Guide Touristique Intelligent · V3',
  metricDistance: 'Distance',
  metricDuration: 'Durée estimée',
  metricWeather: 'Météo à destination',
  metricElevation: 'Dénivelé positif',
  metricTotalCost: 'Coût total',
  metricPerTraveler: 'Par voyageur',
  mapHintAnp: 'Cliquez sur un marqueur de station pour consulter les données réglementaires ANP.',
  anpBadge: 'Station régulée ANP',
  anpCorporateName: 'Raison Sociale',
  anpRating: 'Évaluation',
  anpAuthTime: 'Durée d’autorisation ANP',
  anpFuels: 'Carburants',
  anpRanking: 'Classement ANP',
  yearsSuffix: 'ans',
  guideTitle: 'Guide du voyageur',
  chatTitle: 'Personnalisez votre itinéraire avec l’IA',
  chatPaceLabel: 'Rythme de voyage',
  chatPaceRelaxed: 'Tranquille',
  chatPaceModerate: 'Modéré',
  chatPaceIntense: 'Intense',
  chatCompanionsLabel: 'Compagnons',
  chatGastronomyLabel: 'Gastronomie',
  chatSend: 'Envoyer',
  chatSending: 'Envoi…',
  chatPreservedHeritage: 'Patrimoines locaux préservés',
  dispatchTitle: 'Recevoir l’itinéraire complet',
  dispatchChannelEmail: 'E-mail (HTML)',
  dispatchSubmit: 'Envoyer l’itinéraire',
  dispatchClose: 'Fermer',
  errorServiceFriendly: 'Nous ajustons quelques détails. Veuillez réessayer dans un instant.',
}

const zh: TranslationKeys = {
  ...en,
  brandTitle: '智能旅游指南',
  brandSubtitle: 'V3',
  languageSelectorLabel: '界面和行程语言',
  visitorSession: '访客会话',
  logout: '退出',
  continueVisitor: '以访客身份继续',
  introHeading: '让每一次旅程从清晰的计划开始。',
  plannerTitle: '规划您的下一段行程',
  originLabel: '出发地',
  destinationLabel: '目的地',
  planButton: '开始规划',
  calculatedRoute: '已规划行程',
  sendEmailButton: '通过电子邮件发送',
  sendWhatsAppButton: '通过 WhatsApp 发送',
  historyTitle: '已保存的行程',
  footerLeft: '智能旅游指南 · V3',
  metricDistance: '距离',
  metricDuration: '预计时间',
  metricWeather: '目的地天气',
  metricElevation: '累计爬升',
  metricTotalCost: '总费用',
  metricPerTraveler: '人均费用',
  mapHintAnp: '点击地图上的加油站标记即可查看 ANP 监管详情。',
  anpBadge: 'ANP 认证加油站',
  anpCorporateName: '企业名称',
  anpRating: '评分',
  anpAuthTime: 'ANP 授权时长',
  anpFuels: '可用燃油',
  anpRanking: 'ANP 排名',
  yearsSuffix: '年',
  guideTitle: '旅行指南',
  chatTitle: '与 AI 定制您的专属行程',
  chatPaceLabel: '旅行节奏',
  chatPaceRelaxed: '悠闲',
  chatPaceModerate: '适中',
  chatPaceIntense: '紧凑',
  chatCompanionsLabel: '同行人员',
  chatGastronomyLabel: '美食偏好',
  chatSend: '发送',
  chatSending: '思考中…',
  chatPreservedHeritage: '保留原名的当地遗产',
  dispatchTitle: '接收完整行程',
  dispatchChannelEmail: '电子邮件 (HTML)',
  dispatchSubmit: '发送行程',
  dispatchClose: '关闭',
  errorServiceFriendly: '系统正在调整细节，请稍后再试。',
}

const hi: TranslationKeys = {
  ...en,
  brandTitle: 'स्मार्ट टूरिस्ट गाइड',
  brandSubtitle: 'V3',
  languageSelectorLabel: 'इंटरफ़ेस और यात्रा कार्यक्रम की भाषा',
  visitorSession: 'विज़िटर सत्र',
  logout: 'बाहर निकलें',
  continueVisitor: 'विज़िटर के रूप में जारी रखें',
  introHeading: 'आपकी यात्रा एक स्मार्ट योजना से शुरू होती है।',
  plannerTitle: 'अपना अगला मार्ग प्लान करें',
  originLabel: 'प्रस्थान',
  destinationLabel: 'गंतव्य',
  planButton: 'यात्रा प्लान करें',
  calculatedRoute: 'तैयार यात्रा कार्यक्रम',
  sendEmailButton: 'ईमेल द्वारा भेजें',
  sendWhatsAppButton: 'WhatsApp द्वारा भेजें',
  historyTitle: 'सहेजी गई यात्राएँ',
  footerLeft: 'स्मार्ट टूरिस्ट गाइड · V3',
  metricDistance: 'दूरी',
  metricDuration: 'अनुमानित समय',
  metricWeather: 'गंतव्य मौसम',
  metricElevation: 'ऊँचाई लाभ',
  metricTotalCost: 'कुल लागत',
  metricPerTraveler: 'प्रति यात्री',
  mapHintAnp: 'ANP नियामक विवरण देखने के लिए मानचित्र पर ईंधन स्टेशन मार्कर पर क्लिक करें।',
  anpBadge: 'ANP विनियमित स्टेशन',
  anpCorporateName: 'कंपनी का नाम',
  anpRating: 'रेटिंग',
  anpAuthTime: 'ANP प्राधिकरण अवधि',
  anpFuels: 'उपलब्ध ईंधन',
  anpRanking: 'ANP रैंकिंग',
  yearsSuffix: 'वर्ष',
  guideTitle: 'यात्री गाइड',
  chatTitle: 'AI के साथ अपना यात्रा कार्यक्रम निजीकृत करें',
  chatPaceLabel: 'यात्रा की गति',
  chatPaceRelaxed: 'आरामदायक',
  chatPaceModerate: 'मध्यम',
  chatPaceIntense: 'तेज़',
  chatCompanionsLabel: 'साथी यात्री',
  chatGastronomyLabel: 'खान-पान पसंद',
  chatSend: 'भेजें',
  chatSending: 'भेजा जा रहा है…',
  chatPreservedHeritage: 'संरक्षित स्थानीय धरोहर नाम',
  dispatchTitle: 'पूरा यात्रा कार्यक्रम प्राप्त करें',
  dispatchChannelEmail: 'ईमेल (HTML)',
  dispatchSubmit: 'यात्रा कार्यक्रम भेजें',
  dispatchClose: 'बंद करें',
  errorServiceFriendly: 'हम अभी कुछ विवरण ठीक कर रहे हैं। कृपया थोड़ी देर बाद फिर प्रयास करें।',
}

const ar: TranslationKeys = {
  ...en,
  brandTitle: 'دليل السائح الذكي',
  brandSubtitle: 'V3',
  languageSelectorLabel: 'لغة الواجهة ومسار الرحلة',
  visitorSession: 'جلسة زائر',
  logout: 'تسجيل الخروج',
  continueVisitor: 'المتابعة كزائر',
  introHeading: 'تبدأ رحلتك بخطة ذكية وواضحة.',
  plannerTitle: 'خطط لمسار رحلتك القادم',
  originLabel: 'نقطة الانطلاق',
  destinationLabel: 'الوجهة',
  planButton: 'تخطيط الرحلة',
  calculatedRoute: 'مسار الرحلة المحسوب',
  sendEmailButton: 'إرسال عبر البريد',
  sendWhatsAppButton: 'إرسال عبر واتساب',
  historyTitle: 'الرحلات المحفوظة',
  footerLeft: 'دليل السائح الذكي · V3',
  metricDistance: 'المسافة',
  metricDuration: 'الوقت المتوقع',
  metricWeather: 'طقس الوجهة',
  metricElevation: 'الارتفاع المكتسب',
  metricTotalCost: 'التكلفة الإجمالية',
  metricPerTraveler: 'لكل مسافر',
  mapHintAnp: 'انقر على علامة محطة الوقود على الخريطة لعرض البيانات التنظيمية لـ ANP.',
  anpBadge: 'محطة معتمدة من ANP',
  anpCorporateName: 'الاسم القانوني',
  anpCnpj: 'رقم CNPJ',
  anpRating: 'التقييم',
  anpAuthTime: 'مدة ترخيص ANP',
  anpFuels: 'الوقود المتاح',
  anpRanking: 'تصنيف ANP',
  yearsSuffix: 'سنوات',
  guideTitle: 'دليل المسافر',
  chatTitle: 'خصّص رحلتك مع الذكاء الاصطناعي',
  chatPaceLabel: 'وتيرة الرحلة',
  chatPaceRelaxed: 'هادئة',
  chatPaceModerate: 'معتدلة',
  chatPaceIntense: 'مكثفة',
  chatCompanionsLabel: 'المرافقون',
  chatGastronomyLabel: 'المأكولات المفضلة',
  chatSend: 'إرسال',
  chatSending: 'جارٍ الإرسال…',
  chatPreservedHeritage: 'المعالم المحلية المحفوظة بأسمائها الأصلية',
  dispatchTitle: 'استلام مسار الرحلة الكامل',
  dispatchChannelEmail: 'البريد الإلكتروني (HTML)',
  dispatchChannelWhatsApp: 'واتساب',
  dispatchSubmit: 'إرسال المسار',
  dispatchClose: 'إغلاق',
  errorServiceFriendly: 'نقوم بضبط بعض التفاصيل حالياً. يرجى المحاولة مرة أخرى بعد لحظات.',
}

const ru: TranslationKeys = {
  ...en,
  brandTitle: 'Умный гид туриста',
  brandSubtitle: 'V3',
  languageSelectorLabel: 'Язык интерфейса и маршрута',
  visitorSession: 'Гостевая сессия',
  logout: 'Выйти',
  continueVisitor: 'Продолжить как гость',
  introHeading: 'Путешествие начинается с понятного плана.',
  plannerTitle: 'Спланируйте следующий маршрут',
  originLabel: 'Откуда',
  destinationLabel: 'Куда',
  planButton: 'Построить маршрут',
  calculatedRoute: 'Готовый маршрут',
  sendEmailButton: 'Отправить на E-mail',
  sendWhatsAppButton: 'Отправить в WhatsApp',
  historyTitle: 'Сохранённые поездки',
  footerLeft: 'Умный гид туриста · V3',
  metricDistance: 'Расстояние',
  metricDuration: 'Время в пути',
  metricWeather: 'Погода в пункте назначения',
  metricElevation: 'Набор высоты',
  metricTotalCost: 'Общая стоимость',
  metricPerTraveler: 'На путешественника',
  mapHintAnp: 'Нажмите на маркер АЗС на карте, чтобы увидеть регуляторные данные ANP.',
  anpBadge: 'Сертифицированная АЗС ANP',
  anpCorporateName: 'Юридическое название',
  anpRating: 'Рейтинг',
  anpAuthTime: 'Срок лицензии ANP',
  anpFuels: 'Виды топлива',
  anpRanking: 'Рейтинг ANP',
  yearsSuffix: 'лет',
  guideTitle: 'Путеводитель',
  chatTitle: 'Настройте маршрут с помощью ИИ',
  chatPaceLabel: 'Темп путешествия',
  chatPaceRelaxed: 'Спокойный',
  chatPaceModerate: 'Умеренный',
  chatPaceIntense: 'Насыщенный',
  chatCompanionsLabel: 'Попутчики',
  chatGastronomyLabel: 'Гастрономия',
  chatSend: 'Отправить',
  chatSending: 'Отправка…',
  chatPreservedHeritage: 'Сохранённые названия местных достопримечательностей',
  dispatchTitle: 'Получить полный маршрут',
  dispatchChannelEmail: 'E-mail (HTML)',
  dispatchSubmit: 'Отправить маршрут',
  dispatchClose: 'Закрыть',
  errorServiceFriendly: 'Мы уточняем несколько деталей. Пожалуйста, попробуйте чуть позже.',
}

export const TRANSLATIONS: Record<SupportedLanguage, TranslationKeys> = {
  'pt-BR': ptBR,
  en,
  es,
  fr,
  zh,
  hi,
  ar,
  ru,
}
