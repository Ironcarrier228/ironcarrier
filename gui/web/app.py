#!/usr/bin/env python3
"""
Flask Web Application
Main web interface for IronCarrier C2
"""

import os
import json
from flask import Flask, render_template, send_from_directory, request, redirect, url_for
from datetime import datetime

from .api import APIBlueprint
from .websocket import WebSocketBlueprint


def create_app(c2_server=None) -> Flask:
    """Flask application factory"""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), 'static'),
    )
    
    app.config['SECRET_KEY'] = os.urandom(32).hex()
    app.config['C2_SERVER'] = c2_server
    
    # Register blueprints
    api_bp = APIBlueprint(c2_server)
    ws_bp = WebSocketBlueprint(c2_server)
    
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(ws_bp, url_prefix='/ws')
    
    # Routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/agents')
    def agents():
        return render_template('agents.html')
    
    @app.route('/attack')
    def attack():
        return render_template('attack.html')
    
    @app.route('/settings')
    def settings():
        return render_template('settings.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500
    
    return app
