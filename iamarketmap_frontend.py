import streamlit as st
import json
import pandas as pd
import investpy
import openai
import matplotlib.pyplot as plt
import numpy as np
import time
import datetime
from alpha_vantage.timeseries import TimeSeries
import re
import requests

# ✅ Este debe ir antes de cualquier otra función de Streamlit
st.set_page_config(page_title="Developer", layout="wide")   # ← este es el único cambio clave

# 🔐 Importa módulos de autenticación Supabase
from streamlit_supabase_auth import login_form, logout_button
from supabase import create_client

# 🧠 FORMULARIO DE LOGIN / SIGNUP
session = login_form(
    url = st.secrets["SUPABASE_URL"],
    apiKey = st.secrets["SUPABASE_KEY"],
    providers = ["google"],  # Puedes incluir "github", "facebook" si lo activas en Supabase
)

# ✋ Bloquea la app si no ha iniciado sesión
if not session:
    st.stop()

# 🔌 Cliente Supabase para guardar o leer datos si lo necesitas
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
user = session["user"]
st.success(f"Bienvenido, {user['email']}")


def run_app():


    # ============ NUEVO: FUNCIÓN PARA EXTRAER SECCIONES ============
    def extract_numbered_blocks(text):
        # Busca los títulos que empiezan con un número y dos puntos
        pattern = r"(?sm)^(\d+)\.\s*(.*?)(?=^\d+\.|\Z)"
        matches = re.findall(pattern, text)
        bloques = {}
        for num, content in matches:
            bloques[int(num)] = content.strip()
        # Buscar conclusión si existe, aunque no esté enumerada
        conc_pat = r"(?i)(Conclusi[oó]n.*?)$"
        conc_match = re.search(conc_pat, text)
        conclusion = conc_match.group(1).strip() if conc_match else ""
        return bloques, conclusion

    import csv
    import io




    def extraer_conclusion_json(text):
        """
        Busca el primer bloque JSON con la clave 'conclusion' y lo devuelve como dict.
        Si no se encuentra, retorna None.
        Si falta una llave de cierre al final, la agrega.
        """
        import re, json
        pattern = r'(\{[\s\S]*?"conclusion"[\s\S]*?\})'
        match = re.search(pattern, text)
        if match:
            json_str = match.group(1)
            # Limpieza: sin saltos de línea ni espacios extra
            json_str = json_str.replace('\n', '').replace('\r', '').strip()
            # Si falta la llave de cierre final, la agregamos
            if json_str.count('{') > json_str.count('}'):
                json_str += "}"
            try:
                return json.loads(json_str)['conclusion']
            except Exception as e:
                st.warning(f"Error al parsear el JSON: {e}\nContenido recibido: {json_str}")
                return None
        return None





    #openai.api_key = st.secrets["OPENAI_API_KEY"]
    # Inicializa ticker seleccionado
    if 'selected_ticker' not in st.session_state:
        st.session_state['selected_ticker'] = "AAPL"


    # =====================
    # CACHÉ y sesión
    # =====================

    @st.cache_data(ttl=3600)
    def obtener_datos_y_analisis(ticker, selected_interval):
        # Cambia la URL si tu backend está en otro host/puerto
        url = "https://backendaimm-production.up.railway.app/analizar"
        payload = {
            "ticker": ticker,
            "intervalo": selected_interval
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                data = response.json()
                resultado = data.get("resultado", "")
                return data.get("data", []), resultado
    # El primer valor (data) es None, a menos que necesites reconstruir un DataFrame en el frontend
            else:
                return None, f"Error en API: {response.text}"
        except Exception as e:
            return None, f"Error conectando con backend: {e}"





    if 'ultimo_analisis' not in st.session_state:
        st.session_state['ultimo_analisis'] = None

    # =====================
    # UI y estilo
    # =====================
    st.markdown("""
        <style>
        body { background-color: #0f172a; color: white; }
        .stApp { background-color: #0f172a; color: white; }
        .card {
            background-color: #1e293b;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        div.stButton > button {
            background-color: #3b82f6;
            color: white;
            border-radius: 8px;
            border: none;
            transition: background-color 0.3s ease;
        }
        div.stButton > button:hover {
            background-color: #2563eb;
        }
        .card-metricas {
            background-color: #1e293b;
            padding: 25px;
            border-radius: 12px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        .metric-title {
            font-size: 14px;
            color: #cbd5e1;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 22px;
            font-weight: bold;
            color: white;
        }
        .metric-sub {
            font-size: 13px;
            color: #94a3b8;
        }
        .metric-sub.positive {
            color: #4ade80;
        }
        .metric-sub.negative {
            color: #f87171;
        }
    .metric-box {
        background-color: #1e2533;
        padding: 15px;
        border-radius: 10px;
        text-align: left;
        margin-bottom: 10px;
    }
    .symbol-card {
        background-color: #1e2533;
        padding: 20px;
        border-radius: 12px;
        margin-top: 20px;
        margin-bottom: 20px;
    }

    .symbol-button {
        display: inline-block;
        padding: 8px 14px;
        border-radius: 16px;
        font-size: 13px;
        margin-right: 8px;
        margin-bottom: 8px;
        background-color: #334155;
        color: white;
    }

    .symbol-button.positive {
        background-color: #166534;
        color: #bbf7d0;
    }

    .symbol-button.negative {
        background-color: #7f1d1d;
        color: #fecaca;
    }

    .symbol-selected {
        background-color: #2563eb !important;
        color: white !important;
    }

    .symbol-search {
        padding: 8px 12px;
        border-radius: 8px;
        border: none;
        width: 100%;
        background-color: #0f172a;
        color: white;
        font-size: 13px;
    }
    .timeframe-button {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 13px;
        margin-right: 8px;
        margin-bottom: 8px;
        background-color: #334155;
        color: white;
        cursor: pointer;
    }

    .timeframe-button.selected {
        background-color: #2563eb;
        color: white;
    }
    /* Estilo mejorado para botones de temporalidad */
    div[role="radiogroup"] > label {
        background-color: #334155;
        color: white !important;
        padding: 6px 14px;
        border-radius: 8px;
        margin-right: 6px;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Hover */
    div[role="radiogroup"] > label:hover {
        background-color: #475569 !important;
        color: white !important;
    }

    /* ✅ Selección activa: ambas versiones de Streamlit */
    div[role="radiogroup"] > label[data-selected="true"],
    div[role="radiogroup"] > label[aria-checked="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
        font-weight: 700;
    }

    /* Forzar texto blanco en todo el contenido interno */
    div[role="radiogroup"] > label * {
        color: white !important;
        opacity: 1 !important;
    }

    /* Oculta el círculo del radio */
    div[role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    </style>

    """, unsafe_allow_html=True)

    # =====================
    # Encabezado y selección
    # =====================
    st.title("Developer")

    # ✅ Lista simplificada de tickers + cambios ya formateados para mostrar en el dropdown
    ticker_labels = [
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "NVDA",
        "TSLA",
        "BTC/USD",
        "ETH/USD",
        "SOL/USD",
        "ADA/USD",
        "BNB/USD"
    ]

    # ✅ Esta lista solo extrae el ticker puro para lógica interna
    tickers = [label.split(" ")[0] for label in ticker_labels]

    # === Disclaimer interactivo con botón para minimizar ===
    if 'disclaimer_aceptado' not in st.session_state:
        st.session_state['disclaimer_aceptado'] = False

    if not st.session_state['disclaimer_aceptado']:
        with st.expander("⚠️ Disclaimer Legal - Por favor, léelo antes de continuar", expanded=True):
            st.markdown("""
            <p style='color:#cbd5e1; font-size:15px;'>
            Este análisis generado por inteligencia artificial tiene fines exclusivamente educativos e informativos.<br>
            No constituye asesoramiento financiero ni una recomendación de inversión.<br>
            Los mercados conllevan riesgos, y el uso de esta herramienta es responsabilidad exclusiva del usuario.
            </p>
            """, unsafe_allow_html=True)

            if st.button("✅ Aceptar y minimizar"):
                st.session_state['disclaimer_aceptado'] = True




    col1, col2 = st.columns([1, 1])  # Solo usamos dos columnas ahora

    with col1:
        st.markdown("**Escoge los Criterios para obtener el Análisis del A.I.**", unsafe_allow_html=True)

        selected_label = st.selectbox(
            "Selecciona un Ticker",
            ticker_labels,
            index=tickers.index(st.session_state['selected_ticker']),
            key="select_ticker"
        )

        # Guardar el ticker correspondiente (parte antes del espacio)
        st.session_state['selected_ticker'] = selected_label.split(" ")[0]


    with col2:
        selected_interval = st.radio(
            "**Selecciona la Temporalidad**",
            ["15M", "1H", "1D"],
            key="interval_radio",
            horizontal=True,
        )

        # Botón "Obtener Análisis" debajo de la temporalidad
        if st.button("🤖 Clic Aquí para Obtener Análisis", key="analisis_btn_col3"):
            with st.spinner("The AI Market Map is Generating the Analysis"):
                data, resultado = obtener_datos_y_analisis(
                    st.session_state['selected_ticker'], selected_interval)
                bloques, conclusion_text = extract_numbered_blocks(resultado)
                conclusion_json = extraer_conclusion_json(resultado)
                st.session_state['ultimo_analisis'] = (data, resultado)
                st.session_state['bloques'] = bloques
                st.session_state['conclusion'] = conclusion_text
                st.session_state['conclusion_json'] = conclusion_json
                conclusion = conclusion_text

        # Estilo visual dinámico para la opción seleccionada
        st.markdown(f"""
            <style>
            div[role="radiogroup"] > label:nth-child({['15M','1H','1D','1W'].index(selected_interval)+1}) {{
                background-color: #3b82f6 !important;
                color: white !important;
                font-weight: 700;
            }}
            </style>
        """, unsafe_allow_html=True)


        st.markdown("""
            <style>
            div[role="radiogroup"] {
                display: flex;
                justify-content: flex-start;
                gap: 8px;
                flex-wrap: wrap;
                margin-top: 6px;
            }
            </style>
        """, unsafe_allow_html=True)


    np.random.seed(1)
    dias = pd.date_range("2024-03-08", "2024-06-06", freq="B")
    precios = np.cumsum(np.random.normal(0.6, 1.1, len(dias))) + 164

    # ========== ZONA DE RESULTADOS Y GRÁFICA EN DOS COLUMNAS ==========



    # Cuando obtienes el resultado, haz:




    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""
    <div style='width:100vw; height:2.5px; background:linear-gradient(to right, #334155 10%, #3b82f6 90%); border-radius:2px; margin: -10px 0 30px 0;'></div>
    """, unsafe_allow_html=True)



    # ================== MOSTRAR SECCIONES ==================
    def seccion_html(titulo, contenido, emoji):
        return f"""
        <div style="background-color:#1e293b; padding: 20px; border-radius: 12px; margin-top: 20px;">
            <h3 style="color:white; margin-bottom:10px;">{emoji} {titulo}</h3>
            <div style="background-color:#334155; padding: 15px; border-radius: 10px;">
                <p style="color:white; font-size:15px;">
                    {contenido.strip() if contenido else 'Aquí va a ir el análisis de la AI. Este texto es un placeholder.'}
                </p>
            </div>
        </div>
        """


    # Asegura que estas variables estén definidas correctamente antes de usarlas
    if 'bloques' in st.session_state:
        bloques = st.session_state['bloques']
        conclusion = st.session_state.get('conclusion', "")
        conclusion_json = st.session_state.get('conclusion_json', None)
    else:
        bloques = {}
        conclusion = ""
        conclusion_json = None

    # Renderizar solo si hay contenido en los bloques
    if bloques:
        col_izq, col_der = st.columns([1.2, 1])  # Puedes ajustar la proporción si quieres

        # -------- COLUMNA DERECHA (texto AI) --------
        with col_der:
            st.markdown(
                seccion_html("Resultado Completo de la AI", bloques.get(1, ""), "🤖"),
                unsafe_allow_html=True,
            )
            st.markdown(
                seccion_html("Proyección de Precios Target y Stop Loss", bloques.get(4, ""), "🎯"),
                unsafe_allow_html=True,
            )
            st.markdown(
                seccion_html("Evaluación de Riesgo/Beneficio", bloques.get(5, ""), "⚖️"),
                unsafe_allow_html=True,
            )

        # -------- COLUMNA IZQUIERDA (prob, gráfico, RR) --------
        with col_izq:
            # ===== Preparar variables =====
            if conclusion_json:
                last = float(conclusion_json.get("last_price"))
                target = float(conclusion_json.get("probable_target"))
                stop = float(conclusion_json.get("probable_stop"))
                rr_ratio = conclusion_json.get("risk_reward_ratio")
                probability = conclusion_json.get("probability")
                tendencia = "📈 Alcista" if target > last else "📉 Bajista"
            else:
                last = target = stop = rr_ratio = probability = None
                tendencia = ""

            # 1️⃣ PROBABILIDAD
            if probability is not None:
                prob = float(probability)
                if prob < 50:
                    bar_color = "#ef4444"
                elif 50 <= prob < 60:
                    bar_color = "#f59e42"
                elif 60 <= prob < 80:
                    bar_color = "#fbbf24"
                else:
                    bar_color = "#22d46c"

                st.markdown(
                    f"""
                    <div style="background-color:#1e293b; padding:18px 16px 20px 18px; border-radius:12px; margin-top:10px;">
                        <h4 style="color:white; margin-bottom:6px;">📊 Probability — {tendencia}</h4>
                        <div style="background-color:#334155; border-radius:7px; height:30px; width:100%; margin-bottom:8px; position:relative;">
                            <div style="height:100%; width:{prob}%; background:{bar_color}; border-radius:7px;"></div>
                            <div style="position:absolute; left:0; top:0; width:100%; height:30px; display:flex; align-items:center; justify-content:center; color:white; font-size:19px; font-weight:700;">
                                {prob:.1f}%
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 2️⃣ GRÁFICO DE PRICE / TARGET / STOP
            if last is not None:
                st.markdown("#### 📊 Price, Target y Stop")  # encabezado del gráfico
                last_y = 0.5

                if target > last:
                    target_y = 0.9
                    dist_target = target - last
                    dist_stop = last - stop
                    pos_stop = (
                        last_y - (dist_stop / dist_target) * (target_y - last_y)
                        if dist_target != 0
                        else 0.1
                    )
                    pos_stop = max(0.1, min(pos_stop, 0.49))
                else:
                    target_y = 0.1
                    pos_stop = 0.8

                y_vals = [pos_stop, last_y, target_y]
                labels = [
                    f"Stop\n${stop:.3f}",
                    f"Last\n${last:.2f}",
                    f"Target\n${target:.3f}",
                ]
                colors = ["#f87171", "#60a5fa", "#22d3ee"]

                fig2, ax2 = plt.subplots(figsize=(4, 2))
                for y, color, label in zip(y_vals, colors, labels):
                    ax2.axhline(y, color=color, linewidth=1, linestyle="--")
                    ax2.text(
                        0.07,
                        y,
                        label,
                        va="center",
                        ha="left",
                        fontsize=10,
                        color=color,
                        weight="bold",
                    )

                ax2.set_ylim(0, 1)
                ax2.set_yticks([])
                ax2.set_xticks([])
                ax2.set_facecolor("#1e2533")
                fig2.patch.set_facecolor("#1e2533")
                for spine in ax2.spines.values():
                    spine.set_visible(False)
                st.pyplot(fig2)
            else:
                st.warning(
                    "No se pudo extraer el bloque JSON de la conclusión para graficar."
                )

            # 3️⃣ RISK-REWARD RATIO
            if rr_ratio is not None:
                st.markdown(
                    f"""
                    <div style="background-color:#1e293b; padding:18px 16px 10px 18px; border-radius:12px; margin-top:22px;">
                        <h4 style="color:white; margin-bottom:6px;">⚖️ Risk Reward Ratio</h4>
                        <p style="color:#fbbf24; font-size:21px; font-weight:700; margin-bottom:0;">{rr_ratio}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )





    # ===================== MOSTRAR RESULTADO COMPLETO (RAW) =====================
    #st.markdown(
    #    """
    #    <div style="background-color:#1e2533; padding: 20px; border-radius: 12px; margin-top: 20px;">
    #        <h3 style="color:white; margin-bottom:10px;">📝 Resultado completo de la AI</h3>
    #        <div style="background-color:#334155; padding: 15px; border-radius: 10px;">
    #            <pre style="color:white; font-size:14px; white-space: pre-wrap;">{}</pre>
    #        </div>
    #    </div>
    #    """.format(
    #        st.session_state['ultimo_analisis'][1] if 'ultimo_analisis' in st.session_state and st.session_state['ultimo_analisis'] else ""
    #    ),
    #    unsafe_allow_html=True,
    #)

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)


    # --- Título y datos del ticker seleccionado ---
    selected_interval = st.session_state["interval_radio"] if "interval_radio" in st.session_state else "1D"

    st.markdown(f"""
    <div style="background-color:#1e2533; padding: 28px 32px 32px 32px; border-radius: 18px; margin-bottom: 20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="font-size:2.2rem; font-weight:700; color:white;">{st.session_state['selected_ticker']}</span>
                <span style="font-size:2.2rem; font-weight:700; color:#4ade80; margin-left:8px;">—</span><br>
                <span style="font-size:1.1rem; color:#cbd5e1;">
                    Período: <span style="color:#38bdf8;">{selected_interval}</span>
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)



    # --- Graficar los datos reales del backend ---
    import matplotlib.dates as mdates
    from matplotlib.dates import DateFormatter, HourLocator, DayLocator

    # Asegura que haya datos antes de intentar acceder
    if 'ultimo_analisis' in st.session_state and st.session_state['ultimo_analisis']:
        data_json = st.session_state['ultimo_analisis'][0]
    else:
        data_json = None  # o un dict vacío si lo necesitas así
    selected_interval = st.session_state.get("interval_radio", "1D")

    if data_json:
        df_real = pd.DataFrame(data_json)

        # Normaliza la columna de tiempo
        if "timestamp" in df_real.columns:
            df_real.rename(columns={"timestamp": "datetime"}, inplace=True)
        elif "date" in df_real.columns:
            df_real.rename(columns={"date": "datetime"}, inplace=True)
        else:
            st.warning("No se encontró una columna de tiempo válida.")
            st.stop()

        df_real['datetime'] = pd.to_datetime(df_real['datetime'])
        df_real.set_index('datetime', inplace=True)
        df_real.sort_index(inplace=True)  # ✅ Asegura orden temporal

        # Gráfico
        fig, ax = plt.subplots(figsize=(8.5, 4))
        ax.plot(df_real.index, df_real['Close'], color='#3b82f6', linewidth=2.7)

        # Estética
        ax.set_facecolor('#1e2533')
        fig.patch.set_facecolor('#1e2533')
        for spine in ax.spines.values():
            spine.set_color('#1e293b')
        ax.tick_params(colors='#94a3b8', labelsize=7)
        ax.grid(False)

        # Eje X dinámico
        if selected_interval in ["15M", "1H"]:
            ax.xaxis.set_major_locator(HourLocator(interval=1))
            ax.xaxis.set_major_formatter(DateFormatter('%d %b\n%H:%M'))
        else:
            ax.xaxis.set_major_locator(DayLocator(interval=1))
            ax.xaxis.set_major_formatter(DateFormatter('%d %b'))

        fig.autofmt_xdate()
        plt.yticks(fontsize=7)
        st.pyplot(fig)
    else:
        st.warning("No hay datos disponibles para graficar aún.")

run_app()
logout_button()




#comandos de actuallizacion en visul termina
#git add iamarketmap_frontend.py
#git commit -m "user portal login signup"
#git push