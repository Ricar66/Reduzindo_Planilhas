# app/blueprints/impressoras.py

from __future__ import annotations
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx

bp = Blueprint("impressoras", __name__, template_folder="../templates")

def caminho_arquivo():
    return Path(current_app.config["DIRETORIO_DADOS"]) / "impressoras.json"

CAMPOS = ['filial','porta_ip','impressora','modelo','serial','login','senha','scanner','nf','departamento','responsavel','mod_toner']

# ... (as rotas listar, novo, criar, editar, atualizar, excluir ficam iguais) ...

@bp.get("/")
@login_required
def listar():
    regs = repo.listar(caminho_arquivo())
    filial = request.args.get('filial','').strip()
    termo  = request.args.get('q','').strip().lower()
    if termo:  regs = [r for r in regs if termo in (r.get('impressora','')+r.get('modelo','')+r.get('porta_ip','')).lower()]
    if filial: regs = [r for r in regs if (r.get('filial') or '') == filial]
    return render_template("impressoras_listar.html", registros=regs, termo=termo, filial_atual=filial)

@bp.get("/novo")
@login_required
def novo():
    return render_template("impressoras_form.html", dados={})

@bp.post("/criar")
@somente_ti
def criar():
    d = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.criar(caminho_arquivo(), d); flash("Impressora cadastrada!", "success")
    return redirect(url_for("impressoras.listar"))

@bp.get("/editar/<id>")
@login_required
def editar(id: str):
    it = repo.obter_por_id(caminho_arquivo(), id)
    if not it: flash("Registro não encontrado.", "warning"); return redirect(url_for("impressoras.listar"))
    return render_template("impressoras_form.html", dados=it)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar(id: str):
    d = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.atualizar(caminho_arquivo(), id, d); flash("Impressora atualizada!", "success")
    return redirect(url_for("impressoras.listar"))

@bp.post("/excluir/<id>")
@somente_ti
def excluir(id: str):
    repo.excluir(caminho_arquivo(), id); flash("Registro removido.", "info")
    return redirect(url_for("impressoras.listar"))

@bp.get("/importar")
@login_required
def importar_form():
    return render_template("impressoras_importar.html")

@bp.post("/importar")
@somente_ti
def importar_post():
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Envie CSV/XLSX.", "warning"); return redirect(url_for("impressoras.importar_form"))
    try:
        regs = importar_generico(arq.read(), arq.filename, MAPA_IMPORT)
        for it in regs: repo.criar(caminho_arquivo(), it)
        flash(f"Importação concluída: {len(regs)} registros.", "success")
    except Exception as e:
        flash(f"Falha na importação: {e}", "danger")
    return redirect(url_for("impressoras.listar"))

@bp.get("/exportar")
@login_required
def exportar():
    regs = repo.listar(caminho_arquivo())
    filial = request.args.get('filial','').strip()
    termo = request.args.get('q','').strip().lower()
    
    if termo: regs = [r for r in regs if termo in (r.get('impressora','') + r.get('modelo','') + r.get('porta_ip','')).lower()]
    if filial: regs = [r for r in regs if (r.get('filial') or '') == filial]
    
    campos = [
        ('Filial','filial'), ('Porta IP','porta_ip'), ('Impressora','impressora'),
        ('Modelo','modelo'), ('Serial','serial'), ('Login','login'), ('Senha','senha'),
        ('Scanner','scanner'), ('NF','nf'), ('Depto','departamento'),
        ('Responsável','responsavel'), ('Mod. Toner','mod_toner')
    ]
    
    buf = gerar_xlsx("Impressoras", regs, campos)
    
    return send_file(
        buf, as_attachment=True, download_name="impressoras.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

MAPA_IMPORT = {
    'filial':['filial'],'porta_ip':['porta_ip','ip'],'impressora':['impressora'],'modelo':['modelo'],
    'serial':['serial','numero_serie'],'login':['login','usuario'],'senha':['senha'],
    'scanner':['scanner'],'nf':['nf'],'departamento':['departamento'],'responsavel':['responsavel'],
    'mod_toner':['mod_toner','modelo_toner']
}