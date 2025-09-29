from __future__ import annotations
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from datetime import date

# Helpers do seu projeto
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx
# from ..helpers.constants import FILIAIS
from ..helpers.padronizador import encontrar_filial_correspondente
# No topo de licenças.py
from ..helpers.importador import importar_generico, analisar_cabecalhos_planilha

bp = Blueprint("licencas", __name__, url_prefix="/licencas")

def caminho_arquivo():
    """Retorna o caminho para o arquivo JSON de licenças."""
    return Path(current_app.config["DIRETORIO_DADOS"]) / "licencas.json"

# --- CAMPOS ATUALIZADOS PARA A NOVA ESTRUTURA ---
CAMPOS = [
    'email', 'matricula', 'nome', 'filial', 'cargo', 'licenca', 'qtde',
    'departamento', 'empresa', 'observacao', 'situacao', 'data_desligamento'
]

@bp.get("/")
@login_required
def listar():
    """Lista as licenças ativas."""
    registros = repo.listar(caminho_arquivo())
    
    # Filtra para mostrar apenas registros ativos por padrão
    registros_ativos = [r for r in registros if r.get('situacao', 'ATIVO') != 'INATIVO']

    termo = request.args.get('q', '').strip().lower()
    if termo:
        registros_ativos = [r for r in registros_ativos if termo in (r.get('email', '') + r.get('nome', '')).lower()]
    
    return render_template("licencas_listar.html", registros=registros_ativos, termo=termo)

@bp.get("/inativos")
@login_required
def inativos():
    """Lista as licenças marcadas como inativas."""
    registros = repo.listar(caminho_arquivo())
    registros_inativos = [r for r in registros if r.get('situacao') == 'INATIVO']
    return render_template("licencas_inativos.html", registros=registros_inativos)

@bp.get("/novo")
@login_required
def novo():
    """Exibe o formulário para criar uma nova licença."""
    return render_template("licencas_form.html", dados={}, lista_licencas=tipos_de_licencas)

@bp.route("/criar", methods=['POST'])
@somente_ti
def criar():
    """Processa a criação de uma nova licença."""
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    dados['situacao'] = 'ATIVO' # Garante que novos registros sejam sempre ativos
    repo.criar(caminho_arquivo(), dados)
    flash("Licença cadastrada com sucesso!", "success")
    return redirect(url_for("licencas.listar"))

@bp.get("/editar/<id>")
@login_required
def editar(id: str):
    """Exibe o formulário para editar uma licença existente."""
    it = repo.obter_por_id(caminho_arquivo(), id)
    if not it:
        flash("Registro não encontrado.", "warning")
        return redirect(url_for("licencas.listar"))
    return render_template("licencas_form.html", dados=it, filiais=FILIAIS, lista_licencas=tipos_de_licencas)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar(id: str):
    """Processa a atualização de uma licença."""
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.atualizar(caminho_arquivo(), id, dados)
    flash("Licença atualizada com sucesso!", "success")
    return redirect(url_for("licencas.listar"))

@bp.post("/desativar/<id>")
@somente_ti
def desativar(id: str):
    """Marca uma licença como inativa (soft delete)."""
    it = repo.obter_por_id(caminho_arquivo(), id)
    if it:
        it['situacao'] = 'INATIVO'
        it['data_desligamento'] = date.today().isoformat()
        repo.atualizar(caminho_arquivo(), id, it)
        flash("Colaborador marcado como INATIVO.", "info")
    return redirect(url_for("licencas.listar"))

@bp.post("/reativar/<id>")
@somente_ti
def reativar(id: str):
    """Reativa uma licença que estava inativa."""
    it = repo.obter_por_id(caminho_arquivo(), id)
    if it:
        it['situacao'] = 'ATIVO'
        it['data_desligamento'] = ''
        repo.atualizar(caminho_arquivo(), id, it)
        flash("Colaborador reativado com sucesso.", "success")
    return redirect(url_for('licencas.inativos'))

@bp.get("/importar")
@login_required
def importar_form():
    return render_template("licencas_importar.html")

@bp.post("/importar")
@somente_ti
def importar_post():
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Nenhum arquivo enviado. Por favor, selecione um arquivo CSV ou XLSX.", "warning")
        return redirect(url_for("licencas.importar_form"))
    try:
        registros_brutos = importar_generico(arq.read(), arq.filename, MAPA_IMPORT)
        
        registros_processados = 0
        for item in registros_brutos:
            if not item.get('nome') and not item.get('email'):
                continue

            # --- LÓGICA DE FILIAIS DESATIVADA ---
            # A linha abaixo foi comentada para ignorar o processamento de filial
            # item['filial'] = encontrar_filial_correspondente(item.get('filial', ''), FILIAIS)

            item["situacao"] = item.get("situacao") or "ATIVO"
            
            repo.criar(caminho_arquivo(), item)
            registros_processados += 1

        flash(f"Importação concluída: {registros_processados} registros processados.", "success")
    except Exception as e:
        flash(f"Falha na importação: {e}", "danger")
    return redirect(url_for("licencas.listar"))

@bp.get("/exportar")
@login_required
def exportar():
    registros = repo.listar(caminho_arquivo())
    registros_ativos = [r for r in registros if (r.get("situacao", "ATIVO") or "ATIVO").strip().upper() != "INATIVO"]

    # --- MAPA DE EXPORTAÇÃO CORRIGIDO ---
    campos_exportacao = [
        ('Email', 'email'),
        ('Matricula', 'matricula'),
        ('Nome', 'nome'),
        ('Filial', 'filial'),
        ('Cargo', 'cargo'),
        ('Licenca', 'licenca'),
        ('QTDE', 'qtde'),
        ('Departamento', 'departamento'),
        ('Empresa', 'empresa')
    ]

    buf = gerar_xlsx("Licencas Ativas", registros_ativos, campos_exportacao)
    return send_file(buf, as_attachment=True, download_name="licencas_ativas.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- MAPA DE IMPORTAÇÃO AJUSTADO PARA SUAS COLUNAS ---
MAPA_IMPORT = {
    'email': [],       # O sistema vai encontrar "Email", "E-mail", etc. sozinho
    'matricula': [],
    'nome': [],        # O sistema vai encontrar "Nome", "Colaborador", etc. sozinho
    'filial': [],
    'cargo': [],
    'licenca': [],     # O sistema vai encontrar "Licenca", "Licença", etc. sozinho
    'qtde': [],
    'departamento': [],
    'empresa': []
}

# Lista de tipos de licença para o formulário
tipos_de_licencas = [
    'Microsoft Power Automate Free', 'Microsoft Power Automate Premium', 'Microsoft Stream Trial',
    'Microsoft Teams Rooms Pro', 'Office 365 E1 Plus', 'Office 365 E3',
    'Microsoft 365 Copilot', 'Microsoft Fabric (Free)', 'Microsoft Power Apps Plan 2',
    'Microsoft Power Apps for Developer', 'Microsoft 365 Business Center', 'Microsoft 365 Business Standard',
    'Microsoft 365 Apps for enterprise', 'Exchange Online (Plan 1)', 'Exchange Online Kiosk',
    'Microsoft Defender for Office 365 (Plan 2)', 'Microsoft Copilot Studio Viral Trial',
    'Microsoft Planner and Project Plan 3', 'Microsoft 365 Defender'
]