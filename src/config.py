import os
from dotenv import load_dotenv

load_dotenv()
EMBEDDING_WEIGHTS_DIR = os.getenv('EMBEDDING_WEIGHTS_DIR', 'embedding_weights')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
