"""Reusable UI components and formatters for Gradio interface."""
import pandas as pd
from typing import Dict, Any, List


def format_status_badge(status: str) -> str:
    """Format status as a colored badge."""
    status_colors = {
        "completed": "🟢",
        "running": "🟡",
        "processing": "🟡",
        "pending": "⚪",
        "failed": "🔴",
        "started": "🟡"
    }
    icon = status_colors.get(status.lower(), "⚫")
    return f"{icon} {status.upper()}"


def format_chat_history(session_data: Dict[str, Any]) -> str:
    """Format chat history for display."""
    if "error" in session_data:
        return f"Error: {session_data['error']}"
    
    messages = session_data.get("messages", [])
    
    if not messages:
        return "No messages in this session."
    
    formatted = []
    for msg in messages:
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        
        if role == "USER":
            formatted.append(f"👤 **USER** ({timestamp}):\n{content}\n")
        elif role == "ASSISTANT":
            formatted.append(f"🤖 **ASSISTANT** ({timestamp}):\n{content}\n")
        else:
            formatted.append(f"**{role}** ({timestamp}):\n{content}\n")
    
    return "\n".join(formatted)


def format_retrieved_documents(results: Dict[str, Any]) -> str:
    """Format retrieved documents for display."""
    if "error" in results:
        return f"Error: {results['error']}"
    
    documents = results.get("documents", [])
    query = results.get("query", "")
    total = results.get("total_retrieved", 0)
    
    if not documents:
        return f"No documents retrieved for query: '{query}'"
    
    formatted = [f"**Query:** {query}\n**Total Retrieved:** {total}\n"]
    
    for i, doc in enumerate(documents, 1):
        text = doc.get("text", "")[:300]  # Truncate to 300 chars
        source = doc.get("source", "Unknown")
        score = doc.get("score")
        
        formatted.append(f"\n---\n**Result {i}:**")
        formatted.append(f"**Source:** {source}")
        if score is not None:
            formatted.append(f"**Score:** {score:.4f}")
        formatted.append(f"**Text:** {text}...")
    
    return "\n".join(formatted)


def format_ingestion_status(status_data: Dict[str, Any]) -> str:
    """Format ingestion job status for display."""
    if "error" in status_data:
        return f"Error: {status_data['error']}"
    
    job_id = status_data.get("job_id", "Unknown")
    status = status_data.get("status", "unknown")
    progress = status_data.get("progress_percentage", 0)
    total = status_data.get("total_documents", 0)
    processed = status_data.get("processed_documents", 0)
    successful = status_data.get("successful_documents", 0)
    failed = status_data.get("failed_documents", 0)
    current_file = status_data.get("current_file", "")
    time_remaining = status_data.get("estimated_time_remaining_seconds")
    
    lines = [
        f"**Job ID:** {job_id}",
        f"**Status:** {format_status_badge(status)}",
        f"**Progress:** {progress:.1f}%",
        f"**Documents:** {processed}/{total}",
        f"**Successful:** {successful}",
        f"**Failed:** {failed}"
    ]
    
    if current_file:
        lines.append(f"**Current File:** {current_file}")
    
    if time_remaining is not None and time_remaining > 0:
        mins = int(time_remaining // 60)
        secs = int(time_remaining % 60)
        lines.append(f"**Time Remaining:** {mins}m {secs}s")
    
    return "\n".join(lines)


def format_jobs_list(jobs_data: Dict[str, Any]) -> pd.DataFrame:
    """Format active jobs list as DataFrame."""
    if "error" in jobs_data:
        return pd.DataFrame([{"Error": jobs_data["error"]}])
    
    jobs = jobs_data.get("active_jobs", [])
    
    if not jobs:
        return pd.DataFrame([{"Message": "No active jobs"}])
    
    # Convert to DataFrame
    df_data = []
    for job in jobs:
        df_data.append({
            "Job ID": job.get("job_id", "")[:20] + "...",  # Truncate
            "Status": format_status_badge(job.get("status", "unknown")),
            "Progress": f"{job.get('progress_percentage', 0):.1f}%",
            "Updated": job.get("updated_at", "")
        })
    
    return pd.DataFrame(df_data)


def format_evaluation_results(eval_data: Dict[str, Any]) -> str:
    """Format evaluation results for display."""
    if "error" in eval_data:
        return f"Error: {eval_data['error']}"
    
    eval_id = eval_data.get("evaluation_id", "Unknown")
    status = eval_data.get("status", "unknown")
    folder = eval_data.get("folder_path", "")
    num_docs = eval_data.get("num_documents_processed", 0)
    
    lines = [
        f"# Evaluation Results",
        f"\n**Evaluation ID:** {eval_id}",
        f"**Status:** {format_status_badge(status)}",
        f"**Folder:** {folder}",
        f"**Documents Processed:** {num_docs}"
    ]
    
    # Retrieval parameters
    params = eval_data.get("retrieve_params", {})
    if params:
        lines.append("\n## Configuration")
        lines.append(f"- Top-K: {params.get('top_k', 'N/A')}")
        lines.append(f"- Query Enhancer: {params.get('use_query_enhancer', False)}")
        lines.append(f"- Reranking: {params.get('use_reranking', False)}")
    
    # Results summary
    results = eval_data.get("results_summary")
    if results:
        lines.append("\n## Metrics")
        lines.append(f"- **Hit Rate:** {results.get('hit_rate', 0):.4f}")
        lines.append(f"- **MRR (Mean Reciprocal Rank):** {results.get('mrr', 0):.4f}")
        lines.append(f"- **Average Score:** {results.get('average_score', 0):.4f}")
        lines.append(f"- **Total Questions:** {results.get('total_questions', 0)}")
    
    # Related evaluations
    related = eval_data.get("related_evaluation_ids", [])
    if related:
        lines.append(f"\n## Related Evaluations")
        lines.append(f"This evaluation shares questions with {len(related)} other evaluation(s):")
        for rel_id in related[:5]:  # Show first 5
            lines.append(f"- {rel_id}")
    
    # Error message
    error = eval_data.get("error_message")
    if error:
        lines.append(f"\n**Error:** {error}")
    
    return "\n".join(lines)


def format_evaluations_comparison_table(evaluations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format multiple evaluations as comparison table."""
    if not evaluations:
        return pd.DataFrame([{"Message": "No evaluations found"}])
    
    df_data = []
    for eval_data in evaluations:
        results = eval_data.get("results_summary", {})
        params = eval_data.get("retrieve_params", {})
        
        df_data.append({
            "ID": eval_data.get("evaluation_id", "")[:15] + "...",
            "Status": format_status_badge(eval_data.get("status", "unknown")),
            "Top-K": params.get("top_k", "N/A"),
            "Query Enh.": "✓" if params.get("use_query_enhancer") else "✗",
            "Reranking": "✓" if params.get("use_reranking") else "✗",
            "Hit Rate": f"{results.get('hit_rate', 0):.4f}" if results else "N/A",
            "MRR": f"{results.get('mrr', 0):.4f}" if results else "N/A",
            "Docs": eval_data.get("num_documents_processed", 0)
        })
    
    return pd.DataFrame(df_data)


def format_assets_tree(assets_data: Dict[str, Any]) -> str:
    """Format assets directory tree."""
    if "error" in assets_data:
        return f"Error: {assets_data['error']}"
    
    current_path = assets_data.get("current_path", ".")
    folders = assets_data.get("folders", [])
    files = assets_data.get("files", [])
    
    lines = [f"**Current Path:** assets/{current_path}\n"]
    
    if folders:
        lines.append("**Folders:**")
        for folder in folders:
            name = folder.get("name", "")
            count = folder.get("file_count", 0)
            lines.append(f"📁 {name} ({count} files)")
    
    if files:
        lines.append(f"\n**Files:** (showing first {len(files)})")
        for file in files[:20]:  # Limit display
            name = file.get("name", "")
            size = file.get("size_bytes", 0)
            size_kb = size / 1024
            lines.append(f"📄 {name} ({size_kb:.1f} KB)")
    
    return "\n".join(lines)

