from flask import Flask
from .config import Config
from . import db

def create_app():
    """
    Factory-функция: создаёт и возвращает экземпляр Flask-приложения.
    Внутри:
      - Загружается конфигурация
      - Инициализируется SQLAlchemy (db.init_app)
      - Создаются таблицы (db.create_all)
      - Регистрируется Blueprint, описанный в routes.py
    """
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    # Привязываем SQLAlchemy к приложению
    db.init_app(app)

    # Создаём таблицы, если их нет
    with app.app_context():
        db.create_all()

    # Регистрируем Blueprint
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
