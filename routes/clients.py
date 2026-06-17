from flask import Blueprint, render_template
import repository

bp = Blueprint('clients', __name__, url_prefix='/clients')

@bp.route('/')
def list_clients():
    clients = repository.get_clients_with_last_report()
    return render_template('client_list.html', clients=clients)
