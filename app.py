
import streamlit as st
import requests
import openai
import xml.etree.ElementTree as ET

# Configura tu API key en Streamlit Secrets (Settings > Secrets)
openai.api_key = st.secrets["openai_api_key"]

st.set_page_config(page_title="PhysioDigest", layout="wide")
st.title("📚 PhysioDigest - Actualización Clínica Automatizada para Fisioterapeutas")

# --------- Filtros personalizados ---------
st.sidebar.header("🧠 Filtros de búsqueda")

temas = [
    "ACL", "rotator cuff", "low back pain", "patellofemoral pain",
    "shoulder instability", "tendinopathy", "plantar fasciitis"
]
tipos_estudio = ["randomized controlled trial", "systematic review", "clinical trial"]
periodos = {
    "Últimos 7 días": "last 7 days",
    "Últimos 30 días": "last 30 days",
    "Últimos 5 años": "last 5 years"
}
perfiles = ["Estudiante", "Clínico", "Investigador"]

tema = st.sidebar.selectbox("🦴 Tema clínico", temas)
tipo_estudio = st.sidebar.multiselect("📄 Tipo de estudio", tipos_estudio, default=tipos_estudio)
periodo = st.sidebar.selectbox("📅 Rango de publicación", list(periodos.keys()))
perfil = st.sidebar.selectbox("👤 Perfil del lector", perfiles)
max_articulos = st.sidebar.slider("🔢 Nº máximo de artículos", 1, 10, 3)

buscar = st.sidebar.button("🔍 Buscar y generar resumen")

# --------- Construcción del query ---------
def construir_query(tema, tipo_estudio, periodo):
    temas = f"({tema}[Title/Abstract])"
    estudios = " OR ".join([f'"{t}"[Publication Type]' for t in tipo_estudio])
    query = f"{temas} AND ({estudios}) AND ({periodos[periodo]}[PDat]) AND (english[lang])"
    return query

def buscar_ids_pubmed(query, max_articulos):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_articulos
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data["esearchresult"].get("idlist", [])

# --------- Obtener abstracts de PubMed ---------
def obtener_abstracts(id_list):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    root = ET.fromstring(response.content)
    abstracts = []
    for article in root.findall(".//PubmedArticle"):
        title = article.findtext(".//ArticleTitle", default="Sin título")
        abstract = article.findtext(".//AbstractText", default="Sin resumen disponible")
        abstracts.append((title, abstract))
    return abstracts

# --------- Prompt según perfil ---------
def construir_prompt(title, abstract, perfil):
    if perfil == "Estudiante":
        tono = "Resume el artículo de forma clara, explica los términos técnicos y añade 3 aprendizajes clave para estudiantes de fisioterapia."
    elif perfil == "Clínico":
        tono = "Resume el artículo en lenguaje sencillo y extrae 3 aplicaciones clínicas prácticas que un fisioterapeuta pueda usar con sus pacientes."
    elif perfil == "Investigador":
        tono = "Resume el artículo con enfoque en metodología, resultados y limitaciones. Añade un comentario crítico sobre su nivel de evidencia."
    else:
        tono = "Haz un resumen general del artículo."

    return f"{tono}\n\nTítulo: {title}\nResumen: {abstract}"

def resumir_con_gpt(title, abstract, perfil):
    prompt = construir_prompt(title, abstract, perfil)
    respuesta = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return respuesta["choices"][0]["message"]["content"]

# --------- Ejecución principal ---------
if buscar:
    with st.spinner("Buscando artículos y generando resúmenes..."):
        query = construir_query(tema, tipo_estudio, periodo)
        ids = buscar_ids_pubmed(query, max_articulos)

        if not ids:
            st.warning("No se encontraron artículos con esos filtros.")
        else:
            abstracts = obtener_abstracts(ids)
            for i, (title, abstract) in enumerate(abstracts, start=1):
                resumen = resumir_con_gpt(title, abstract, perfil)
                st.markdown(f"## 📝 Artículo {i}: {title}")
                st.markdown(resumen)
                st.markdown("---")
