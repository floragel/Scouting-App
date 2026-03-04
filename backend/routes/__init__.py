"""
Flask Blueprint route modules for the Scouting App.

All blueprints are registered in app.py via register_blueprints().
"""

from .auth import auth_bp
from .admin import admin_bp
from .events import events_bp
from .teams import teams_bp
from .scouting import scouting_bp
from .assignments import assignments_bp
from .analytics import analytics_bp
from .picklist import picklist_bp
from .briefing import briefing_bp
from .pages import pages_bp
from .pwa import pwa_bp

ALL_BLUEPRINTS = [
    auth_bp,
    admin_bp,
    events_bp,
    teams_bp,
    scouting_bp,
    assignments_bp,
    analytics_bp,
    picklist_bp,
    briefing_bp,
    pages_bp,
    pwa_bp,
]


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
