import os
import psycopg2
import streamlit as st
from datetime import datetime, date
from fpdf import FPDF

# -------------------------------------------------------------------
# CONFIGURAÇÃO DE PÁGINA E SEGURANÇA
# -------------------------------------------------------------------
st.set_page_config(page_title="Sistema Disciplinar PMPE", page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "icone.png"), layout="wide")

USUARIO_CORRETO = "admin"
SENHA_CORRETA = "pmpe2026"

def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acesso Restrito - Sistema PMPE")
        st.markdown("---")
        col1, col2 = st.columns([1, 2])
        with col1:
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                if usuario == USUARIO_CORRETO and senha == SENHA_CORRETA:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")
        return False
    return True

if verificar_login():

    # -------------------------------------------------------------------
    # CONEXÃO COM O SUPABASE (POSTGRESQL) E CRIAÇÃO DAS TABELAS
    # -------------------------------------------------------------------
    def conectar_banco():
        # Conecta via URL salva no Streamlit Cloud Secrets
        db_url = st.secrets["postgres"]["url"]
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS policiais (
                matricula TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                cpf TEXT,
                posto_graduacao TEXT NOT NULL,
                ome TEXT NOT NULL,
                subunidade TEXT,
                data_inclusao DATE NOT NULL,
                situacao TEXT DEFAULT 'ATIVA'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS punicoes (
                id SERIAL PRIMARY KEY,
                matricula TEXT NOT NULL REFERENCES policiais(matricula) ON DELETE CASCADE,
                tipo_pena TEXT NOT NULL,
                dias_pena INTEGER NOT NULL,
                boletim TEXT NOT NULL,
                data_fato DATE NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS elogios (
                id SERIAL PRIMARY KEY,
                matricula TEXT NOT NULL REFERENCES policiais(matricula) ON DELETE CASCADE,
                tipo_elogio TEXT NOT NULL,
                boletim TEXT NOT NULL,
                data_elogio DATE NOT NULL,
                descricao TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS observacoes (
                id SERIAL PRIMARY KEY,
                matricula TEXT NOT NULL REFERENCES policiais(matricula) ON DELETE CASCADE,
                data_registro DATE NOT NULL,
                categoria TEXT NOT NULL,
                descricao TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        return conn

    conectar_banco()

    # -------------------------------------------------------------------
    # GERADOR DE FICHA EM PDF (FPDF)
    # -------------------------------------------------------------------
    class FichaPDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 10)
            self.cell(0, 5, 'GOVERNO DO ESTADO DE PERNAMBUCO', 0, 1, 'C')
            self.cell(0, 5, 'POLÍCIA MILITAR DE PERNAMBUCO', 0, 1, 'C')
            self.cell(0, 5, 'DIRETORIA DE GESTÃO DE PESSOAS - FICHA DISCIPLINAR FUNCIONAL', 0, 1, 'C')
            self.line(10, 27, 200, 27)
            self.ln(5)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}/{{nb}} - Documento Gerado em {date.today().strftime("%d/%m/%Y")}', 0, 0, 'C')

    def gerar_pdf_ficha(pm, comp, tempo, punicoes, elogios, obs):
        pdf = FichaPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Dados Pessoais
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, '1. DADOS DE QUALIFICAÇÃO DO MILITAR', 0, 1, 'L')
        pdf.set_font('Helvetica', '', 10)
        
        pdf.cell(95, 6, f"Matrícula: {pm[0]}", 1)
        pdf.cell(95, 6, f"CPF: {pm[2] if pm[2] else 'Não Informado'}", 1, 1)
        pdf.cell(95, 6, f"Nome: {pm[3]} {pm[1]}", 1)
        pdf.cell(95, 6, f"Situação: {pm[7]}", 1, 1)
        pdf.cell(95, 6, f"OME: {pm[4]} ({pm[5] if pm[5] else 'Geral'})", 1)
        
        dt_inc_str = pm[6].strftime("%d/%m/%Y") if isinstance(pm[6], (date, datetime)) else datetime.strptime(str(pm[6]), '%Y-%m-%d').strftime('%d/%m/%Y')
        pdf.cell(95, 6, f"Data de Inclusão: {dt_inc_str}", 1, 1)
        
        pdf.ln(4)
        
        # Comportamento
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, '2. QUADRO DE COMPORTAMENTO DISCIPLINAR', 0, 1, 'L')
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(95, 8, f"COMPORTAMENTO ATUAL: {comp}", 1)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(95, 8, f"Tempo sem Infração: {tempo} anos", 1, 1)
        
        pdf.ln(4)

        # Elogios
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, '3. REGISTRO DE ELOGIOS E MÉRITOS', 0, 1, 'L')
        if elogios:
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(25, 6, 'Data', 1)
            pdf.cell(35, 6, 'Tipo', 1)
            pdf.cell(30, 6, 'Boletim', 1)
            pdf.cell(100, 6, 'Descrição', 1, 1)
            pdf.set_font('Helvetica', '', 8)
            for e in elogios:
                dt = e[4].strftime("%d/%m/%Y") if isinstance(e[4], (date, datetime)) else datetime.strptime(str(e[4]), '%Y-%m-%d').strftime('%d/%m/%Y')
                pdf.cell(25, 6, dt, 1)
                pdf.cell(35, 6, e[2], 1)
                pdf.cell(30, 6, e[3], 1)
                pdf.cell(100, 6, str(e[5])[:55], 1, 1)
        else:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.cell(0, 6, 'Nenhum elogio registrado.', 1, 1)

        pdf.ln(4)

        # Punições
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, '4. REGISTRO DE SANÇÕES DISCIPLINARES', 0, 1, 'L')
        if punicoes:
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(25, 6, 'Data Fato', 1)
            pdf.cell(30, 6, 'Pena', 1)
            pdf.cell(15, 6, 'Dias', 1)
            pdf.cell(30, 6, 'Boletim', 1)
            pdf.cell(90, 6, 'Período', 1, 1)
            pdf.set_font('Helvetica', '', 8)
            for p in punicoes:
                dt_f = p[5].strftime("%d/%m/%Y") if isinstance(p[5], (date, datetime)) else datetime.strptime(str(p[5]), '%Y-%m-%d').strftime('%d/%m/%Y')
                dt_i = p[6].strftime("%d/%m/%Y") if isinstance(p[6], (date, datetime)) else datetime.strptime(str(p[6]), '%Y-%m-%d').strftime('%d/%m/%Y')
                dt_m = p[7].strftime("%d/%m/%Y") if isinstance(p[7], (date, datetime)) else datetime.strptime(str(p[7]), '%Y-%m-%d').strftime('%d/%m/%Y')
                pdf.cell(25, 6, dt_f, 1)
                pdf.cell(30, 6, p[2], 1)
                pdf.cell(15, 6, str(p[3]), 1)
                pdf.cell(30, 6, p[4], 1)
                pdf.cell(90, 6, f"De {dt_i} a {dt_m}", 1, 1)
        else:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.cell(0, 6, 'Nenhuma sanção disciplinar registrada.', 1, 1)

        pdf.ln(4)

        # Observações
        pdf.set_font('Helvetica', 'B', 12)
        pdf.cell(0, 8, '5. OBSERVAÇÕES E ANOTAÇÕES GERAIS', 0, 1, 'L')
        if obs:
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(25, 6, 'Data', 1)
            pdf.cell(40, 6, 'Categoria', 1)
            pdf.cell(125, 6, 'Descrição', 1, 1)
            pdf.set_font('Helvetica', '', 8)
            for o in obs:
                dt = o[2].strftime("%d/%m/%Y") if isinstance(o[2], (date, datetime)) else datetime.strptime(str(o[2]), '%Y-%m-%d').strftime('%d/%m/%Y')
                pdf.cell(25, 6, dt, 1)
                pdf.cell(40, 6, o[3], 1)
                pdf.cell(125, 6, str(o[4])[:70], 1, 1)
        else:
            pdf.set_font('Helvetica', 'I', 9)
            pdf.cell(0, 6, 'Nenhuma observação cadastrada.', 1, 1)

        # Assinatura
        pdf.ln(15)
        pdf.cell(0, 5, '____________________________________________________', 0, 1, 'C')
        pdf.cell(0, 5, 'Chefe da Seção de Pessoal / Unidade', 0, 1, 'C')

        return bytes(pdf.output())

    # -------------------------------------------------------------------
    # CÁLCULO DISCIPLINAR
    # -------------------------------------------------------------------
    def obter_dados_fichas(matricula):
        conn = conectar_banco()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM policiais WHERE matricula = %s", (matricula,))
        pm = cursor.fetchone()
        if not pm:
            conn.close()
            return None, None, None, [], [], []

        cursor.execute("SELECT * FROM punicoes WHERE matricula = %s ORDER BY data_fim DESC", (matricula,))
        punicoes = cursor.fetchall()

        cursor.execute("SELECT * FROM elogios WHERE matricula = %s ORDER BY data_elogio DESC", (matricula,))
        elogios = cursor.fetchall()

        cursor.execute("SELECT * FROM observacoes WHERE matricula = %s ORDER BY data_registro DESC", (matricula,))
        obs = cursor.fetchall()
        
        conn.close()

        data_inclusao = pm[6] if isinstance(pm[6], date) else datetime.strptime(str(pm[6]), "%Y-%m-%d").date()
        hoje = date.today()
        punicoes_ativas = []
        
        for p in punicoes:
            dt_fim = p[7] if isinstance(p[7], date) else datetime.strptime(str(p[7]), "%Y-%m-%d").date()
            anos_decorridos = (hoje - dt_fim).days / 365.25
            if not ((p[2] == 'Prisão' and anos_decorridos >= 6) or (p[2] == 'Detenção' and anos_decorridos >= 4)):
                punicoes_ativas.append((p[2], dt_fim))

        if punicoes_ativas:
            data_marco_zero = punicoes_ativas[0][1]
        else:
            data_marco_zero = data_inclusao

        anos_no_marco = (hoje - data_marco_zero).days / 365.25
        qtd_prisoes = sum(1 for p in punicoes_ativas if p[0] == 'Prisão')
        qtd_detencoes = sum(1 for p in punicoes_ativas if p[0] == 'Detenção')
        equiv = qtd_prisoes + (qtd_detencoes / 2)

        if anos_no_marco >= 6 and len(punicoes_ativas) == 0:
            comp = "EXCEPCIONAL"
        elif equiv <= 0.5 and anos_no_marco >= 4:
            comp = "ÓTIMO"
        elif equiv <= 1:
            comp = "BOM"
        elif equiv <= 2:
            comp = "INSUFICIENTE"
        else:
            comp = "MAU"

        return pm, comp, round(anos_no_marco, 1), punicoes, elogios, obs

    # -------------------------------------------------------------------
    # INTERFACE DE NAVEGAÇÃO
    # -------------------------------------------------------------------
    st.sidebar.title("Navegação")
    if st.sidebar.button("Sair / Logout"):
        st.session_state["autenticado"] = False
        st.rerun()

    opcao = st.sidebar.radio("Menu Principal:", [
        "🔎 Ficha Disciplinar & PDF", 
        "➕ Cadastrar Policial", 
        "🌟 Registrar Elogio", 
        "⚠️ Registrar Punição",
        "📝 Adicionar Observação",
        "✏️ Editar Policial",
        "🗑️ Excluir Registros"
    ])

    st.title("🛡️ Gestão Disciplinar PMPE - Ficha Funcional")

    # 1. CONSULTA E EMISSÃO DE PDF
    if opcao == "🔎 Ficha Disciplinar & PDF":
        st.subheader("Consultar Ficha Funcional")
        mat_busca = st.text_input("Digite a Matrícula do Policial:")
        
        if st.button("Buscar Ficha"):
            pm, comp, tempo, punicoes, elogios, obs = obter_dados_fichas(mat_busca)
            if pm:
                st.success("Policial Encontrado!")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Militar", f"{pm[3]} {pm[1]}")
                col2.metric("Matrícula", pm[0])
                col3.metric("Comportamento", comp)
                col4.metric("Tempo sem Punição", f"{tempo} anos")

                st.markdown("---")
                
                pdf_bytes = gerar_pdf_ficha(pm, comp, tempo, punicoes, elogios, obs)
                st.download_button(
                    label="📄 Baixar Ficha Disciplinar Completa (PDF)",
                    data=pdf_bytes,
                    file_name=f"Ficha_Disciplinar_{pm[0]}.pdf",
                    mime="application/pdf"
                )

                st.markdown("---")
                tab1, tab2, tab3 = st.tabs(["🌟 Elogios", "⚠️ Punições", "📝 Observações"])
                
                with tab1:
                    if elogios:
                        for e in elogios:
                            st.write(f"**[{e[4]}] {e[2]}** - *Boletim:* {e[3]}")
                            st.caption(e[5])
                    else:
                        st.info("Nenhum elogio registrado.")

                with tab2:
                    if punicoes:
                        for p in punicoes:
                            st.write(f"**{p[2]} ({p[3]} dias)** - *Boletim:* {p[4]} | Período: {p[6]} a {p[7]}")
                    else:
                        st.info("Nenhuma punição registrada.")

                with tab3:
                    if obs:
                        for o in obs:
                            st.write(f"**[{o[2]}] {o[3]}**")
                            st.caption(o[4])
                    else:
                        st.info("Nenhuma observação registrada.")

            else:
                st.error("Policial não encontrado.")

    # 2. CADASTRO EXPANDIDO
    elif opcao == "➕ Cadastrar Policial":
        st.subheader("Cadastro Completo de Policial")
        with st.form("form_cad"):
            c1, c2 = st.columns(2)
            mat = c1.text_input("Matrícula*")
            nome = c2.text_input("Nome Completo*")
            cpf = c1.text_input("CPF")
            posto = c2.selectbox("Posto/Graduação", ["Soldado PM", "Cabo PM", "3º Sgt PM", "2º Sgt PM", "1º Sgt PM", "Subten PM", "2º Ten PM", "1º Ten PM", "Capitão PM", "Major PM", "Ten Cel PM", "Coronel PM"])
            ome = c1.text_input("OME (ex: 1º BPM)*")
            subunidade = c2.text_input("Subunidade / Seção (ex: 1ª CPM / P-1)")
            dt_inc = c1.date_input("Data de Inclusão", value=date(2015, 1, 1))
            situacao = c2.selectbox("Situação", ["ATIVA", "INATIVA / REFORMA", "LICENÇA"])
            
            if st.form_submit_button("Cadastrar Policial") and mat and nome:
                conn = conectar_banco()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO policiais VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                                   (mat, nome, cpf, posto, ome, subunidade, str(dt_inc), situacao))
                    conn.commit()
                    st.success("Policial cadastrado com sucesso!")
                except psycopg2.IntegrityError:
                    st.error("Matrícula já cadastrada!")
                conn.close()

    # 3. REGISTRAR ELOGIO
    elif opcao == "🌟 Registrar Elogio":
        st.subheader("Registro de Elogio / Mérito")
        with st.form("form_elo"):
            mat_e = st.text_input("Matrícula do Policial*")
            tipo_e = st.selectbox("Tipo de Elogio", ["Elogio Individual", "Elogio Coletivo", "Referência Elogiosa", "Medalha / Condecoração"])
            bol_e = st.text_input("Boletim (ex: BI nº 045/2024)*")
            dt_e = st.date_input("Data do Elogio")
            desc_e = st.text_area("Transcrição / Descrição do Elogio*")
            
            if st.form_submit_button("Salvar Elogio") and mat_e and bol_e:
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO elogios (matricula, tipo_elogio, boletim, data_elogio, descricao) VALUES (%s, %s, %s, %s, %s)",
                               (mat_e, tipo_e, bol_e, str(dt_e), desc_e))
                conn.commit()
                conn.close()
                st.success("Elogio registrado com sucesso!")

    # 4. REGISTRAR PUNIÇÃO
    elif opcao == "⚠️ Registrar Punição":
        st.subheader("Registro de Punição Disciplinar")
        with st.form("form_pun"):
            mat_p = st.text_input("Matrícula do Policial*")
            tipo_p = st.selectbox("Tipo de Punição", ["Repreensão", "Detenção", "Prisão"])
            dias_p = st.number_input("Dias de Punição", min_value=1, max_value=30, value=1)
            bol_p = st.text_input("Boletim de Publicação (ex: BG nº 120/2023)*")
            dt_fato = st.date_input("Data do Fato")
            dt_i = st.date_input("Início do Cumprimento")
            dt_f = st.date_input("Fim do Cumprimento")
            
            if st.form_submit_button("Salvar Punição") and mat_p and bol_p:
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO punicoes (matricula, tipo_pena, dias_pena, boletim, data_fato, data_inicio, data_fim) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                               (mat_p, tipo_p, dias_p, bol_p, str(dt_fato), str(dt_i), str(dt_f)))
                conn.commit()
                conn.close()
                st.success("Punição registrada com sucesso!")

    # 5. REGISTRAR OBSERVAÇÃO
    elif opcao == "📝 Adicionar Observação":
        st.subheader("Observação ou Anotação Funcional")
        with st.form("form_obs"):
            mat_o = st.text_input("Matrícula do Policial*")
            cat_o = st.selectbox("Categoria", ["Processo Administrativo (PAD/CD/CJ)", "Licença Médica", "Restrição Operacional", "Outros"])
            dt_o = st.date_input("Data do Registro")
            desc_o = st.text_area("Descrição da Observação*")
            
            if st.form_submit_button("Salvar Observação") and mat_o:
                conn = conectar_banco()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO observacoes (matricula, data_registro, categoria, descricao) VALUES (%s, %s, %s, %s)",
                               (mat_o, str(dt_o), cat_o, desc_o))
                conn.commit()
                conn.close()
                st.success("Observação registrada com sucesso!")

    # 6. EDITAR DADOS DO POLICIAL
    elif opcao == "✏️ Editar Policial":
        st.subheader("Editar Dados Cadastrais do Policial")
        mat_busca_ed = st.text_input("Digite a Matrícula do Policial para Editar:")
        if mat_busca_ed:
            conn = conectar_banco()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM policiais WHERE matricula = %s", (mat_busca_ed,))
            pm = cursor.fetchone()
            conn.close()

            if pm:
                with st.form("form_edit_pol"):
                    st.info(f"Editando: {pm[3]} {pm[1]} (Matrícula: {pm[0]})")
                    c1, c2 = st.columns(2)
                    novo_nome = c1.text_input("Nome Completo", value=pm[1])
                    novo_cpf = c2.text_input("CPF", value=pm[2] if pm[2] else "")
                    
                    postos_lista = ["Soldado PM", "Cabo PM", "3º Sgt PM", "2º Sgt PM", "1º Sgt PM", "Subten PM", "2º Ten PM", "1º Ten PM", "Capitão PM", "Major PM", "Ten Cel PM", "Coronel PM"]
                    idx_p = postos_lista.index(pm[3]) if pm[3] in postos_lista else 0
                    novo_posto = c1.selectbox("Posto/Graduação", postos_lista, index=idx_p)
                    
                    nova_ome = c2.text_input("OME", value=pm[4])
                    nova_sub = c1.text_input("Subunidade / Seção", value=pm[5] if pm[5] else "")
                    
                    dt_inc_atual = pm[6] if isinstance(pm[6], date) else datetime.strptime(str(pm[6]), "%Y-%m-%d").date()
                    nova_dt = c2.date_input("Data de Inclusão", value=dt_inc_atual)
                    
                    sit_lista = ["ATIVA", "INATIVA / REFORMA", "LICENÇA"]
                    idx_s = sit_lista.index(pm[7]) if pm[7] in sit_lista else 0
                    nova_sit = c1.selectbox("Situação", sit_lista, index=idx_s)
                    
                    if st.form_submit_button("Salvar Alterações"):
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE policiais 
                            SET nome = %s, cpf = %s, posto_graduacao = %s, ome = %s, subunidade = %s, data_inclusao = %s, situacao = %s
                            WHERE matricula = %s
                        """, (novo_nome, novo_cpf, novo_posto, nova_ome, nova_sub, str(nova_dt), nova_sit, mat_busca_ed))
                        conn.commit()
                        conn.close()
                        st.success("Dados do policial atualizados com sucesso!")
            else:
                st.error("Policial não encontrado.")

    # 7. EXCLUIR REGISTROS OU MILITAR
    elif opcao == "🗑️ Excluir Registros":
        st.subheader("Painel de Exclusão (Correção de Erros)")
        mat_exc = st.text_input("Digite a Matrícula do Policial para gerenciar exclusões:")
        if mat_exc:
            pm, comp, tempo, punicoes, elogios, obs = obter_dados_fichas(mat_exc)
            if pm:
                st.warning(f"Policial Selecionado: {pm[3]} {pm[1]} (Matrícula: {pm[0]})")
                
                acao_exc = st.selectbox("Escolha o que deseja remover:", [
                    "Selecione uma opção...",
                    "Excluir um Elogio específico",
                    "Excluir uma Punição específica",
                    "Excluir uma Observação específica",
                    "🔴 Excluir o Policial COMPLETO (com todo o histórico)"
                ])
                
                if acao_exc == "Excluir um Elogio específico":
                    if elogios:
                        opcoes_e = {f"[{e[4]}] {e[2]} - {e[3]}": e[0] for e in elogios}
                        sel_e = st.selectbox("Selecione o elogio:", list(opcoes_e.keys()))
                        if st.button("Excluir Elogio Selecionado"):
                            conn = conectar_banco()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM elogios WHERE id = %s", (opcoes_e[sel_e],))
                            conn.commit()
                            conn.close()
                            st.success("Elogio excluído com sucesso!")
                    else:
                        st.info("Nenhum elogio cadastrado para este militar.")
                        
                elif acao_exc == "Excluir uma Punição específica":
                    if punicoes:
                        opcoes_p = {f"Data Fato: {p[5]} | {p[2]} ({p[3]} dias) - BG: {p[4]}": p[0] for p in punicoes}
                        sel_p = st.selectbox("Selecione a punição:", list(opcoes_p.keys()))
                        if st.button("Excluir Punição Selecionada"):
                            conn = conectar_banco()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM punicoes WHERE id = %s", (opcoes_p[sel_p],))
                            conn.commit()
                            conn.close()
                            st.success("Punição excluída com sucesso!")
                    else:
                        st.info("Nenhuma punição cadastrada para este militar.")
                        
                elif acao_exc == "Excluir uma Observação específica":
                    if obs:
                        opcoes_o = {f"[{o[2]}] {o[3]}": o[0] for o in obs}
                        sel_o = st.selectbox("Selecione a observação:", list(opcoes_o.keys()))
                        if st.button("Excluir Observação Selecionada"):
                            conn = conectar_banco()
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM observacoes WHERE id = %s", (opcoes_o[sel_o],))
                            conn.commit()
                            conn.close()
                            st.success("Observação excluída com sucesso!")
                    else:
                        st.info("Nenhuma observação cadastrada para este militar.")
                        
                elif acao_exc == "🔴 Excluir o Policial COMPLETO (com todo o histórico)":
                    st.error("⚠️ ATENÇÃO: Esta ação é irreversível! Apagará o cadastro do policial e todas as suas punições, elogios e observações.")
                    if st.button("SIM, EXCLUIR DEFINITIVAMENTE ESTE MILITAR"):
                        conn = conectar_banco()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM elogios WHERE matricula = %s", (mat_exc,))
                        cursor.execute("DELETE FROM punicoes WHERE matricula = %s", (mat_exc,))
                        cursor.execute("DELETE FROM observacoes WHERE matricula = %s", (mat_exc,))
                        cursor.execute("DELETE FROM policiais WHERE matricula = %s", (mat_exc,))
                        conn.commit()
                        conn.close()
                        st.success("Policial e todo o seu histórico foram excluídos do sistema com sucesso!")
            else:
                st.error("Policial não encontrado.")
