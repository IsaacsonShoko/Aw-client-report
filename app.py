from flask import Flask, redirect, url_for
from dotenv import load_dotenv
import logging
import sys
import traceback

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Setup basic logging to stdout so it shows up in Railway
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.ERROR)
    app.logger.addHandler(handler)

    from routes.clients import bp as clients_bp
    from routes.reports import bp as reports_bp
    from routes.exports import bp as exports_bp

    app.register_blueprint(clients_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(exports_bp)

    @app.route('/')
    def index():
        return redirect(url_for('clients.list_clients'))

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the full stack trace to Railway's console
        app.logger.error("Unhandled Exception: %s", str(e))
        app.logger.error(traceback.format_exc())
        return "Internal Server Error (Check Logs)", 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
