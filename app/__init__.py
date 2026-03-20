#!/usr/bin/env python
from pathlib import Path

from flask import Flask, render_template
import jinja2.exceptions

from app.config import DefaultConfig
from app.proxy.routes import proxy_blueprint
from app.web.routes import web_blueprint


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(config_object: type[DefaultConfig] = DefaultConfig) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )
    app.config.from_object(config_object)

    app.register_blueprint(web_blueprint)
    app.register_blueprint(proxy_blueprint)

    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(jinja2.exceptions.TemplateNotFound)
    def template_not_found(error):  # noqa: ANN001
        return render_template("404.html"), 404

    @app.errorhandler(404)
    def page_not_found(error):  # noqa: ANN001
        return render_template("404.html"), 404
