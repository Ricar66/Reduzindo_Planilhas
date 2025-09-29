from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from pathlib import Path
from flask_login import UserMixin
import json

bp = Blueprint("auth", __name__, template_folder="../templates")

class Usuario(UserMixin):
    def __init__(self, id, login, nome, papel):
        self.id = id
        self.login = login
        self.nome = nome
        self.papel = papel  # Esse é o atributo que será usado como 'role' para o Flask-Login

    @property
    def role(self):
        return self.papel  # O atributo papel se torna o role esperado pelo Flask-Login

    @staticmethod
    def _path(base):
        return Path(base) / "usuarios.json"

    @staticmethod
    def _seed_if_missing(base):
        p = Usuario._path(base)
        if not p.exists() or not p.read_text(encoding="utf-8").strip():
            p.parent.mkdir(parents=True, exist_ok=True)
            defaults = [
                {"id": "1", "login": "admin", "senha": "admin123", "nome": "Administrador TI", "papel": "ti"},
                {"id": "2", "login": "leitor", "senha": "leitor123", "nome": "Leitor", "papel": "leitura"}
            ]
            p.write_text(json.dumps(defaults, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def obter_por_id(id, base_dir):
        Usuario._seed_if_missing(base_dir)
        p = Usuario._path(base_dir)
        for u in json.loads(p.read_text(encoding="utf-8")):
            if str(u.get("id")) == str(id):
                return Usuario(u["id"], u["login"], u["nome"], u["papel"])
        return None

    @staticmethod
    def obter_por_login(login, base_dir):
        Usuario._seed_if_missing(base_dir)
        p = Usuario._path(base_dir)
        for u in json.loads(p.read_text(encoding="utf-8")):
            if u.get("login") == login:
                return u  # Retorna o dicionário de dados do usuário
        return None

@bp.get("/login")
def login():
    return render_template("login.html")

@bp.post("/login")
def login_post():
    login = request.form.get("login", "").strip()
    senha = request.form.get("senha", "").strip()
    base = Path(current_app.config["DIRETORIO_DADOS"])
    
    u = Usuario.obter_por_login(login, base)  # Obtém o usuário do arquivo JSON
    if not u or u.get("senha") != senha:
        flash("Credenciais inválidas.", "danger")
        return redirect(url_for("auth.login"))
    
    usuario = Usuario(u["id"], u["login"], u["nome"], u["papel"])  # Atribui o papel ao usuário
    login_user(usuario)  # Usando o objeto Usuario para o login
    flash("Bem-vindo!", "success")
    return redirect(url_for("index"))


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))

# (Opcional) endpoint de emergência para reseed manual
@bp.get("/seed")
def seed():
    base = Path(current_app.config["DIRETORIO_DADOS"])
    Usuario._seed_if_missing(base)
    return "usuarios.json gerado/garantido com sucesso."
