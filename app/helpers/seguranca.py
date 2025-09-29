
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

login_manager = LoginManager()
login_manager.login_view = "auth.login"

@dataclass
class Usuario(UserMixin):
    id: str
    nome: str
    papel: str
    senha_hash: str
    def verificar_senha(self, s: str) -> bool: return check_password_hash(self.senha_hash, s)

def _arquivo(app) -> Path:
    return Path(app.config["DIRETORIO_DADOS"]) / "usuarios.json"

def carregar(app) -> dict:
    p = _arquivo(app)
    if not p.exists():
        base = {
            "admin": {"login":"admin","nome":"Administrador TI","papel":"ti","senha_hash": generate_password_hash("admin123")},
            "leitor": {"login":"leitor","nome":"Usuário Leitura","papel":"leitura","senha_hash": generate_password_hash("leitor123")},
        }
        p.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(p.read_text(encoding="utf-8"))

def obter(app, login: str) -> Optional[Usuario]:
    d = carregar(app).get(login)
    if not d: return None
    return Usuario(id=d["login"], nome=d["nome"], papel=d["papel"], senha_hash=d["senha_hash"])

def registrar_login_manager(app):
    login_manager.init_app(app)
    @login_manager.user_loader
    def load(uid: str): return obter(app, uid)
