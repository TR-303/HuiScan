from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import db
from .models import *


def create_app(config_class=Config):
    app = Flask(__name__, static_folder=config_class.STATIC_FOLDER, static_url_path=config_class.STATIC_URL_PATH)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    CORS(app)

    # 注册蓝图
    from src.routes.image_controller import image_bp
    from src.routes.batch_controller import batch_bp
    from src.routes.detect_controller import detect_bp
    from src.routes.report_controller import report_bp

    app.register_blueprint(image_bp, url_prefix='/api/image')
    app.register_blueprint(batch_bp, url_prefix='/api/batch')
    app.register_blueprint(detect_bp, url_prefix='/api/detect')
    app.register_blueprint(report_bp, url_prefix='/api/report')

    # 初始化数据库
    with app.app_context():
        db.create_all()

    return app
