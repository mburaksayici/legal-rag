"""Service layer for evaluation operations."""
from typing import List, Optional
import logging
from datetime import datetime

from .models import EvaluationDocument, QuestionAnswerDocument
from .schemas import StartEvaluationRequest, StartEvaluationResponse, EvaluationStatusResponse
from .evaluator import Evaluator
from src.embeddings.base import BaseEmbedding

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for managing evaluations."""
    
    def __init__(self, embedding: BaseEmbedding):
        """
        Initialize evaluation service.
        
        Args:
            embedding: Embedding model for retrieval
        """
        self.evaluator = Evaluator(embedding=embedding)
    
    async def start_evaluation(self, request: StartEvaluationRequest) -> StartEvaluationResponse:
        """
        Start a new evaluation.
        
        Args:
            request: Evaluation configuration
            
        Returns:
            Response with evaluation_id and status
        """
        # Create evaluation document
        eval_doc = EvaluationDocument(
            folder_path=request.folder_path,
            top_k=request.top_k,
            use_query_enhancer=request.use_query_enhancer,
            use_reranking=request.use_reranking,
            num_questions_per_doc=request.num_questions_per_doc,
            status="pending"
        )
        
        await eval_doc.insert()
        
        logger.info(f"Created evaluation {eval_doc.evaluation_id}")
        
        # Run evaluation asynchronously (in real production, use Celery)
        # For now, we'll run it directly but could be moved to background task
        try:
            await self.evaluator.run_evaluation(eval_doc.evaluation_id)
        except Exception as e:
            logger.error(f"Evaluation {eval_doc.evaluation_id} failed: {str(e)}")
        
        return StartEvaluationResponse(
            evaluation_id=eval_doc.evaluation_id,
            status=eval_doc.status,
            message=f"Evaluation started for folder: {request.folder_path}"
        )
    
    async def get_evaluation_status(self, evaluation_id: str) -> Optional[EvaluationStatusResponse]:
        """
        Get status and results of an evaluation.
        
        Args:
            evaluation_id: The evaluation ID
            
        Returns:
            Evaluation status response or None if not found
        """
        eval_doc = await EvaluationDocument.find_one(
            EvaluationDocument.evaluation_id == evaluation_id
        )
        
        if not eval_doc:
            return None
        
        return EvaluationStatusResponse(
            evaluation_id=eval_doc.evaluation_id,
            status=eval_doc.status,
            folder_path=eval_doc.folder_path,
            retrieve_params={
                "top_k": eval_doc.top_k,
                "use_query_enhancer": eval_doc.use_query_enhancer,
                "use_reranking": eval_doc.use_reranking
            },
            num_documents_processed=eval_doc.num_documents_processed,
            created_at=eval_doc.created_at,
            completed_at=eval_doc.completed_at,
            results_summary=eval_doc.results_summary,
            error_message=eval_doc.error_message
        )
    
    async def list_evaluations(self, limit: int = 50) -> List[EvaluationStatusResponse]:
        """
        List all evaluations.
        
        Args:
            limit: Maximum number of evaluations to return
            
        Returns:
            List of evaluation status responses
        """
        eval_docs = await EvaluationDocument.find_all().sort("-created_at").limit(limit).to_list()
        
        return [
            EvaluationStatusResponse(
                evaluation_id=doc.evaluation_id,
                status=doc.status,
                folder_path=doc.folder_path,
                retrieve_params={
                    "top_k": doc.top_k,
                    "use_query_enhancer": doc.use_query_enhancer,
                    "use_reranking": doc.use_reranking
                },
                num_documents_processed=doc.num_documents_processed,
                created_at=doc.created_at,
                completed_at=doc.completed_at,
                results_summary=doc.results_summary,
                error_message=doc.error_message
            )
            for doc in eval_docs
        ]

