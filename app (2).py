import base64
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

CATEGORIES = [
    ("amenity", "restaurant", "Restaurante"),
    ("amenity", "cafe", "Cafeteria"),
    ("shop", "bakery", "Padaria"),
    ("amenity", ["bar", "pub", "nightclub"], "Bar"),
    ("leisure", ["fitness_centre", "sports_centre"], "Academia"),
    ("shop", "hairdresser", "Salão de beleza / barbearia"),
    ("shop", "beauty", "Clínica de estética / spa"),
    ("amenity", "pharmacy", "Farmácia"),
    ("shop", "clothes", "Loja de roupas"),
    ("shop", "shoes", "Loja de calçados"),
    ("shop", "pet", "Pet shop"),
    ("shop", "electronics", "Loja de eletrônicos"),
    ("shop", "supermarket", "Supermercado"),
    ("shop", "convenience", "Mercado de conveniência"),
    ("office", "lawyer", "Escritório de advocacia"),
    ("amenity", "dentist", "Consultório odontológico"),
    ("amenity", "doctors", "Clínica médica"),
    ("shop", "car_repair", "Oficina mecânica"),
    ("office", "estate_agent", "Imobiliária"),
    ("tourism", ["hotel", "guest_house"], "Pousada / hotel"),
    ("shop", "furniture", "Loja de móveis"),
    ("shop", "books", "Livraria"),
    ("shop", "florist", "Floricultura"),
]

PORTES = ["MEI / autônomo", "Pequena empresa", "Média empresa", "Grande empresa / rede"]

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]

HTTP_HEADERS = {"User-Agent": "mapa-da-concorrencia/1.0 (uso pessoal, contato nao informado)"}

# =========================================================
# Estilo: preto, branco e azul da marca, mantendo o
# vermelho/amarelo/verde só nos indicadores de concorrência
# =========================================================
st.markdown(
    f"""
    <style>
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
        background:{INK}; border-color:{INK}; color:#fff;
    }}
    .stButton>button[kind="primary"]:hover {{ background:{ACCENT}; border-color:{ACCENT}; }}
    a {{ color:{ACCENT}; }}
    /* Força campos legíveis independente do tema claro/escuro do navegador */
    label, .stMarkdown, p, span, div {{ color:{INK}; }}
    .stTextInput input, .stTextArea textarea {{
        background-color:#FFFFFF !important; color:{INK} !important;
        border:1px solid rgba(0,0,0,.25) !important;
    }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{ color:rgba(0,0,0,.45) !important; }}
    [data-baseweb="select"] > div {{
        background-color:#FFFFFF !important; color:{INK} !important;
        border:1px solid rgba(0,0,0,.25) !important;
    }}
    [data-baseweb="select"] span {{ color:{INK} !important; }}
    [data-baseweb="popover"] li {{ background-color:#FFFFFF !important; color:{INK} !important; }}
    [data-testid="stSlider"] label {{ color:{INK} !important; }}
    [data-testid="stWidgetLabel"] p {{ color:{INK} !important; }}
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
    .header-bar .title {{ color:#fff; font-size:22px; font-weight:700; line-height:1.1; }}
    .header-bar .subtitle {{ color:rgba(255,255,255,.65); font-size:12.5px; margin-top:2px; }}
    .legend-pill {{
        padding:8px 10px; border-radius:6px; font-weight:700; font-size:12.5px; text-align:center;
    }}
    .company-card {{
        background:{INK}; color:#fff; border-radius:10px; padding:14px 18px; margin-bottom:14px;
    }}
    .company-card .meta {{ color:rgba(255,255,255,.75); font-size:12.5px; margin-top:4px; }}
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
# Busca: geocodificação + Overpass (roda no servidor,
# então não sofre o bloqueio de CORS que afeta a versão
# 100% em navegador)
# =========================================================
@st.cache_data(show_spinner=False, ttl=3600)
def geocode(address: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"format": "json", "limit": 1, "q": address}
    resp = requests.get(url, params=params, headers=HTTP_HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return None
    return float(data[0]["lat"]), float(data[0]["lon"])


def build_tag_filter(key, value):
    if isinstance(value, list):
        return f'["{key}"~"^({"|".join(value)})$"]'
    return f'["{key}"="{value}"]'


def overpass_search(lat, lon, key, value, radius_km):
    radius_m = int(radius_km * 1000)
    result_cap = 200 if radius_km > 10 else 80
    tag_filter = build_tag_filter(key, value)
    query = (
        f"[out:json][timeout:25];"
        f"(node{tag_filter}(around:{radius_m},{lat},{lon});"
        f"way{tag_filter}(around:{radius_m},{lat},{lon}););"
        f"out center tags {result_cap};"
    )
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
            return data["elements"], None
        except Exception as e:  # noqa: BLE001
            last_err = f"{url.split('/')[2]}: {e}"
            continue
    return [], last_err


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
    for el in elements:
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
# Chat (Gemini, chave gratuita colada pelo próprio usuário).
# A chamada roda no servidor, então também não sofre bloqueio
# de CORS como a versão em navegador sofria.
# =========================================================
def fake_revenue_demo_reply():
    time.sleep(0.9)
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
        f"Categoria: {CATEGORIES[company['cat_idx']][2]}",
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
    return "\n".join(lines)


def call_gemini(api_key, context_prompt, history, user_text):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
        f"?key={api_key}"
    )
    contents = [
        {"role": "user", "parts": [{"text": context_prompt}]},
        {"role": "model", "parts": [{"text": "Entendido — vou usar só esses dados e avisar quando não souber algo."}]},
    ]
    for m in history:
        contents.append({"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["text"]}]})
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    resp = requests.post(url, json={"contents": contents}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"http-{resp.status_code}: {resp.text[:150]}")
    data = resp.json()
    parts = (((data.get("candidates") or [{}])[0]).get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts)
    return text or "(sem resposta do modelo)"


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
    cat_labels = [c[2] for c in CATEGORIES]
    cat_idx = st.selectbox("Categoria do negócio", range(len(cat_labels)), format_func=lambda i: cat_labels[i])
    porte = st.selectbox("Porte da empresa (opcional)", [""] + PORTES)
    publico_alvo = st.text_input("Público-alvo (opcional)", placeholder="Ex.: famílias classe B/C, bairro tal")
    endereco = st.text_input("Endereço", placeholder="Rua, número, bairro, cidade")
    diferenciais = st.text_area("Diferenciais (opcional)", placeholder="Ex.: entrega em 20 min, produtos sem glúten...")
    raio_km = st.slider("Raio de busca (km)", 0.5, 30.0, 5.0, 0.5)
    if raio_km > 15:
        st.caption("Acima de ~15 km a busca cobre a cidade toda, mas demora mais (pode levar até 40s).")
    buscar = st.button("Analisar concorrência", type="primary", use_container_width=True)
    st.caption("Geocodificação: Nominatim/OSM · Busca de locais: Overpass API/OSM. Servidores públicos, para uso leve.")

if buscar:
    if not nome or not endereco:
        st.sidebar.error("Informe pelo menos o nome da empresa e o endereço.")
    else:
        with st.spinner("Geocodificando endereço..."):
            coords = geocode(endereco)
        if not coords:
            st.sidebar.error(
                "Não encontramos esse endereço no OpenStreetMap. Tente um formato mais completo, ou um "
                "endereço em área mais urbana."
            )
        else:
            lat, lon = coords
            key, value = CATEGORIES[cat_idx][0], CATEGORIES[cat_idx][1]
            with st.spinner("Buscando empresas parecidas (pode levar até 40s em raios grandes)..."):
                elements, err = overpass_search(lat, lon, key, value, raio_km)
            if err and not elements:
                st.sidebar.error(
                    f"Os servidores públicos do OpenStreetMap estão indisponíveis no momento ({err}). "
                    "Tente de novo em alguns minutos."
                )
            else:
                results = parse_and_score(elements, lat, lon, raio_km, nome)
                st.session_state.company = {
                    "nome": nome,
                    "cat_idx": cat_idx,
                    "porte": porte,
                    "endereco": endereco,
                    "diferenciais": diferenciais,
                    "publico_alvo": publico_alvo,
                    "raio_km": raio_km,
                    "lat": lat,
                    "lon": lon,
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
    meta = CATEGORIES[company["cat_idx"]][2]
    if company["porte"]:
        meta += f" · {company['porte']}"
    meta += f" · raio de {company['raio_km']:.1f} km"
    publico_line = f"<div class='meta'>Público-alvo: {company['publico_alvo']}</div>" if company["publico_alvo"] else ""
    st.markdown(
        f"""
        <div class="company-card">
            <div style="font-size:18px; font-weight:700;">{company['nome']}</div>
            <div class="meta">{meta}</div>
            {publico_line}
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='legend-pill' style='background:{RED_BG};color:{RED};'>Alta</div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='legend-pill' style='background:{AMBER_BG};color:{AMBER};'>Média</div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='legend-pill' style='background:{GREEN_BG};color:{GREEN};'>Baixa</div>", unsafe_allow_html=True)

    with st.expander("Como o nível de concorrência é calculado"):
        st.write(
            "O OpenStreetMap não tem nota nem número de avaliações por local, então a pontuação usa só "
            "proximidade (85%) e indício de rede/franquia (15% — locais com tag de marca/operador somam "
            "pontos, por tendencialmente terem mais estrutura). É uma estimativa mais grosseira do que uma "
            "versão com o Google traria — trate como um primeiro filtro visual, não como medida final de "
            "força do concorrente."
        )

    # ---- Mapa ----
    fmap = folium.Map(location=[company["lat"], company["lon"]], zoom_start=14, tiles=None)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr="&copy; colaboradores do OpenStreetMap &copy; CARTO",
        subdomains="abcd",
        name="CARTO Voyager",
    ).add_to(fmap)

    folium.CircleMarker(
        location=[company["lat"], company["lon"]],
        radius=9,
        color="#fff",
        weight=2,
        fill=True,
        fill_color=ACCENT,
        fill_opacity=1,
        popup=folium.Popup(f"<b>{company['nome']}</b><br>(empresa cadastrada)", max_width=220),
    ).add_to(fmap)

    for r in results:
        tags = r["tags"]
        addr_parts = [tags.get("addr:street"), tags.get("addr:housenumber")]
        address = ", ".join([p for p in addr_parts if p])
        phone = tags.get("phone") or tags.get("contact:phone")
        website = tags.get("website") or tags.get("contact:website")
        hours = tags.get("opening_hours")
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={r['lat']},{r['lon']}"

        popup_html = f"<b>{r['name']}</b><br>Pontuação: {r['score']} ({LEVEL_LABEL[r['level']]})<br>{r['distance_km']:.2f} km"
        if address:
            popup_html += f"<br>Endereço: {address}"
        if phone:
            popup_html += f"<br>Tel: {phone}"
        if website:
            popup_html += f"<br><a href='{website}' target='_blank'>Site</a>"
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

    st_folium(fmap, width=None, height=480, key="competitor_map")

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
                        <b>{r['name']}</b><br>
                        <span style="font-size:12px;color:rgba(0,0,0,.6);">
                            {r['distance_km']:.2f} km{' · rede/marca identificada' if r['brand'] else ''}
                        </span>
                    </div>
                    <div class="score-badge" style="background:{LEVEL_BG[r['level']]};color:{LEVEL_COLOR[r['level']]};">
                        {r['score']}
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
