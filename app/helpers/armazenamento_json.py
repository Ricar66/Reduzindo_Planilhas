from __future__ import annotations
from pathlib import Path
import json, uuid, copy

def _ler(path: Path) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    try:
        return json.loads(path.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

def _gravar(path: Path, lista: list[dict]) -> None:
    path.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")

def listar(path: Path) -> list[dict]:
    return _ler(path)

def criar(path: Path, dados: dict) -> dict:
    lista = _ler(path)
    item = copy.deepcopy(dados)
    item["id"] = item.get("id") or str(uuid.uuid4())
    lista.append(item)
    _gravar(path, lista)
    return item

def atualizar(path: Path, id: str, dados: dict) -> bool:
    lista = _ler(path)
    ok = False
    for i, it in enumerate(lista):
        if it.get("id") == id:
            novo = copy.deepcopy(dados)
            novo["id"] = id
            lista[i] = novo
            ok = True
            break
    if ok: _gravar(path, lista)
    return ok

def excluir(path: Path, id: str) -> bool:
    lista = _ler(path); size = len(lista)
    lista = [it for it in lista if it.get("id") != id]
    _gravar(path, lista)
    return len(lista) != size

def obter_por_id(path: Path, id: str) -> dict | None:
    for it in _ler(path):
        if it.get("id") == id: return it
    return None
