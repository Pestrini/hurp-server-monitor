import json
import hashlib
import os
import logging

if not os.path.exists("logs"):
    os.makedirs("logs")

auth_logger = logging.getLogger("auth_logger")
auth_logger.setLevel(logging.INFO)
if not auth_logger.handlers:
    fh = logging.FileHandler("logs/auth.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    auth_logger.addHandler(fh)

USERS_FILE = "users.json"

def get_password_hash(password: str) -> str:
    """Gera um hash SHA-256 da senha."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def ensure_users_file():
    """Garante que o arquivo de usuários exista, criando o admin padrão se necessário."""
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "name": "Administrador",
                "password_hash": get_password_hash("admin"),
                "role": "admin"
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, indent=4)
        auth_logger.info("Arquivo users.json não existia. Usuário padrão 'admin' criado.")

def load_users():
    """Carrega os usuários do arquivo."""
    ensure_users_file()
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users_data):
    """Salva o dicionário de usuários no arquivo."""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=4)

def authenticate(username, password):
    """
    Verifica se o usuário e senha são válidos.
    Retorna o dict do usuário (sem hash) se for válido, ou None se for inválido.
    """
    users = load_users()
    if username in users:
        if users[username]['password_hash'] == get_password_hash(password):
            return {
                "role": users[username]['role'],
                "name": users[username].get('name', username)
            }
    return None

def add_user(username, password, role, name, action_by):
    """Adiciona um novo usuário (ou sobrescreve)."""
    users = load_users()
    users[username] = {
        "name": name,
        "password_hash": get_password_hash(password),
        "role": role
    }
    save_users(users)
    auth_logger.info(f"Usuário '{username}' ({name}) criado por '{action_by}'.")
    return True

def update_user_info(username, role, name, action_by, new_password=None):
    """Atualiza dados do usuário. Pode alterar a senha (usado por admins)."""
    users = load_users()
    if username in users:
        users[username]["name"] = name
        users[username]["role"] = role
        if new_password:
            users[username]["password_hash"] = get_password_hash(new_password)
        save_users(users)
        auth_logger.info(f"Usuário '{username}' ({name}) editado por '{action_by}'.")
        return True
    return False

def delete_user(username, action_by):
    """Remove um usuário."""
    users = load_users()
    if username in users:
        del users[username]
        save_users(users)
        auth_logger.info(f"Usuário '{username}' excluído por '{action_by}'.")
        return True
    return False

def get_all_users():
    """Retorna a lista de usuários com seus perfis e nomes (sem as senhas)."""
    users = load_users()
    return {u: {"role": d['role'], "name": d.get('name', u)} for u, d in users.items()}

def change_password(username, old_password, new_password):
    """Altera a própria senha, verificando a antiga."""
    users = load_users()
    if username in users:
        if users[username]['password_hash'] == get_password_hash(old_password):
            users[username]['password_hash'] = get_password_hash(new_password)
            save_users(users)
            auth_logger.info(f"Usuário '{username}' alterou a própria senha.")
            return True
    return False
