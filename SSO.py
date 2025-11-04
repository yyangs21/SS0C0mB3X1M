import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import os
import base64
import requests

# ------------------------------------------------
# 🔄 FUNCIÓN: Subir Excel actualizado a GitHub
# ------------------------------------------------
def subir_excel_a_github(local_path, repo, ruta_en_repo, mensaje="Actualización automática de incidentes"):
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        st.warning("⚠️ No se encontró el token de GitHub. Agrega GITHUB_TOKEN en tus Secrets.")
        return
    try:
        with open(local_path, "rb") as f:
            contenido = f.read()
        contenido_b64 = base64.b64encode(contenido).decode("utf-8")
        url = f"https://api.github.com/repos/{repo}/contents/{ruta_en_repo}"
        headers = {"Authorization": f"token {token}"}
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None
        data = {"message": mensaje, "content": contenido_b64, "branch": "main"}
        if sha:
            data["sha"] = sha
        r = requests.put(url, headers=headers, json=data)
        if r.status_code in [200, 201]:
            st.success("✅ Archivo Excel actualizado en GitHub correctamente.")
        else:
            st.warning(f"⚠️ Error al subir a GitHub: {r.text}")
    except Exception as e:
        st.error(f"❌ Error al intentar subir el archivo a GitHub: {e}")

# ------------------------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------------------------
st.set_page_config(page_title="SSO Dashboard - Datos Reales", layout="wide")
DEFAULT_EXCEL_PATH = r"SSO_datos_ejemplo.xlsx"

# ------------------------------------------------
# FUNCIONES DE CARGA Y EXPORTACIÓN
# ------------------------------------------------
@st.cache_data
def cargar_datos_excel(path=DEFAULT_EXCEL_PATH):
    if not os.path.exists(path):
        st.error(f"❌ No se encontró el archivo en la ruta: {path}")
        st.stop()
    try:
        df_incidentes = pd.read_excel(path, sheet_name="Incidentes")
        df_riesgos = pd.read_excel(path, sheet_name="Riesgos")
        df_capacitaciones = pd.read_excel(path, sheet_name="Capacitaciones")
        # Limpieza básica
        df_incidentes['Fecha'] = pd.to_datetime(df_incidentes['Fecha'], errors='coerce')
        if 'Riesgo' not in df_incidentes.columns:
            df_incidentes['Riesgo'] = df_incidentes['Severidad'] * df_incidentes['Probabilidad']
        if 'Nivel de Riesgo' in df_riesgos.columns:
            df_riesgos['Nivel'] = df_riesgos['Nivel de Riesgo']
        else:
            if 'Probabilidad' in df_riesgos.columns and 'Severidad' in df_riesgos.columns:
                df_riesgos['Riesgo'] = df_riesgos['Probabilidad'] * df_riesgos['Severidad']
                df_riesgos['Nivel'] = df_riesgos['Riesgo'].apply(lambda x: "Alto" if x >= 15 else ("Medio" if x >= 6 else "Bajo"))
        if 'Mes' in df_capacitaciones.columns:
            df_capacitaciones['Mes'] = df_capacitaciones['Mes'].astype(str)
        return df_incidentes, df_riesgos, df_capacitaciones
    except Exception as e:
        st.error(f"⚠️ Error al leer las hojas del archivo: {e}")
        st.stop()

def df_to_excel_bytes(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    output.seek(0)
    return output.getvalue()

# ------------------------------------------------
# CARGA DE DATOS REALES
# ------------------------------------------------
df_incidentes, df_riesgos, df_capacitaciones = cargar_datos_excel()

if 'incidentes' not in st.session_state:
    st.session_state['incidentes'] = df_incidentes.copy()
if 'df_riesgos' not in st.session_state:
    st.session_state['df_riesgos'] = df_riesgos.copy()

# Crear columna Riesgo numérico
def calcular_riesgo_valor(df):
    mapping = {"Baja":1, "Media":2, "Alta":3, "Crítica":4}
    if 'Severidad' in df.columns and 'Probabilidad' in df.columns:
        df['Riesgo_valor'] = df['Severidad'].map(mapping) * df['Probabilidad'].map(mapping)
    else:
        df['Riesgo_valor'] = 0
    return df

st.session_state['incidentes'] = calcular_riesgo_valor(st.session_state['incidentes'])

# ------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------
def calcular_kpis(df_inc):
    total_accidentes = df_inc[df_inc['Tipo'] == 'Accidente'].shape[0]
    total_incidentes = df_inc[df_inc['Tipo'] == 'Incidente'].shape[0]
    dias_perdidos = int(df_inc['Días_Perdidos'].sum())
    tasa_acc = round((total_accidentes / (len(df_inc) + 1)) * 100, 2)
    tasa_inc = round((total_incidentes / (len(df_inc) + 1)) * 100, 2)
    return total_accidentes, total_incidentes, dias_perdidos, tasa_acc, tasa_inc

# ------------------------------------------------
# SIDEBAR
# ------------------------------------------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/yyangs21/SS0C0mB3X1M/master/LogoC.png", width=180)
    st.image("https://raw.githubusercontent.com/yyangs21/SS0C0mB3X1M/master/LogoSSO.png", width=180)
    st.title("SSO Dashboard")
    page = st.radio("Secciones", ["Dashboard", "Matriz de Riesgos", "Incidentes", "Alertas", "Predictivo", "Reportes"], index=0)
    st.markdown("---")
    st.caption("Versión con datos reales")

# ------------------------------------------------
# DASHBOARD
# ------------------------------------------------
if page == "Dashboard":
    st.header("📊 Dashboard General")
    total_acc, total_inc, dias_perdidos, tasa_acc, tasa_inc = calcular_kpis(st.session_state['incidentes'])

    def generar_sparkline(df_tipo, color='#10b981'):
        df_tipo['Mes'] = df_tipo['Fecha'].dt.to_period('M').astype(str)
        meses_ordenados = sorted(df_tipo['Mes'].unique())
        counts = df_tipo.groupby('Mes').size().reindex(meses_ordenados, fill_value=0)
        fig = go.Figure(go.Scatter(y=counts.values, x=counts.index, mode='lines+markers',
                                   line=dict(color=color, width=3),
                                   marker=dict(size=6),
                                   fill='tozeroy'))
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                          xaxis=dict(showgrid=False, visible=False),
                          yaxis=dict(showgrid=False, visible=False),
                          height=50)
        return fig

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    df_acc = st.session_state['incidentes'][st.session_state['incidentes']['Tipo'] == 'Accidente']
    df_inc = st.session_state['incidentes'][st.session_state['incidentes']['Tipo'] == 'Incidente']

    kpi1.metric("🔴 Accidentes", total_acc)
    kpi1.plotly_chart(generar_sparkline(df_acc, '#ef4444'), use_container_width=True)
    kpi2.metric("🟡 Incidentes", total_inc)
    kpi2.plotly_chart(generar_sparkline(df_inc, '#facc15'), use_container_width=True)
    kpi3.metric("🟢 Días perdidos", dias_perdidos)
    kpi4.metric("🔴 Tasa Accidentes (%)", tasa_acc)
    kpi5.metric("🟡 Tasa Incidentes (%)", tasa_inc)

    st.markdown("---")
    left, right = st.columns([2,1])
    df = st.session_state['incidentes'].copy()
    df['Mes'] = df['Fecha'].dt.to_period('M').astype(str)
    with left:
        st.subheader("📊 Incidentes por mes")
        df_inc = df[df['Tipo'] == 'Incidente']
        by_month_inc = df_inc.groupby('Mes').size().reset_index(name='Count')
        fig_inc = px.bar(by_month_inc, x='Mes', y='Count', color_discrete_sequence=['#10b981'])
        fig_inc.update_layout(xaxis={'categoryorder':'category ascending'}, height=380)
        st.plotly_chart(fig_inc, use_container_width=True)
        st.subheader("📊 Accidentes por mes")
        df_acc = df[df['Tipo'] == 'Accidente']
        by_month_acc = df_acc.groupby('Mes').size().reset_index(name='Count')
        fig_acc = px.bar(by_month_acc, x='Mes', y='Count', color_discrete_sequence=['#ef4444'])
        fig_acc.update_layout(xaxis={'categoryorder':'category ascending'}, height=380)
        st.plotly_chart(fig_acc, use_container_width=True)
    with right:
        st.subheader("🚦 Semáforo de riesgo")
        nivel_global = st.session_state['df_riesgos']['Nivel'].value_counts().to_dict()
        alto = nivel_global.get('Alto', 0)
        medio = nivel_global.get('Medio', 0)
        bajo = nivel_global.get('Bajo', 0)
        st.markdown(f"#### 🔴 Alto: {alto}")
        st.markdown(f"#### 🟡 Medio: {medio}")
        st.markdown(f"#### 🟢 Bajo: {bajo}")
        st.markdown("---")
        st.subheader("📈 Capacitaciones (últimos 12 meses)")
        fig3 = px.line(df_capacitaciones, x='Mes', y='Asistentes', markers=True)
        st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------
# MATRIZ DE RIESGOS
# ------------------------------------------------
elif page == "Matriz de Riesgos":
    st.header("📋 Matriz de Identificación de Riesgos (IPERC)")
    st.dataframe(st.session_state['df_riesgos'].reset_index(drop=True))
    st.markdown("---")
    st.subheader("🔥 Heatmap de Riesgo por Clasificación")
    df_r = st.session_state['df_riesgos']
    if 'Clasificación de peligro' in df_r.columns:
        heat = df_r.groupby(['Clasificación de peligro', 'Nivel']).size().reset_index(name='Count')
        heat_pivot = heat.pivot(index='Clasificación de peligro', columns='Nivel', values='Count').fillna(0)
        fig_heat = go.Figure(data=go.Heatmap(z=heat_pivot.values, x=heat_pivot.columns, y=heat_pivot.index))
        fig_heat.update_layout(height=400)
        st.plotly_chart(fig_heat, use_container_width=True)

# ------------------------------------------------
# INCIDENTES
# ------------------------------------------------
elif page == "Incidentes":
    st.header("📋 Registro de Incidentes y Accidentes")
    df_actual = st.session_state['incidentes']
    st.markdown("Aquí puedes registrar nuevos incidentes o accidentes y ver el historial completo cargado desde el archivo o generado.")

    with st.expander("➕ Agregar Nuevo Incidente", expanded=False):
        st.subheader("Registrar un nuevo incidente")
        df_riesgos = st.session_state['df_riesgos']
        causas_posibles = sorted(df_riesgos['Peligro'].dropna().unique().tolist()) if 'Peligro' in df_riesgos.columns else []
        severidades_posibles = sorted(df_riesgos['Severidad'].dropna().unique().tolist()) if 'Severidad' in df_riesgos.columns else ["Baja","Media","Alta","Crítica"]
        probabilidades_posibles = sorted(df_riesgos['Probabilidad'].dropna().unique().tolist()) if 'Probabilidad' in df_riesgos.columns else ["Baja","Media","Alta"]

        col1, col2 = st.columns(2)
        with col1:
            id_incidente = st.text_input("🆔 ID del Incidente")
            fecha_incidente = st.date_input("📅 Fecha del Incidente")
            hora_evento = st.text_input("🕒 Hora del Evento (HH:MM)", placeholder="Ejemplo: 14:30")
        with col2:
            tipo_incidente = st.selectbox("Tipo de Incidente", ["Casi Accidente", "Incidente", "Otro"])
            area_incidente = st.text_input("Área o Puesto involucrado")
            dias_perdidos = st.number_input("Días perdidos (si aplica)", min_value=0, step=1)

        causa_seleccionada = st.selectbox("Causa probable (Peligro identificado)", causas_posibles + ["Otro"])
        if causa_seleccionada == "Otro":
            causa_incidente = st.text_input("📝 Especifique otra causa")
        else:
            causa_incidente = causa_seleccionada

        severidad = st.selectbox("📈 Severidad", severidades_posibles)
        probabilidad = st.selectbox("🎯 Probabilidad", probabilidades_posibles)
        riesgo = f"{severidad} x {probabilidad}"
        st.info(f"Nivel de riesgo: **{riesgo}**")
        descripcion = st.text_area("🗒️ Descripción del incidente o hallazgo")

        if st.button("💾 Guardar incidente"):
            nuevo_incidente = {
                "ID": id_incidente,
                "Fecha": pd.to_datetime(fecha_incidente),
                "Hora del Evento": hora_evento,
                "Área": area_incidente,
                "Puesto": area_incidente,
                "Tipo": tipo_incidente,
                "Causa": causa_incidente,
                "Días_Perdidos": dias_perdidos,
                "Severidad": severidad,
                "Probabilidad": probabilidad,
                "Descripción": descripcion,
                "Riesgo": riesgo
            }
            df_actual = pd.concat([st.session_state['incidentes'], pd.DataFrame([nuevo_incidente])], ignore_index=True)
            df_actual = calcular_riesgo_valor(df_actual)
            st.session_state['incidentes'] = df_actual
            try:
                df_actual.to_excel(DEFAULT_EXCEL_PATH, index=False, engine='openpyxl')
                st.success("✅ Incidente agregado y guardado correctamente en local.")
                subir_excel_a_github(
                    local_path=DEFAULT_EXCEL_PATH,
                    repo="yyangs21/SS0C0mB3X1M",
                    ruta_en_repo="SSO_datos_ejemplo.xlsx",
                    mensaje=f"Nuevo incidente agregado - {id_incidente or 'sin ID'}"
                )
            except Exception as e:
                st.warning(f"⚠️ No se pudo guardar o subir a GitHub. Error: {e}")

    st.subheader("📜 Historial de Incidentes")
    df_mostrar = st.session_state['incidentes'].copy()
    df_mostrar['Fecha'] = pd.to_datetime(df_mostrar['Fecha'], errors='coerce')
    df_mostrar = df_mostrar.sort_values(by='Fecha', ascending=False)
    st.dataframe(df_mostrar)

    # Descargar Excel actualizado
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Incidentes')
        return output.getvalue()
    excel_data = to_excel(st.session_state['incidentes'])
    st.download_button(
        label="📥 Descargar registro actualizado (Excel)",
        data=excel_data,
        file_name='incidentes_actualizados.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ------------------------------------------------
# ALERTAS
# ------------------------------------------------
elif page == "Alertas":
    st.header("🚨 Alertas Preventivas")
    df_r = st.session_state['df_riesgos']
    altos_mat = df_r[df_r['Nivel'] == 'Alto']
    st.subheader("Riesgos con nivel Alto")
    if not altos_mat.empty:
        for _, r in altos_mat.iterrows():
            st.warning(f"⚠️ Peligro: {r.get('Peligro', 'N/A')} - Nivel: {r.get('Nivel', 'N/A')}")
    else:
        st.success("Sin riesgos altos en la matriz.")
    st.markdown("---")
    st.subheader("Incidentes con Riesgo Alto")
    inc_altos = st.session_state['incidentes'][st.session_state['incidentes']['Riesgo_valor'] >= 15]
    if not inc_altos.empty:
        st.dataframe(inc_altos[['ID','Fecha','Área','Tipo','Causa','Riesgo']])
    else:
        st.info("No hay incidentes recientes con riesgo alto.")

# ------------------------------------------------
# PREDICTIVO
# ------------------------------------------------
elif page == "Predictivo":
    st.header("🤖 Módulo Predictivo (placeholder)")
    areas = st.session_state['incidentes']['Área'].unique()
    probs = np.round(np.random.rand(len(areas)) * 0.6 + 0.1, 2)
    df_probs = pd.DataFrame({'Área': areas, 'Probabilidad_Accidente': probs})
    figp = px.bar(df_probs, x='Área', y='Probabilidad_Accidente', range_y=[0, 1])
    st.plotly_chart(figp, use_container_width=True)

# ------------------------------------------------
# REPORTES
# ------------------------------------------------
elif page == "Reportes":
    st.header("📤 Reportes y Exportación")
    st.write("Descarga un consolidado de todas las hojas en Excel:")
    if st.button("Exportar datos completos"):
        excel_bytes = df_to_excel_bytes({
            'Incidentes': st.session_state['incidentes'],
            'Riesgos': st.session_state['df_riesgos'],
            'Capacitaciones': df_capacitaciones
        })
        st.download_button(
            label="📥 Descargar Excel Consolidado",
            data=excel_bytes,
            file_name=f"SSO_Reportes_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )




