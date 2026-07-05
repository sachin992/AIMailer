"""
AI Generator module for AIMailer
Generates email responses using OpenAI GPT with error handling
"""
from typing import List, Tuple, Optional
from openai import OpenAI, OpenAIError

from config import Config
from logger import get_logger
from utils import retry_with_backoff

logger = get_logger("ai_generator")


class AIGeneratorError(Exception):
    """Custom exception for AI generator errors"""
    pass


class AIGenerator:
    """Generates AI-powered email responses"""
    
    def __init__(self):
        """Initialize AI generator"""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    @retry_with_backoff(
        max_retries=Config.MAX_RETRIES,
        exceptions=(OpenAIError,)
    )
    def generate_email_response(
        self,
        user_query: str,
        faq_matches: List[Tuple[str, str, float]],
        sender_name: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Generate email response using GPT
        
        Args:
            user_query: User's query from email
            faq_matches: List of (question, answer, distance) tuples
            sender_name: Optional sender name for personalization
            
        Returns:
            Tuple of (response_text, is_confident)
        """
        try:
            # Check if we have FAQ matches
            if not faq_matches:
                logger.info("No FAQ matches found, generating fallback response")
                return self._generate_fallback_response(sender_name), False
            
            # Build context from FAQ matches
            context = self._build_faq_context(faq_matches)
            
            # Generate prompt
            prompt = self._build_prompt(user_query, context, sender_name)
            
            logger.debug(f"Generating response with {len(faq_matches)} FAQ matches")
            
            # Call OpenAI API
            completion = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an automated email reply assistant. "
                            "Your task is to generate professional, helpful email responses "
                            "based ONLY on the provided FAQ information. "
                            "Do NOT make up information. "
                            "Be concise and professional."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=Config.OPENAI_TEMPERATURE,
                max_tokens=500
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Determine confidence based on best match distance
            best_distance = min(dist for _, _, dist in faq_matches)
            is_confident = best_distance < (Config.FAQ_SIMILARITY_THRESHOLD * 0.5)
            
            logger.info(
                f"Generated response (confident: {is_confident}, "
                f"best_distance: {best_distance:.4f})"
            )
            
            return response_text, is_confident
        
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise AIGeneratorError(f"Failed to generate response: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error in response generation: {e}")
            raise AIGeneratorError(f"Response generation failed: {e}")
    
    def _build_faq_context(self, faq_matches: List[Tuple[str, str, float]]) -> str:
        """
        Build context string from FAQ matches
        
        Args:
            faq_matches: List of (question, answer, distance) tuples
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for i, (question, answer, distance) in enumerate(faq_matches, 1):
            context_parts.append(f"FAQ {i}:\nQ: {question}\nA: {answer}\n")
        
        return "\n".join(context_parts)
    
    def _build_prompt(
        self,
        user_query: str,
        faq_context: str,
        sender_name: Optional[str] = None
    ) -> str:
        """
        Build prompt for GPT
        
        Args:
            user_query: User's query
            faq_context: FAQ context string
            sender_name: Optional sender name
            
        Returns:
            Formatted prompt
        """
        greeting = f"Dear {sender_name}" if sender_name else "Dear User"
        
        prompt = f"""
User Query:
{user_query}

Relevant FAQ Information:
{faq_context}

Instructions:
1. Use ONLY the FAQ information above to answer the user's query
2. If the FAQ information doesn't fully answer the query, say: "I am unable to fully answer this question. Our support team will review your email and respond shortly."
3. Do NOT make up any information
4. Do NOT add personal opinions
5. Start the email with: "{greeting},"
6. Keep the answer concise (2-4 sentences)
7. End with: "Thank you for contacting us."
8. Be professional and helpful

Write the email response:
"""
        return prompt
    
    def _generate_fallback_response(self, sender_name: Optional[str] = None) -> str:
        """
        Generate fallback response when no FAQ matches found
        
        Args:
            sender_name: Optional sender name
            
        Returns:
            Fallback response text
        """
        greeting = f"Dear {sender_name}" if sender_name else "Dear User"
        
        response = f"""{greeting},

Thank you for contacting us. I am currently unable to answer your query as it requires manual review.

Our customer support team has been notified and will respond to you shortly.

Thank you for your patience.

Best regards,
Support Team"""
        
        logger.info("Generated fallback response")
        return response
    
    def generate_custom_response(
        self,
        user_query: str,
        custom_instructions: str
    ) -> str:
        """
        Generate custom response with specific instructions
        Used for admin-approved responses
        
        Args:
            user_query: User's query
            custom_instructions: Custom instructions for response
            
        Returns:
            Generated response
        """
        try:
            completion = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional email response assistant."
                    },
                    {
                        "role": "user",
                        "content": f"""
User Query:
{user_query}

Instructions:
{custom_instructions}

Generate a professional email response:
"""
                    }
                ],
                temperature=Config.OPENAI_TEMPERATURE,
                max_tokens=500
            )
            
            response = completion.choices[0].message.content.strip()
            logger.info("Generated custom response")
            return response
        
        except OpenAIError as e:
            logger.error(f"Error generating custom response: {e}")
            raise AIGeneratorError(f"Failed to generate custom response: {e}")
