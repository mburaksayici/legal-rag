import json
import os
import sqlite3
from typing import List, Dict, Any

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../assets"))
DB_PATH = os.path.join(ASSETS_DIR, "milvus_local.db")


class MilvusInterface:
	def __init__(self, uri: str = "local-sqlite", collection: str = "documents"):
		self.uri = uri
		self.collection = collection
		os.makedirs(ASSETS_DIR, exist_ok=True)
		self._init_db()

	def _init_db(self) -> None:
		conn = sqlite3.connect(DB_PATH)
		try:
			cur = conn.cursor()
			cur.execute(
				"""
				CREATE TABLE IF NOT EXISTS collections (
					name TEXT PRIMARY KEY,
					dim INTEGER NOT NULL
				)
				"""
			)
			cur.execute(
				"""
				CREATE TABLE IF NOT EXISTS vectors (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					collection TEXT NOT NULL,
					vector TEXT NOT NULL,
					metadata TEXT NOT NULL
				)
				"""
			)
			conn.commit()
		finally:
			conn.close()

	def ensure_collection(self, dim: int) -> None:
		conn = sqlite3.connect(DB_PATH)
		try:
			cur = conn.cursor()
			cur.execute("SELECT dim FROM collections WHERE name=?", (self.collection,))
			row = cur.fetchone()
			if row is None:
				cur.execute(
					"INSERT INTO collections(name, dim) VALUES (?, ?)",
					(self.collection, int(dim)),
				)
				conn.commit()
		finally:
			conn.close()

	def upsert_embeddings(self, vectors: List[List[float]], metadatas: List[Dict[str, Any]]) -> None:
		if not vectors:
			return
		conn = sqlite3.connect(DB_PATH)
		try:
			cur = conn.cursor()
			for vec, meta in zip(vectors, metadatas):
				cur.execute(
					"INSERT INTO vectors(collection, vector, metadata) VALUES (?, ?, ?)",
					(self.collection, json.dumps(vec), json.dumps(meta)),
				)
			conn.commit()
		finally:
			conn.close()
