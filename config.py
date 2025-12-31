import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///hmdbms.sql'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
