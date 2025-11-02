"""Metrics calculation functions for evaluation."""
from typing import List
from .models import QuestionAnswerDocument


def calculate_hit_rate(qa_documents: List[QuestionAnswerDocument]) -> float:
    """
    Calculate hit rate: percentage of queries where ground truth document was retrieved.
    
    Args:
        qa_documents: List of Q&A documents with retrieval results
        
    Returns:
        Hit rate as a float between 0 and 1
    """
    if not qa_documents:
        return 0.0
    
    hits = sum(1 for qa in qa_documents if qa.hit)
    return hits / len(qa_documents)


def calculate_hit_rate_at_k(qa_documents: List[QuestionAnswerDocument], k: int) -> float:
    """
    Calculate hit rate at k: percentage of queries where ground truth was in top k results.
    
    Args:
        qa_documents: List of Q&A documents with retrieval results
        k: Consider only top k results
        
    Returns:
        Hit rate at k as a float between 0 and 1
    """
    if not qa_documents:
        return 0.0
    
    hits = sum(1 for qa in qa_documents if qa.hit and qa.rank is not None and qa.rank <= k)
    return hits / len(qa_documents)


def calculate_mrr(qa_documents: List[QuestionAnswerDocument]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR).
    
    Args:
        qa_documents: List of Q&A documents with retrieval results
        
    Returns:
        MRR score as a float between 0 and 1
    """
    if not qa_documents:
        return 0.0
    
    reciprocal_ranks = []
    for qa in qa_documents:
        if qa.hit and qa.rank is not None:
            reciprocal_ranks.append(1.0 / qa.rank)
        else:
            reciprocal_ranks.append(0.0)
    
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def calculate_all_metrics(qa_documents: List[QuestionAnswerDocument], k_values: List[int] = None) -> dict:
    """
    Calculate all available metrics.
    
    Args:
        qa_documents: List of Q&A documents with retrieval results
        k_values: List of k values to calculate hit_rate@k for (default: [1, 3, 5, 10])
        
    Returns:
        Dictionary with all metrics
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]
    
    metrics = {
        "hit_rate": calculate_hit_rate(qa_documents),
        "mrr": calculate_mrr(qa_documents),
        "total_questions": len(qa_documents),
        "total_hits": sum(1 for qa in qa_documents if qa.hit)
    }
    
    # Add hit_rate@k for each k value
    for k in k_values:
        metrics[f"hit_rate@{k}"] = calculate_hit_rate_at_k(qa_documents, k)
    
    return metrics

