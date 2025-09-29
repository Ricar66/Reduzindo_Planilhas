# app/blueprints/equipamentos.py

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx
# from ..helpers.constants import FILIAIS
from ..helpers.padronizador import encontrar_filial_correspondente

bp = Blueprint("equipamentos", __name__, template_folder="../templates")

def caminho_arquivo():
    return Path(current_app.config["DIRETORIO_DADOS"]) / "equipamentos.json"

# Lista de todos os campos que vamos armazenar, baseada na sua planilha
CAMPOS = [
    'nome', 'cpf', 'cargo', 'filial', 'descricao_filial', 'cc', 'descricao_cc',
    'tipo', 'marca', 'modelo', 'numero_serie', 'patrimonio', 'acessorios', 'anc', 'termo_assinado'
]

@bp.get("/")
@login_required
def listar():
    regs = repo.listar(caminho_arquivo())
    filial = request.args.get('filial', '').strip()
    termo  = request.args.get('q', '').strip().lower()
    if termo:
        regs = [r for r in regs if termo in (
            r.get('nome','')+
            r.get('patrimonio','')+
            r.get('numero_serie','')+
            r.get('modelo','')
        ).lower()]
    if filial:
        regs = [r for r in regs if (r.get('filial') or '') == filial]
    return render_template("equipamentos_listar.html", registros=regs, termo=termo)

@bp.get("/novo")
@login_required
def novo():
    # CORREÇÃO: Passando um dicionário vazio chamado 'dados'
    return render_template("equipamentos_form.html", dados={})

@bp.post("/criar")
@somente_ti
def criar():
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.criar(caminho_arquivo(), dados)
    flash("Equipamento cadastrado com sucesso!", "success")
    return redirect(url_for("equipamentos.listar"))

@bp.get("/editar/<id>")
@login_required
def editar(id: str):
    it = repo.obter_por_id(caminho_arquivo(), id)
    if not it:
        flash("Registro não encontrado.", "warning")
        return redirect(url_for("equipamentos.listar"))

    # CORREÇÃO: Garante que a variável 'dados' sempre exista ao renderizar
    return render_template("equipamentos_form.html", dados=it)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar(id: str):
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS}
    repo.atualizar(caminho_arquivo(), id, dados)
    flash("Equipamento atualizado com sucesso!", "success")
    return redirect(url_for("equipamentos.listar"))

@bp.post("/excluir/<id>")
@somente_ti
def excluir(id: str):
    repo.excluir(caminho_arquivo(), id)
    flash("Registro removido.", "info")
    return redirect(url_for("equipamentos.listar"))

@bp.get("/importar")
@login_required
def importar_form():
    return render_template("equipamentos_importar.html")

# Em app/blueprints/licencas.py

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
    return redirect(url_for("equipamentos.listar"))

@bp.get("/exportar")
@login_required
def exportar():
    regs = repo.listar(caminho_arquivo())
    # Adicionando a mesma lógica de filtro da listagem para a exportação
    filial = request.args.get('filial', '').strip()
    termo  = request.args.get('q', '').strip().lower()
    if termo:
        regs = [r for r in regs if termo in (r.get('nome','')+r.get('patrimonio','')+r.get('numero_serie','')).lower()]
    if filial:
        regs = [r for r in regs if (r.get('filial') or '') == filial]

    campos_exportacao = [
        ('NOME', 'nome'), ('CPF', 'cpf'), ('CARGO', 'cargo'), ('FILIAL', 'filial'),
        ('DESCRICAO FILIAL', 'descricao_filial'), ('CC', 'cc'), ('DESCRICAO CC', 'descricao_cc'),
        ('TIPO', 'tipo'), ('MARCA', 'marca'), ('MODELO', 'modelo'), ('NÚMERO DE SÉRIE', 'numero_serie'),
        ('PATRIMÔNIO', 'patrimonio'), ('ACESSÓRIOS', 'acessorios'), ('ANC', 'anc'), ('TERMO ASSINADO', 'termo_assinado')
    ]
    buf = gerar_xlsx("Equipamentos", regs, campos_exportacao)
    return send_file(buf, as_attachment=True, download_name="equipamentos.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Mapa para a importação de planilhas, com vários nomes possíveis para cada coluna
# Em app/blueprints/equipamentos.py

MAPA_IMPORT = {
    'nome': ['colaborador', 'funcionario'],
    'cpf': [],
    'cargo': [],
    'filial': [],
    'cc': ['centro de custo'],
    'descricao_cc': [],
    'tipo': ['tipo de equipamento'],
    'marca': [],
    'modelo': [],
    'filial': ['filial', 'descricao_filial'],
    'numero_serie': ['serial', 'serial number'],
    'patrimonio': ['asset', 'etiqueta'],
    'acessorios': ['observacao'],
    'anc': [],
    'termo_assinado': ['termo']
}