"""Main evaluation orchestration logic."""
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from src.embeddings.base import BaseEmbedding
from src.agents.retrieval_agent.agent import RetrievalAgent
from src.data_preprocess_pipelines.simple_pdf_preprocess import SimplePDFPreprocess
from .question_generator_agent import QuestionGeneratorAgent
from .models import EvaluationDocument, QuestionAnswerDocument
from .metrics import calculate_all_metrics

logger = logging.getLogger(__name__)


class Evaluator:
    """Main evaluator class that orchestrates the evaluation process."""
    
    def __init__(self, embedding: BaseEmbedding):
        """
        Initialize evaluator with required components.
        
        Args:
            embedding: Embedding model for retrieval
        """
        self.embedding = embedding
        self.retrieval_agent = RetrievalAgent(embedding=embedding)
        self.pdf_processor = SimplePDFPreprocess()
        self.question_generator = QuestionGeneratorAgent()
    
    def generate_questions_from_folder(
        self,
        folder_path: str,
        num_per_doc: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate questions from all PDFs in a folder.
        
        Args:
            folder_path: Path to folder containing PDFs
            num_per_doc: Number of questions to generate per document
            
        Returns:
            List of dicts with keys: question, ground_truth_text, source_path
        """
        folder = Path(folder_path)
        
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        # Find all PDF files
        pdf_files = list(folder.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files in {folder_path}")
        
        all_questions = []
        
        for pdf_file in pdf_files:
            try:
                # Extract text from PDF
                result = self.pdf_processor.run_single_doc(str(pdf_file))
                
                if not result["success"]:
                    logger.warning(f"Failed to extract text from {pdf_file}: {result.get('error')}")
                    continue
                
                document_text = result["text"]
                
                # Generate questions
                question_outputs = self.question_generator.generate_multiple_questions(
                    document_text=document_text,
                    source_path=str(pdf_file),
                    num_questions=num_per_doc
                )
                
                # Convert to dict format
                for qo in question_outputs:
                    all_questions.append({
                        "question": qo.question,
                        "ground_truth_text": qo.fact,
                        "source_path": str(pdf_file)
                    })
                
                logger.info(f"Generated {len(question_outputs)} questions from {pdf_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {str(e)}")
                continue
        
        logger.info(f"Total questions generated: {len(all_questions)}")
        return all_questions
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a file path for comparison.
        Converts to absolute path and resolves any symlinks.
        
        Args:
            path: File path to normalize
            
        Returns:
            Normalized absolute path
        """
        try:
            p = Path(path)
            # If path exists, resolve it
            if p.exists():
                return str(p.resolve())
            # Otherwise, just convert to absolute and normalize
            return str(p.absolute())
        except Exception:
            # Fallback: just use the string as-is
            return str(path)
    
    def _check_hit_and_rank(self, source_path: str, retrieved_paths: List[str]) -> tuple[bool, Optional[int]]:
        """
        Check if source document was retrieved and at what rank.
        Uses filename-based matching to handle path differences.
        
        Args:
            source_path: Ground truth source path
            retrieved_paths: List of retrieved document paths
            
        Returns:
            Tuple of (hit: bool, rank: Optional[int])
        """
        # Get the filename from source
        source_filename = Path(source_path).name
        
        # Check each retrieved path
        for i, retrieved_path in enumerate(retrieved_paths, 1):
            retrieved_filename = Path(retrieved_path).name
            
            # Match by filename (more robust than full path)
            if source_filename == retrieved_filename:
                return True, i
        
        return False, None
    
    def run_retrieval(
        self,
        question: str,
        top_k: int = 10,
        use_query_enhancer: bool = False,
        use_reranking: bool = False
    ) -> List[str]:
        """
        Run retrieval for a question and return list of source document paths.
        
        Args:
            question: The query question
            top_k: Number of documents to retrieve
            use_query_enhancer: Enable query enhancement
            use_reranking: Enable reranking
            
        Returns:
            List of source document paths from retrieved results
        """
        try:
            results = self.retrieval_agent.retrieve(
                question=question,
                use_query_enhancer=use_query_enhancer,
                use_reranking=use_reranking,
                top_k=top_k
            )
            
            # Extract source paths
            source_paths = [doc["source"] for doc in results if "source" in doc]
            return source_paths
            
        except Exception as e:
            logger.error(f"Retrieval failed for question '{question}': {str(e)}")
            return []
    
    async def run_evaluation(self, evaluation_id: str) -> Dict[str, Any]:
        """
        Run full evaluation workflow for a given evaluation ID.
        
        Args:
            evaluation_id: The evaluation ID from EvaluationDocument
            
        Returns:
            Dictionary with evaluation results
        """
        # Get evaluation configuration
        eval_doc = await EvaluationDocument.find_one(
            EvaluationDocument.evaluation_id == evaluation_id
        )
        
        if not eval_doc:
            raise ValueError(f"Evaluation not found: {evaluation_id}")
        
        try:
            # Update status to running
            eval_doc.status = "running"
            await eval_doc.save()
            
            # Step 1: Generate questions
            logger.info(f"Generating questions from {eval_doc.folder_path}")
            questions_data = self.generate_questions_from_folder(
                folder_path=eval_doc.folder_path,
                num_per_doc=eval_doc.num_questions_per_doc
            )
            
            eval_doc.num_documents_processed = len(questions_data)
            await eval_doc.save()
            
            if not questions_data:
                raise ValueError("No questions generated from folder")
            
            # Step 2: Run retrieval for each question and store results
            logger.info(f"Running retrieval for {len(questions_data)} questions")
            qa_documents = []
            
            for i, q_data in enumerate(questions_data, 1):
                logger.info(f"Processing question {i}/{len(questions_data)}")
                
                # Run retrieval
                retrieved_paths = self.run_retrieval(
                    question=q_data["question"],
                    top_k=eval_doc.top_k,
                    use_query_enhancer=eval_doc.use_query_enhancer,
                    use_reranking=eval_doc.use_reranking
                )
                
                # Check if ground truth was retrieved
                source_path = q_data["source_path"]
                hit, rank = self._check_hit_and_rank(source_path, retrieved_paths)
                
                logger.info(f"Question {i}: hit={hit}, rank={rank}, source={Path(source_path).name}")
                
                # Create and save Q&A document
                qa_doc = QuestionAnswerDocument(
                    evaluation_id=evaluation_id,
                    question=q_data["question"],
                    ground_truth_text=q_data["ground_truth_text"],
                    source_document_path=source_path,
                    retrieved_documents=retrieved_paths,
                    hit=hit,
                    rank=rank
                )
                
                await qa_doc.insert()
                qa_documents.append(qa_doc)
            
            # Step 3: Calculate metrics
            logger.info("Calculating metrics")
            metrics = calculate_all_metrics(qa_documents)
            
            # Update evaluation document with results
            eval_doc.status = "completed"
            eval_doc.completed_at = datetime.utcnow()
            eval_doc.results_summary = metrics
            await eval_doc.save()
            
            logger.info(f"Evaluation {evaluation_id} completed successfully")
            return metrics
            
        except Exception as e:
            logger.error(f"Evaluation {evaluation_id} failed: {str(e)}")
            eval_doc.status = "failed"
            eval_doc.error_message = str(e)
            eval_doc.completed_at = datetime.utcnow()
            await eval_doc.save()
            raise

