from __future__ import annotations
from flask import Flask, render_template, url_for
from flask_login import LoginManager, login_required
from pathlib import Path
from collections import Counter
from .helpers import armazenamento_json as repo

def criar_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "troque-esta-chave-em-producao"

    # Diretório de dados (JSONs)
    base = Path(__file__).resolve().parent.parent
    dados_dir = base / "dados"
    dados_dir.mkdir(parents=True, exist_ok=True)
    app.config["DIRETORIO_DADOS"] = str(dados_dir)

    # Configuração do Login
    from .blueprints.auth import Usuario
    lm = LoginManager(app)
    lm.login_view = "auth.login"

    @lm.user_loader
    def load_user(uid):
        return Usuario.obter_por_id(uid, base_dir=dados_dir)

    # Importa e registra os blueprints DENTRO da função
    from .blueprints import licencas, vpn, equipamentos, cameras, impressoras, auth, perifericos
    from .blueprints.ferias import bp as ferias_bp

    app.register_blueprint(auth.bp, url_prefix="/auth")
    app.register_blueprint(licencas.bp, url_prefix="/licencas")
    app.register_blueprint(vpn.bp, url_prefix="/vpn")
    app.register_blueprint(equipamentos.bp, url_prefix="/equipamentos")
    app.register_blueprint(cameras.bp, url_prefix="/cameras")
    app.register_blueprint(impressoras.bp, url_prefix="/impressoras")
    app.register_blueprint(perifericos.bp, url_prefix="/perifericos")
    app.register_blueprint(ferias_bp, url_prefix="/ferias")


    # --- A ROTA PRINCIPAL PRECISA ESTAR DENTRO DE CRIAR_APP ---
    @app.route("/")
    @login_required
    def index():
        dados_dir = Path(app.config["DIRETORIO_DADOS"])
        
        # Carregando todos os dados necessários
        lic = repo.listar(dados_dir / "licencas.json")
        vpn = repo.listar(dados_dir / "vpn.json")
        eqp = repo.listar(dados_dir / "equipamentos.json")
        entregas = repo.listar(dados_dir / "perifericos_entregas.json")
        estoque = repo.listar(dados_dir / "perifericos_estoque.json")
    
        # KPIs de Estoque
        total_perifericos_estoque = sum(int(item.get('qtd_estoque', 0)) for item in estoque)
        itens_estoque_baixo = len([item for item in estoque if 0 < int(item.get('qtd_estoque', 0)) <= 5])
        
        # Dados para Gráficos
        lic_ativas = [r for r in lic if r.get("situacao","ATIVO") != "INATIVO"]
        contador_lic = Counter([r.get("licenca","") for r in lic_ativas])
        top_licencas = contador_lic.most_common(5)
        licencas_chart_data = {"labels": [i[0] for i in top_licencas], "data": [i[1] for i in top_licencas]}
        
        contador_equip = Counter([r.get("filial","Sem Filial") for r in eqp])
        top_filiais = contador_equip.most_common(10)
        equip_chart_data = {"labels": [i[0] for i in top_filiais], "data": [i[1] for i in top_filiais]}
    
        kpis = {
            "vpn_pendentes": sum(1 for r in vpn if r.get("status","").upper() in ("PENDENTE","AGUARDANDO","")),
            "lic_inativos": sum(1 for r in lic if r.get("situacao","").upper()=="INATIVO"),
            "total_equipamentos": len(eqp),
            "total_licencas": len(lic_ativas),
            "ultimas_entregas": sorted(entregas, key=lambda x: x.get('id', ''), reverse=True)[:5],
            
            # Garante que os novos KPIs estejam sendo enviados
            "total_perifericos_estoque": total_perifericos_estoque,
            "itens_estoque_baixo": itens_estoque_baixo,
    
            "licencas_chart_data": licencas_chart_data,
            "equip_chart_data": equip_chart_data
        }
        return render_template("index.html", kpis=kpis)

    # O context_processor também deve estar dentro da função
    @app.context_processor
    def _helpers():
        def url_dashboard():
            return url_for("index")
        return {"url_dashboard": url_dashboard}

    # O 'return app' deve ser a última linha da função criar_app
    return app