"""Service layer for evaluation operations."""
from typing import List, Optional, Dict
import logging
from datetime import datetime

from .models import EvaluationDocument, QuestionDocument, EvaluationResultDocument
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
        # Determine question_group_id to use
        question_group_id = None
        reused_questions = False
        
        if request.source_evaluation_id:
            # Reuse questions from existing evaluation
            source_eval = await EvaluationDocument.find_one(
                EvaluationDocument.evaluation_id == request.source_evaluation_id
            )
            if not source_eval:
                raise ValueError(f"Source evaluation not found: {request.source_evaluation_id}")
            
            question_group_id = source_eval.question_group_id
            reused_questions = True
            logger.info(f"Reusing questions from evaluation {request.source_evaluation_id} (group: {question_group_id})")
        
        elif request.question_group_id:
            # Use specified question_group_id
            # Verify it exists
            questions = await QuestionDocument.find(
                QuestionDocument.question_group_id == request.question_group_id
            ).limit(1).to_list()
            
            if not questions:
                raise ValueError(f"No questions found for question_group_id: {request.question_group_id}")
            
            question_group_id = request.question_group_id
            reused_questions = True
            logger.info(f"Reusing questions from question_group_id: {question_group_id}")
        
        # Create evaluation document (question_group_id will be set during evaluation)
        eval_doc = EvaluationDocument(
            question_group_id=question_group_id or "",  # Will be set during evaluation if generating new
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
            await self.evaluator.run_evaluation(eval_doc.evaluation_id, question_group_id)
        except Exception as e:
            logger.error(f"Evaluation {eval_doc.evaluation_id} failed: {str(e)}")
        
        # Reload to get updated question_group_id
        eval_doc = await EvaluationDocument.find_one(
            EvaluationDocument.evaluation_id == eval_doc.evaluation_id
        )
        
        return StartEvaluationResponse(
            evaluation_id=eval_doc.evaluation_id,
            question_group_id=eval_doc.question_group_id,
            status=eval_doc.status,
            message=f"Evaluation started for folder: {request.folder_path}",
            reused_questions=reused_questions
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
        
        # Get related evaluations (same question_group_id)
        related_evaluation_ids = await self._get_related_evaluation_ids(
            eval_doc.question_group_id, 
            exclude_evaluation_id=evaluation_id
        )
        
        return EvaluationStatusResponse(
            evaluation_id=eval_doc.evaluation_id,
            question_group_id=eval_doc.question_group_id,
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
            error_message=eval_doc.error_message,
            related_evaluation_ids=related_evaluation_ids
        )
    
    async def _get_related_evaluation_ids(
        self, 
        question_group_id: str, 
        exclude_evaluation_id: Optional[str] = None
    ) -> List[str]:
        """
        Get all evaluation IDs that share the same question_group_id.
        
        Args:
            question_group_id: The question group ID
            exclude_evaluation_id: Evaluation ID to exclude from results
            
        Returns:
            List of evaluation IDs
        """
        related_evals = await EvaluationDocument.find(
            EvaluationDocument.question_group_id == question_group_id
        ).to_list()
        
        related_ids = [
            eval_doc.evaluation_id 
            for eval_doc in related_evals 
            if eval_doc.evaluation_id != exclude_evaluation_id
        ]
        
        return related_ids
    
    async def list_evaluations(self, limit: int = 50) -> List[EvaluationStatusResponse]:
        """
        List all evaluations.
        
        Args:
            limit: Maximum number of evaluations to return
            
        Returns:
            List of evaluation status responses
        """
        eval_docs = await EvaluationDocument.find_all().sort("-created_at").limit(limit).to_list()
        
        # Build a cache of related evaluations by question_group_id
        related_cache: Dict[str, List[str]] = {}
        
        responses = []
        for doc in eval_docs:
            # Get or cache related evaluation IDs
            if doc.question_group_id not in related_cache:
                related_cache[doc.question_group_id] = await self._get_related_evaluation_ids(
                    doc.question_group_id
                )
            
            # Get related IDs excluding this one
            all_related = related_cache[doc.question_group_id]
            related_ids = [eid for eid in all_related if eid != doc.evaluation_id]
            
            responses.append(
                EvaluationStatusResponse(
                    evaluation_id=doc.evaluation_id,
                    question_group_id=doc.question_group_id,
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
                    error_message=doc.error_message,
                    related_evaluation_ids=related_ids
                )
            )
        
        return responses

