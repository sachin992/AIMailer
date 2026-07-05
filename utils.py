"""
Utility functions for AIMailer
Includes retry mechanisms, validation, and helper functions
"""
import re
import time
import logging
from typing import Callable, Any, Optional, List
from functools import wraps
from email.utils import parseaddr
import pandas as pd

logger = logging.getLogger(__name__)


class RetryException(Exception):
    """Exception raised when retries are exhausted"""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_retries} retry attempts exhausted for {func.__name__}"
                        )
            
            raise RetryException(
                f"Failed after {max_retries} retries: {str(last_exception)}"
            ) from last_exception
        
        return wrapper
    return decorator


class EmailValidator:
    """Validate and sanitize email-related data"""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email:
            return False
        
        # Parse email address
        _, addr = parseaddr(email)
        
        # Basic regex pattern for email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, addr))
    
    @staticmethod
    def extract_email_address(email_string: str) -> Optional[str]:
        """
        Extract clean email address from string like 'Name <email@example.com>'
        
        Args:
            email_string: Email string to parse
            
        Returns:
            Clean email address or None
        """
        _, addr = parseaddr(email_string)
        return addr if EmailValidator.is_valid_email(addr) else None
    
    @staticmethod
    def sanitize_email_body(body: str, max_length: int = 10000) -> str:
        """
        Sanitize email body text
        
        Args:
            body: Raw email body
            max_length: Maximum length to truncate
            
        Returns:
            Sanitized email body
        """
        if not body:
            return ""
        
        # Remove excessive whitespace
        body = re.sub(r'\s+', ' ', body)
        
        # Remove common email artifacts
        body = re.sub(r'(Sent from my iPhone|Sent from my Android)', '', body)
        
        # Truncate if too long
        if len(body) > max_length:
            body = body[:max_length] + "..."
        
        return body.strip()


class QueryValidator:
    """Validate and sanitize user queries"""
    
    @staticmethod
    def is_valid_query(query: str, min_length: int = 3, max_length: int = 5000) -> bool:
        """
        Check if query is valid
        
        Args:
            query: User query text
            min_length: Minimum query length
            max_length: Maximum query length
            
        Returns:
            True if valid, False otherwise
        """
        if not query or not query.strip():
            return False
        
        query_length = len(query.strip())
        return min_length <= query_length <= max_length
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize user query
        
        Args:
            query: Raw query text
            
        Returns:
            Sanitized query
        """
        if not query:
            return ""
        
        # Remove excessive whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Remove potentially harmful characters for embeddings
        query = re.sub(r'[<>{}[\]\\]', '', query)
        
        return query.strip()


class FAQValidator:
    """Validate FAQ data integrity"""
    
    @staticmethod
    def validate_faq_dataframe(df: pd.DataFrame) -> List[str]:
        """
        Validate FAQ DataFrame structure and content
        
        Args:
            df: FAQ DataFrame
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required columns
        required_columns = ["Question", "Answer"]
        for col in required_columns:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
        
        if errors:
            return errors
        
        # Check for empty DataFrame
        if df.empty:
            errors.append("FAQ DataFrame is empty")
            return errors
        
        # Check for null values
        null_questions = df["Question"].isnull().sum()
        null_answers = df["Answer"].isnull().sum()
        
        if null_questions > 0:
            errors.append(f"Found {null_questions} null values in Question column")
        
        if null_answers > 0:
            errors.append(f"Found {null_answers} null values in Answer column")
        
        # Check for empty strings
        empty_questions = (df["Question"].astype(str).str.strip() == "").sum()
        empty_answers = (df["Answer"].astype(str).str.strip() == "").sum()
        
        if empty_questions > 0:
            errors.append(f"Found {empty_questions} empty questions")
        
        if empty_answers > 0:
            errors.append(f"Found {empty_answers} empty answers")
        
        # Check for duplicate questions
        duplicates = df["Question"].duplicated().sum()
        if duplicates > 0:
            errors.append(f"Found {duplicates} duplicate questions")
        
        return errors
    
    @staticmethod
    def clean_faq_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and prepare FAQ DataFrame
        
        Args:
            df: Raw FAQ DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        # Create a copy
        df_clean = df.copy()
        
        # Remove rows with null values
        df_clean = df_clean.dropna(subset=["Question", "Answer"])
        
        # Convert to string and strip whitespace
        df_clean["Question"] = df_clean["Question"].astype(str).str.strip()
        df_clean["Answer"] = df_clean["Answer"].astype(str).str.strip()
        
        # Remove empty strings
        df_clean = df_clean[df_clean["Question"] != ""]
        df_clean = df_clean[df_clean["Answer"] != ""]
        
        # Remove duplicates (keep first occurrence)
        df_clean = df_clean.drop_duplicates(subset=["Question"], keep="first")
        
        # Reset index
        df_clean = df_clean.reset_index(drop=True)
        
        return df_clean


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
