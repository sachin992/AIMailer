"""
Configuration management for AIMailer
Loads settings from environment variables with sensible defaults
"""
import os
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # Gmail API Configuration
    GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
    GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "token.json")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0"))
    
    # FAQ Configuration
    FAQ_EXCEL_FILE = os.getenv("FAQ_EXCEL_FILE", "faq.xlsx")
    VECTOR_STORE_FILE = os.getenv("VECTOR_STORE_FILE", "faq.index")
    FAQ_SIMILARITY_THRESHOLD = float(os.getenv("FAQ_SIMILARITY_THRESHOLD", "2.0"))
    FAQ_TOP_K_RESULTS = int(os.getenv("FAQ_TOP_K_RESULTS", "3"))
    
    # Email Filtering Configuration
    EMAIL_FILTER_MODE = os.getenv("EMAIL_FILTER_MODE", "whitelist")  # whitelist, blacklist, or all
    EMAIL_WHITELIST = os.getenv("EMAIL_WHITELIST", "").split(",") if os.getenv("EMAIL_WHITELIST") else []
    EMAIL_BLACKLIST = os.getenv("EMAIL_BLACKLIST", "").split(",") if os.getenv("EMAIL_BLACKLIST") else []
    EMAIL_LABEL_FILTER = os.getenv("EMAIL_LABEL_FILTER", "")  # Optional Gmail label
    
    # Batch Processing Configuration
    MAX_EMAILS_PER_RUN = int(os.getenv("MAX_EMAILS_PER_RUN", "10"))
    ENABLE_BATCH_PROCESSING = os.getenv("ENABLE_BATCH_PROCESSING", "true").lower() == "true"
    
    # Retry Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))
    INITIAL_RETRY_DELAY = float(os.getenv("INITIAL_RETRY_DELAY", "1.0"))
    
    # Database Configuration
    DATABASE_ENABLED = os.getenv("DATABASE_ENABLED", "true").lower() == "true"
    DATABASE_PATH = os.getenv("DATABASE_PATH", "aimailer.db")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/aimailer.log")
    LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    
    # Human-in-the-Loop Configuration
    HITL_ENABLED = os.getenv("HITL_ENABLED", "true").lower() == "true"
    HITL_CONFIDENCE_THRESHOLD = float(os.getenv("HITL_CONFIDENCE_THRESHOLD", "0.7"))
    HITL_AUTO_SEND_HIGH_CONFIDENCE = os.getenv("HITL_AUTO_SEND_HIGH_CONFIDENCE", "true").lower() == "true"
    
    # API Rate Limiting
    OPENAI_RATE_LIMIT_RPM = int(os.getenv("OPENAI_RATE_LIMIT_RPM", "60"))
    GMAIL_RATE_LIMIT_QPM = int(os.getenv("GMAIL_RATE_LIMIT_QPM", "250"))
    
    # Email Templates
    EMAIL_TEMPLATE_FOLDER = os.getenv("EMAIL_TEMPLATE_FOLDER", "templates/email")
    DEFAULT_EMAIL_TEMPLATE = os.getenv("DEFAULT_EMAIL_TEMPLATE", "default.html")
    ENABLE_HTML_EMAILS = os.getenv("ENABLE_HTML_EMAILS", "true").lower() == "true"
    
    # Monitoring & Analytics
    ENABLE_MONITORING = os.getenv("ENABLE_MONITORING", "true").lower() == "true"
    METRICS_EXPORT_INTERVAL = int(os.getenv("METRICS_EXPORT_INTERVAL", "300"))  # 5 minutes
    
    # Admin Dashboard Configuration
    ADMIN_DASHBOARD_ENABLED = os.getenv("ADMIN_DASHBOARD_ENABLED", "true").lower() == "true"
    ADMIN_DASHBOARD_PORT = int(os.getenv("ADMIN_DASHBOARD_PORT", "3000"))
    ADMIN_API_PORT = int(os.getenv("ADMIN_API_PORT", "5000"))
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        
        if not os.path.exists(cls.GMAIL_CREDENTIALS_FILE):
            errors.append(f"Gmail credentials file not found: {cls.GMAIL_CREDENTIALS_FILE}")
        
        if not os.path.exists(cls.FAQ_EXCEL_FILE):
            errors.append(f"FAQ Excel file not found: {cls.FAQ_EXCEL_FILE}")
        
        if cls.EMAIL_FILTER_MODE not in ["whitelist", "blacklist", "all"]:
            errors.append(f"Invalid EMAIL_FILTER_MODE: {cls.EMAIL_FILTER_MODE}")
        
        if cls.EMAIL_FILTER_MODE == "whitelist" and not cls.EMAIL_WHITELIST:
            errors.append("EMAIL_WHITELIST is empty but EMAIL_FILTER_MODE is 'whitelist'")
        
        return errors
    
    @classmethod
    def get_summary(cls) -> dict:
        """Get configuration summary (without sensitive data)"""
        return {
            "openai_model": cls.OPENAI_MODEL,
            "faq_file": cls.FAQ_EXCEL_FILE,
            "email_filter_mode": cls.EMAIL_FILTER_MODE,
            "max_emails_per_run": cls.MAX_EMAILS_PER_RUN,
            "batch_processing": cls.ENABLE_BATCH_PROCESSING,
            "database_enabled": cls.DATABASE_ENABLED,
            "hitl_enabled": cls.HITL_ENABLED,
            "monitoring_enabled": cls.ENABLE_MONITORING,
        }
