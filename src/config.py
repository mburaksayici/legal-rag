import os
from dotenv import load_dotenv

load_dotenv()
EMBEDDING_WEIGHTS_DIR = os.getenv('EMBEDDING_WEIGHTS_DIR', 'embedding_weights')
