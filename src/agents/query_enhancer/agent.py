from typing import Optional, List
from crewai import Agent, LLM  # type: ignore
from langchain_openai import ChatOpenAI  # type: ignore

from src.config import OPENAI_API_KEY
from src.agents.schemas import EnhancedQueries


class QueryEnhancerAgent:
	"""Agent that enhances queries for better legal document retrieval."""
	
	def __init__(self):
		self.agent = Agent(
			role="Legal Query Enhancement Specialist",
			goal="Transform user queries into optimized search queries for European legislation and legal documents",
			backstory="""You are a legal research specialist with deep expertise in European Union legislation, 
			directives, regulations, and legal terminology. Your role is to enhance user queries to improve 
			document retrieval from legal databases containing EU laws, regulations, and legal documents.""",
			llm=self._create_llm(),
			verbose=True,
			allow_delegation=False,
		)
	
	def _create_llm(self):
		return ChatOpenAI(
			model="gpt-4o-mini",
			temperature=0.3,  # Lower temperature for more consistent legal terminology
			openai_api_key=OPENAI_API_KEY,
		)
	
	def enhance_query(self, original_query: str) -> List[str]:
		"""
		Enhance a single query into multiple optimized variations for legal document retrieval.
		Returns a list of enhanced queries.
		"""
		enhancement_prompt = f"""You are a legal agent reading EURO legislation law docs. Enhance this query for better document retrieval.

Original query: "{original_query}"

Your task:
1. Create 3-5 enhanced query variations that would retrieve relevant European legal documents
2. Include relevant legal terminology, synonyms, and related concepts
3. Consider different ways lawyers and legal professionals might search for this information
4. Include both broad and specific variations
5. Use proper legal terminology when applicable

Guidelines:
- Focus on European Union legislation, directives, regulations, and legal frameworks
- Include relevant legal concepts, article numbers, or directive references if applicable
- Consider both English and common legal Latin terms
- Think about related legal areas that might contain relevant information"""

		try:
			# Use CrewAI's structured LLM output
			llm = LLM(model="gpt-4o-mini", api_key=OPENAI_API_KEY, response_format=EnhancedQueries)
			
			response = llm.call(enhancement_prompt)
			
			# Extract enhanced queries from structured response
			if hasattr(response, 'enhanced_queries') and isinstance(response.enhanced_queries, list):
				enhanced_queries = response.enhanced_queries
				
				# Always include the original query as fallback
				if original_query not in enhanced_queries:
					enhanced_queries.insert(0, original_query)  
				print(f"Enhanced queries (after post-processing): {enhanced_queries}")

				return enhanced_queries[:5]  # Limit to 5 queries max
			else:
				print(f"Invalid response format: {response}")
				return [original_query]
			
		except Exception as e:
			print(f"Query enhancement failed: {e}")
			# Fallback to original query
			return [original_query]
	
	def enhance_query_simple(self, original_query: str) -> str:
		"""
		Simple enhancement that returns a single enhanced query.
		Useful when you just want one improved version.
		"""
		enhanced_queries = self.enhance_query(original_query)
		return enhanced_queries[0] if enhanced_queries else original_query
