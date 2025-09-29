from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

def somente_ti(f):
    """ Decorador para garantir que apenas usuários de TI tenham acesso """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se o usuário tem o papel 'TI'
        if current_user.role != 'ti':  # Aqui estamos verificando o 'role' do current_user
            flash("Você não tem permissão para acessar essa página.", "danger")
            return redirect(url_for('index'))  # Redirecionar para a página inicial ou outra
        return f(*args, **kwargs)
    return decorated_function
