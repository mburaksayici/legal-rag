
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv('CHROMADB_PATH', './legal_chromadb')

