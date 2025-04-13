from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db
from .models import *


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    CORS(app)

    # 注册蓝图
    from .routes.image_import import import_bp
    from .routes.defect_recognition import defect_bp
    from .routes.data_query import query_bp
    from .routes.data_inspect import inspect_bp

    app.register_blueprint(import_bp, url_prefix='/api/import')
    app.register_blueprint(defect_bp, url_prefix='/api/detect')
    app.register_blueprint(query_bp, url_prefix='/api/query')
    app.register_blueprint(inspect_bp, url_prefix='/api/inspect')

    # 初始化数据库
    with app.app_context():
        db.create_all()

    return app