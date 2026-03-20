#!/usr/bin/env python
from flask import Blueprint, render_template


web_blueprint = Blueprint("web", __name__)


@web_blueprint.get("/")
def index():
    return render_template("index.html")


@web_blueprint.get("/<pagename>")
def page(pagename: str):
    return render_template(f"{pagename}.html")
