# app/blueprints/ferias.py

from __future__ import annotations
from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx
from ..helpers.importador import importar_generico, analisar_cabecalhos_planilha

bp = Blueprint("ferias", __name__, template_folder="../templates")

def caminho_arquivo():
    return Path(current_app.config["DIRETORIO_DADOS"]) / "ferias.json"

# Garanta que esta lista de campos esteja assim:
CAMPOS = ['nome', 'data_saida', 'data_retorno', 'departamento_filial', 
          'ad', 'email', 'totvs', 'crm', 'john_deere', 'atendente']

# Lista de aplicativos disponíveis para bloqueio
APPS_BLOQUEAVEIS = ['AD', 'Email', 'TOTVS', 'CRM', 'John Deere']

@bp.get("/")
@login_required
def listar_ferias():
    registros = repo.listar(caminho_arquivo())
    termo = request.args.get('q', '').strip().lower()
    if termo:
        registros = [r for r in registros if termo in (r.get('nome', '') + r.get('atendente', '') + r.get('departamento', '')).lower()]
    return render_template("ferias_listar.html", registros=registros, termo=termo)

@bp.get("/novo")
@login_required
def novo():
    return render_template("ferias_form.html", dados={}, lista_apps=APPS_BLOQUEAVEIS)

@bp.post("/criar")
@somente_ti
def criar():
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS if c != 'bloqueios'}
    dados['bloqueios'] = ', '.join(request.form.getlist('bloqueios'))
    repo.criar(caminho_arquivo(), dados)
    flash("Férias cadastradas com sucesso!", "success")
    return redirect(url_for("ferias.listar_ferias"))

@bp.get("/editar/<id>")
@login_required
def editar(id: str):
    it = repo.obter_por_id(caminho_arquivo(), id)
    if not it:
        flash("Registro não encontrado.", "warning")
        return redirect(url_for("ferias.listar_ferias"))
    return render_template("ferias_form.html", dados=it, lista_apps=APPS_BLOQUEAVEIS)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar(id: str):
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS if c != 'bloqueios'}
    dados['bloqueios'] = ', '.join(request.form.getlist('bloqueios'))
    repo.atualizar(caminho_arquivo(), id, dados)
    flash("Férias atualizadas com sucesso!", "success")
    return redirect(url_for("ferias.listar_ferias"))

@bp.post("/excluir/<id>")
@somente_ti
def excluir(id: str):
    repo.excluir(caminho_arquivo(), id)
    flash("Registro de férias removido.", "info")
    return redirect(url_for("ferias.listar_ferias"))

@bp.get("/exportar")
@login_required
def exportar_ferias():
    regs = repo.listar(caminho_arquivo())


    # --- MAPA DE EXPORTAÇÃO CORRIGIDO ---
    campos = [
        ('NOME COMPLETO', 'nome'),
        ('DATA DE SAÍDA', 'data_saida'),
        ('DATA DE RETORNO', 'data_retorno'),
        ('DEPARTAMENTO E FILIAL', 'departamento_filial'),
        ('AD', 'ad'),
        ('EMAIL', 'email'),
        ('TOTVS', 'totvs'),
        ('CRM', 'crm'),
        ('JOHN DEERE', 'john_deere'),
        ('ATENDENTE', 'atendente')
    ]

    buf = gerar_xlsx("Controle de Ferias", regs, campos)
    
    return send_file(buf, as_attachment=True, download_name="controle_ferias.xlsx", 
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@bp.get("/importar")
@login_required
def importar_form():
    return render_template("ferias_importar.html")

@bp.post("/importar")
@somente_ti
def importar_post():
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Envie um arquivo CSV ou Excel.", "warning")
        return redirect(url_for("ferias.importar_form"))
    try:
        # A função agora usa o MAPA_IMPORT corrigido
        regs = importar_generico(arq.read(), arq.filename, MAPA_IMPORT)
        
        registros_processados = 0
        for item in regs:
            # Pula linhas que não tenham um nome de colaborador
            if not item.get('nome'):
                continue
            
            # Salva o registro limpo
            repo.criar(caminho_arquivo(), item)
            registros_processados += 1
        
        flash(f"Importação concluída: {registros_processados} registros processados.", "success")
    except Exception as e:
        flash(f"Falha na importação: {e}", "danger")
        
    return redirect(url_for("ferias.listar_ferias"))


# --- MAPA DE IMPORTAÇÃO CORRIGIDO CONFORME O RELATÓRIO ---
MAPA_IMPORT = {
    'nome': ['nome_completo'],
    'data_saida': ['data_de_saida'],
    'data_retorno': ['data_de_retorno'],
    'departamento_filial': ['departamento_e_filial'],
    'ad': ['ad'],
    'email': ['email'],
    'totvs': ['totvs'],
    'crm': ['crm'],
    'john_deere': ['john_deere'],
    'atendente': ['atendente']
}
