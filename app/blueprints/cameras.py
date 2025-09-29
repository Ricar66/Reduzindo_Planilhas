from __future__ import annotations
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx

bp = Blueprint("cameras", __name__, url_prefix="/cameras")

def caminho_arquivo():
    """Retorna o caminho para o arquivo JSON de câmeras."""
    return Path(current_app.config["DIRETORIO_DADOS"]) / "cameras.json"

# --- CAMPOS ATUALIZADOS CONFORME A NOVA PLANILHA ---
# Adicionado 'loja', 'localidade' e removido 'usuario', 'senha'
CAMPOS = ['filial', 'loja', 'localidade', 'nome', 'acesso_web', 'ip', 'descricao', 'observacao', 'portas']

@bp.get("/")
@login_required
def listar():
    """Exibe a lista de câmeras com filtros."""
    registros = repo.listar(caminho_arquivo())
    filial = request.args.get('filial', '').strip()
    termo = request.args.get('q', '').strip().lower()
    if termo:
        registros = [r for r in registros if termo in (r.get('nome', '') + r.get('ip', '') + r.get('localidade', '')).lower()]
    if filial:
        registros = [r for r in registros if (r.get('filial') or '') == filial]
    return render_template("cameras_listar.html", registros=registros, termo=termo, filial_atual=filial)

@bp.get("/novo")
@login_required
def novo():
    """Exibe o formulário para adicionar uma nova câmera."""
    return render_template("cameras_form.html", dados={}, filiais=FILIAIS)

@bp.post("/criar")
@somente_ti
def criar():
    """Processa o formulário de criação de nova câmera."""
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.criar(caminho_arquivo(), dados)
    flash("Câmera cadastrada com sucesso!", "success")
    return redirect(url_for("cameras.listar"))

@bp.get("/editar/<id>")
@login_required
def editar(id: str):
    """Exibe o formulário para editar uma câmera existente."""
    item = repo.obter_por_id(caminho_arquivo(), id)
    if not item:
        flash("Registro não encontrado.", "warning")
        return redirect(url_for("cameras.listar"))
    return render_template("cameras_form.html", dados=item, filiais=FILIAIS)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar(id: str):
    """Processa o formulário de atualização de uma câmera."""
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.atualizar(caminho_arquivo(), id, dados)
    flash("Câmera atualizada com sucesso!", "success")
    return redirect(url_for("cameras.listar"))

@bp.post("/excluir/<id>")
@somente_ti
def excluir(id: str):
    """Exclui o registro de uma câmera."""
    repo.excluir(caminho_arquivo(), id)
    flash("Registro removido.", "info")
    return redirect(url_for("cameras.listar"))

@bp.get("/importar")
@login_required
def importar_form():
    """Exibe a página de importação."""
    return render_template("cameras_importar.html")

@bp.post("/importar")
@somente_ti
def importar_post():
    """Processa a importação de um arquivo."""
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Nenhum arquivo enviado. Por favor, envie um CSV ou XLSX.", "warning")
        return redirect(url_for("cameras.importar_form"))
    try:
        registros_brutos = importar_generico(arq.read(), arq.filename, MAPA_IMPORT)
        for item in registros_brutos:
            repo.criar(caminho_arquivo(), item)
        flash(f"Importação concluída: {len(registros_brutos)} registros processados.", "success")
    except Exception as e:
        flash(f"Falha na importação: {e}", "danger")
    return redirect(url_for("cameras.listar"))

@bp.get("/exportar")
@login_required
def exportar():
    """Exporta os dados de câmeras para um arquivo Excel."""
    registros = repo.listar(caminho_arquivo())
    
    # --- MAPA DE EXPORTAÇÃO CORRIGIDO ---
    campos_exportacao = [
        ('Filial', 'filial'),
        ('LOJA', 'loja'),
        ('LOCALIDADE', 'localidade'),
        ('Nome', 'nome'),
        ('Acesso Via Web', 'acesso_web'),
        ('IP', 'ip'),
        ('Descrição', 'descricao'),
        ('Portas', 'portas')
    ]
    
    buf = gerar_xlsx("Cameras", registros, campos_exportacao)
    return send_file(buf, as_attachment=True, download_name="cameras.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- MAPA DE IMPORTAÇÃO CORRIGIDO ---
MAPA_IMPORT = {
    'filial': [],
    'loja': [],
    'localidade': [],
    'nome': [],
    'acesso_web': ['acesso via web'],
    'ip': [],
    'descricao': []
    # 'usuario' e 'senha' foram removidos
}