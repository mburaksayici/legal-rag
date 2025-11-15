"""API client wrapper for communicating with FastAPI backend."""
import os
import requests
from typing import Optional, Dict, Any, List

# Get API base URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIClient:
    """Client for interacting with FastAPI backend."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response and errors."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                error_detail = error_data.get("detail", str(e))
            except:
                error_detail = str(e)
            raise Exception(f"API Error: {error_detail}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    # ===== CHAT ENDPOINTS =====
    
    def send_chat_message(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a chat message."""
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={
                    "message": message,
                    "session_id": session_id,
                    "metadata": {}
                },
                timeout=60
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session by ID."""
        try:
            response = requests.get(
                f"{self.base_url}/sessions/{session_id}",
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def list_sessions(self, limit: int = 100) -> Dict[str, Any]:
        """List all sessions."""
        try:
            response = requests.get(
                f"{self.base_url}/sessions",
                params={"limit": limit},
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e), "sessions": [], "total": 0}
    
    # ===== RETRIEVAL ENDPOINTS =====
    
    def retrieve_documents(
        self,
        query: str,
        top_k: int = 10,
        use_query_enhancer: bool = False,
        use_reranking: bool = False,
        pipeline_type: str = "recursive_overlap"
    ) -> Dict[str, Any]:
        """Retrieve documents from vector database."""
        try:
            response = requests.post(
                f"{self.base_url}/retrieve",
                json={
                    "query": query,
                    "top_k": top_k,
                    "use_query_enhancer": use_query_enhancer,
                    "use_reranking": use_reranking,
                    "pipeline_type": pipeline_type
                },
                timeout=60
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    # ===== INGESTION ENDPOINTS =====
    
    def start_ingestion_job(
        self,
        folder_path: str,
        file_types: List[str] = None,
        pipeline_type: str = "recursive_overlap"
    ) -> Dict[str, Any]:
        """Start a folder ingestion job."""
        try:
            if file_types is None:
                file_types = ["pdf", "json"]
            
            response = requests.post(
                f"{self.base_url}/ingestion/start_job",
                json={
                    "folder_path": folder_path,
                    "file_types": file_types,
                    "pipeline_type": pipeline_type
                },
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def get_ingestion_status(self, job_id: str) -> Dict[str, Any]:
        """Get ingestion job status."""
        try:
            response = requests.get(
                f"{self.base_url}/ingestion/status/{job_id}",
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def list_ingestion_jobs(self) -> Dict[str, Any]:
        """List all active ingestion jobs."""
        try:
            response = requests.get(
                f"{self.base_url}/ingestion/jobs",
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e), "active_jobs": []}
    
    # ===== EVALUATION ENDPOINTS =====
    
    def start_evaluation(
        self,
        folder_path: str,
        top_k: int = 10,
        use_query_enhancer: bool = False,
        use_reranking: bool = False,
        num_questions_per_doc: int = 1,
        source_evaluation_id: Optional[str] = None,
        question_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start an evaluation job."""
        try:
            payload = {
                "folder_path": folder_path,
                "top_k": top_k,
                "use_query_enhancer": use_query_enhancer,
                "use_reranking": use_reranking,
                "num_questions_per_doc": num_questions_per_doc
            }
            
            if source_evaluation_id:
                payload["source_evaluation_id"] = source_evaluation_id
            if question_group_id:
                payload["question_group_id"] = question_group_id
            
            response = requests.post(
                f"{self.base_url}/evaluation/start",
                json=payload,
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def get_evaluation_status(self, evaluation_id: str) -> Dict[str, Any]:
        """Get evaluation status and results."""
        try:
            response = requests.get(
                f"{self.base_url}/evaluation/{evaluation_id}",
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e)}
    
    def list_evaluations(self, limit: int = 50) -> Dict[str, Any]:
        """List all evaluations."""
        try:
            response = requests.get(
                f"{self.base_url}/evaluations",
                params={"limit": limit},
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e), "evaluations": [], "total": 0}
    
    # ===== ASSETS ENDPOINTS =====
    
    def list_assets(self, path: Optional[str] = None) -> Dict[str, Any]:
        """List assets folders and files."""
        try:
            params = {"path": path} if path else {}
            response = requests.get(
                f"{self.base_url}/assets/list",
                params=params,
                timeout=10
            )
            return self._handle_response(response)
        except Exception as e:
            return {"error": str(e), "folders": [], "files": []}


# Global API client instance
api_client = APIClient()

