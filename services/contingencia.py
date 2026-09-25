"""Guia de contingência determinístico (texto puro com emojis) usado quando a IA falha."""

import re
import unicodedata
from typing import Any

# Base de conhecimento curada para os principais destinos turísticos do Brasil
_GUIAS_CURADOS: dict[str, dict[str, Any]] = {
    "fortaleza": {
        "pontos": [
            "Praia do Futuro: Famosa orla com mega barracas de praia completas (CrocoBeach, Chico do Caranguejo) com piscinas e culinária à beira-mar.",
            "Centro Dragão do Mar de Arte e Cultura: Polo cultural na Praia de Iracema com cinemas de arte, Museu da Cultura Cearense e planetário.",
            "Mercado Central e Feirinha da Beira-Mar: Pontos tradicionais para compra de artesanato em renda de bilro, castanhas de caju, redes e lembranças.",
            "Beach Park (Aquiraz): Um dos maiores parques aquáticos do mundo, localizado a cerca de 25 km da capital.",
        ],
        "culinaria": [
            "Baião de Dois cremoso com carne de sol na chapa, queijo coalho tostado e manteiga de garrafa.",
            "Tradicional Caranguejada servida com farofa de dendê e vinagrete (patrimônio das quintas-feiras cearenses).",
            "Peixada Cearense ao leite de coco e pirão escaldado, acompanhada de cajuína genuína bem gelada.",
        ],
        "dica": "Participe da famosa 'Quinta do Caranguejo' nas barracas da Praia do Futuro. Ao entardecer, caminhe pelo calçadão da Beira-Mar e contemple o pôr do sol no Espigão do Náutico ou na Ponte dos Ingleses.",
    },
    "teresina": {
        "pontos": [
            "Parque Ambiental Encontro dos Rios: Espetacular confluência dos rios Parnaíba e Poti, com quiosques de artesanato em cerâmica do Poti Velho.",
            "Ponte Estaiada João Luís Ferreira: Mirante panorâmico a 95 metros de altura com vista de 360 graus de toda a capital piauiense.",
            "Central de Artesanato Mestre Dezinho e Palácio da Cidade: Referências de patrimônio histórico, arte santeira em talha de madeira e rendas.",
            "Parque da Cidadania: Grande espaço arborizado no centro da cidade, ideal para caminhadas, piqueniques e eventos culturais ao ar livre.",
        ],
        "culinaria": [
            "Maria Isabel (arroz soltinho cozido com carne de sol em cubos) e Capote (galinha-d'angola cozida e servida com pirão).",
            "Paçoca de Carne de Sol socada no pilão com farinha de mandioca fininha e pedaços de banana da terra.",
            "Doces artesanais de caju em calda e a autêntica Cajuína piauiense servida estupidamente gelada.",
        ],
        "dica": "Para fugir do forte calor da 'Chapada do Corisco', priorize passeios ao ar livre e no Encontro dos Rios nas primeiras horas da manhã ou após as 16h30, desfrutando da brisa dos parques fluviais no fim de tarde.",
    },
    "brasilia": {
        "pontos": [
            "Eixo Monumental e Praça dos Três Poderes: Conjunto arquitetônico de Oscar Niemeyer e Lucio Costa tombado pela UNESCO.",
            "Catedral Metropolitana Nossa Senhora Aparecida: Espetaculares vitrais translúcidos de Marianne Peretti e esculturas suspensas de anjos.",
            "Pontão do Lago Sul e Parque da Cidade: Centros de lazer e esportes náuticos com restaurantes à beira do Lago Paranoá.",
            "Memorial JK e Torre de TV: Monumentos históricos com feira de artesanato típico e mirante panorâmico sobre o Plano Piloto.",
        ],
        "culinaria": [
            "Gastronomia cosmopolita de alta gastronomia e pratos com peixes de água doce como tilápia e tucunaré.",
            "Sabores autênticos do Cerrado: galinhada com pequi, baru, doces e picolés artesanais de cagaita e jatobá.",
            "Pastéis de feira e caldinhos de boteco tradicionais nas quadras residenciais das Asas Sul e Norte.",
        ],
        "dica": "O pôr do sol na Ermida Dom Bosco ou no Pontão do Lago Sul é um espetáculo imperdível. Em virtude do clima seco do Planalto Central, mantenha hidratação constante com água e utilize protetor solar.",
    },
    "fernando de noronha": {
        "pontos": [
            "Baía do Sancho: Frequentemente eleita a praia mais deslumbrante do mundo, com águas verde-esmeralda protegidas por falésias.",
            "Baía dos Porcos e Morro Dois Irmãos: O mais famoso cartão-postal do Brasil, ideal para mergulho livre com tartarugas e raias.",
            "Praia do Atalaia e Baía dos Golfinhos: Aquário natural preservado com corais e observatório de golfinhos-rotadores ao nascer do sol.",
            "Praia da Conceição e Mirante do Boldró: Excelentes para assistir ao pôr do sol no mar com vista para o Morro do Pico.",
        ],
        "culinaria": [
            "Peixes nobres e frutos do mar frescos grelhados (cavala, bijupirá, polvo e camarão).",
            "Tubaralhau: Famoso bolinho crocante feito com carne de cação dessalgada, criação gastronômica icônica da ilha.",
            "Mariscada ao leite de coco e tapiocas recheadas nas vilas históricas dos Remédios e do Trinta.",
        ],
        "dica": "Como o acesso é exclusivamente aéreo ou marítimo, planeje os traslados com antecedência. Agende suas trilhas logo no primeiro dia no Centro do ICMBio e leve sua própria máscara de snorkel para aproveitar ao máximo a vida marinha.",
    },
    "salvador": {
        "pontos": [
            "Pelourinho e Centro Histórico: Casarões coloniais barrocos, ruas de paralelepípedo e a suntuosa Igreja de São Francisco banhada a ouro.",
            "Farol da Barra e Elevador Lacerda: Pontos históricos estratégicos com vista panorâmica espetacular da Baía de Todos-os-Santos.",
            "Igreja de Nosso Senhor do Bonfim: Tradição secular da bênção e amarração das fitinhas coloridas nos gradis sagrados.",
            "Dique do Tororó e Rio Vermelho: Esculturas monumentais dos orixás sobre o espelho d'água e o bairro boêmio mais charmoso da capital.",
        ],
        "culinaria": [
            "Acarajé e Abará legítimos no azeite de dendê servidos com vatapá, caruru, salada e camarão seco nos tabuleiros tradicionais.",
            "Moqueca Baiana servida fervente em panela de barro com pescada fresca, camarão, leite de coco e coentro fresco.",
            "Cocadas artesanais de tabuleiro, beijus de tapioca na manteiga e refrescos naturais de mangaba e umbu.",
        ],
        "dica": "Assista ao entardecer no Farol da Barra ou no Museu de Arte Moderna (MAM) com música ao vivo. No Pelourinho, aproveite as terças-feiras da bênção para assistir ao show do Olodum nas ladeiras históricas.",
    },
    "rio de janeiro": {
        "pontos": [
            "Cristo Redentor (Morro do Corcovado) e Pão de Açúcar: As maravilhas mais célebres do Brasil com vistas panorâmicas de tirar o fôlego.",
            "Praias de Copacabana, Ipanema e Leblon: A orla mais famosa do mundo, ideal para caminhadas, água de coco e futevôlei.",
            "Jardim Botânico e Parque Lage: Oásis de Mata Atlântica com palmeiras imperiais centenárias e vista privilegiada do Corcovado.",
            "Lapa e Santa Teresa: Bairros boêmios com os Arcos da Lapa, a Escadaria Selarón e ateliês de arte vibrantes.",
        ],
        "culinaria": [
            "Feijoada Carioca tradicional completa servida com couve mineira, farofa de torresmo, laranja fatiada e caipirinha de cachaça artesanal.",
            "Biscoito Globo e Mate gelado com toque de limão na beira da praia.",
            "Filé à Osvaldo Aranha e petiscos clássicos de botequim (bolinhos de bacalhau e caldinho de feijão preto).",
        ],
        "dica": "Compre ingressos para o trem do Corcovado e bondinho do Pão de Açúcar com antecedência pela internet para evitar filas. Use o metrô e VLT para circular com rapidez e segurança entre a Zona Sul e o Centro Histórico.",
    },
    "sao paulo": {
        "pontos": [
            "Avenida Paulista e MASP: Coração pulsante do país com museus de renome internacional, centros culturais e arquitetura marcante.",
            "Parque Ibirapuera: Principal parque urbano da capital, repleto de lagos, pistas de corrida, Bienal de Artes e auditório de Niemeyer.",
            "Bairro da Liberdade e Beco do Batman: O maior reduto da cultura oriental fora da Ásia e galerias de arte urbana a céu aberto na Vila Madalena.",
            "Pinacoteca do Estado e Mercado Municipal (Mercadão): Arte brasileira de primeira grandeza e o polo gastronômico histórico do centro.",
        ],
        "culinaria": [
            "Famoso Sanduíche de Mortadela com queijo derretido e Pastel de Bacalhau gigante no Mercadão da Cantareira.",
            "Pizzas artesanais napolitanas com fermentação natural nos bairros do Bixiga, Mooca e Pinheiros.",
            "Autêntica gastronomia oriental na Liberdade (lámen artesanal, guiozas no vapor, sushis e doces japoneses tradicionais).",
        ],
        "dica": "Aos domingos, a Avenida Paulista é totalmente fechada para veículos e aberta a ciclistas, pedestres e apresentações de artistas de rua. A rede de metrô paulistana é pontual, limpa e a melhor alternativa para evitar o trânsito da cidade.",
    },
    "recife": {
        "pontos": [
            "Recife Antigo e Praça do Marco Zero: Centro histórico com o Centro de Artesanato de Pernambuco e Centro Cultural Caixa Cultural.",
            "Instituto Ricardo Brennand e Oficina Francisco Brennand: Museu em formato de castelo com acervo de esculturas e armaduras.",
            "Olinda (cidade irmã vizinha a 7 km): Ladeiras coloniais históricas, Alto da Sé com vista para o mar, berço do frevo e do maracatu.",
            "Praia de Boa Viagem: Orla urbanizada com calçadão movimentado e arrecifes naturais que formam piscinas de águas mornas.",
        ],
        "culinaria": [
            "Bolo de Rolo tradicional de massa finíssima com goiabada, reconhecido como Patrimônio Cultural Imaterial.",
            "Carne de Sol com Macaxeira frita, Arrumadinho de feijão verde com vinagrete e Caldinho de Sururu à beira-mar.",
            "Cartola pernambucana: sobremesa clássica com banana frita, queijo manteiga grelhado, açúcar e canela salpicada.",
        ],
        "dica": "Faça um passeio de catamarã pelo Rio Capibaribe no fim de tarde para admirar as pontes iluminadas que conferem a Recife o charme da 'Veneza Brasileira'. Experimente a tapioca recheada com coco ralado no Alto da Sé em Olinda.",
    },
    "tiangua": {
        "pontos": [
            "Sítio do Bosco Park: Complexo ecológico no topo da Serra da Ibiapaba com mirante panorâmico sobre o vale, rampa de voo livre para parapente e piscina natural de água corrente.",
            "Cachoeira do Pinga e Cachoeira da Sete: Quedas d'água em meio à mata nativa com poços cristalinos refrescantes e trilhas ecológicas preservadas.",
            "Catedral de Sant'Anna (Igreja Matriz): Edificação histórica imponente no centro da cidade com vitrais coloridos e praça arborizada acolhedora.",
            "Complexo Chapada da Ibiapaba e Ecoparque Cassauro: Mirantes da serra, tirolesa, arvorismo e passeios a engenhos tradicionais de rapadura e alambiques artesanais.",
        ],
        "roteiro": [
            "Manhã: Subida ao Sítio do Bosco bem cedo para contemplar o nascer do sol e a neblina matinal (serração) cobrindo as encostas da serra.",
            "Tarde: Banho refrescante na Cachoeira do Pinga e visita aos alambiques e engenhos locais para degustar rapadura batida com castanha.",
            "Noite: Passeio a pé pela Praça da Catedral, aproveitando o clima frio de serra para provar cafés regionais e a gastronomia local.",
        ],
        "culinaria": [
            "Galinha caipira ao molho pardo cozida em panela de barro com pirão escaldado e macaxeira frita.",
            "Carne de sol na nata da serra com feijão verde, queijo coalho tostado e farofa de manteiga da terra.",
            "Rapadura batida cremosa com castanha de caju, compotas de frutas da estação e licores artesanais de jabuticaba e maracujá da Ibiapaba.",
        ],
        "dica": "O clima na serra de Tianguá é surpreendentemente ameno e frio à noite (muitas vezes abaixo de 18°C), exigindo agasalho na bagagem. Para registrar fotos com horizonte aberto nos mirantes, dê preferência ao horário entre 10h e 14h, quando a névoa matinal se dissipa.",
    },
}


def gerar_guia_contingencia(destino: str) -> str:
    """Gera roteiro estruturado determinístico em texto puro com emojis em caso de falha da IA."""
    nome_destino = destino.strip() or "Destino Selecionado"
    nome_sem_uf = re.sub(r"\s*-\s*[A-Z]{2}$", "", nome_destino).strip()
    nfkd = unicodedata.normalize("NFKD", nome_sem_uf)
    nome_chave = "".join(c for c in nfkd if not unicodedata.combining(c)).lower()

    # Se o destino for uma das cidades mapeadas, entrega curadoria refinada
    for chave, dados in _GUIAS_CURADOS.items():
        if chave in nome_chave or nome_chave in chave:
            pontos_txt = "\n".join(f"• {p}" for p in dados["pontos"])
            roteiro_bloco = ""
            if "roteiro" in dados:
                roteiro_txt = "\n".join(f"• {r}" for r in dados["roteiro"])
                roteiro_bloco = f"\n🗺️ ROTEIRO RECOMENDADO (PASSO A PASSO)\n{roteiro_txt}\n"
            culinaria_txt = "\n".join(f"• {c}" for c in dados["culinaria"])
            dica_txt = f"• {dados['dica']}"
            return (
                f"🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
                f"{pontos_txt}\n"
                f"{roteiro_bloco}\n"
                f"🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
                f"{culinaria_txt}\n\n"
                f"💡 DICA DE OURO DO VIAJANTE\n"
                f"{dica_txt}"
            )

    # Para outras cidades brasileiras, gera um guia regionalmente contextualizado e detalhado
    return (
        f"🏛️ PONTOS TURÍSTICOS PRINCIPAIS\n"
        f"• Explore os principais cartões-postais históricos, igrejas seculares e praças centrais de {nome_destino}.\n"
        f"• Visite os parques naturais, reservas ecológicas e mirantes panorâmicos que revelam a beleza da geografia local.\n"
        f"• Conheça o mercado municipal de artesanato e os centros culturais para vivenciar as tradições e costumes populares.\n"
        f"• Realize passeios guiados aos atrativos ecológicos e monumentos mais emblemáticos da região.\n\n"
        f"🗺️ ROTEIRO RECOMENDADO (PASSO A PASSO)\n"
        f"• Manhã: Passeio histórico matinal pelas praças centrais e mirantes panorâmicos com temperaturas amenas.\n"
        f"• Tarde: Visita a reservas ecológicas, cachoeiras ou feiras de artesanato e produtos da terra.\n"
        f"• Noite: Jantar em restaurantes de comida caseira típica e convivência nos principais polos da cidade.\n\n"
        f"🍲 CULINÁRIA LOCAL & GASTRONOMIA\n"
        f"• Saboreie os pratos típicos regionais preparados com temperos frescos e ingredientes nativos da culinária local.\n"
        f"• Experimente doces artesanais, compotas de frutas da estação e bebidas típicas consagradas pelos moradores.\n"
        f"• Desfrute dos melhores restaurantes de comida caseira, feiras gastronômicas e bistrôs acolhedores de {nome_destino}.\n\n"
        f"💡 DICA DE OURO DO VIAJANTE\n"
        f"• Programe seus passeios ao ar livre nas primeiras horas da manhã para aproveitar temperaturas agradáveis e fotos sem aglomeração.\n"
        f"• Converse com moradores nos mercados populares para descobrir recantos pouco explorados e confirmar horários das atrações."
    )
