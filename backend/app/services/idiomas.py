"""Suporte multilíngue do guia e do chat: idiomas aceitos, textos de contingência e patrimônios locais.

Regra obrigatória da V3: nomes próprios de patrimônios locais (ex.: "Parque Nacional de Sete Cidades",
"Serra da Capivara", "Delta do Parnaíba", "BR-343", "Pelourinho") nunca são traduzidos literalmente,
em nenhum idioma. O prompt pede isso ao Gemini e `preservar_patrimonios` corrige a resposta caso
alguma tradução literal conhecida escape.
"""

import re
import unicodedata
from typing import Any

IDIOMA_PADRAO = "pt"

# Código ISO 639-1 -> nome do idioma usado na instrução do prompt
NOMES_IDIOMA: dict[str, str] = {
    "pt": "português do Brasil",
    "en": "inglês (English)",
    "es": "espanhol (Español)",
    "fr": "francês (Français)",
    "zh": "mandarim em chinês simplificado (简体中文)",
    "hi": "hindi (हिन्दी)",
    "ar": "árabe (العربية)",
    "ru": "russo (Русский)",
}


def normalizar_codigo_idioma(idioma: str | None) -> str:
    """'en-US' -> 'en', 'pt_BR' -> 'pt'; vazio ou idioma não suportado -> 'pt'."""
    codigo = re.split(r"[-_;,\s]", (idioma or "").strip().lower(), maxsplit=1)[0]
    return codigo if codigo in NOMES_IDIOMA else IDIOMA_PADRAO


def normalizar_texto(texto: str) -> str:
    """Minúsculo e sem acentos, para comparações tolerantes."""
    nfkd = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


# --------------------------------------------------------------------------- patrimônios locais

# Cidade (normalizada, sem UF) -> patrimônios locais preservados no diálogo, em ordem de relevância
PATRIMONIOS_POR_CIDADE: dict[str, tuple[str, ...]] = {
    "piripiri": ("Parque Nacional de Sete Cidades", "Açude Caldeirão", "BR-343"),
    "piracuruca": ("Parque Nacional de Sete Cidades", "Cachoeira do Riachão", "BR-343"),
    "campo maior": ("Monumento do Jenipapo", "Açude Grande de Campo Maior", "BR-343"),
    "parnaiba": ("Delta do Parnaíba", "Porto das Barcas", "Lagoa do Portinho", "BR-343"),
    "luis correia": ("Delta do Parnaíba", "Praia de Atalaia", "Lagoa do Portinho"),
    "teresina": ("Encontro dos Rios", "Ponte Estaiada João Luís Ferreira", "Polo Cerâmico do Poti Velho"),
    "sao raimundo nonato": ("Serra da Capivara", "Museu do Homem Americano"),
    "salvador": ("Pelourinho", "Elevador Lacerda", "Mercado Modelo"),
    "lencois": ("Chapada Diamantina", "Morro do Pai Inácio"),
    "barreirinhas": ("Lençóis Maranhenses", "Lagoa Azul"),
    "fernando de noronha": ("Baía do Sancho", "Baía dos Porcos", "Forte de Nossa Senhora dos Remédios"),
    "brasilia": ("Congresso Nacional", "Catedral Metropolitana", "Esplanada dos Ministérios"),
    "fortaleza": ("Praia de Iracema", "Centro Dragão do Mar de Arte e Cultura", "Mercado Central"),
    "recife": ("Recife Antigo", "Marco Zero", "Instituto Ricardo Brennand"),
    "rio de janeiro": ("Cristo Redentor", "Pão de Açúcar", "Escadaria Selarón"),
    "sao paulo": ("Avenida Paulista", "Mercado Municipal de São Paulo", "Pinacoteca"),
    "tiangua": ("Serra da Ibiapaba", "Bica do Ipu"),
}

# Patrimônio -> traduções literais conhecidas que devem voltar ao nome original
TRADUCOES_LITERAIS: dict[str, tuple[str, ...]] = {
    "Parque Nacional de Sete Cidades": (
        "Seven Cities National Park",
        "National Park of Seven Cities",
        "Parque Nacional de las Siete Ciudades",
        "Parque Nacional de Siete Ciudades",
        "Parc national des Sept Villes",
        "Parc national des Sept Cités",
        "Национальный парк Семь городов",
        "七城国家公园",
        "सात शहर राष्ट्रीय उद्यान",
        "حديقة المدن السبع الوطنية",
    ),
    "Serra da Capivara": (
        "Capybara Mountains",
        "Capybara Range",
        "Capybara Hills",
        "Sierra del Carpincho",
        "Sierra de la Capibara",
        "Montagnes du Capybara",
        "Горы Капибары",
        "水豚山",
    ),
    "Delta do Parnaíba": ("Parnaíba Delta", "Parnaiba Delta", "Delta del Parnaíba", "Delta du Parnaíba"),
    "Açude Caldeirão": ("Cauldron Reservoir", "Cauldron Dam", "Embalse del Caldero", "Réservoir du Chaudron"),
    "Lençóis Maranhenses": ("Maranhão Sheets", "Sheets of Maranhão", "Sábanas de Maranhão", "Draps du Maranhão"),
    "Chapada Diamantina": ("Diamond Plateau", "Diamantina Plateau", "Meseta Diamantina", "Plateau Diamantin"),
    "Encontro dos Rios": ("Meeting of the Rivers", "Meeting of the Waters", "Encuentro de los Ríos", "Rencontre des Rivières"),
    "Congresso Nacional": ("National Congress", "Congrès national"),
    "Pão de Açúcar": ("Sugarloaf Mountain", "Sugar Loaf Mountain", "Sugarloaf", "Pan de Azúcar", "Pain de Sucre"),
    "Cristo Redentor": ("Christ the Redeemer", "Christ Rédempteur", "Христос-Искупитель"),
    "Pelourinho": ("Pillory Square", "The Pillory"),
}

PATRIMONIOS_CONHECIDOS: tuple[str, ...] = tuple(
    dict.fromkeys([*TRADUCOES_LITERAIS, *(p for itens in PATRIMONIOS_POR_CIDADE.values() for p in itens)])
)


def _nome_cidade(destino: str) -> str:
    return re.sub(r"\s*-\s*[A-Za-z]{2}$", "", (destino or "").strip()).strip()


def identificar_patrimonios(destino: str, *textos: str) -> list[str]:
    """Patrimônios a preservar: os citados pelo viajante (inclusive por tradução literal) e os da cidade."""
    encontrados: list[str] = []
    conteudo = normalizar_texto(" ".join(t for t in textos if t))
    for patrimonio in PATRIMONIOS_CONHECIDOS:
        variantes = (patrimonio, *TRADUCOES_LITERAIS.get(patrimonio, ()))
        if any(normalizar_texto(v) in conteudo for v in variantes):
            encontrados.append(patrimonio)

    cidade = normalizar_texto(_nome_cidade(destino))
    encontrados.extend(p for p in PATRIMONIOS_POR_CIDADE.get(cidade, ()) if p not in encontrados)
    return encontrados


def preservar_patrimonios(texto: str, patrimonios: list[str] | None = None) -> str:
    """Substitui traduções literais conhecidas pelo nome próprio original (sem diferenciar maiúsculas)."""
    if not texto:
        return ""
    alvo = patrimonios if patrimonios is not None else list(TRADUCOES_LITERAIS)
    pares = [(t, original) for original in alvo for t in TRADUCOES_LITERAIS.get(original, ())]
    # Traduções mais longas primeiro, para "Sugarloaf Mountain" não virar "Pão de Açúcar Mountain"
    for traducao, original in sorted(pares, key=lambda par: len(par[0]), reverse=True):
        # Limite de palavra só faz sentido em escrita latina; em chinês não há espaços entre palavras
        inicio = r"(?<!\w)(the\s+)?" if traducao[0].isascii() else ""
        fim = r"(?!\w)" if traducao[-1].isascii() else ""
        texto = re.sub(f"{inicio}{re.escape(traducao)}{fim}", original, texto, flags=re.IGNORECASE)
    return texto


# --------------------------------------------------------------------------- textos localizados

# Textos dos fallbacks (guia de contingência e chat sem IA). Nomes próprios entram sempre sem tradução.
TEXTOS: dict[str, dict[str, Any]] = {
    "pt": {
        "titulos": ("🏛️ IDENTIDADE", "🗺️ ROTEIRO", "🍲 GASTRONOMIA", "💡 DICA PRÁTICA"),
        "turnos": ("Manhã", "Tarde", "Noite"),
        "dia": "Dia {n}",
        "identidade": "{cidade}, destino de cultura, sabores e paisagens marcantes do Brasil.",
        "prove": "Prove {pratos}.",
        "locais_genericos": ("o centro histórico de {cidade}", "os parques e mirantes da região", "o mercado e a feira locais"),
        "gastronomia_generica": "Prove a culinária regional em restaurantes de comida caseira e feiras da cidade.",
        "dica_generica": "Passeie ao ar livre nas primeiras horas da manhã, com temperaturas mais amenas.",
        "dica_calor": "Com {t} °C, use roupa leve e protetor solar e passeie cedo ou ao fim da tarde.",
        "dica_ameno": "Com {t} °C, roupa leve resolve; leve um agasalho fino para a noite.",
        "dica_frio": "Com {t} °C, leve agasalho e deixe os passeios ao ar livre para o meio do dia.",
        "chat_intro": "Roteiro para {destino}: {dias} dia(s), ritmo {ritmo}, com {acompanhantes}.",
        "chat_gastronomia": "Sabores para buscar: {gastronomia}.",
        "chat_ajuste": "Ajustado ao seu pedido: “{pedido}”.",
        "chat_sugestoes": (
            "Quais restaurantes típicos ficam perto da rota?",
            "Como adaptar o roteiro para um dia de chuva?",
            "Onde abastecer com segurança na BR-343?",
        ),
    },
    "en": {
        "titulos": ("🏛️ IDENTITY", "🗺️ ITINERARY", "🍲 FOOD", "💡 PRACTICAL TIP"),
        "turnos": ("Morning", "Afternoon", "Evening"),
        "dia": "Day {n}",
        "identidade": "{cidade}, a Brazilian destination of culture, flavors and striking landscapes.",
        "prove": "Try {pratos}.",
        "locais_genericos": ("the historic center of {cidade}", "the parks and viewpoints of the region", "the local market and street fair"),
        "gastronomia_generica": "Try the regional cuisine at home-style restaurants and local fairs.",
        "dica_generica": "Plan outdoor walks for the early morning, when temperatures are milder.",
        "dica_calor": "At {t} °C, wear light clothes and sunscreen, and go out early or late in the afternoon.",
        "dica_ameno": "At {t} °C, light clothes are enough; bring a thin jacket for the evening.",
        "dica_frio": "At {t} °C, bring a jacket and keep outdoor visits for midday.",
        "chat_intro": "Itinerary for {destino}: {dias} day(s), {ritmo} pace, traveling with {acompanhantes}.",
        "chat_gastronomia": "Flavors to look for: {gastronomia}.",
        "chat_ajuste": "Adjusted to your request: “{pedido}”.",
        "chat_sugestoes": (
            "Which traditional restaurants are close to the route?",
            "How can I adapt the plan for a rainy day?",
            "Where can I refuel safely along BR-343?",
        ),
    },
    "es": {
        "titulos": ("🏛️ IDENTIDAD", "🗺️ ITINERARIO", "🍲 GASTRONOMÍA", "💡 CONSEJO PRÁCTICO"),
        "turnos": ("Mañana", "Tarde", "Noche"),
        "dia": "Día {n}",
        "identidade": "{cidade}, destino brasileño de cultura, sabores y paisajes inolvidables.",
        "prove": "Pruebe {pratos}.",
        "locais_genericos": ("el centro histórico de {cidade}", "los parques y miradores de la región", "el mercado y la feria local"),
        "gastronomia_generica": "Pruebe la cocina regional en restaurantes caseros y ferias de la ciudad.",
        "dica_generica": "Haga los paseos al aire libre temprano, con temperaturas más suaves.",
        "dica_calor": "Con {t} °C, use ropa ligera y protector solar, y salga temprano o al final de la tarde.",
        "dica_ameno": "Con {t} °C, basta ropa ligera; lleve un abrigo fino para la noche.",
        "dica_frio": "Con {t} °C, lleve abrigo y deje los paseos al aire libre para el mediodía.",
        "chat_intro": "Itinerario para {destino}: {dias} día(s), ritmo {ritmo}, con {acompanhantes}.",
        "chat_gastronomia": "Sabores que buscar: {gastronomia}.",
        "chat_ajuste": "Ajustado a su pedido: “{pedido}”.",
        "chat_sugestoes": (
            "¿Qué restaurantes típicos hay cerca de la ruta?",
            "¿Cómo adapto el plan para un día de lluvia?",
            "¿Dónde repostar con seguridad en la BR-343?",
        ),
    },
    "fr": {
        "titulos": ("🏛️ IDENTITÉ", "🗺️ ITINÉRAIRE", "🍲 GASTRONOMIE", "💡 CONSEIL PRATIQUE"),
        "turnos": ("Matin", "Après-midi", "Soir"),
        "dia": "Jour {n}",
        "identidade": "{cidade}, destination brésilienne de culture, de saveurs et de paysages marquants.",
        "prove": "Goûtez {pratos}.",
        "locais_genericos": ("le centre historique de {cidade}", "les parcs et belvédères de la région", "le marché et la foire locale"),
        "gastronomia_generica": "Goûtez la cuisine régionale dans les restaurants familiaux et les foires de la ville.",
        "dica_generica": "Prévoyez les balades en plein air tôt le matin, quand il fait plus doux.",
        "dica_calor": "Avec {t} °C, portez des vêtements légers et de la crème solaire ; sortez tôt ou en fin d'après-midi.",
        "dica_ameno": "Avec {t} °C, des vêtements légers suffisent ; prenez une petite veste pour le soir.",
        "dica_frio": "Avec {t} °C, prenez une veste et gardez les visites en plein air pour la mi-journée.",
        "chat_intro": "Itinéraire pour {destino} : {dias} jour(s), rythme {ritmo}, avec {acompanhantes}.",
        "chat_gastronomia": "Saveurs à découvrir : {gastronomia}.",
        "chat_ajuste": "Adapté à votre demande : « {pedido} ».",
        "chat_sugestoes": (
            "Quels restaurants typiques se trouvent près du trajet ?",
            "Comment adapter le programme à un jour de pluie ?",
            "Où faire le plein en sécurité sur la BR-343 ?",
        ),
    },
    "zh": {
        "titulos": ("🏛️ 城市印象", "🗺️ 行程", "🍲 美食", "💡 实用贴士"),
        "turnos": ("上午", "下午", "晚上"),
        "dia": "第{n}天",
        "identidade": "{cidade}：融合文化、美食与壮丽风景的巴西目的地。",
        "prove": "推荐品尝：{pratos}。",
        "locais_genericos": ("{cidade} 历史中心", "当地公园与观景台", "当地市场与集市"),
        "gastronomia_generica": "在家常餐馆和当地集市品尝地方特色菜。",
        "dica_generica": "户外活动尽量安排在清晨，气温更舒适。",
        "dica_calor": "气温 {t} °C：穿轻便衣物并涂防晒霜，尽量清晨或傍晚出行。",
        "dica_ameno": "气温 {t} °C：轻便衣物即可，晚上带一件薄外套。",
        "dica_frio": "气温 {t} °C：请带外套，户外活动安排在中午前后。",
        "chat_intro": "{destino} 行程：{dias} 天，节奏：{ritmo}，同行：{acompanhantes}。",
        "chat_gastronomia": "美食推荐：{gastronomia}。",
        "chat_ajuste": "已根据您的要求调整：“{pedido}”。",
        "chat_sugestoes": ("路线附近有哪些地道餐厅？", "下雨天如何调整行程？", "BR-343 沿线哪里可以安全加油？"),
    },
    "hi": {
        "titulos": ("🏛️ पहचान", "🗺️ यात्रा कार्यक्रम", "🍲 व्यंजन", "💡 व्यावहारिक सुझाव"),
        "turnos": ("सुबह", "दोपहर", "शाम"),
        "dia": "दिन {n}",
        "identidade": "{cidade}, संस्कृति, स्वाद और सुंदर दृश्यों वाला ब्राज़ील का गंतव्य।",
        "prove": "ज़रूर चखें: {pratos}।",
        "locais_genericos": ("{cidade} का ऐतिहासिक केंद्र", "क्षेत्र के पार्क और व्यू पॉइंट", "स्थानीय बाज़ार और मेला"),
        "gastronomia_generica": "घरेलू रेस्तरां और स्थानीय मेलों में क्षेत्रीय व्यंजन चखें।",
        "dica_generica": "बाहर घूमने की योजना सुबह जल्दी बनाएँ, जब तापमान कम हो।",
        "dica_calor": "{t} °C पर हल्के कपड़े और सनस्क्रीन इस्तेमाल करें; सुबह जल्दी या शाम को घूमें।",
        "dica_ameno": "{t} °C पर हल्के कपड़े काफ़ी हैं; रात के लिए पतली जैकेट रखें।",
        "dica_frio": "{t} °C पर जैकेट रखें और बाहर की सैर दोपहर में करें।",
        "chat_intro": "{destino} के लिए कार्यक्रम: {dias} दिन, गति: {ritmo}, साथ: {acompanhantes}।",
        "chat_gastronomia": "आज़माने लायक स्वाद: {gastronomia}।",
        "chat_ajuste": "आपके अनुरोध के अनुसार बदला गया: “{pedido}”।",
        "chat_sugestoes": ("मार्ग के पास कौन से पारंपरिक रेस्तरां हैं?", "बारिश के दिन के लिए योजना कैसे बदलें?", "BR-343 पर सुरक्षित ईंधन कहाँ भरवाएँ?"),
    },
    "ar": {
        "titulos": ("🏛️ الهوية", "🗺️ البرنامج", "🍲 المطبخ", "💡 نصيحة عملية"),
        "turnos": ("الصباح", "بعد الظهر", "المساء"),
        "dia": "اليوم {n}",
        "identidade": "{cidade}، وجهة برازيلية للثقافة والنكهات والمناظر الخلابة.",
        "prove": "جرّب {pratos}.",
        "locais_genericos": ("المركز التاريخي في {cidade}", "الحدائق ونقاط المشاهدة في المنطقة", "السوق والمعرض المحلي"),
        "gastronomia_generica": "جرّب المطبخ الإقليمي في المطاعم المنزلية والأسواق المحلية.",
        "dica_generica": "خطط للنزهات في الهواء الطلق في الصباح الباكر حين تكون الحرارة ألطف.",
        "dica_calor": "مع {t} °C ارتدِ ملابس خفيفة واستخدم واقي الشمس، وتجول باكرًا أو آخر النهار.",
        "dica_ameno": "مع {t} °C تكفي الملابس الخفيفة؛ خذ سترة خفيفة للمساء.",
        "dica_frio": "مع {t} °C خذ سترة واجعل الزيارات الخارجية في منتصف النهار.",
        "chat_intro": "برنامج رحلة إلى {destino}: {dias} يوم، بوتيرة {ritmo}، برفقة {acompanhantes}.",
        "chat_gastronomia": "نكهات تستحق التجربة: {gastronomia}.",
        "chat_ajuste": "تم التعديل حسب طلبك: «{pedido}».",
        "chat_sugestoes": ("ما المطاعم التقليدية القريبة من الطريق؟", "كيف أعدّل البرنامج ليوم ممطر؟", "أين أتزود بالوقود بأمان على BR-343؟"),
    },
    "ru": {
        "titulos": ("🏛️ ОБРАЗ ГОРОДА", "🗺️ МАРШРУТ", "🍲 ГАСТРОНОМИЯ", "💡 ПРАКТИЧЕСКИЙ СОВЕТ"),
        "turnos": ("Утро", "День", "Вечер"),
        "dia": "День {n}",
        "identidade": "{cidade} — бразильское направление с богатой культурой, вкусами и пейзажами.",
        "prove": "Попробуйте {pratos}.",
        "locais_genericos": ("исторический центр {cidade}", "парки и смотровые площадки региона", "местный рынок и ярмарку"),
        "gastronomia_generica": "Попробуйте региональную кухню в домашних ресторанах и на местных ярмарках.",
        "dica_generica": "Планируйте прогулки рано утром, когда не так жарко.",
        "dica_calor": "При {t} °C носите лёгкую одежду и солнцезащитный крем, гуляйте утром или под вечер.",
        "dica_ameno": "При {t} °C достаточно лёгкой одежды; возьмите тонкую куртку на вечер.",
        "dica_frio": "При {t} °C возьмите куртку и планируйте прогулки на середину дня.",
        "chat_intro": "Маршрут в {destino}: {dias} дн., темп: {ritmo}, компания: {acompanhantes}.",
        "chat_gastronomia": "Что попробовать: {gastronomia}.",
        "chat_ajuste": "Учтён ваш запрос: «{pedido}».",
        "chat_sugestoes": ("Какие традиционные рестораны есть рядом с маршрутом?", "Как изменить план на дождливый день?", "Где безопасно заправиться на BR-343?"),
    },
}


def textos(idioma: str | None) -> dict[str, Any]:
    """Textos localizados do idioma (português quando não suportado)."""
    return TEXTOS[normalizar_codigo_idioma(idioma)]
