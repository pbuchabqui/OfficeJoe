import streamlit as st
import requests
import json
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="OfficeJoe - Perícia Contábil",
    page_icon="📋",
    layout="wide"
)

# URL da API
API_BASE_URL = "http://localhost:8000/api/v1"

# Estilos
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - Autenticação
# ============================================================================
st.sidebar.title("🔐 Autenticação")

if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.user_email = None

if st.session_state.token is None:
    st.sidebar.write("**Status:** Não autenticado")
    
    with st.sidebar.form("login_form"):
        email = st.text_input("Email", value="admin@example.com")
        password = st.text_input("Senha", type="password", value="admin123")
        submit = st.form_submit_button("Login")
        
        if submit:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/auth/login",
                    json={"email": email, "password": password}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data.get("access_token")
                    st.session_state.user_email = email
                    st.success("✅ Login realizado!")
                    st.rerun()
                else:
                    st.error("❌ Credenciais inválidas")
            except Exception as e:
                st.error(f"❌ Erro ao conectar: {e}")
else:
    st.sidebar.write(f"✅ **Autenticado como:** {st.session_state.user_email}")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.user_email = None
        st.rerun()

# ============================================================================
# HEADER
# ============================================================================
st.title("📋 OfficeJoe - Sistema de Perícias Contábeis")
st.markdown("---")

if st.session_state.token is None:
    st.warning("⚠️ Faça login para usar a aplicação")
    st.stop()

# ============================================================================
# TABS PRINCIPAIS
# ============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard",
    "➕ Novo Processo",
    "📁 Processos",
    "📤 Upload"
])

# ============================================================================
# TAB 1: Dashboard
# ============================================================================
with tab1:
    st.header("Dashboard")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Processos", "12", "+2 esta semana")
    with col2:
        st.metric("Documentos", "145", "+23 hoje")
    with col3:
        st.metric("Pendências", "5", "-1 hoje")
    
    st.markdown("---")
    st.subheader("Atividades Recentes")
    st.info("Nenhuma atividade recente para exibir")

# ============================================================================
# TAB 2: Novo Processo
# ============================================================================
with tab2:
    st.header("➕ Criar Novo Processo")
    
    with st.form("novo_processo_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            case_number = st.text_input(
                "Número do Processo",
                placeholder="0000001-00.2025.1.00.0000"
            )
        
        with col2:
            case_type = st.selectbox(
                "Tipo de Perícia",
                ["contábil", "trabalhista", "ambiental", "tributária", "outras"]
            )
        
        title = st.text_input(
            "Título da Perícia",
            placeholder="Ex: Perícia Contábil da Empresa XYZ"
        )
        
        description = st.text_area(
            "Descrição (opcional)",
            placeholder="Adicione detalhes sobre o processo..."
        )
        
        submitted = st.form_submit_button("Criar Processo", use_container_width=True)
        
        if submitted:
            if not case_number or not title:
                st.error("❌ Preencha todos os campos obrigatórios")
            else:
                try:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    payload = {
                        "case_number": case_number,
                        "case_type": case_type,
                        "title": title,
                        "description": description
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/cases",
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code == 201:
                        st.success("✅ Processo criado com sucesso!")
                        st.json(response.json())
                    else:
                        st.error(f"❌ Erro: {response.text}")
                except Exception as e:
                    st.error(f"❌ Erro ao criar: {e}")

# ============================================================================
# TAB 3: Processos
# ============================================================================
with tab3:
    st.header("📁 Meus Processos")
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{API_BASE_URL}/cases", headers=headers)
        
        if response.status_code == 200:
            cases = response.json()
            
            if isinstance(cases, dict) and "items" in cases:
                cases = cases["items"]
            
            if cases:
                for case in cases:
                    with st.expander(f"📋 {case.get('case_number')} - {case.get('title')}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Tipo:** {case.get('case_type')}")
                        with col2:
                            st.write(f"**Status:** {case.get('status', 'ativo')}")
                        with col3:
                            st.write(f"**ID:** {case.get('id')}")
                        
                        if case.get('description'):
                            st.write(f"**Descrição:** {case.get('description')}")
                        
                        # Botões de ação
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.button("📄 Ver Detalhes", key=f"details_{case.get('id')}")
                        with col2:
                            st.button("📤 Upload", key=f"upload_{case.get('id')}")
                        with col3:
                            st.button("🗑️ Deletar", key=f"delete_{case.get('id')}")
            else:
                st.info("ℹ️ Nenhum processo encontrado")
        else:
            st.error(f"❌ Erro ao buscar processos: {response.text}")
    except Exception as e:
        st.error(f"❌ Erro: {e}")

# ============================================================================
# TAB 4: Upload de Documentos
# ============================================================================
with tab4:
    st.header("📤 Upload de Documentos")
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{API_BASE_URL}/cases", headers=headers)
        
        if response.status_code == 200:
            cases = response.json()
            if isinstance(cases, dict) and "items" in cases:
                cases = cases["items"]
            
            if cases:
                case_options = {f"{c.get('case_number')} - {c.get('title')}": c.get('id') for c in cases}
                
                with st.form("upload_form"):
                    selected_case = st.selectbox(
                        "Selecione o Processo",
                        options=case_options.keys()
                    )
                    
                    category = st.selectbox(
                        "Categoria do Documento",
                        ["balanço", "diário", "razão", "nota_fiscal", "recibo", "contrato", "outro"]
                    )
                    
                    uploaded_file = st.file_uploader(
                        "Selecione um PDF",
                        type=["pdf"]
                    )
                    
                    submitted = st.form_submit_button("Fazer Upload", use_container_width=True)
                    
                    if submitted:
                        if uploaded_file and selected_case:
                            try:
                                case_id = case_options[selected_case]
                                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                                data = {"category": category}
                                
                                response = requests.post(
                                    f"{API_BASE_URL}/cases/{case_id}/documents",
                                    files=files,
                                    data=data,
                                    headers=headers
                                )
                                
                                if response.status_code == 201:
                                    st.success("✅ Documento enviado com sucesso!")
                                    st.json(response.json())
                                else:
                                    st.error(f"❌ Erro: {response.text}")
                            except Exception as e:
                                st.error(f"❌ Erro ao enviar: {e}")
                        else:
                            st.error("❌ Selecione um processo e um arquivo")
            else:
                st.warning("⚠️ Crie um processo antes de fazer upload")
    except Exception as e:
        st.error(f"❌ Erro: {e}")

# ============================================================================
# FOOTER
# ============================================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 12px;">
    <p>OfficeJoe v1.0 | Powered by Streamlit</p>
    <p>API: http://localhost:8000 | Frontend: http://localhost:3000</p>
</div>
""", unsafe_allow_html=True)
