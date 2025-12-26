import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app
from app.models import db

app = create_app()
with app.app_context():
    db.create_all()
    print('Database initialized successfully!')
