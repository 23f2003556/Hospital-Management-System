import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    
    # Use Vercel DATABASE_URL if available, otherwise fallback to local SQLite
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///hmdbms.sql'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
