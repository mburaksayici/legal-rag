
from .config import db_path

from pymilvus import MilvusClient


client = MilvusClient(db_path)


