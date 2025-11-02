"""Metrics calculation functions for evaluation."""
from typing import List, Union
from .models import QuestionAnswerDocument, EvaluationResultDocument


# Type alias for result documents
ResultDocument = Union[QuestionAnswerDocument, EvaluationResultDocument]


def calculate_hit_rate(results: List[ResultDocument]) -> float:
    """
    Calculate hit rate: percentage of queries where ground truth document was retrieved.
    
    Args:
        results: List of result documents with retrieval results
        
    Returns:
        Hit rate as a float between 0 and 1
    """
    if not results:
        return 0.0
    
    hits = sum(1 for result in results if result.hit)
    return hits / len(results)


def calculate_hit_rate_at_k(results: List[ResultDocument], k: int) -> float:
    """
    Calculate hit rate at k: percentage of queries where ground truth was in top k results.
    
    Args:
        results: List of result documents with retrieval results
        k: Consider only top k results
        
    Returns:
        Hit rate at k as a float between 0 and 1
    """
    if not results:
        return 0.0
    
    hits = sum(1 for result in results if result.hit and result.rank is not None and result.rank <= k)
    return hits / len(results)


def calculate_mrr(results: List[ResultDocument]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR).
    
    Args:
        results: List of result documents with retrieval results
        
    Returns:
        MRR score as a float between 0 and 1
    """
    if not results:
        return 0.0
    
    reciprocal_ranks = []
    for result in results:
        if result.hit and result.rank is not None:
            reciprocal_ranks.append(1.0 / result.rank)
        else:
            reciprocal_ranks.append(0.0)
    
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def calculate_all_metrics(results: List[ResultDocument], k_values: List[int] = None) -> dict:
    """
    Calculate all available metrics.
    
    Args:
        results: List of result documents with retrieval results
        k_values: List of k values to calculate hit_rate@k for (default: [1, 3, 5, 10])
        
    Returns:
        Dictionary with all metrics
    """
    if k_values is None:
        k_values = [1, 3, 5, 10]
    
    metrics = {
        "hit_rate": calculate_hit_rate(results),
        "mrr": calculate_mrr(results),
        "total_questions": len(results),
        "total_hits": sum(1 for result in results if result.hit)
    }
    
    # Add hit_rate@k for each k value
    for k in k_values:
        metrics[f"hit_rate@{k}"] = calculate_hit_rate_at_k(results, k)
    
    return metrics

