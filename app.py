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

INK = "#000000"
ACCENT = "#0063A9"
RED, RED_BG = "#C1443D", "#F7E4E2"
AMBER, AMBER_BG = "#B9812A", "#F7EBD6"
GREEN, GREEN_BG = "#357A5D", "#E1EFE7"
LEVEL_COLOR = {"alta": RED, "media": AMBER, "baixa": GREEN}
LEVEL_BG = {"alta": RED_BG, "media": AMBER_BG, "baixa": GREEN_BG}
LEVEL_LABEL = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}

# Cada categoria mapeia para uma lista de pares (chave_osm, valor_ou_lista_osm)
# para cobrir variações comuns de mapeamento no OpenStreetMap Brasil
CATEGORIES = [
    ("Restaurante", [("amenity", ["restaurant", "food_court"])]),
    ("Cafeteria", [("amenity", "cafe"), ("shop", "coffee")]),
    ("Padaria", [("shop", "bakery"), ("amenity", "bakery")]),
    ("Bar", [("amenity", ["bar", "pub", "nightclub", "biergarten"])]),
    ("Academia", [("leisure", ["fitness_centre", "sports_centre"]), ("sport", "fitness")]),
    ("Salão de beleza / barbearia", [("shop", ["hairdresser", "barber"])]),
    ("Clínica de estética / spa", [("shop", ["beauty", "massage"]), ("leisure", "spa")]),
    ("Farmácia", [("amenity", "pharmacy"), ("shop", "chemist")]),
    ("Loja de roupas", [("shop", ["clothes", "boutique", "fashion"])]),
    ("Loja de calçados", [("shop", "shoes")]),
    ("Pet shop", [("shop", "pet"), ("amenity", "veterinary")]),
    ("Loja de eletrônicos", [("shop", ["electronics", "mobile_phone", "computer"])]),
    ("Supermercado", [("shop", "supermarket")]),
    ("Mercado de conveniência", [("shop", ["convenience", "greengrocer", "grocery"])]),
    ("Escritório de advocacia", [("office", "lawyer")]),
    ("Consultório odontológico", [("amenity", "dentist")]),
    ("Clínica médica", [("amenity", ["doctors", "clinic"])]),
    ("Oficina mecânica", [("shop", ["car_repair", "tyres"]), ("craft", "car_repair")]),
    ("Imobiliária", [("office", "estate_agent")]),
    ("Pousada / hotel", [("tourism", ["hotel", "guest_house", "hostel", "motel"])]),
    ("Loja de móveis", [("shop", ["furniture", "interior_decoration"])]),
    ("Livraria", [("shop", "books")]),
    ("Floricultura", [("shop", "florist")]),
]

PORTES = ["MEI / autônomo", "Pequena empresa", "Média empresa", "Grande empresa / rede"]

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

HTTP_HEADERS = {
    "User-Agent": "MapaDaConcorrenciaApp/1.3 (https://mapa-da-concorrencia-h7ca5nycufbwqsfsychauq.streamlit.app)",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

# =========================================================
# Estilo
# =========================================================
st.markdown(
    f"""
    <style>
    :root {{ color-scheme: light !important; }}
    html, body, .stApp,
    [data-testid="stAppViewContainer"], [data-testid="stMain"],
    [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"],
    [data-testid="stBlock"], [data-testid="stHeader"] {{
        background-color:#FFFFFF !important; color:{INK} !important;
    }}
    [data-testid="stSidebar"] {{ background:#FFFFFF !important; border-right:1px solid rgba(0,0,0,.12); }}
    [data-testid="stSidebar"] * {{ color:{INK} !important; }}
    h1, h2, h3, h4 {{ color:{INK} !important; }}
    .stButton>button[kind="primary"] {{
        background:{INK} !important; border-color:{INK} !important; color:#FFFFFF !important;
    }}
    .stButton>button[kind="primary"] * {{ color:#FFFFFF !important; }}
    .stButton>button[kind="primary"]:hover {{ background:{ACCENT} !important; border-color:{ACCENT} !important; }}
    [data-testid="stSidebar"] button[kind="primary"],
    [data-testid="stSidebar"] button[kind="primary"] *,
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] * {{
        background-color: {INK} !important;
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] button[kind="primary"]:hover,
    [data-testid="stSidebar"] button[kind="primary"]:hover *,
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover,
    [data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover * {{
        background-color: {ACCENT} !important;
        color: #FFFFFF !important;
    }}
    a {{ color:{ACCENT}; }}
    label, .stMarkdown p, .stMarkdown span {{ color:{INK}; }}
    .stTextInput > div,
    .stTextInput > div > div,
    .stTextInput input,
    .stTextArea > div,
    .stTextArea > div > div,
    .stTextArea textarea,
    [data-baseweb="input"],
    [data-baseweb="input"] > div,
    [data-baseweb="base-input"],
    [data-baseweb="textarea"] {{
        background-color:#FFFFFF !important; color:{INK} !important;
    }}
    .stTextInput input, .stTextArea textarea {{
        border:1px solid rgba(0,0,0,.25) !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{ color:rgba(0,0,0,.45) !important; }}
    [data-baseweb="select"],
    [data-baseweb="select"] > div,
    [data-baseweb="select"] > div > div,
    [data-baseweb="select"] input {{
        background-color:#FFFFFF !important; color:{INK} !important;
    }}
    [data-baseweb="select"] > div {{
        border:1px solid rgba(0,0,0,.25) !important;
    }}
    [data-baseweb="select"] span, [data-baseweb="select"] svg {{ color:{INK} !important; fill:{INK} !important; }}
    html body [data-baseweb="popover"],
    html body [data-baseweb="popover"] div,
    html body [data-baseweb="menu"],
    html body [data-baseweb="menu"] ul,
    html body ul[role="listbox"],
    html body li[role="option"],
    html body li[data-baseweb="menu-option"] {{
        background-color:#FFFFFF !important; color:{INK} !important;
    }}
    html body li[role="option"] *,
    html body li[data-baseweb="menu-option"] * {{
        color:{INK} !important;
    }}
    html body li[role="option"]:hover,
    html body li[role="option"][aria-selected="true"],
    html body li[data-baseweb="menu-option"]:hover,
    html body li[data-baseweb="menu-option"][aria-selected="true"] {{
        background-color:#EAF2F8 !important; color:{INK} !important;
    }}
    [data-testid="stSlider"] label, [data-testid="stWidgetLabel"] p {{ color:{INK} !important; }}
    [data-testid="stAlert"], [data-testid="stAlertContainer"] {{
        background-color:#EAF2F8 !important; border:1px solid {ACCENT} !important;
    }}
    [data-testid="stAlert"] *, [data-testid="stAlertContainer"] * {{ color:{INK} !important; }}
    [data-testid="stChatMessage"] {{ background-color:#F5F5F5 !important; }}
    [data-testid="stChatMessage"] * {{ color:{INK} !important; }}
    [data-testid="stExpander"] {{ background-color:#FFFFFF !important; border:1px solid rgba(0,0,0,.2) !important; }}
    [data-testid="stExpander"] * {{ color:{INK} !important; }}
    [data-testid="stCaptionContainer"] {{ color:rgba(0,0,0,.6) !important; }}
    .header-bar {{
        background:{INK}; border-radius:10px; padding:14px 20px;
        display:flex; align-items:center; gap:14px; margin-bottom:18px;
    }}
    .header-bar img {{ height:40px; }}
    .header-bar .title {{ color:#FFFFFF !important; font-size:22px; font-weight:700; line-height:1.1; }}
    .header-bar .subtitle {{ color:rgba(255,255,255,.75) !important; font-size:12.5px; margin-top:2px; }}
    .legend-pill {{
        padding:10px 12px; border-radius:8px; font-weight:700; font-size:13px; text-align:center;
        margin-bottom:8px;
    }}
    .legend-pill small {{
        display:block; font-weight:400; font-size:11.5px; opacity:0.85; margin-top:2px;
    }}
    .summary-banner {{
        border:1px solid rgba(0,0,0,.15); border-radius:8px; padding:10px 14px;
        margin-bottom:10px; font-size:13.5px; background:#F9FAFB;
    }}
    .company-card {{
        background:{INK}; border-radius:10px; padding:14px 18px; margin-bottom:14px;
    }}
    .company-card .company-title {{ color:#FFFFFF !important; font-size:18px; font-weight:700; }}
    .company-card .meta {{ color:rgba(255,255,255,.8) !important; font-size:12.5px; margin-top:4px; }}
    .result-row {{
        display:flex; justify-content:space-between; align-items:center;
        border:1px solid rgba(0,0,0,.14); border-radius:10px; padding:10px 14px; margin-bottom:8px;
    }}
    .score-badge {{ font-weight:700; font-size:12px; padding:3px 10px; border-radius:20px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


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
            <div class="subtitle">OpenStreetMap · sem chave de API obrigatória, sem custo</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Busca: geocodificação (com fallback) + Overpass
# =========================================================
@st.cache_data(show_spinner=False, ttl=86400)
def _geocode_cached(address_norm: str):
    errors = []

    # 1. Photon (Komoot / OpenStreetMap) — sem bloqueio de IP compartilhado
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

    # 2. ArcGIS World Geocoding (gratuito sem chave para busca simples)
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

    # 3. Nominatim (OpenStreetMap oficial)
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


@st.cache_data(show_spinner=False, ttl=1800)
def _overpass_cached(lat: float, lon: float, tag_pairs: tuple, radius_km: float):
    radius_m = int(radius_km * 1000)
    result_cap = 200 if radius_km > 10 else 100
    clauses = []
    for key, value in tag_pairs:
        val_arg = list(value) if isinstance(value, tuple) else value
        tf = build_tag_filter(key, val_arg)
        clauses.append(f"node{tf}(around:{radius_m},{lat},{lon});")
        clauses.append(f"way{tf}(around:{radius_m},{lat},{lon});")
        clauses.append(f"relation{tf}(around:{radius_m},{lat},{lon});")

    query = f"[out:json][timeout:25];({''.join(clauses)});out center tags {result_cap};"
    last_err = None
    for url in OVERPASS_MIRRORS:
        try:
            resp = requests.post(url, data={"data": query}, headers=HTTP_HEADERS, timeout=30)
            if resp.status_code != 200:
                last_err = f"{url.split('/')[2]}: HTTP {resp.status_code}"
                continue
            data = resp.json()
            if "elements" not in data:
                last_err = f"{url.split('/')[2]}: resposta sem dados ({data.get('remark', '?')})"
                continue
            return data["elements"]
        except Exception as e:  # noqa: BLE001
            last_err = f"{url.split('/')[2]}: {e}"
            continue
    raise ConnectionError(last_err or "Todos os espelhos Overpass falharam.")


def overpass_search(lat, lon, tag_pairs, radius_km):
    frozen_pairs = tuple(
        (k, tuple(v) if isinstance(v, list) else v)
        for k, v in tag_pairs
    )
    try:
        elements = _overpass_cached(round(lat, 5), round(lon, 5), frozen_pairs, float(radius_km))
        return elements, None
    except ConnectionError as e:
        return [], str(e)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_and_score(elements, center_lat, center_lon, radius_km, own_name):
    rows = []
    seen_ids = set()
    for el in elements:
        el_uid = (el.get("type"), el.get("id"))
        if el_uid in seen_ids:
            continue
        seen_ids.add(el_uid)

        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        tags = el.get("tags", {}) or {}
        name = tags.get("name", "Sem nome no OSM")
        dist = haversine_km(center_lat, center_lon, lat, lon)
        if dist < 0.015 and name.strip().lower() == (own_name or "").strip().lower():
            continue
        brand = bool(tags.get("brand") or tags.get("operator"))
        distance_score = max(0.0, 1 - dist / max(radius_km, 0.1))
        raw = distance_score * 0.85 + (0.15 if brand else 0)
        score = round(raw * 100)
        level = "alta" if score >= 60 else ("media" if score >= 30 else "baixa")
        rows.append(
            {
                "name": name,
                "lat": lat,
                "lon": lon,
                "distance_km": dist,
                "brand": brand,
                "score": score,
                "level": level,
                "tags": tags,
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
        "[EXEMPLO ILUSTRATIVO — não é um dado real]

"
        "A internet não expõe o faturamento de empresas pequenas/locais, então isto é só uma simulação de "
        f"como a resposta apareceria aqui: com base no porte e na categoria informados, uma estimativa "
        f"fictícia de faturamento mensal ficaria por volta de R$ {lo}.000 a R$ {hi}.000.

"
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
    lines.append(f"Concorrentes encontrados ({len(results)}):")
    for r in results[:25]:
        extra = " | parece ser rede/marca" if r["brand"] else ""
        lines.append(f"- {r['name']} | {r['distance_km']:.2f}km | pontuação {r['score']} ({r['level']}){extra}")
    lines.append(
        "Esses dados vêm do OpenStreetMap (gratuito) e podem estar incompletos ou desatualizados. Você não "
        "tem acesso à internet em tempo real: não invente faturamento, número de funcionários, avaliações ou "
        "público-alvo dos concorrentes que não foram informados aqui — deixe claro quando não souber algo, e "
        "ajude com análise e sugestões em cima do que foi fornecido."
    )
    return "
".join(lines)


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
if "search_warning" not in st.session_state:
    st.session_state.search_warning = None

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
    if raio_km > 15:
        st.caption("Acima de ~15 km a busca cobre a cidade toda, mas demora mais (pode levar até 40s).")
    buscar = st.button("Analisar concorrência", type="primary", use_container_width=True)
    st.caption("Geocodificação: Photon/OSM · Busca de locais: Overpass API/OSM. Servidores públicos, para uso leve.")

if buscar:
    if not nome.strip() or not endereco.strip():
        st.sidebar.error("Informe pelo menos o nome da empresa e o endereço.")
    else:
        with st.spinner("Geocodificando endereço..."):
            coords, geo_err = geocode(endereco.strip())
        if not coords:
            st.sidebar.error(
                f"{geo_err} Tente um formato completo (ex.: Rua, Número, Bairro, Cidade - UF)."
            )
        else:
            lat, lon = coords
            tag_pairs = CATEGORIES[cat_idx][1]
            with st.spinner("Buscando empresas parecidas (pode levar até 40s em raios grandes)..."):
                elements, err = overpass_search(lat, lon, tag_pairs, raio_km)
            if err and not elements:
                st.sidebar.error(
                    f"Os servidores públicos do OpenStreetMap estão indisponíveis no momento ({err}). "
                    "Tente de novo em alguns minutos."
                )
            else:
                results = parse_and_score(elements, lat, lon, raio_km, nome)
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
                }
                st.session_state.results = results
                st.session_state.chat_history = []
                st.session_state.search_warning = err

company = st.session_state.company
results = st.session_state.results

# =========================================================
# Conteúdo principal
# =========================================================
if not company:
    st.info("Cadastre a empresa na barra lateral à esquerda pra ver o mapa de concorrência aqui.")
else:
    safe_company_name = html.escape(company["nome"])
    meta = CATEGORIES[company["cat_idx"]][0]
    if company["porte"]:
        meta += f" · {company['porte']}"
    meta += f" · raio de {company['raio_km']:.1f} km"
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
            f"{overall} · <b>{len(results)}</b> concorrente(s) mapeado(s) · "
            f"mais próximo: <b>{html.escape(top['name'])}</b> ({top['distance_km']:.2f} km, pontuação {top['score']}).</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            f"Nenhum concorrente da categoria **{CATEGORIES[company['cat_idx']][0]}** foi encontrado no "
            f"OpenStreetMap num raio de {company['raio_km']:.1f} km. Isso geralmente indica baixa densidade de "
            "mapeamento colaborativo nesse bairro — tente aumentar o raio de busca ou testar uma categoria mais ampla."
        )

    with st.expander("Como o nível de concorrência é calculado"):
        st.write(
            "O OpenStreetMap não tem nota nem número de avaliações por local, então a pontuação usa só "
            "proximidade (85%) e indício de rede/franquia (15% — locais com tag de marca/operador somam "
            "pontos, por tendencialmente terem mais estrutura). É uma estimativa mais grosseira do que uma "
            "versão com o Google traria — trate como um primeiro filtro visual, não como medida final de "
            "força do concorrente."
        )

    # ---- Mapa ----
    zoom_start = 15 if company["raio_km"] <= 1.5 else (14 if company["raio_km"] <= 5 else (12 if company["raio_km"] <= 15 else 11))
    fmap = folium.Map(location=[company["lat"], company["lon"]], zoom_start=zoom_start, tiles="OpenStreetMap")

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
        tags = r["tags"]
        safe_r_name = html.escape(r["name"])
        addr_parts = [tags.get("addr:street"), tags.get("addr:housenumber")]
        address = html.escape(", ".join([p for p in addr_parts if p]))
        phone = html.escape(str(tags.get("phone") or tags.get("contact:phone") or ""))
        website = tags.get("website") or tags.get("contact:website")
        hours = html.escape(str(tags.get("opening_hours") or ""))
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lon']}"

        popup_html = f"<b>{safe_r_name}</b><br>Pontuação: {r['score']} ({LEVEL_LABEL[r['level']]})<br>{r['distance_km']:.2f} km"
        if address:
            popup_html += f"<br>Endereço: {address}"
        if phone:
            popup_html += f"<br>Tel: {phone}"
        if website and str(website).startswith(("http://", "https://")):
            popup_html += f"<br><a href='{html.escape(str(website))}' target='_blank'>Site</a>"
        if hours:
            popup_html += f"<br>Horário: {hours}"
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
            "Nenhuma empresa parecida encontrada no OpenStreetMap dentro desse raio. A cobertura do OSM "
            "varia bastante por região — tente aumentar o raio ou testar em área mais urbana."
        )
    else:
        for r in results:
            st.markdown(
                f"""
                <div class="result-row">
                    <div>
                        <b>{html.escape(r['name'])}</b><br>
                        <span style="font-size:12px;color:rgba(0,0,0,.6);">
                            {r['distance_km']:.2f} km{' · rede/marca identificada' if r['brand'] else ''}
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
