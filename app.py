import base64
import html
import math
import random
import re
import time
from pathlib import Path

import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

# =========================================================
# Configuração geral
# =========================================================
st.set_page_config(page_title="Mapa da concorrência", page_icon="🗺️", layout="wide")

INK = "#111111"
ACCENT = "#0063A9"
RED, RED_BG = "#C1443D", "#F7E4E2"
AMBER, AMBER_BG = "#B9812A", "#F7EBD6"
GREEN, GREEN_BG = "#357A5D", "#E1EFE7"
LEVEL_COLOR = {"alta": RED, "media": AMBER, "baixa": GREEN}
LEVEL_BG = {"alta": RED_BG, "media": AMBER_BG, "baixa": GREEN_BG}
LEVEL_LABEL = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}

# (Nome exibido, tags OSM, termos de busca livre / ArcGIS, tipo Google Places)
CATEGORIES = [
    ("Restaurante", [("amenity", ["restaurant", "food_court"])], ["restaurante", "restaurant"], "restaurant"),
    ("Cafeteria", [("amenity", "cafe"), ("shop", "coffee")], ["cafeteria", "cafe", "café"], "cafe"),
    ("Padaria", [("shop", "bakery"), ("amenity", "bakery")], ["padaria", "confeitaria", "bakery"], "bakery"),
    ("Bar", [("amenity", ["bar", "pub", "nightclub", "biergarten"])], ["bar", "pub", "cervejaria", "choperia"], "bar"),
    ("Academia", [("leisure", ["fitness_centre", "sports_centre"]), ("sport", "fitness")], ["academia", "crossfit", "fitness"], "gym"),
    ("Salão de beleza / barbearia", [("shop", ["hairdresser", "barber"])], ["salão de beleza", "barbearia", "cabeleireiro"], "hair_care"),
    ("Clínica de estética / spa", [("shop", ["beauty", "massage"]), ("leisure", "spa")], ["clínica de estética", "estética", "spa"], "beauty_salon"),
    ("Farmácia", [("amenity", "pharmacy"), ("shop", "chemist")], ["farmácia", "drogaria", "pharmacy"], "pharmacy"),
    ("Loja de roupas", [("shop", ["clothes", "boutique", "fashion"])], ["loja de roupas", "boutique", "moda"], "clothing_store"),
    ("Loja de calçados", [("shop", "shoes")], ["loja de calçados", "calçados", "sapataria"], "shoe_store"),
    ("Pet shop", [("shop", "pet"), ("amenity", "veterinary")], ["pet shop", "veterinária", "agropecuária"], "pet_store"),
    ("Loja de eletrônicos", [("shop", ["electronics", "mobile_phone", "computer"])], ["loja de eletrônicos", "informática", "celulares"], "electronics_store"),
    ("Supermercado", [("shop", "supermarket")], ["supermercado", "hipermercado"], "supermarket"),
    ("Mercado de conveniência", [("shop", ["convenience", "greengrocer", "grocery"])], ["mercado", "minimercado", "conveniência", "fruteira"], "convenience_store"),
    ("Escritório de advocacia", [("office", "lawyer")], ["advocacia", "advogado"], "lawyer"),
    ("Consultório odontológico", [("amenity", "dentist")], ["dentista", "odontologia", "clínica odontológica"], "dentist"),
    ("Clínica médica", [("amenity", ["doctors", "clinic"])], ["clínica médica", "consultório médico", "policlínica"], "doctor"),
    ("Oficina mecânica", [("shop", ["car_repair", "tyres"]), ("craft", "car_repair")], ["oficina mecânica", "auto center", "mecânica"], "car_repair"),
    ("Imobiliária", [("office", "estate_agent")], ["imobiliária", "corretora de imóveis"], "real_estate_agency"),
    ("Pousada / hotel", [("tourism", ["hotel", "guest_house", "hostel", "motel"])], ["hotel", "pousada", "hostel"], "lodging"),
    ("Loja de móveis", [("shop", ["furniture", "interior_decoration"])], ["loja de móveis", "móveis", "decoração"], "furniture_store"),
    ("Livraria", [("shop", "books")], ["livraria", "papelaria"], "book_store"),
    ("Floricultura", [("shop", "florist")], ["floricultura", "flores"], "florist"),
]

PORTES = ["MEI / autônomo", "Pequena empresa", "Média empresa", "Grande empresa / rede"]

# Apenas espelhos globais (removido osm.ch que só tinha dados da Suíça e kumi.systems que foi desativado)
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

HTTP_HEADERS = {
    "User-Agent": "MapaDaConcorrenciaApp/2.0 (https://mapa-da-concorrencia-h7ca5nycufbwqsfsychauq.streamlit.app)",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# =========================================================
# Estilo (força modo claro completo, corrigindo inputs, selects, autofill e expanders)
# =========================================================
st.markdown(
    f"""
    <style>
    :root {{
        color-scheme: light !important;
        --primary-color: {ACCENT} !important;
        --background-color: #FFFFFF !important;
        --secondary-background-color: #F8F9FA !important;
        --text-color: {INK} !important;
    }}
    html, body, .stApp,
    [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"],
    [data-testid="stBlock"], [data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stDecoration"] {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
    }}

    /* Barra lateral */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebarContent"],
    [data-testid="stSidebarUserContent"] {{
        background-color: #F8F9FA !important;
        color: {INK} !important;
        border-right: 1px solid rgba(0, 0, 0, 0.12) !important;
    }}
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {{
        color: {INK} !important;
    }}

    /* Inputs de texto e TextArea (incluindo autofill do navegador) */
    .stTextInput > div,
    .stTextInput > div > div,
    .stTextArea > div,
    .stTextArea > div > div,
    [data-baseweb="input"],
    [data-baseweb="input"] > div,
    [data-baseweb="base-input"],
    [data-baseweb="textarea"] {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
        border-color: rgba(0, 0, 0, 0.25) !important;
    }}
    .stTextInput input,
    .stTextArea textarea,
    input[type="text"],
    input[type="password"],
    textarea {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
        -webkit-text-fill-color: {INK} !important;
        caret-color: {INK} !important;
    }}
    input:-webkit-autofill,
    input:-webkit-autofill:hover,
    input:-webkit-autofill:focus,
    input:-webkit-autofill:active {{
        -webkit-box-shadow: 0 0 0 1000px #FFFFFF inset !important;
        -webkit-text-fill-color: {INK} !important;
        background-color: #FFFFFF !important;
        color: {INK} !important;
    }}
    .stTextInput input::placeholder,
    .stTextArea textarea::placeholder {{
        color: rgba(0, 0, 0, 0.45) !important;
        -webkit-text-fill-color: rgba(0, 0, 0, 0.45) !important;
    }}
    /* Botão olho da senha */
    [data-baseweb="input"] button {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
    }}

    /* Selectbox (caixa fechada e menu aberto) */
    [data-baseweb="select"],
    [data-baseweb="select"] > div,
    [data-baseweb="select"] > div > div,
    [data-baseweb="select"] input {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
    }}
    [data-baseweb="select"] > div {{
        border: 1px solid rgba(0, 0, 0, 0.25) !important;
        border-radius: 6px !important;
    }}
    [data-baseweb="select"] span,
    [data-baseweb="select"] div,
    [data-baseweb="select"] svg {{
        color: {INK} !important;
        fill: {INK} !important;
    }}
    html body [data-baseweb="popover"],
    html body [data-baseweb="popover"] div,
    html body [data-baseweb="menu"],
    html body [data-baseweb="menu"] ul,
    html body ul[role="listbox"],
    html body li[role="option"],
    html body li[data-baseweb="menu-option"] {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
    }}
    html body li[role="option"] *,
    html body li[data-baseweb="menu-option"] * {{
        color: {INK} !important;
    }}
    html body li[role="option"]:hover,
    html body li[role="option"][aria-selected="true"],
    html body li[data-baseweb="menu-option"]:hover,
    html body li[data-baseweb="menu-option"][aria-selected="true"] {{
        background-color: #EAF2F8 !important;
        color: {INK} !important;
    }}

    /* Expanders (corrige cabeçalho preto) */
    [data-testid="stExpander"],
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] > div {{
        background-color: #FFFFFF !important;
        color: {INK} !important;
        border-color: rgba(0, 0, 0, 0.2) !important;
    }}
    [data-testid="stExpander"] summary:hover {{
        background-color: #F2F4F7 !important;
    }}
    [data-testid="stExpander"] summary *,
    [data-testid="stExpander"] svg {{
        color: {INK} !important;
        fill: {INK} !important;
    }}

    /* Botão primário */
    .stButton > button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"],
    [data-testid="stBaseButton-primary"] {{
        background-color: {INK} !important;
        border-color: {INK} !important;
        color: #FFFFFF !important;
    }}
    .stButton > button[kind="primary"] *,
    [data-testid="stSidebar"] button[kind="primary"] *,
    [data-testid="stBaseButton-primary"] * {{
        color: #FFFFFF !important;
    }}
    .stButton > button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {{
        background-color: {ACCENT} !important;
        border-color: {ACCENT} !important;
    }}

    /* Alertas, chat, slider e textos gerais */
    h1, h2, h3, h4, label, .stMarkdown p, .stMarkdown span {{
        color: {INK} !important;
    }}
    [data-testid="stSlider"] label, [data-testid="stWidgetLabel"] p {{
        color: {INK} !important;
    }}
    [data-testid="stAlert"], [data-testid="stAlertContainer"] {{
        background-color: #EAF2F8 !important;
        border: 1px solid {ACCENT} !important;
    }}
    [data-testid="stAlert"] *, [data-testid="stAlertContainer"] * {{
        color: {INK} !important;
    }}
    [data-testid="stChatMessage"] {{
        background-color: #F5F5F5 !important;
    }}
    [data-testid="stChatMessage"] * {{
        color: {INK} !important;
    }}
    [data-testid="stCaptionContainer"] {{
        color: rgba(0, 0, 0, 0.65) !important;
    }}
    a {{ color: {ACCENT} !important; }}

    /* Componentes customizados */
    .header-bar {{
        background: {INK}; border-radius: 10px; padding: 14px 20px;
        display: flex; align-items: center; gap: 14px; margin-bottom: 18px;
    }}
    .header-bar img {{ height: 40px; }}
    .header-bar .title {{ color: #FFFFFF !important; font-size: 22px; font-weight: 700; line-height: 1.1; }}
    .header-bar .subtitle {{ color: rgba(255,255,255,.78) !important; font-size: 12.5px; margin-top: 2px; }}
    .legend-pill {{
        padding: 10px 12px; border-radius: 8px; font-weight: 700; font-size: 13px; text-align: center;
        margin-bottom: 8px;
    }}
    .legend-pill small {{
        display: block; font-weight: 400; font-size: 11.5px; opacity: 0.85; margin-top: 2px;
    }}
    .summary-banner {{
        border: 1px solid rgba(0,0,0,.15); border-radius: 8px; padding: 10px 14px;
        margin-bottom: 10px; font-size: 13.5px; background: #F9FAFB; color: {INK} !important;
    }}
    .company-card {{
        background: {INK}; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px;
    }}
    .company-card .company-title {{ color: #FFFFFF !important; font-size: 18px; font-weight: 700; }}
    .company-card .meta {{ color: rgba(255,255,255,.82) !important; font-size: 12.5px; margin-top: 4px; }}
    .result-row {{
        display: flex; justify-content: space-between; align-items: center;
        border: 1px solid rgba(0,0,0,.14); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px;
        background: #FFFFFF;
    }}
    .score-badge {{ font-weight: 700; font-size: 12px; padding: 3px 10px; border-radius: 20px; white-space: nowrap; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def get_secret(key_name: str) -> str:
    try:
        return str(st.secrets.get(key_name, "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def logo_base64() -> str:
    logo_path = Path(__file__).parent / "logo.png"
    if not logo_path.exists():
        return ""
    return base64.b64encode(logo_path.read_bytes()).decode("ascii")


_logo_b64 = logo_base64()
_logo_img = f'<img src="data:image/png;base64,{_logo_b64}" alt="Logo">' if _logo_b64 else ""
st.markdown(
    f"""
    <div class="header-bar">
        {_logo_img}
        <div>
            <div class="title">Mapa da concorrência</div>
            <div class="subtitle">Análise geoespacial de concorrentes locais</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Geocodificação e busca multi-fonte (Overpass + ArcGIS + Photon + Google Places opcional)
# =========================================================
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def normalize_name(name: str) -> str:
    s = re.sub(r"[^a-z0-9à-ú\s]", "", (name or "").lower().strip())
    return " ".join(s.split())


@st.cache_data(show_spinner=False, ttl=86400)
def _geocode_cached(address_norm: str):
    errors = []

    # 1. Photon (Komoot / OpenStreetMap)
    try:
        resp = requests.get(
            "https://photon.komoot.io/api/",
            params={"q": address_norm, "limit": 1},
            headers=HTTP_HEADERS,
            timeout=12,
        )
        if resp.status_code == 200:
            features = resp.json().get("features") or []
            if features:
                lon, lat = features[0]["geometry"]["coordinates"]
                return float(lat), float(lon)
        else:
            errors.append(f"Photon HTTP {resp.status_code}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"Photon: {e}")

    # 2. ArcGIS World Geocoding
    try:
        resp = requests.get(
            "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
            params={"SingleLine": address_norm, "f": "json", "maxLocations": 1, "countryCode": "BRA"},
            headers=HTTP_HEADERS,
            timeout=12,
        )
        if resp.status_code == 200:
            candidates = resp.json().get("candidates") or []
            if candidates and candidates[0].get("score", 0) >= 60:
                loc = candidates[0]["location"]
                return float(loc["y"]), float(loc["x"])
        else:
            errors.append(f"ArcGIS HTTP {resp.status_code}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"ArcGIS: {e}")

    # 3. Nominatim
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"format": "json", "limit": 1, "q": address_norm},
            headers=HTTP_HEADERS,
            timeout=12,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            errors.append(f"Nominatim HTTP {resp.status_code}")
    except Exception as e:  # noqa: BLE001
        errors.append(f"Nominatim: {e}")

    raise LookupError(" | ".join(errors) if errors else "Endereço não encontrado.")


def geocode(address: str):
    clean = " ".join(address.strip().split())
    if "brasil" not in clean.lower() and "brazil" not in clean.lower():
        query = f"{clean}, Brasil"
    else:
        query = clean
    try:
        coords = _geocode_cached(query)
        return coords, None
    except LookupError as e:
        return None, f"Não foi possível localizar o endereço ({e})."


def build_tag_filter(key, value):
    if isinstance(value, list):
        return f'["{key}"~"^({"|".join(value)})$"]'
    return f'["{key}"="{value}"]'


def compute_bbox(lat: float, lon: float, radius_km: float):
    dlat = radius_km / 111.32
    dlon = radius_km / (111.32 * max(math.cos(math.radians(lat)), 0.1))
    return (
        round(lat - dlat, 5),
        round(lon - dlon, 5),
        round(lat + dlat, 5),
        round(lon + dlon, 5),
    )


@st.cache_data(show_spinner=False, ttl=1800)
def _overpass_cached(lat: float, lon: float, tag_pairs: tuple, radius_km: float):
    south, west, north, east = compute_bbox(lat, lon, radius_km)
    bbox_str = f"({south},{west},{north},{east})"
    result_cap = 250 if radius_km > 10 else 120
    clauses = []
    for key, value in tag_pairs:
        val_arg = list(value) if isinstance(value, tuple) else value
        tf = build_tag_filter(key, val_arg)
        clauses.append(f"nwr{tf}{bbox_str};")

    query = f"[out:json][timeout:20];({''.join(clauses)});out center tags {result_cap};"
    last_err = None
    for url in OVERPASS_MIRRORS:
        try:
            resp = requests.post(url, data={"data": query}, headers=HTTP_HEADERS, timeout=22)
            if resp.status_code != 200:
                last_err = f"{url.split('/')[2]}: HTTP {resp.status_code}"
                continue
            data = resp.json()
            if "elements" not in data:
                last_err = f"{url.split('/')[2]}: sem dados"
                continue
            if not data["elements"] and data.get("remark"):
                last_err = f"{url.split('/')[2]}: {data['remark']}"
                continue
            return data["elements"]
        except Exception as e:  # noqa: BLE001
            last_err = f"{url.split('/')[2]}: {e}"
            continue
    raise ConnectionError(last_err or "Espelhos Overpass indisponíveis.")


@st.cache_data(show_spinner=False, ttl=1800)
def _arcgis_poi_cached(lat: float, lon: float, search_terms: tuple, radius_km: float):
    """Busca gratuita de estabelecimentos próximos via ArcGIS World Geocoding (sem chave de API)."""
    found = []
    seen = set()
    radius_m = int(min(radius_km * 1000, 50000))
    for term in search_terms[:3]:
        try:
            resp = requests.get(
                "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates",
                params={
                    "SingleLine": term,
                    "location": f"{lon},{lat}",
                    "distance": radius_m,
                    "countryCode": "BRA",
                    "category": "POI",
                    "maxLocations": 50,
                    "outFields": "PlaceName,Place_addr,Type,Phone,URL",
                    "f": "json",
                },
                headers=HTTP_HEADERS,
                timeout=12,
            )
            if resp.status_code != 200:
                continue
            for c in resp.json().get("candidates") or []:
                attrs = c.get("attributes") or {}
                loc = c.get("location") or {}
                clat, clon = loc.get("y"), loc.get("x")
                if clat is None or clon is None:
                    continue
                name = (attrs.get("PlaceName") or c.get("address") or "").strip()
                if not name:
                    continue
                key = (normalize_name(name), round(float(clat), 4), round(float(clon), 4))
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    {
                        "name": name,
                        "lat": float(clat),
                        "lon": float(clon),
                        "address": str(attrs.get("Place_addr") or ""),
                        "phone": str(attrs.get("Phone") or ""),
                        "website": str(attrs.get("URL") or ""),
                    }
                )
        except Exception:  # noqa: BLE001
            continue
    return found


@st.cache_data(show_spinner=False, ttl=1800)
def _photon_poi_cached(lat: float, lon: float, search_terms: tuple, radius_km: float):
    """Busca gratuita adicional de POIs no índice do Photon/OSM por proximidade geográfica."""
    found = []
    seen = set()
    for term in search_terms[:2]:
        try:
            resp = requests.get(
                "https://photon.komoot.io/api/",
                params={"q": term, "lat": lat, "lon": lon, "limit": 40},
                headers=HTTP_HEADERS,
                timeout=12,
            )
            if resp.status_code != 200:
                continue
            for feat in resp.json().get("features") or []:
                props = feat.get("properties") or {}
                geom = feat.get("geometry") or {}
                coords = geom.get("coordinates") or []
                if len(coords) < 2:
                    continue
                clon, clat = float(coords[0]), float(coords[1])
                name = (props.get("name") or "").strip()
                if not name:
                    continue
                key = (normalize_name(name), round(clat, 4), round(clon, 4))
                if key in seen:
                    continue
                seen.add(key)
                addr_parts = [props.get("street"), props.get("housenumber"), props.get("district")]
                found.append(
                    {
                        "name": name,
                        "lat": clat,
                        "lon": clon,
                        "address": ", ".join([str(p) for p in addr_parts if p]),
                        "phone": "",
                        "website": "",
                    }
                )
        except Exception:  # noqa: BLE001
            continue
    return found


def search_free_sources(lat: float, lon: float, tag_pairs: list, search_terms: list, radius_km: float, own_name: str):
    """Combina Overpass + ArcGIS POI + Photon POI (100% gratuito e sem chave) para máxima cobertura."""
    frozen_pairs = tuple((k, tuple(v) if isinstance(v, list) else v) for k, v in tag_pairs)
    frozen_terms = tuple(search_terms)
    rlat, rlon, rkm = round(lat, 5), round(lon, 5), float(radius_km)

    osm_elements = []
    try:
        osm_elements = _overpass_cached(rlat, rlon, frozen_pairs, rkm)
    except Exception:  # noqa: BLE001
        osm_elements = []

    arcgis_pois = _arcgis_poi_cached(rlat, rlon, frozen_terms, rkm)
    photon_pois = _photon_poi_cached(rlat, rlon, frozen_terms, rkm)

    rows = []
    seen_keys = set()
    own_norm = normalize_name(own_name)

    def add_candidate(name, clat, clon, brand=False, address="", phone="", website="", hours="", source="OSM"):
        dist = haversine_km(lat, lon, clat, clon)
        if dist > radius_km:
            return
        n_norm = normalize_name(name)
        if dist < 0.02 and own_norm and (n_norm == own_norm or own_norm in n_norm or n_norm in own_norm):
            return
        # Deduplicação espacial por nome normalizado + grade ~100m
        dedup_key = (n_norm or f"sem_nome_{round(clat,4)}_{round(clon,4)}", round(clat, 3), round(clon, 3))
        if dedup_key in seen_keys:
            return
        seen_keys.add(dedup_key)

        distance_score = max(0.0, 1 - dist / max(radius_km, 0.1))
        raw = distance_score * 0.85 + (0.15 if brand else 0)
        score = round(raw * 100)
        level = "alta" if score >= 60 else ("media" if score >= 30 else "baixa")
        rows.append(
            {
                "name": name,
                "lat": clat,
                "lon": clon,
                "distance_km": dist,
                "brand": brand,
                "score": score,
                "level": level,
                "address": address,
                "phone": phone,
                "website": website,
                "hours": hours,
                "rating": None,
                "rating_count": None,
                "source": source,
            }
        )

    # 1. Processa elementos do Overpass (OSM direto)
    for el in osm_elements:
        elat = el.get("lat")
        elon = el.get("lon")
        if elat is None or elon is None:
            center = el.get("center") or {}
            elat, elon = center.get("lat"), center.get("lon")
        if elat is None or elon is None:
            continue
        tags = el.get("tags", {}) or {}
        name = tags.get("name", "Sem nome no OSM")
        brand = bool(tags.get("brand") or tags.get("operator"))
        addr_parts = [tags.get("addr:street"), tags.get("addr:housenumber")]
        add_candidate(
            name=name,
            clat=float(elat),
            clon=float(elon),
            brand=brand,
            address=", ".join([p for p in addr_parts if p]),
            phone=str(tags.get("phone") or tags.get("contact:phone") or ""),
            website=str(tags.get("website") or tags.get("contact:website") or ""),
            hours=str(tags.get("opening_hours") or ""),
            source="OpenStreetMap",
        )

    # 2. Enriquecimento com ArcGIS POI
    for p in arcgis_pois:
        add_candidate(
            name=p["name"],
            clat=p["lat"],
            clon=p["lon"],
            brand=False,
            address=p["address"],
            phone=p["phone"],
            website=p["website"],
            source="ArcGIS Places",
        )

    # 3. Enriquecimento com Photon POI
    for p in photon_pois:
        add_candidate(
            name=p["name"],
            clat=p["lat"],
            clon=p["lon"],
            brand=False,
            address=p["address"],
            source="Photon/OSM",
        )

    rows.sort(key=lambda r: -r["score"])
    return rows


@st.cache_data(show_spinner=False, ttl=1800)
def _google_places_cached(api_key: str, lat: float, lon: float, place_type: str, radius_km: float):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.rating,places.userRatingCount,places.websiteUri,places.nationalPhoneNumber"
        ),
    }
    body = {
        "includedTypes": [place_type],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": min(float(radius_km) * 1000.0, 50000.0),
            }
        },
        "languageCode": "pt-BR",
    }
    resp = requests.post(url, json=body, headers=headers, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"Google Places HTTP {resp.status_code}: {resp.text[:160]}")
    return resp.json().get("places") or []


def parse_and_score_google(places, center_lat, center_lon, radius_km, own_name):
    rows = []
    own_norm = normalize_name(own_name)
    for p in places:
        loc = p.get("location") or {}
        lat, lon = loc.get("latitude"), loc.get("longitude")
        if lat is None or lon is None:
            continue
        name = ((p.get("displayName") or {}).get("text")) or "Sem nome"
        dist = haversine_km(center_lat, center_lon, lat, lon)
        if dist > radius_km:
            continue
        n_norm = normalize_name(name)
        if dist < 0.02 and own_norm and (n_norm == own_norm or own_norm in n_norm):
            continue

        rating = p.get("rating")
        rating_count = p.get("userRatingCount") or 0
        distance_score = max(0.0, 1 - dist / max(radius_km, 0.1))
        rating_score = (float(rating) / 5.0) if rating else 0.5
        volume_score = min(1.0, math.log10(rating_count + 1) / 3.0) if rating_count else 0.0
        raw = distance_score * 0.60 + rating_score * 0.20 + volume_score * 0.20
        score = round(raw * 100)
        level = "alta" if score >= 60 else ("media" if score >= 30 else "baixa")

        rows.append(
            {
                "name": name,
                "lat": lat,
                "lon": lon,
                "distance_km": dist,
                "brand": rating_count >= 300,
                "score": score,
                "level": level,
                "address": str(p.get("formattedAddress") or ""),
                "phone": str(p.get("nationalPhoneNumber") or ""),
                "website": str(p.get("websiteUri") or ""),
                "hours": "",
                "rating": rating,
                "rating_count": rating_count,
                "source": "Google Places",
            }
        )
    rows.sort(key=lambda r: -r["score"])
    return rows


# =========================================================
# Chat (Gemini)
# =========================================================
def fake_revenue_demo_reply():
    time.sleep(0.6)
    lo = 25 + random.randint(0, 9)
    hi = lo + 15 + random.randint(0, 19)
    return (
        "[EXEMPLO ILUSTRATIVO — não é um dado real]\n\n"
        "A internet não expõe o faturamento de empresas pequenas/locais, então isto é só uma simulação de "
        f"como a resposta apareceria aqui: com base no porte e na categoria informados, uma estimativa "
        f"fictícia de faturamento mensal ficaria por volta de R$ {lo}.000 a R$ {hi}.000.\n\n"
        "Num uso real, eu deixaria claro que não tenho como confirmar esse número — não invento faturamento "
        "de concorrentes de verdade."
    )


def build_context_prompt(company, results):
    lines = [
        f"Empresa cadastrada: {company['nome']}",
        f"Categoria: {CATEGORIES[company['cat_idx']][0]}",
    ]
    if company["porte"]:
        lines.append(f"Porte: {company['porte']}")
    if company["publico_alvo"]:
        lines.append(f"Público-alvo informado pelo usuário: {company['publico_alvo']}")
    if company["diferenciais"]:
        lines.append(f"Diferenciais informados pelo usuário: {company['diferenciais']}")
    lines.append(f"Raio analisado: {company['raio_km']} km")
    lines.append(f"Fonte dos dados: {company.get('source', 'Base aberta (OSM + ArcGIS)')}")
    lines.append(f"Concorrentes encontrados ({len(results)}):")
    for r in results[:25]:
        extra = ""
        if r.get("rating"):
            extra += f" | nota {r['rating']} ({r.get('rating_count', 0)} avaliações)"
        elif r["brand"]:
            extra += " | parece ser rede/marca"
        lines.append(f"- {r['name']} | {r['distance_km']:.2f}km | pontuação {r['score']} ({r['level']}){extra}")
    lines.append(
        "Esses dados podem estar incompletos ou desatualizados. Você não tem acesso à internet em tempo real: "
        "não invente faturamento, número de funcionários, avaliações ou público-alvo dos concorrentes que não "
        "foram informados aqui — deixe claro quando não souber algo, e ajude com análise e sugestões em cima do "
        "que foi fornecido."
    )
    return "\n".join(lines)


def call_gemini(api_key, context_prompt, history, user_text):
    contents = [
        {"role": "user", "parts": [{"text": context_prompt}]},
        {"role": "model", "parts": [{"text": "Entendido — vou usar só esses dados e avisar quando não souber algo."}]},
    ]
    for m in history:
        contents.append({"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]})
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    last_err = ""
    for model in ("gemini-2.5-flash", "gemini-2.0-flash"):
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={api_key.strip()}"
        )
        resp = requests.post(url, json={"contents": contents}, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            parts = (((data.get("candidates") or [{}])[0]).get("content") or {}).get("parts") or []
            text = "".join(p.get("text", "") for p in parts)
            return text or "(sem resposta do modelo)"
        last_err = f"{model} -> HTTP {resp.status_code}: {resp.text[:150]}"
    raise RuntimeError(last_err)


# =========================================================
# Estado
# =========================================================
if "company" not in st.session_state:
    st.session_state.company = None
if "results" not in st.session_state:
    st.session_state.results = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =========================================================
# Barra lateral: cadastro
# =========================================================
with st.sidebar:
    st.markdown("### Cadastre a empresa")
    nome = st.text_input("Nome da empresa")
    cat_labels = [c[0] for c in CATEGORIES]
    cat_idx = st.selectbox("Categoria do negócio", range(len(cat_labels)), format_func=lambda i: cat_labels[i])
    porte = st.selectbox("Porte da empresa (opcional)", [""] + PORTES)
    publico_alvo = st.text_input("Público-alvo (opcional)", placeholder="Ex.: famílias classe B/C, bairro tal")
    endereco = st.text_input("Endereço", placeholder="Rua, número, bairro, cidade")
    diferenciais = st.text_area("Diferenciais (opcional)", placeholder="Ex.: entrega em 20 min, produtos sem glúten...")
    raio_km = st.slider("Raio de busca (km)", 0.5, 30.0, 5.0, 0.5)

    with st.expander("Opções avançadas (mapa e Google Places)"):
        map_style = st.selectbox(
            "Estilo do mapa",
            [
                "Cinza minimalista (padrão, sem chave)",
                "OpenStreetMap colorido",
            ],
        )
        google_places_key_input = st.text_input(
            "Chave Google Places API (opcional)",
            type="password",
            value=get_secret("GOOGLE_PLACES_API_KEY"),
            help="Opcional: se preenchida, puxa notas e avaliações do Google. Se vazia, usa a busca gratuita (OSM + ArcGIS).",
        )

    buscar = st.button("Analisar concorrência", type="primary", use_container_width=True)
    st.caption("Busca gratuita integrada: OpenStreetMap + ArcGIS Places + Photon (sem chave obrigatória).")

if buscar:
    if not nome.strip() or not endereco.strip():
        st.sidebar.error("Informe pelo menos o nome da empresa e o endereço.")
    else:
        with st.spinner("Localizando endereço..."):
            coords, geo_err = geocode(endereco.strip())
        if not coords:
            st.sidebar.error(
                f"{geo_err} Tente um formato completo (ex.: Rua, Número, Bairro, Cidade - UF)."
            )
        else:
            lat, lon = coords
            g_key = google_places_key_input.strip()
            if g_key:
                place_type = CATEGORIES[cat_idx][3]
                with st.spinner("Buscando concorrentes no Google Places..."):
                    try:
                        places = _google_places_cached(g_key, round(lat, 5), round(lon, 5), place_type, float(raio_km))
                        results = parse_and_score_google(places, lat, lon, raio_km, nome)
                        source_used = "Google Places"
                        err = None
                    except Exception as e:  # noqa: BLE001
                        results = []
                        source_used = "Google Places"
                        err = str(e)
            else:
                tag_pairs = CATEGORIES[cat_idx][1]
                search_terms = CATEGORIES[cat_idx][2]
                with st.spinner("Buscando concorrentes na região..."):
                    results = search_free_sources(lat, lon, tag_pairs, search_terms, raio_km, nome)
                source_used = "Base aberta (OSM + ArcGIS)"
                err = None

            if err and not results:
                st.sidebar.error(f"Erro na busca ({err}).")
            else:
                st.session_state.company = {
                    "nome": nome.strip(),
                    "cat_idx": cat_idx,
                    "porte": porte,
                    "endereco": endereco.strip(),
                    "diferenciais": diferenciais.strip(),
                    "publico_alvo": publico_alvo.strip(),
                    "raio_km": raio_km,
                    "lat": lat,
                    "lon": lon,
                    "source": source_used,
                }
                st.session_state.results = results
                st.session_state.chat_history = []

company = st.session_state.company
results = st.session_state.results

# =========================================================
# Conteúdo principal
# =========================================================
if not company:
    st.info("Cadastre a empresa na barra lateral à esquerda pra ver o mapa de concorrência aqui.")
else:
    safe_company_name = html.escape(company["nome"])
    source_label = company.get("source", "Base aberta (OSM + ArcGIS)")
    meta = f"{CATEGORIES[company['cat_idx']][0]}"
    if company["porte"]:
        meta += f" · {company['porte']}"
    meta += f" · raio de {company['raio_km']:.1f} km · fonte: {source_label}"
    safe_meta = html.escape(meta)
    publico_line = (
        f"<div class='meta'>Público-alvo: {html.escape(company['publico_alvo'])}</div>"
        if company["publico_alvo"]
        else ""
    )
    st.markdown(
        f"""
        <div class="company-card">
            <div class="company-title">{safe_company_name}</div>
            <div class="meta">{safe_meta}</div>
            {publico_line}
        </div>
        """,
        unsafe_allow_html=True,
    )

    n_alta = sum(1 for r in results if r["level"] == "alta")
    n_media = sum(1 for r in results if r["level"] == "media")
    n_baixa = sum(1 for r in results if r["level"] == "baixa")

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f"<div class='legend-pill' style='background:{RED_BG};color:{RED};'>Alta: {n_alta}<small>Pontuação ≥ 60</small></div>",
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"<div class='legend-pill' style='background:{AMBER_BG};color:{AMBER};'>Média: {n_media}<small>Pontuação 30–59</small></div>",
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"<div class='legend-pill' style='background:{GREEN_BG};color:{GREEN};'>Baixa: {n_baixa}<small>Pontuação &lt; 30</small></div>",
        unsafe_allow_html=True,
    )

    if results:
        avg_score = round(sum(r["score"] for r in results) / len(results))
        top = results[0]
        if n_alta >= 3 or avg_score >= 60:
            overall = "Concorrência local Alta"
        elif len(results) >= 3 or avg_score >= 35:
            overall = "Concorrência local Moderada"
        else:
            overall = "Concorrência local Baixa"
        st.markdown(
            f"<div class='summary-banner'><b>Panorama no raio de {company['raio_km']:.1f} km:</b> "
            f"{overall} · <b>{len(results)}</b> concorrente(s) encontrado(s) · "
            f"principal: <b>{html.escape(top['name'])}</b> ({top['distance_km']:.2f} km, pontuação {top['score']}).</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            f"Nenhum concorrente da categoria **{CATEGORIES[company['cat_idx']][0]}** foi encontrado "
            f"num raio de {company['raio_km']:.1f} km. Tente aumentar o raio ou testar uma categoria mais ampla."
        )

    with st.expander("Como o nível de concorrência é calculado"):
        if source_label == "Google Places":
            st.write(
                "Com o Google Places ativo, a pontuação pondera proximidade (60%), nota média no Google (20%) "
                "e volume de avaliações (20%, escala logarítmica até 1.000 avaliações)."
            )
        else:
            st.write(
                "No modo gratuito (OpenStreetMap + ArcGIS), a pontuação pondera proximidade (85%) e indício "
                "de rede/franquia (15% — locais com tag de marca/operador somam pontos). Se quiser notas e "
                "volume de avaliações, adicione uma chave do Google Places nas opções avançadas."
            )

    # ---- Mapa ----
    zoom_start = 15 if company["raio_km"] <= 1.5 else (14 if company["raio_km"] <= 5 else (12 if company["raio_km"] <= 15 else 11))

    if map_style == "OpenStreetMap colorido":
        fmap = folium.Map(location=[company["lat"], company["lon"]], zoom_start=zoom_start, tiles="OpenStreetMap")
    else:
        # Fundo cinza minimalista sem marca d'água e sem chave de API
        fmap = folium.Map(location=[company["lat"], company["lon"]], zoom_start=zoom_start, tiles=None)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
            name="Cinza minimalista",
            max_zoom=16,
        ).add_to(fmap)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles &copy; Esri",
            name="Rótulos",
            overlay=True,
            max_zoom=16,
        ).add_to(fmap)

    # Círculo visual do raio de busca
    folium.Circle(
        location=[company["lat"], company["lon"]],
        radius=company["raio_km"] * 1000,
        color=ACCENT,
        weight=1.5,
        dash_array="5, 5",
        fill=True,
        fill_color=ACCENT,
        fill_opacity=0.05,
    ).add_to(fmap)

    folium.CircleMarker(
        location=[company["lat"], company["lon"]],
        radius=9,
        color="#fff",
        weight=2,
        fill=True,
        fill_color=ACCENT,
        fill_opacity=1,
        popup=folium.Popup(f"<b>{safe_company_name}</b><br>(empresa cadastrada)", max_width=220),
    ).add_to(fmap)

    for r in results:
        safe_r_name = html.escape(r["name"])
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lon']}"

        popup_html = f"<b>{safe_r_name}</b><br>Pontuação: {r['score']} ({LEVEL_LABEL[r['level']]})<br>{r['distance_km']:.2f} km"
        if r.get("rating"):
            popup_html += f"<br>Nota Google: {r['rating']} ({r.get('rating_count', 0)} aval.)"
        if r.get("address"):
            popup_html += f"<br>Endereço: {html.escape(r['address'])}"
        if r.get("phone"):
            popup_html += f"<br>Tel: {html.escape(r['phone'])}"
        if r.get("website") and r["website"].startswith(("http://", "https://")):
            popup_html += f"<br><a href='{html.escape(r['website'])}' target='_blank'>Site</a>"
        if r.get("hours"):
            popup_html += f"<br>Horário: {html.escape(r['hours'])}"
        popup_html += f"<br><a href='{gmaps_url}' target='_blank'>Ver no Google Maps</a>"

        folium.CircleMarker(
            location=[r["lat"], r["lon"]],
            radius=7,
            color="#fff",
            weight=2,
            fill=True,
            fill_color=LEVEL_COLOR[r["level"]],
            fill_opacity=1,
            popup=folium.Popup(popup_html, max_width=260),
        ).add_to(fmap)

    st_folium(
        fmap,
        use_container_width=True,
        height=480,
        returned_objects=[],
        key="competitor_map",
    )

    # ---- Lista de resultados ----
    st.markdown(f"#### {len(results)} empresa(s) encontrada(s) por perto")
    if not results:
        st.write(
            f"Nenhuma empresa parecida encontrada no {source_label} dentro desse raio. "
            "Tente aumentar o raio ou testar em área mais urbana."
        )
    else:
        for r in results:
            extra_info = f"{r['distance_km']:.2f} km"
            if r.get("rating"):
                extra_info += f" · ★ {r['rating']} ({r.get('rating_count', 0)})"
            elif r["brand"]:
                extra_info += " · rede/marca identificada"
            if r.get("address"):
                extra_info += f" · {html.escape(r['address'])}"

            st.markdown(
                f"""
                <div class="result-row">
                    <div>
                        <b>{html.escape(r['name'])}</b><br>
                        <span style="font-size:12px;color:rgba(0,0,0,.65);">
                            {extra_info}
                        </span>
                    </div>
                    <div class="score-badge" style="background:{LEVEL_BG[r['level']]};color:{LEVEL_COLOR[r['level']]};">
                        {LEVEL_LABEL[r['level']]} · {r['score']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ---- Chat (Gemini) ----
    st.divider()
    st.markdown("### 💬 Assistente (Gemini, gratuito)")
    gemini_key = st.text_input(
        "Chave gratuita da API do Gemini",
        type="password",
        value=get_secret("GEMINI_API_KEY"),
        help="Gere grátis em aistudio.google.com/apikey — não pede cartão.",
        key="gemini_key_input",
    )
    if not gemini_key:
        st.caption(
            "Cole sua chave acima pra ativar o assistente. Ele conversa sobre os dados que esta página já "
            "coletou (concorrentes, distância, pontuação) — não tem acesso à internet em tempo real, então "
            "não vai 'descobrir' faturamento ou dados que não estão aqui."
        )
    else:
        for msg in st.session_state.chat_history:
            with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                st.write(msg["text"])

        user_msg = st.chat_input("Pergunte algo sobre a empresa ou os concorrentes...")
        if user_msg:
            st.session_state.chat_history.append({"role": "user", "text": user_msg})
            with st.chat_message("user"):
                st.write(user_msg)
            with st.chat_message("assistant"):
                with st.spinner("digitando..."):
                    try:
                        if re.search(r"fatura", user_msg, re.I):
                            reply = fake_revenue_demo_reply()
                        else:
                            context_prompt = build_context_prompt(company, results)
                            reply = call_gemini(gemini_key, context_prompt, st.session_state.chat_history[:-1], user_msg)
                    except Exception as e:  # noqa: BLE001
                        reply = (
                            f"Não consegui responder agora ({e}). Confira se a chave está correta e ainda "
                            "tem cota disponível."
                        )
                st.write(reply)
            st.session_state.chat_history.append({"role": "model", "text": reply})
