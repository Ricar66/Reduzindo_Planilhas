from __future__ import annotations
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx
from ..helpers.padronizador import encontrar_filial_correspondente
# No topo de licenças.py
from ..helpers.importador import importar_generico, analisar_cabecalhos_planilha
# from ..helpers.constants import FILIAIS

bp = Blueprint("vpn", __name__, template_folder="../templates")

def caminho_arquivo():
    return Path(current_app.config["DIRETORIO_DADOS"]) / "vpn.json"

CAMPOS = ['nome','email','filial','data_solicitacao','data_retirada','status','glpi_chamado']

@bp.get("/")
@login_required
def listar():
    registros = repo.listar(caminho_arquivo())
    filial = request.args.get('filial','').strip()
    termo  = request.args.get('q','').strip().lower()
    status = request.args.get('status','').strip().upper()
    if termo:  registros = [r for r in registros if termo in (r.get('nome','') + r.get('email','')).lower()]
    if filial: registros = [r for r in registros if (r.get('filial') or '') == filial]
    if status: registros = [r for r in registros if (r.get('status','').upper() == status)]
    registros.sort(key=lambda x: x.get('data_solicitacao',''), reverse=True)
    return render_template("vpn_listar.html", registros=registros, termo=termo, filial_atual=filial, status_atual=status)

@bp.get("/novo")
@login_required
def novo():
    return render_template("vpn_form.html", dados={})

@bp.route("/criar", methods=['POST'])
@somente_ti
def criar():
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.criar(caminho_arquivo(), dados); flash("VPN cadastrada!", "success")
    return redirect(url_for("vpn.listar"))

@bp.get("/editar/<id>")
@login_required
def editar(id: str):
    it = repo.obter_por_id(caminho_arquivo(), id)
    if not it:
        flash("Registro não encontrado.", "warning"); return redirect(url_for("vpn.listar"))
    return render_template("vpn_form.html", dados=it)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar(id: str):
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.atualizar(caminho_arquivo(), id, dados); flash("VPN atualizada!", "success")
    return redirect(url_for("vpn.listar"))

@bp.post("/excluir/<id>")
@somente_ti
def excluir(id: str):
    repo.excluir(caminho_arquivo(), id); flash("Registro removido.", "info")
    return redirect(url_for("vpn.listar"))

@bp.get("/importar")
@login_required
def importar_form():
    return render_template("vpn_importar.html")

# Em app/blueprints/vpn.py

# Em app/blueprints/vpn.py

@bp.route("/importar", methods=['POST']) # <--- VERSÃO CORRIGIDA
@somente_ti
def importar_post():
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Nenhum arquivo enviado. Por favor, selecione um arquivo CSV ou XLSX.", "warning")
        return redirect(url_for("vpn.importar_form"))
    try:
        # Sua lógica de importação...
        registros_brutos = importar_generico(arq.read(), arq.filename, MAPA_IMPORT)

        registros_processados = 0
        for item in registros_brutos:
            if not item.get('nome'):
                continue

            # A lógica de filiais está desativada, como solicitado

            repo.criar(caminho_arquivo(), item)
            registros_processados += 1

        flash(f"Importação concluída: {registros_processados} registros processados.", "success")
    except Exception as e:
        flash(f"Falha na importação: {e}", "danger")

    return redirect(url_for("vpn.listar"))

@bp.get("/exportar")
@login_required
def exportar():
    registros = repo.listar(caminho_arquivo())
    # Filtros (opcional, mas bom manter)
    termo  = request.args.get('q','').strip().lower()
    if termo:  registros = [r for r in registros if termo in (r.get('nome','')+r.get('email','')).lower()]

    # --- MAPA DE EXPORTAÇÃO CORRIGIDO ---
    campos = [
        ('NOME', 'nome'),
        ('DATA DA SOLICITAÇÃO', 'data_solicitacao'),
        ('DATA DE RETIRADA', 'data_retirada'),
        ('FEITO', 'status'),
        ('GLPI', 'glpi_chamado')
    ]

    buf = gerar_xlsx("Liberacao_VPN", registros, campos)
    return send_file(buf, as_attachment=True, download_name="liberacao_vpn.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Em app/blueprints/vpn.py

# Em app/blueprints/vpn.py

MAPA_IMPORT = {
    'nome': ['nome', 'colaborador', 'solicitante'],
    'email': ['email', 'e-mail'],
    'data_solicitacao': ['data da solicitacao', 'data solicitacao'],
    'data_retirada': ['data de retirada', 'data retirada'],
    'status': ['status', 'feito', 'situação'],
    'glpi_chamado': ['glpi', 'chamado', 'nº chamado']
}