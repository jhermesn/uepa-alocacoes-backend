import os
import sys

# Adiciona o diretório raiz ao path para importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.try_database import Base, engine
from app.models import *  # Garante que todos os modelos sejam carregados

def create_tables():
    print("Sincronizando schema do banco de dados via SQLAlchemy...")
    Base.metadata.create_all(bind=engine)
    print("Schema sincronizado com sucesso.")

if __name__ == "__main__":
    create_tables()
