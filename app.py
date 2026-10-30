"""
serpapi_viagens.py
Uma função por API da SerpApi, pensada para bots de IA de agências de viagens.

Configuração:
    export SERPAPI_KEY="a_tua_chave"      (nunca coloques a chave no código)

Notas:
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv


BASE_URL = "https://serpapi.com/search.json"


class SerpApiError(Exception):
    """Erro devolvido pela SerpApi ou falha de comunicação."""

load_dotenv()

def _criar_sessao() -> requests.Session:
    sessao = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    sessao.mount("https://", HTTPAdapter(max_retries=retry))
    return sessao


_SESSAO = _criar_sessao()


def _chamar(
    engine: str,
    params: dict[str, Any],
    api_key: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Chamada genérica à SerpApi, com limpeza de parâmetros e tratamento de erros."""
    chave = api_key or os.environ.get("SERPAPI_KEY")
    if not chave:
        raise SerpApiError("Define a variável de ambiente SERPAPI_KEY.")

    consulta: dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            v = str(v).lower()
        elif isinstance(v, (list, tuple)):
            v = ",".join(str(i) for i in v)
        consulta[k] = v
    consulta["engine"] = engine
    consulta["api_key"] = chave

    try:
        resp = _SESSAO.get(BASE_URL, params=consulta, timeout=timeout)
    except requests.RequestException as e:
        raise SerpApiError(f"{engine}: falha de rede ({e})") from e

    try:
        dados = resp.json()
    except ValueError:
        raise SerpApiError(f"{engine}: resposta não JSON (HTTP {resp.status_code})")

    erro = dados.get("error")
    if erro and "hasn't returned any results" in str(erro):
        return dados  # pesquisa válida sem resultados
    if resp.status_code >= 400 or erro:
        raise SerpApiError(f"{engine}: {erro or 'HTTP ' + str(resp.status_code)}")
    return dados


# ---------------------------------------------------------------------------
# 1. VOOS
# ---------------------------------------------------------------------------

def pesquisar_voos(
    origem: str,
    destino: str,
    data_ida: str,
    data_volta: str | None = None,
    adultos: int = 1,
    criancas: int = 0,
    classe: int | None = None,
    moeda: str = "EUR",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Flights. origem/destino: código IATA (LIS, GRU). Datas: YYYY-MM-DD.
    classe: 1 económica, 2 premium, 3 executiva, 4 primeira."""
    return _chamar("google_flights", {
        "departure_id": origem,
        "arrival_id": destino,
        "outbound_date": data_ida,
        "return_date": data_volta,
        "type": 1 if data_volta else 2,  # 1 ida e volta, 2 só ida
        "adults": adultos,
        "children": criancas,
        "travel_class": classe,
        "currency": moeda,
        "hl": idioma,
        **extra,
    }, api_key)


def opcoes_reserva_voo(
    booking_token: str,
    origem: str,
    destino: str,
    data_ida: str,
    data_volta: str | None = None,
    moeda: str = "EUR",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Flights Booking Options: links de compra de um voo escolhido.
    O booking_token vem do resultado de pesquisar_voos()."""
    return _chamar("google_flights", {
        "booking_token": booking_token,
        "departure_id": origem,
        "arrival_id": destino,
        "outbound_date": data_ida,
        "return_date": data_volta,
        "type": 1 if data_volta else 2,
        "currency": moeda,
        "hl": idioma,
        **extra,
    }, api_key)


def autocompletar_voos(texto: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Flights Autocomplete: sugere aeroportos/cidades. [CONFIRMAR engine]"""
    return _chamar("google_flights_autocomplete", {"q": texto, "hl": idioma, **extra}, api_key)


def ofertas_voos(
    origem: str,
    moeda: str = "EUR",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Flights Deals: promoções de voos. [CONFIRMAR engine e parâmetros]"""
    return _chamar("google_flights_deals", {
        "departure_id": origem, "currency": moeda, "hl": idioma, **extra,
    }, api_key)


def explorar_destinos(
    origem: str,
    data_ida: str | None = None,
    data_volta: str | None = None,
    moeda: str = "EUR",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Travel Explore: destinos mais baratos a partir de uma origem."""
    return _chamar("google_travel_explore", {
        "departure_id": origem,
        "outbound_date": data_ida,
        "return_date": data_volta,
        "currency": moeda,
        "hl": idioma,
        **extra,
    }, api_key)


def estado_voo_tempo_real(api_key: str | None = None, **filtros) -> dict:
    """Flightradar24: voos em tempo real. Os filtros (ex.: indicativo, aeroporto)
    seguem a documentação. [CONFIRMAR parâmetros]"""
    return _chamar("flightradar24", filtros, api_key)


# ---------------------------------------------------------------------------
# 2. HOTÉIS E ALOJAMENTO
# ---------------------------------------------------------------------------

def pesquisar_hoteis(
    destino: str,
    check_in: str,
    check_out: str,
    adultos: int = 2,
    criancas: int = 0,
    moeda: str = "EUR",
    idioma: str = "pt",
    pais: str | None = None,
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Hotels: pesquisa por destino e datas (YYYY-MM-DD)."""
    return _chamar("google_hotels", {
        "q": destino,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adultos,
        "children": criancas,
        "currency": moeda,
        "hl": idioma,
        "gl": pais,
        **extra,
    }, api_key)


def detalhes_hotel(
    property_token: str,
    check_in: str,
    check_out: str,
    adultos: int = 2,
    moeda: str = "EUR",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Hotels Property Details: preços por fornecedor, comodidades, etc."""
    return _chamar("google_hotels", {
        "q": extra.pop("q", "hotel"),
        "property_token": property_token,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adultos,
        "currency": moeda,
        "hl": idioma,
        **extra,
    }, api_key)


def avaliacoes_hotel(
    property_token: str,
    idioma: str = "pt",
    pagina_seguinte: str | None = None,
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Hotels Reviews."""
    return _chamar("google_hotels_reviews", {
        "property_token": property_token,
        "hl": idioma,
        "next_page_token": pagina_seguinte,
        **extra,
    }, api_key)


def fotos_hotel(property_token: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Hotels Photos. [CONFIRMAR engine]"""
    return _chamar("google_hotels_photos", {"property_token": property_token, "hl": idioma, **extra}, api_key)


def calendario_precos_hotel(
    property_token: str,
    moeda: str = "EUR",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Hotels Price Calendar: preço por dia. [CONFIRMAR engine e parâmetros]"""
    return _chamar("google_hotels_price_calendar", {
        "property_token": property_token, "currency": moeda, "hl": idioma, **extra,
    }, api_key)


def autocompletar_hoteis(texto: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Hotels Autocomplete. [CONFIRMAR engine]"""
    return _chamar("google_hotels_autocomplete", {"q": texto, "hl": idioma, **extra}, api_key)


def pesquisar_booking(
    destino: str,
    check_in: str,
    check_out: str,
    adultos: int = 2,
    quartos: int = 1,
    criancas: int = 0,
    idades_criancas: list[int] | None = None,
    moeda: str | None = None,
    idioma: str = "pt-br",
    ordenar_por: str | None = None,
    estrelas: list[int] | None = None,
    nota_minima: int | None = None,
    cancelamento_gratis: bool | None = None,
    limite: int = 25,
    api_key: str | None = None,
    **extra,
) -> dict:
    """Booking.com Search. ordenar_por: popularity, price, review_score_and_price,
    bayesian_review_score, class, distance_from_search, ...
    nota_minima: 6, 7, 8 ou 9. Máximo 90 noites; crianças exigem idades."""
    return _chamar("booking", {
        "q": destino,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adultos,
        "rooms": quartos,
        "children": criancas or None,
        "children_ages": idades_criancas,
        "currency": moeda,
        "hl": idioma,
        "sort_by": ordenar_por,
        "hotel_class": estrelas,
        "rating": nota_minima,
        "free_cancellation": cancelamento_gratis,
        "limit": limite,
        **extra,
    }, api_key)


def pesquisar_airbnb(
    destino: str,
    check_in: str,
    check_out: str,
    adultos: int = 2,
    moeda: str = "EUR",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Airbnb Search. [CONFIRMAR parâmetros]"""
    return _chamar("airbnb", {
        "q": destino,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "adults": adultos,
        "currency": moeda,
        **extra,
    }, api_key)


# ---------------------------------------------------------------------------
# 3. DESTINO E EXPERIÊNCIAS
# ---------------------------------------------------------------------------

def pesquisar_locais_maps(
    consulta: str,
    coordenadas: str | None = None,
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Maps: locais, restaurantes, atrações. coordenadas: '@38.72,-9.14,14z'."""
    return _chamar("google_maps", {
        "type": "search", "q": consulta, "ll": coordenadas, "hl": idioma, **extra,
    }, api_key)


def detalhes_local_maps(data_id: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Maps Place Results, a partir do data_id."""
    return _chamar("google_maps", {"type": "place", "data_id": data_id, "hl": idioma, **extra}, api_key)


def avaliacoes_maps(data_id: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Maps Reviews."""
    return _chamar("google_maps_reviews", {"data_id": data_id, "hl": idioma, **extra}, api_key)


def fotos_maps(data_id: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Maps Photos."""
    return _chamar("google_maps_photos", {"data_id": data_id, "hl": idioma, **extra}, api_key)


def direcoes_maps(
    origem: str,
    destino: str,
    modo: int | None = None,
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Maps Directions. modo: 0 carro, 1 transportes públicos... [CONFIRMAR valores]"""
    return _chamar("google_maps_directions", {
        "start_addr": origem, "end_addr": destino, "travel_mode": modo, "hl": idioma, **extra,
    }, api_key)


def eventos_destino(consulta: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Events. Ex.: 'concertos em Lisboa'."""
    return _chamar("google_events", {"q": consulta, "hl": idioma, **extra}, api_key)


def pesquisar_tripadvisor(consulta: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Tripadvisor Search: atrações, restaurantes, hotéis."""
    return _chamar("tripadvisor", {"q": consulta, "hl": idioma, **extra}, api_key)


def local_tripadvisor(place_id: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Tripadvisor Place. [CONFIRMAR engine/parâmetros]"""
    return _chamar("tripadvisor_place", {"place_id": place_id, "hl": idioma, **extra}, api_key)


def avaliacoes_tripadvisor(place_id: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Tripadvisor Reviews. [CONFIRMAR engine/parâmetros]"""
    return _chamar("tripadvisor_reviews", {"place_id": place_id, "hl": idioma, **extra}, api_key)


def pesquisar_yelp(termo: str, localizacao: str, api_key: str | None = None, **extra) -> dict:
    """Yelp Search (mais útil nos EUA). [CONFIRMAR parâmetros]"""
    return _chamar("yelp", {"find_desc": termo, "find_loc": localizacao, **extra}, api_key)


def local_yelp(place_id: str, api_key: str | None = None, **extra) -> dict:
    """Yelp Place. [CONFIRMAR engine/parâmetros]"""
    return _chamar("yelp_place", {"place_id": place_id, **extra}, api_key)


def avaliacoes_yelp(place_id: str, api_key: str | None = None, **extra) -> dict:
    """Yelp Reviews. [CONFIRMAR engine/parâmetros]"""
    return _chamar("yelp_reviews", {"place_id": place_id, **extra}, api_key)


def avaliacoes_opentable(place_id: str, api_key: str | None = None, **extra) -> dict:
    """OpenTable Reviews. [CONFIRMAR engine/parâmetros]"""
    return _chamar("open_table_reviews", {"place_id": place_id, **extra}, api_key)


def traduzir(texto: str, idioma_destino: str, idioma_origem: str = "auto", api_key: str | None = None, **extra) -> dict:
    """Google Translate. [CONFIRMAR nomes dos parâmetros]"""
    return _chamar("google_translate", {
        "q": texto, "source": idioma_origem, "target": idioma_destino, **extra,
    }, api_key)


def noticias_destino(consulta: str, idioma: str = "pt", pais: str | None = None, api_key: str | None = None, **extra) -> dict:
    """Google News: notícias do destino (greves, clima, alertas)."""
    return _chamar("google_news", {"q": consulta, "hl": idioma, "gl": pais, **extra}, api_key)


# ---------------------------------------------------------------------------
# 4. MARKETING E CONCORRÊNCIA
# ---------------------------------------------------------------------------

def tendencias_google(
    consulta: str,
    tipo: str = "TIMESERIES",
    idioma: str = "pt",
    api_key: str | None = None,
    **extra,
) -> dict:
    """Google Trends: interesse em destinos ao longo do tempo.
    tipo: TIMESERIES, GEO_MAP, RELATED_QUERIES, RELATED_TOPICS."""
    return _chamar("google_trends", {"q": consulta, "data_type": tipo, "hl": idioma, **extra}, api_key)


def anuncios_google_transparencia(api_key: str | None = None, **filtros) -> dict:
    """Google Ads Transparency Center: anúncios de concorrentes.
    Usa advertiser_id ou texto, conforme a documentação. [CONFIRMAR engine/parâmetros]"""
    return _chamar("google_ads_transparency_center", filtros, api_key)


def anuncios_meta(consulta: str, pais: str = "PT", api_key: str | None = None, **extra) -> dict:
    """Meta Ad Library: anúncios no Facebook/Instagram. [CONFIRMAR engine/parâmetros]"""
    return _chamar("meta_ad_library", {"q": consulta, "country": pais, **extra}, api_key)


def imagens_destino(consulta: str, idioma: str = "pt", api_key: str | None = None, **extra) -> dict:
    """Google Images: imagens de destinos. Confirma os direitos antes de usar comercialmente."""
    return _chamar("google_images", {"q": consulta, "hl": idioma, **extra}, api_key)


# ---------------------------------------------------------------------------
# Resumos compactos para enviar ao LLM do bot
# ---------------------------------------------------------------------------

def resumir_voos(dados: dict, limite: int = 5) -> list[dict]:
    """Extrai preço, duração e trechos dos melhores voos."""
    voos = (dados.get("best_flights") or []) + (dados.get("other_flights") or [])
    saida = []
    for v in voos[:limite]:
        trechos = v.get("flights", [])
        saida.append({
            "preco": v.get("price"),
            "duracao_min": v.get("total_duration"),
            "escalas": max(len(trechos) - 1, 0),
            "companhias": sorted({t.get("airline") for t in trechos if t.get("airline")}),
            "partida": trechos[0].get("departure_airport", {}).get("time") if trechos else None,
            "chegada": trechos[-1].get("arrival_airport", {}).get("time") if trechos else None,
            "booking_token": v.get("booking_token"),
        })
    return saida


def resumir_booking(dados: dict, limite: int = 5) -> list[dict]:
    """Extrai os campos principais das propriedades da Booking.com."""
    saida = []
    for p in dados.get("properties", [])[:limite]:
        saida.append({
            "nome": p.get("name"),
            "tipo": p.get("type"),
            "estrelas": p.get("hotel_class"),
            "nota": p.get("rating"),
            "avaliacoes": p.get("reviews"),
            "preco_total": p.get("price"),
            "preco_noite": p.get("price_per_night"),
            "taxas": p.get("taxes_and_fees"),
            "cancelamento_gratis": p.get("free_cancellation"),
            "regime": p.get("meal_plan"),
            "localizacao": p.get("location"),
            "link": p.get("link"),
        })
    return saida


def resumir_hoteis_google(dados: dict, limite: int = 5) -> list[dict]:
    """Extrai os campos principais das propriedades do Google Hotels."""
    saida = []
    for p in dados.get("properties", [])[:limite]:
        saida.append({
            "nome": p.get("name"),
            "nota": p.get("overall_rating"),
            "avaliacoes": p.get("reviews"),
            "estrelas": p.get("extracted_hotel_class"),
            "preco_noite": (p.get("rate_per_night") or {}).get("lowest"),
            "preco_total": (p.get("total_rate") or {}).get("lowest"),
            "property_token": p.get("property_token"),
        })
    return saida


def resumir_avaliacoes_hotel(dados: dict) -> list[dict]:
    """Mesmo formato do teu script original."""
    saida = []
    for r in dados.get("reviews", []):
        sub = r.get("subratings", {}) or {}
        saida.append({
            "autor": (r.get("user") or {}).get("name"),
            "fonte": r.get("source"),
            "nota": r.get("rating"),
            "data": r.get("date"),
            "comentario": r.get("snippet"),
            "quartos": sub.get("rooms"),
            "servico": sub.get("service"),
            "localizacao": sub.get("location"),
        })
    return saida


if __name__ == "__main__":
    ida = (date.today() + timedelta(days=30)).isoformat()
    volta = (date.today() + timedelta(days=37)).isoformat()

    voos = pesquisar_voos("LIS", "GRU", ida, volta)
    print(resumir_voos(voos))

    booking = pesquisar_booking("Lisboa", ida, volta, ordenar_por="review_score_and_price")
    print(resumir_booking(booking))