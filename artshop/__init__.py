import os
from flask import Flask
from dotenv import load_dotenv


load_dotenv()


def create_flask():
    app = Flask(__name__)
    from .Blue_prints.seller_BPs.seller_views import seller
    from .Blue_prints.user_BPs.user_views import user
    from .Blue_prints.payment_BPs.payment_views import payment

    app.register_blueprint(user)
    app.register_blueprint(payment)
    app.register_blueprint(seller)

    # db = MySQL(app)

    app.config.from_envvar('APP_CONFIG')
    app.config["MAIL_PASSWORD"] = os.getenv('MAIL_PASSWORD')
    app.config["MYSQL_PASSWORD"] = os.getenv('MYSQL_PASSWORD')

    return app
