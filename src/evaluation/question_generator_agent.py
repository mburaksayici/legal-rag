"""Question generator agent using GPT-4o-mini with CrewAI."""
from crewai import Agent, Task, Crew  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore
from src.config import OPENAI_API_KEY
from .schemas import QuestionOutput
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class QuestionGeneratorAgent:
    """Agent that generates questions from PDF text using structured output."""
    
    def __init__(self):
        self.agent = Agent(
            role="Question Generator",
            goal="Generate specific, targeted questions from legal document text that can be used to evaluate retrieval systems",
            backstory="You are an expert at analyzing legal documents and creating precise questions that target specific facts and information within the text.",
            llm=self._create_llm(),
            verbose=False,
            allow_delegation=False,
        )
    
    def _create_llm(self):
        """Create ChatOpenAI LLM for the agent."""
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY,
        )
    
    def generate_question(self, document_text: str, source_path: str) -> Optional[QuestionOutput]:
        """
        Generate a question from document text using structured output.
        
        Args:
            document_text: The full text of the document
            source_path: Path to the source document
            
        Returns:
            QuestionOutput with fact and question, or None if generation fails
        """
        try:
            # Create task with structured output
            task = Task(
                description=f"""Analyze the following legal document text and generate ONE evaluation question.

Document text:
{document_text[:3000]}  # Limit to first 3000 chars to avoid token limits

Your task:
1. Read the document carefully
2. Select ONE specific fact, rule, or piece of information from the document
3. Extract the exact sentence or short passage containing that fact (FACT field)
4. Create a clear, specific question that targets exactly that fact (QUESTION field)

The question should be:
- Specific enough that only the source document would answer it correctly
- Clear and unambiguous
- Focused on factual information from the document

Return your response in the structured format with 'fact' and 'question' fields.""",
                agent=self.agent,
                expected_output="A structured response with a fact from the document and a corresponding question",
                output_pydantic=QuestionOutput
            )
            
            # Execute task
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            result = crew.kickoff()
            
            # CrewAI returns the result as the Pydantic model when using output_pydantic
            if isinstance(result, QuestionOutput):
                return result
            elif hasattr(result, 'pydantic'):
                return result.pydantic
            else:
                logger.warning(f"Unexpected result type from CrewAI: {type(result)}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate question for {source_path}: {str(e)}")
            return None
    
    def generate_multiple_questions(
        self, 
        document_text: str, 
        source_path: str, 
        num_questions: int = 1
    ) -> list[QuestionOutput]:
        """
        Generate multiple questions from a single document.
        
        Args:
            document_text: The full text of the document
            source_path: Path to the source document
            num_questions: Number of questions to generate
            
        Returns:
            List of QuestionOutput objects
        """
        questions = []
        
        for i in range(num_questions):
            question_output = self.generate_question(document_text, source_path)
            if question_output:
                questions.append(question_output)
            else:
                logger.warning(f"Failed to generate question {i+1}/{num_questions} for {source_path}")
        
        return questions

