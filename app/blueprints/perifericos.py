# app/blueprints/perifericos.py

from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required
from pathlib import Path
from ..helpers import armazenamento_json as repo
from ..helpers.autorizacao import somente_ti
from ..helpers.importador import importar_generico
from ..helpers.exportador import gerar_xlsx

bp = Blueprint("perifericos", __name__, url_prefix="/perifericos")

# --- ARQUIVOS DE DADOS ---
def caminho_estoque_arquivo():
    return Path(current_app.config["DIRETORIO_DADOS"]) / "perifericos_estoque.json"

def caminho_entregas_arquivo():
    return Path(current_app.config["DIRETORIO_DADOS"]) / "perifericos_entregas.json"

# --- CONTROLE DE ESTOQUE DE PERIFÉRICOS ---
CAMPOS_ESTOQUE = ['produto', 'qtd_estoque', 'cod_totvs', 'onde_comprar']

@bp.get("/")
@login_required
def listar_estoque():
    registros = repo.listar(caminho_estoque_arquivo())
    termo = request.args.get('q', '').strip().lower()
    if termo:
        registros = [r for r in registros if termo in r.get('produto', '').lower()]
    return render_template("perifericos_listar.html", registros=registros, termo=termo)

@bp.get("/novo")
@login_required
def novo_item_estoque():
    return render_template("perifericos_form.html", dados={})

@bp.post("/criar")
@somente_ti
def criar_item_estoque():
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS_ESTOQUE}
    repo.criar(caminho_estoque_arquivo(), dados)
    flash("Item de estoque cadastrado com sucesso!", "success")
    return redirect(url_for("perifericos.listar_estoque"))

@bp.get("/editar/<id>")
@login_required
def editar_item_estoque(id: str):
    it = repo.obter_por_id(caminho_estoque_arquivo(), id)
    if not it:
        flash("Registro não encontrado.", "warning")
        return redirect(url_for("perifericos.listar_estoque"))
    return render_template("perifericos_form.html", dados=it)

@bp.post("/atualizar/<id>")
@somente_ti
def atualizar_item_estoque(id: str):
    dados = {c: request.form.get(c, '').strip() for c in CAMPOS_ESTOQUE}
    repo.atualizar(caminho_estoque_arquivo(), id, dados)
    flash("Item de estoque atualizado com sucesso!", "success")
    return redirect(url_for("perifericos.listar_estoque"))

@bp.post("/excluir/<id>")
@somente_ti
def excluir_item_estoque(id: str):
    repo.excluir(caminho_estoque_arquivo(), id)
    flash("Registro de estoque removido.", "info")
    return redirect(url_for("perifericos.listar_estoque"))


# --- CONTROLE DE ENTREGAS (COM LÓGICA INTEGRADA) ---
CAMPOS_ENTREGA = ['glpi', 'solicitante', 'produto_id', 'produto_nome', 'qtd', 'observacao']

@bp.get("/entregas")
@login_required
def listar_entregas():
    registros = repo.listar(caminho_entregas_arquivo())
    termo = request.args.get('q', '').strip().lower()
    if termo:
        registros = [r for r in registros if termo in r.get('solicitante', '').lower() or termo in r.get('produto_nome', '').lower()]
    return render_template("entregas_listar.html", registros=registros, termo=termo)

@bp.get("/entregas/nova")
@login_required
def nova_entrega():
    """Prepara o formulário de nova entrega, enviando apenas itens com estoque."""
    estoque_completo = repo.listar(caminho_estoque_arquivo())
    itens_disponiveis = [item for item in estoque_completo if int(item.get('qtd_estoque', 0)) > 0]
    
    if not itens_disponiveis:
        flash("Nenhum item com estoque disponível para entrega.", "warning")

    return render_template("entregas_form.html", dados={}, itens_disponiveis=itens_disponiveis)

@bp.post("/entregas/criar")
@somente_ti
def criar_entrega():
    """Processa a criação de uma nova entrega e deduz do estoque."""
    produto_id = request.form.get('produto_id')
    qtd_entregue_str = request.form.get('qtd', '0')

    if not produto_id or not qtd_entregue_str.isdigit() or int(qtd_entregue_str) <= 0:
        flash("Dados inválidos. Selecione um produto e informe uma quantidade válida.", "danger")
        return redirect(url_for('perifericos.nova_entrega'))

    qtd_entregue = int(qtd_entregue_str)
    item_estoque = repo.obter_por_id(caminho_estoque_arquivo(), produto_id)

    if not item_estoque:
        flash("Produto não encontrado no estoque.", "danger")
        return redirect(url_for('perifericos.nova_entrega'))

    qtd_disponivel = int(item_estoque.get('qtd_estoque', 0))
    if qtd_entregue > qtd_disponivel:
        flash(f"Não há estoque suficiente para esta entrega. Disponível: {qtd_disponivel}", "danger")
        return redirect(url_for('perifericos.nova_entrega'))

    # Lógica de dedução do estoque
    item_estoque['qtd_estoque'] = str(qtd_disponivel - qtd_entregue)
    repo.atualizar(caminho_estoque_arquivo(), produto_id, item_estoque)

    # Cria o registro da entrega
    dados_entrega = {
        'glpi': request.form.get('glpi', ''),
        'solicitante': request.form.get('solicitante', ''),
        'produto_id': produto_id,
        'produto_nome': item_estoque.get('produto'),
        'qtd': str(qtd_entregue),
        'observacao': request.form.get('observacao', '')
    }
    repo.criar(caminho_entregas_arquivo(), dados_entrega)

    flash(f"{qtd_entregue} unidade(s) de '{item_estoque.get('produto')}' entregue(s) com sucesso! Estoque atualizado.", "success")
    return redirect(url_for("perifericos.listar_entregas"))

# (As rotas de editar, atualizar e excluir entregas não precisam da lógica de estoque, então podem ser mantidas como estavam)

# --- IMPORTAÇÃO E EXPORTAÇÃO ---
# (As funções de importação e exportação podem ser mantidas como estavam)


# --- IMPORTAÇÃO E EXPORTAÇÃO ---

@bp.get("/estoque/importar")
@login_required
def importar_estoque_form():
    return render_template("perifericos_importar.html")

@bp.post("/estoque/importar")
@somente_ti
def importar_estoque_post():
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Nenhum arquivo enviado. Por favor, selecione um arquivo CSV ou XLSX.", "warning")
        return redirect(url_for("perifericos.importar_estoque_form"))
    try:
        # Mapa de importação específico para o estoque de periféricos
        mapa = {
            'produto': ['produto', 'item', 'descrição'],
            'qtd_estoque': ['qtd estoque', 'qtd_estoque', 'estoque', 'quantidade'],
            'cod_totvs': ['cod totvs', 'codigo', 'cód totvs'],
            'onde_comprar': ['onde comprar', 'fornecedor', 'comprar em']
        }

        # Chama o importador genérico
        registros = importar_generico(arq.read(), arq.filename, mapa)

        # Salva cada registro no arquivo de estoque
        for item in registros:
            # Pula linhas que não tenham um nome de produto
            if not item.get('produto'):
                continue
            repo.criar(caminho_estoque_arquivo(), item)

        flash(f"Importação de estoque concluída: {len(registros)} registros processados.", "success")

    except Exception as e:
        flash(f"Falha na importação: {e}", "danger")

    # Esta linha de redirect resolve o erro TypeError
    return redirect(url_for("perifericos.listar_estoque"))

@bp.get("/estoque/exportar")
@login_required
def exportar_estoque():
    regs = repo.listar(caminho_estoque_arquivo())
    campos = [
        ('PRODUTO', 'produto'), ('QTD ESTOQUE', 'qtd_estoque'),
        ('COD TOTVS', 'cod_totvs'), ('ONDE COMPRAR', 'onde_comprar')
    ]
    buf = gerar_xlsx("Estoque de Perifericos", regs, campos)
    return send_file(buf, as_attachment=True, download_name="estoque_perifericos.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@bp.get("/entregas/exportar")
@login_required
def exportar_entregas():
    regs = repo.listar(caminho_entregas_arquivo())
    campos = [
        ('GLPI', 'glpi'), ('DESCRIÇÃO/SOLICITANTE', 'descricao_solicitante'),
        ('EQUIPAMENTO', 'equipamento'), ('QTD', 'qtd'), ('OBSERVAÇÃO', 'observacao')
    ]
    buf = gerar_xlsx("Entregas de Perifericos", regs, campos)
    return send_file(buf, as_attachment=True, download_name="entregas_perifericos.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")