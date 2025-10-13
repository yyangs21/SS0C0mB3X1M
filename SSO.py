# SSO Dashboard - Cascaron (VersiÃ³n clara) - Streamlit app
# Guardar como: sso_dashboard_cascaron.py
# Requisitos: streamlit, pandas, numpy, plotly
# Ejecutar: streamlit run sso_dashboard_cascaron.pyhttps://raw.githubusercontent.com/yyangs21/s4lU3b1nEst4r/master/Logo.png

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime, timedelta

st.set_page_config(page_title="SSO Dashboard - Cascaron", layout="wide")

# ----------------------
# Datos simulados
# ----------------------
@st.cache_data
def generar_datos_simulados(seed=42):
    np.random.seed(seed)
    today = pd.Timestamp.today().normalize()
    # Incidentes (12 meses)
    fechas = [today - pd.Timedelta(days=int(x)) for x in np.random.randint(0, 365, 200)]
    areas = ["Produccion", "Mantenimiento", "Logistica", "Administracion", "Calidad"]
    tipos = ["Accidente", "Incidente", "Casi Accidente"]
    causas = ["Humano", "Mecanico", "Ambiental", "Falla de equipo", "Procedimiento"]

    df_inc = pd.DataFrame({
        "ID": [f"INC{1000+i}" for i in range(len(fechas))],
        "Fecha": fechas,
        "Area": np.random.choice(areas, len(fechas)),
        "Puesto": np.random.choice(["Operario","Supervisor","Tecnico","Auxiliar"], len(fechas)),
        "Tipo": np.random.choice(tipos, len(fechas), p=[0.2, 0.6, 0.2]),
        "Causa": np.random.choice(causas, len(fechas)),
        "Dias_Perdidos": np.random.poisson(0.4, len(fechas)),
        "Severidad": np.random.randint(1,6,len(fechas)),
        "Probabilidad": np.random.randint(1,6,len(fechas)),
        "Descripcion": ["Descripcion del evento..." for _ in fechas]
    })
    df_inc["Riesgo"] = df_inc["Severidad"] * df_inc["Probabilidad"]

    # Matriz de riesgos (IPERC)
    peligros = ["Caida de altura","Contacto con maquina","Sobreesfuerzo","Exposicion quimica",
                "Electrico","Ruido","Golpe contra objeto"]
    rows = 30
    df_riesgos = pd.DataFrame({
        "ID_Riesgo": [f"R{100+i}" for i in range(rows)],
        "Area": np.random.choice(areas, rows),
        "Peligro": np.random.choice(peligros, rows),
        "Consecuencia": np.random.choice(["Lesion leve","Lesion grave","Enfermedad"], rows),
        "Probabilidad": np.random.randint(1,6,rows),
        "Severidad": np.random.randint(1,6,rows),
    })
    df_riesgos["Riesgo"] = df_riesgos["Probabilidad"] * df_riesgos["Severidad"]
    df_riesgos["Nivel"] = df_riesgos["Riesgo"].apply(lambda x: "Alto" if x>=15 else ("Medio" if x>=6 else "Bajo"))

    # Capacitaciones
    months = pd.date_range(end=today, periods=12, freq='M')
    df_cap = pd.DataFrame({
        "Mes": months.strftime('%Y-%m'),
        "Capacitaciones": np.random.randint(1,20,len(months)),
        "Asistentes": np.random.randint(10,200,len(months))
    })

    return df_inc.sort_values('Fecha', ascending=False), df_riesgos, df_cap

# Cargar datos
df_incidentes, df_riesgos, df_capacitaciones = generar_datos_simulados()

# Mantener en session state para permitir agregar
if 'incidentes' not in st.session_state:
    st.session_state['incidentes'] = df_incidentes.copy()

# ----------------------
# Helper functions
# ----------------------

def calcular_kpis(df_inc):
    total_accidentes = df_inc[df_inc['Tipo']=='Accidente'].shape[0]
    total_incidentes = df_inc.shape[0]
    dias_perdidos = int(df_inc['Dias_Perdidos'].sum())
    tasa_frecuencia = round((total_accidentes / (len(df_inc)+1)) * 1000,2)  # indicador simplificado
    return total_accidentes, total_incidentes, dias_perdidos, tasa_frecuencia


def riesgo_to_color(nivel):
    return {'Alto':'#ef4444','Medio':'#f59e0b','Bajo':'#10b981'}.get(nivel, '#9ca3af')


def df_to_excel_bytes(df_dict):
    # Espera un dict de {nombre_hoja: df}
    from openpyxl import Workbook
    import pandas as pd
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
        writer.save()
    processed_data = output.getvalue()
    return processed_data

# ----------------------
# UI - Sidebar
# ----------------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/yyangs21/SS0C0mB3X1M/master/LogoC.png", width=180)  # spacer
    st.title("SSO Dashboard")
    page = st.radio("Secciones", ["Dashboard", "Matriz de Riesgos", "Incidentes", "Alertas", "Predictivo", "Reportes"], index=0)
    st.markdown("---")
    st.caption("Cascaron visual")
    st.markdown("\n")
    st.write("\n")

# ----------------------
# Page: Dashboard
# ----------------------
if page == "Dashboard":
    st.header("Dashboard General")
    total_acc, total_inc, dias_perdidos, tasa_freq = calcular_kpis(st.session_state['incidentes'])

    # KPI cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Accidentes (tot)", total_acc)
    kpi2.metric("Incidentes (tot)", total_inc)
    kpi3.metric("Dias perdidos", dias_perdidos)
    kpi4.metric("Tasa de frecuencia (x1000)", tasa_freq)

    st.markdown("---")
    left, right = st.columns([2,1])

    with left:
        st.subheader("Accidentes / Incidentes por mes")
        df = st.session_state['incidentes'].copy()
        df['Mes'] = df['Fecha'].dt.to_period('M').astype(str)
        by_month = df.groupby(['Mes','Tipo']).size().reset_index(name='Count')
        fig = px.bar(by_month, x='Mes', y='Count', color='Tipo', barmode='group')
        fig.update_layout(xaxis={'categoryorder':'category ascending'}, height=420)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Incidentes por Area (Top) ")
        area_count = df['Area'].value_counts().reset_index()
        area_count.columns = ['Area','Count']
        fig2 = px.bar(area_count, x='Area', y='Count')
        st.plotly_chart(fig2, use_container_width=True)

    with right:
        st.subheader("Semaforo de riesgo (Matriz)")
        nivel_global = df_riesgos['Nivel'].value_counts().to_dict()
        # Simple gauge style with colored boxes
        cols = st.columns(1)
        alto = nivel_global.get('Alto',0)
        medio = nivel_global.get('Medio',0)
        bajo = nivel_global.get('Bajo',0)
        st.markdown(f"#### 🔴 Alto: {alto}")
        st.markdown(f"#### 🟡 Medio: {medio}")
        st.markdown(f"#### 🟢 Bajo: {bajo}")

        st.markdown("---")
        st.subheader("Capacitaciones (ultimos 12 meses)")
        fig3 = px.line(df_capacitaciones, x='Mes', y='Asistentes', markers=True)
        st.plotly_chart(fig3, use_container_width=True)

# ----------------------
# Page: Matriz de Riesgos
# ----------------------
elif page == "Matriz de Riesgos":
    st.header("Matriz de Identificacion de Riesgos (IPERC)")
    st.write("La tabla a continuacion es un ejemplo simulado. Puedes cargar tu archivo Excel para reemplazar.")

    # Upload
    uploaded = st.file_uploader("Cargar matriz de riesgos (.xlsx o .csv)", type=['xlsx','csv'])
    if uploaded is not None:
        try:
            if uploaded.name.endswith('.csv'):
                df_r = pd.read_csv(uploaded)
            else:
                df_r = pd.read_excel(uploaded)
            df_r['Riesgo'] = df_r['Probabilidad'] * df_r['Severidad']
            df_r['Nivel'] = df_r['Riesgo'].apply(lambda x: "Alto" if x>=15 else ("Medio" if x>=6 else "Bajo"))
        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")
            df_r = df_riesgos.copy()
    else:
        df_r = df_riesgos.copy()

    st.dataframe(df_r.reset_index(drop=True))

    st.markdown("---")
    st.subheader("Visual - Heatmap de Riesgo por Area x Nivel")
    heat = df_r.groupby(['Area','Nivel']).size().reset_index(name='Count')
    heat_pivot = heat.pivot(index='Area', columns='Nivel', values='Count').fillna(0)
    st.write(heat_pivot)
    fig_heat = go.Figure(data=go.Heatmap(
        z=heat_pivot.values,
        x=heat_pivot.columns,
        y=heat_pivot.index,
        hoverongaps=False
    ))
    fig_heat.update_layout(height=400)
    st.plotly_chart(fig_heat, use_container_width=True)

# ----------------------
# Page: Incidentes
# ----------------------
elif page == "Incidentes":
    st.header("Registro de Incidentes y Accidentes")
    with st.expander("Agregar incidente (form) ", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            fecha = st.date_input("Fecha", value=datetime.today())
            area = st.selectbox("Area", options=['Produccion','Mantenimiento','Logistica','Administracion','Calidad'])
            puesto = st.selectbox("Puesto", options=['Operario','Supervisor','Tecnico','Auxiliar'])
        with col2:
            tipo = st.selectbox("Tipo de evento", options=['Accidente','Incidente','Casi Accidente'])
            causa = st.selectbox("Causa", options=['Humano','Mecanico','Ambiental','Falla de equipo','Procedimiento'])
            dias_perdidos = st.number_input("Dias perdidos", min_value=0, value=0)
        with col3:
            prob = st.slider("Probabilidad (1-5)", 1,5,3)
            sev = st.slider("Severidad (1-5)", 1,5,2)
            desc = st.text_area("Descripcion breve", value="")

        if st.button("Agregar incidente"):
            new_id = f"INC{1000 + len(st.session_state['incidentes']) + 1}"
            new_row = {
                'ID': new_id,
                'Fecha': pd.to_datetime(fecha),
                'Area': area,
                'Puesto': puesto,
                'Tipo': tipo,
                'Causa': causa,
                'Dias_Perdidos': int(dias_perdidos),
                'Severidad': int(sev),
                'Probabilidad': int(prob),
                'Descripcion': desc,
                'Riesgo': int(sev)*int(prob)
            }
            st.session_state['incidentes'] = pd.concat([pd.DataFrame([new_row]), st.session_state['incidentes']], ignore_index=True)
            st.success("Incidente agregado (temporal en session_state). Guarda la data final en Reportes > Exportar.")

    st.markdown("---")
    st.subheader("Tabla de registros")
    st.dataframe(st.session_state['incidentes'].sort_values('Fecha', ascending=False).reset_index(drop=True))

    st.markdown("---")
    st.subheader("Filtros rápidos")
    f_area = st.multiselect("Filtrar por Area", options=st.session_state['incidentes']['Area'].unique(), default=None)
    f_tipo = st.multiselect("Filtrar por Tipo", options=st.session_state['incidentes']['Tipo'].unique(), default=None)
    df_filtered = st.session_state['incidentes']
    if f_area: df_filtered = df_filtered[df_filtered['Area'].isin(f_area)]
    if f_tipo: df_filtered = df_filtered[df_filtered['Tipo'].isin(f_tipo)]
    st.write(df_filtered[['ID','Fecha','Area','Puesto','Tipo','Causa','Riesgo']].sort_values('Fecha', ascending=False))

# ----------------------
# Page: Alertas
# ----------------------
elif page == "Alertas":
    st.header("Alertas Preventivas")
    st.write("Se muestran todos los riesgos con nivel Alto (Riesgo >= 15) de la matriz, y incidentes recientes con Riesgo alto.")
    altos_mat = df_riesgos[df_riesgos['Riesgo']>=15].copy()
    st.subheader("Riesgos en Matriz (Alto)")
    if not altos_mat.empty:
        for _, r in altos_mat.iterrows():
            st.warning(f"Area: {r['Area']} - Peligro: {r['Peligro']} - Riesgo: {r['Riesgo']} - Nivel: {r['Nivel']}")
    else:
        st.success("No hay riesgos altos en la matriz (simulado).")

    st.markdown("---")
    st.subheader("Incidentes recientes con Riesgo Alto")
    inc_altos = st.session_state['incidentes'][st.session_state['incidentes']['Riesgo']>=15]
    if not inc_altos.empty:
        st.dataframe(inc_altos[['ID','Fecha','Area','Tipo','Causa','Riesgo']].sort_values('Fecha', ascending=False))
    else:
        st.info("No hay incidentes recientes con riesgo alto.")

# ----------------------
# Page: Predictivo
# ----------------------
elif page == "Predictivo":
    st.header("Modulo Predictivo (placeholder)")
    st.write("Este espacio sirve como placeholder para integrar un modelo ML. Por ahora se muestran probabilidades simuladas por area.")

    # Simular probabilidades por area
    areas = ['Produccion','Mantenimiento','Logistica','Administracion','Calidad']
    probs = np.round(np.random.rand(len(areas))*0.6 + 0.1,2)
    df_probs = pd.DataFrame({'Area':areas,'Probabilidad_Accidente':probs})
    figp = px.bar(df_probs, x='Area', y='Probabilidad_Accidente', range_y=[0,1])
    st.plotly_chart(figp, use_container_width=True)

    st.markdown("---")
    st.subheader("Simular prediccion por trabajador")
    with st.form("sim_form"):
        edad = st.number_input("Edad", min_value=18, max_value=70, value=32)
        antig = st.number_input("Antiguedad (años)", min_value=0, max_value=50, value=3)
        horas_ext = st.number_input("Horas extra semanales", min_value=0, max_value=80, value=5)
        area_sel = st.selectbox("Area", areas)
        cap = st.number_input("Capacitaciones ultimos 12 meses", min_value=0, max_value=20, value=2)
        submitted = st.form_submit_button("Predecir (simulado)")
    if submitted:
        score = min(0.95, round(0.05 + 0.01*horas_ext + 0.003*(50-edad) + 0.02*(0 if cap>3 else 1) + np.random.rand()*0.05,2))
        st.metric("Probabilidad estimada de accidente", f"{int(score*100)} %")
        st.info("Este valor es una simulacion. Integra tu modelo ML (pickle) para predicciones reales.")

# ----------------------
# Page: Reportes
# ----------------------
elif page == "Reportes":
    st.header("Reportes y Exportacion")
    st.write("Exporta los datos actuales (simulados o cargados) a un archivo Excel listo para compartir.")

    if st.button("Exportar datos a Excel (incidentes, riesgos, capacitaciones)"):
        data = {
            'incidentes': st.session_state['incidentes'].reset_index(drop=True),
            'riesgos': df_riesgos.reset_index(drop=True),
            'capacitaciones': df_capacitaciones.reset_index(drop=True)
        }
        bytes_xlsx = df_to_excel_bytes(data)
        st.download_button(label='Descargar Excel', data=bytes_xlsx, file_name='sso_datos_simulados.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    st.markdown("---")
    st.subheader("Descarga imagenes de graficos (ejemplo)")
    st.write("Haz click derecho en cualquier grafico y guardalo, o usa las opciones nativas de Plotly.")

# ----------------------
# Footer
# ----------------------
st.markdown("\n---\n")
st.markdown("<div style='text-align:center;color:#6b7280;'>Cascaron SSO - Demo .</div>", unsafe_allow_html=True)

