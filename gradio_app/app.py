"""Main Gradio application for SAGA system."""
import gradio as gr
import time
from typing import Optional, Tuple
from api_client import api_client
from components import (
    format_chat_history,
    format_retrieved_documents,
    format_ingestion_status,
    format_jobs_list,
    format_evaluation_results,
    format_evaluations_comparison_table,
    format_assets_tree,
    format_status_badge
)


# ===== CHAT TAB FUNCTIONS =====

def get_sessions_choices():
    """Get sessions as dropdown choices list."""
    try:
        result = api_client.list_sessions()
        sessions = result.get("sessions", [])
        
        if not sessions:
            return []
        
        # Format as (display_name, session_id)
        choices = []
        for session in sessions:
            session_id = session.get("session_id", "")
            first_message = session.get("first_message", "")
            msg_count = session.get("message_count", 0)
            last_activity = session.get("last_activity", "")[:19] if session.get("last_activity") else "N/A"
            
            # Use first message as display if available, otherwise use session ID
            if first_message:
                display = f"{first_message}... ({msg_count} msgs)"
            else:
                display = f"Session {session_id[:8]}... ({msg_count} msgs)"
            
            choices.append((display, session_id))
        
        return choices
    except Exception as e:
        print(f"Error loading sessions: {e}")
        return []

def load_sessions_list():
    """Load list of all sessions for dropdown update."""
    choices = get_sessions_choices()
    return gr.update(choices=choices, value=None)


def load_session_history(session_id):
    """Load chat history for selected session."""
    if not session_id:
        return "Please select a session"
    
    result = api_client.get_session(session_id)
    return format_chat_history(result)


def send_message(message, session_id):
    """Send a chat message."""
    if not message.strip():
        return "Please enter a message", ""
    
    result = api_client.send_chat_message(message, session_id)
    
    if "error" in result:
        return f"Error: {result['error']}", ""
    
    response = result.get("message", "")
    sources = result.get("sources", [])
    new_session_id = result.get("session_id", session_id)
    
    sources_text = "\n\n**Sources:**\n" + "\n".join([f"- {s}" for s in sources]) if sources else ""
    
    return response + sources_text, new_session_id


def refresh_chat_history(session_id):
    """Refresh chat history display."""
    return load_session_history(session_id)


# ===== RETRIEVAL TAB FUNCTIONS =====

def test_retrieval(query, top_k, use_query_enhancer, use_reranking):
    """Test document retrieval."""
    if not query.strip():
        return "Please enter a query"
    
    result = api_client.retrieve_documents(
        query=query,
        top_k=top_k,
        use_query_enhancer=use_query_enhancer,
        use_reranking=use_reranking
    )
    
    return format_retrieved_documents(result)


# ===== INGESTION TAB FUNCTIONS =====

def load_assets_folders():
    """Load list of asset folders."""
    result = api_client.list_assets()
    folders = result.get("folders", [])
    
    if not folders:
        return ["assets/"]
    
    # Return folder paths
    return ["assets/" + f.get("path", f.get("name", "")) for f in folders]


def refresh_assets_folders():
    """Refresh the assets folders dropdown."""
    choices = load_assets_folders()
    return gr.update(choices=choices, value=None)


def start_ingestion(folder_path, pdf_checked, json_checked):
    """Start ingestion job."""
    if not folder_path:
        return "Please select a folder", None
    
    file_types = []
    if pdf_checked:
        file_types.append("pdf")
    if json_checked:
        file_types.append("json")
    
    if not file_types:
        return "Please select at least one file type", None
    
    result = api_client.start_ingestion_job(folder_path, file_types)
    
    if "error" in result:
        return f"Error: {result['error']}", None
    
    job_id = result.get("job_id", "")
    message = result.get("message", "")
    
    return f"{format_status_badge('started')} {message}\n\nJob ID: {job_id}", job_id


def check_ingestion_status(job_id):
    """Check status of ingestion job."""
    if not job_id:
        return "No job ID provided", 0
    
    result = api_client.get_ingestion_status(job_id)
    formatted = format_ingestion_status(result)
    progress = result.get("progress_percentage", 0)
    
    return formatted, progress


def refresh_jobs_list():
    """Refresh active jobs list."""
    result = api_client.list_ingestion_jobs()
    return format_jobs_list(result)


# ===== EVALUATION TAB FUNCTIONS =====

def load_evaluation_folders():
    """Load folders for evaluation."""
    return load_assets_folders()


def refresh_evaluation_folders():
    """Refresh the evaluation folders dropdown."""
    choices = load_evaluation_folders()
    return gr.update(choices=choices, value=None)


def get_evaluations_for_reuse_choices():
    """Get completed evaluations choices list."""
    try:
        result = api_client.list_evaluations(limit=100)
        evaluations = result.get("evaluations", [])
        
        completed = [e for e in evaluations if e.get("status") == "completed"]
        
        if not completed:
            return [("None (generate new questions)", None)]
        
        choices = [("None (generate new questions)", None)]
        for eval_data in completed:
            eval_id = eval_data.get("evaluation_id", "")
            folder = eval_data.get("folder_path", "").split("/")[-1]
            num_docs = eval_data.get("num_documents_processed", 0)
            display = f"{eval_id[:20]}... ({folder}, {num_docs} docs)"
            choices.append((display, eval_id))
        
        return choices
    except Exception as e:
        print(f"Error loading evaluations for reuse: {e}")
        return [("None (generate new questions)", None)]

def load_evaluations_for_reuse():
    """Load completed evaluations for question reuse (for dropdown update)."""
    choices = get_evaluations_for_reuse_choices()
    return gr.update(choices=choices, value=None)


def start_evaluation_job(
    folder_path,
    top_k,
    query_enhancer,
    reranking,
    num_questions,
    source_eval_id
):
    """Start evaluation job."""
    if not folder_path:
        return "Please select a folder"
    
    result = api_client.start_evaluation(
        folder_path=folder_path,
        top_k=top_k,
        use_query_enhancer=query_enhancer,
        use_reranking=reranking,
        num_questions_per_doc=num_questions,
        source_evaluation_id=source_eval_id if source_eval_id else None
    )
    
    if "error" in result:
        return f"Error: {result['error']}"
    
    eval_id = result.get("evaluation_id", "")
    message = result.get("message", "")
    reused = result.get("reused_questions", False)
    
    reused_text = " (Reused questions)" if reused else " (Generated new questions)"
    
    return f"{format_status_badge('started')} {message}{reused_text}\n\nEvaluation ID: {eval_id}"


def get_evaluations_dropdown_choices():
    """Get evaluations choices list."""
    try:
        result = api_client.list_evaluations(limit=50)
        evaluations = result.get("evaluations", [])
        
        if not evaluations:
            return []
        
        choices = []
        for eval_data in evaluations:
            eval_id = eval_data.get("evaluation_id", "")
            status = eval_data.get("status", "unknown")
            folder = eval_data.get("folder_path", "").split("/")[-1]
            display = f"{eval_id[:20]}... ({status}, {folder})"
            choices.append((display, eval_id))
        
        return choices
    except Exception as e:
        print(f"Error loading evaluations: {e}")
        return []

def load_evaluations_dropdown():
    """Load evaluations for dropdown (for dropdown update)."""
    choices = get_evaluations_dropdown_choices()
    return gr.update(choices=choices, value=None)


def load_evaluation_results(eval_id):
    """Load evaluation results."""
    if not eval_id:
        return "Please select an evaluation"
    
    result = api_client.get_evaluation_status(eval_id)
    return format_evaluation_results(result)


def load_evaluations_comparison():
    """Load all evaluations for comparison."""
    result = api_client.list_evaluations(limit=50)
    evaluations = result.get("evaluations", [])
    return format_evaluations_comparison_table(evaluations)


# ===== BUILD GRADIO INTERFACE =====

with gr.Blocks(title="SAGA - Legal Document RAG System", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏛️ SAGA - Legal Document RAG System")
    gr.Markdown("Semantic search and chat interface for legal documents")
    
    with gr.Tabs():
        # ===== TAB 1: CHAT =====
        with gr.Tab("💬 Chat"):
            gr.Markdown("## Chat with your legal documents")
            
            with gr.Row():
                with gr.Column(scale=1):
                    initial_choices = get_sessions_choices()
                    session_dropdown = gr.Dropdown(
                        label="Select Session",
                        choices=initial_choices,
                        value=None,
                        interactive=True,
                        allow_custom_value=False,
                        info="Select a session to view its history" if initial_choices else "No sessions available. Start a new chat below."
                    )
                    refresh_sessions_btn = gr.Button("🔄 Refresh Sessions", size="sm")
                
                with gr.Column(scale=3):
                    chat_history_display = gr.Textbox(
                        label="Conversation History",
                        lines=15,
                        max_lines=20,
                        interactive=False
                    )
            
            with gr.Row():
                message_input = gr.Textbox(
                    label="Your Message",
                    placeholder="Ask a question about legal documents...",
                    lines=3
                )
            
            with gr.Row():
                send_btn = gr.Button("📤 Send Message", variant="primary")
                refresh_history_btn = gr.Button("🔄 Refresh History")
            
            response_output = gr.Textbox(
                label="Assistant Response",
                lines=10,
                interactive=False
            )
            
            current_session_id = gr.State(None)
            
            # Event handlers
            session_dropdown.change(
                fn=load_session_history,
                inputs=[session_dropdown],
                outputs=[chat_history_display]
            ).then(
                fn=lambda x: x,
                inputs=[session_dropdown],
                outputs=[current_session_id]
            )
            
            refresh_sessions_btn.click(
                fn=load_sessions_list,
                inputs=[],
                outputs=[session_dropdown]
            )
            
            send_btn.click(
                fn=send_message,
                inputs=[message_input, current_session_id],
                outputs=[response_output, current_session_id]
            ).then(
                fn=lambda: "",
                inputs=[],
                outputs=[message_input]
            )
            
            refresh_history_btn.click(
                fn=refresh_chat_history,
                inputs=[current_session_id],
                outputs=[chat_history_display]
            )
        
        # ===== TAB 2: RETRIEVAL TESTING =====
        with gr.Tab("🔍 Retrieval Testing"):
            gr.Markdown("## Test document retrieval with different parameters")
            
            with gr.Row():
                with gr.Column():
                    retrieval_query = gr.Textbox(
                        label="Query",
                        placeholder="Enter your search query...",
                        lines=3
                    )
                    
                    retrieval_top_k = gr.Slider(
                        minimum=1,
                        maximum=50,
                        value=10,
                        step=1,
                        label="Top-K Results"
                    )
                    
                    retrieval_query_enhancer = gr.Checkbox(
                        label="Enable Query Enhancer",
                        value=False
                    )
                    
                    retrieval_reranking = gr.Checkbox(
                        label="Enable Reranking",
                        value=False
                    )
                    
                    retrieve_btn = gr.Button("🔍 Retrieve Documents", variant="primary")
                
                with gr.Column():
                    retrieval_results = gr.Textbox(
                        label="Retrieved Documents",
                        lines=25,
                        max_lines=30,
                        interactive=False
                    )
            
            retrieve_btn.click(
                fn=test_retrieval,
                inputs=[retrieval_query, retrieval_top_k, retrieval_query_enhancer, retrieval_reranking],
                outputs=[retrieval_results]
            )
        
        # ===== TAB 3: INGESTION =====
        with gr.Tab("📥 Ingestion"):
            gr.Markdown("## Ingest documents into the system")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Start New Ingestion Job")
                    
                    ingestion_folder = gr.Dropdown(
                        label="Select Folder",
                        choices=load_assets_folders(),
                        interactive=True
                    )
                    
                    refresh_assets_btn = gr.Button("🔄 Refresh Folders", size="sm")
                    
                    with gr.Row():
                        ingest_pdf = gr.Checkbox(label="PDF", value=True)
                        ingest_json = gr.Checkbox(label="JSON", value=True)
                    
                    start_ingestion_btn = gr.Button("🚀 Start Ingestion", variant="primary")
                    
                    ingestion_start_output = gr.Textbox(
                        label="Job Started",
                        lines=3,
                        interactive=False
                    )
                    
                    ingestion_job_id = gr.State(None)
                
                with gr.Column():
                    gr.Markdown("### Job Status")
                    
                    ingestion_status_output = gr.Textbox(
                        label="Current Job Status",
                        lines=8,
                        interactive=False
                    )
                    
                    ingestion_progress = gr.Slider(
                        minimum=0,
                        maximum=100,
                        value=0,
                        label="Progress",
                        interactive=False
                    )
                    
                    with gr.Row():
                        check_status_btn = gr.Button("🔄 Check Status")
                        auto_refresh_checkbox = gr.Checkbox(label="Auto-refresh (3s)", value=False)
            
            gr.Markdown("### Active Jobs")
            jobs_list_output = gr.Dataframe(
                label="Active Ingestion Jobs",
                interactive=False
            )
            refresh_jobs_btn = gr.Button("🔄 Refresh Jobs List")
            
            # Event handlers
            refresh_assets_btn.click(
                fn=refresh_assets_folders,
                inputs=[],
                outputs=[ingestion_folder]
            )
            
            start_ingestion_btn.click(
                fn=start_ingestion,
                inputs=[ingestion_folder, ingest_pdf, ingest_json],
                outputs=[ingestion_start_output, ingestion_job_id]
            )
            
            check_status_btn.click(
                fn=check_ingestion_status,
                inputs=[ingestion_job_id],
                outputs=[ingestion_status_output, ingestion_progress]
            )
            
            refresh_jobs_btn.click(
                fn=refresh_jobs_list,
                inputs=[],
                outputs=[jobs_list_output]
            )
            
            # Auto-refresh functionality
            def auto_refresh_status(auto_refresh, job_id):
                if auto_refresh and job_id:
                    return check_ingestion_status(job_id)
                return None, None
        
        # ===== TAB 4: EVALUATION =====
        with gr.Tab("📊 Evaluation"):
            gr.Markdown("## Evaluate retrieval system performance")
            
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Start New Evaluation")
                    
                    eval_folder = gr.Dropdown(
                        label="Select Folder",
                        choices=load_evaluation_folders(),
                        interactive=True
                    )
                    
                    refresh_eval_folders_btn = gr.Button("🔄 Refresh Folders", size="sm")
                    
                    eval_top_k = gr.Slider(
                        minimum=1,
                        maximum=50,
                        value=10,
                        step=1,
                        label="Top-K Results"
                    )
                    
                    eval_query_enhancer = gr.Checkbox(
                        label="Enable Query Enhancer",
                        value=False
                    )
                    
                    eval_reranking = gr.Checkbox(
                        label="Enable Reranking",
                        value=False
                    )
                    
                    eval_num_questions = gr.Slider(
                        minimum=1,
                        maximum=5,
                        value=1,
                        step=1,
                        label="Questions per Document"
                    )
                    
                    eval_reuse_dropdown = gr.Dropdown(
                        label="Reuse Questions From",
                        choices=get_evaluations_for_reuse_choices(),
                        interactive=True,
                        value=None
                    )
                    
                    refresh_reuse_btn = gr.Button("🔄 Refresh Evaluations", size="sm")
                    
                    start_eval_btn = gr.Button("🚀 Start Evaluation", variant="primary")
                    
                    eval_start_output = gr.Textbox(
                        label="Evaluation Started",
                        lines=4,
                        interactive=False
                    )
                
                with gr.Column():
                    gr.Markdown("### Evaluation Results")
                    
                    eval_results_dropdown = gr.Dropdown(
                        label="Select Evaluation",
                        choices=get_evaluations_dropdown_choices(),
                        interactive=True,
                        value=None
                    )
                    
                    refresh_eval_dropdown_btn = gr.Button("🔄 Refresh List", size="sm")
                    
                    eval_results_output = gr.Textbox(
                        label="Results",
                        lines=20,
                        max_lines=25,
                        interactive=False
                    )
                    
                    refresh_results_btn = gr.Button("🔄 Refresh Results")
            
            gr.Markdown("### Evaluations Comparison")
            eval_comparison_table = gr.Dataframe(
                label="All Evaluations Comparison",
                interactive=False
            )
            refresh_comparison_btn = gr.Button("🔄 Refresh Comparison")
            
            # Event handlers
            refresh_eval_folders_btn.click(
                fn=refresh_evaluation_folders,
                inputs=[],
                outputs=[eval_folder]
            )
            
            start_eval_btn.click(
                fn=start_evaluation_job,
                inputs=[
                    eval_folder,
                    eval_top_k,
                    eval_query_enhancer,
                    eval_reranking,
                    eval_num_questions,
                    eval_reuse_dropdown
                ],
                outputs=[eval_start_output]
            )
            
            refresh_reuse_btn.click(
                fn=load_evaluations_for_reuse,
                inputs=[],
                outputs=[eval_reuse_dropdown]
            )
            
            refresh_eval_dropdown_btn.click(
                fn=load_evaluations_dropdown,
                inputs=[],
                outputs=[eval_results_dropdown]
            )
            
            eval_results_dropdown.change(
                fn=load_evaluation_results,
                inputs=[eval_results_dropdown],
                outputs=[eval_results_output]
            )
            
            refresh_results_btn.click(
                fn=load_evaluation_results,
                inputs=[eval_results_dropdown],
                outputs=[eval_results_output]
            )
            
            refresh_comparison_btn.click(
                fn=load_evaluations_comparison,
                inputs=[],
                outputs=[eval_comparison_table]
            )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )

