# run.py

import sys
from pathlib import Path

# Adiciona o diretório raiz do projeto ao caminho do Python
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app import criar_app

app = criar_app()

if __name__ == '__main__':
    app.run(debug=True)