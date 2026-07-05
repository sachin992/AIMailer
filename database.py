"""
Database module for AIMailer
Tracks processed emails, conversation history, and analytics
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import json
from logger import get_logger

logger = get_logger("database")


class Database:
    """Database manager for email tracking and analytics"""
    
    def __init__(self, db_path: str = "aimailer.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Processed emails table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT UNIQUE NOT NULL,
                    thread_id TEXT,
                    sender TEXT NOT NULL,
                    subject TEXT,
                    body TEXT,
                    received_at TIMESTAMP,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    confidence_score REAL,
                    response_sent BOOLEAN DEFAULT 0,
                    requires_review BOOLEAN DEFAULT 0,
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    error_message TEXT,
                    processing_time_ms INTEGER
                )
            """)
            
            # Add thread_id column if it doesn't exist (migration)
            try:
                cursor.execute("SELECT thread_id FROM processed_emails LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE processed_emails ADD COLUMN thread_id TEXT")
                logger.info("Added thread_id column to processed_emails table")
            
            # FAQ matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faq_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    faq_question TEXT NOT NULL,
                    faq_answer TEXT NOT NULL,
                    similarity_score REAL NOT NULL,
                    rank INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES processed_emails(email_id)
                )
            """)
            
            # Responses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    response_type TEXT NOT NULL,
                    sent_at TIMESTAMP,
                    is_automatic BOOLEAN DEFAULT 1,
                    approved_by TEXT,
                    approved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES processed_emails(email_id)
                )
            """)
            
            # Analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_emails INTEGER DEFAULT 0,
                    auto_replied INTEGER DEFAULT 0,
                    manual_review INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    avg_confidence REAL,
                    avg_processing_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """)
            
            # Admin actions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_id TEXT NOT NULL,
                    admin_email TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    action_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (email_id) REFERENCES processed_emails(email_id)
                )
            """)
            
            # Admin users table (for authentication)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    name TEXT,
                    role TEXT DEFAULT 'admin',
                    is_active BOOLEAN DEFAULT 1,
                    last_login TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_id 
                ON processed_emails(email_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON processed_emails(status)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_requires_review 
                ON processed_emails(requires_review)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON processed_emails(processed_at)
            """)
            
            logger.info("Database initialized successfully")
    
    def email_exists(self, email_id: str) -> bool:
        """Check if email has been processed"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_emails WHERE email_id = ?",
                (email_id,)
            )
            return cursor.fetchone() is not None
    
    def save_processed_email(
        self,
        email_id: str,
        sender: str,
        subject: str,
        body: str,
        status: str,
        thread_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        requires_review: bool = False,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None
    ) -> int:
        """
        Save processed email to database
        
        Returns:
            Row ID of inserted record
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processed_emails 
                (email_id, thread_id, sender, subject, body, status, confidence_score, 
                 requires_review, error_message, processing_time_ms, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email_id, thread_id, sender, subject, body, status, confidence_score,
                requires_review, error_message, processing_time_ms, datetime.now()
            ))
            
            logger.info(f"Saved processed email: {email_id} (thread: {thread_id})")
            return cursor.lastrowid
    
    def save_faq_matches(
        self,
        email_id: str,
        matches: List[tuple]
    ):
        """
        Save FAQ matches for an email
        
        Args:
            email_id: Email identifier
            matches: List of (question, answer, score, rank) tuples
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for question, answer, score, rank in matches:
                cursor.execute("""
                    INSERT INTO faq_matches 
                    (email_id, faq_question, faq_answer, similarity_score, rank)
                    VALUES (?, ?, ?, ?, ?)
                """, (email_id, question, answer, score, rank))
            
            logger.debug(f"Saved {len(matches)} FAQ matches for email {email_id}")
    
    def save_response(
        self,
        email_id: str,
        response_text: str,
        response_type: str,
        is_automatic: bool = True,
        approved_by: Optional[str] = None,
        mark_as_sent: bool = False
    ) -> int:
        """Save response to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO responses 
                (email_id, response_text, response_type, is_automatic, 
                 approved_by, sent_at, approved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                email_id, response_text, response_type, is_automatic,
                approved_by, datetime.now() if mark_as_sent else None,
                datetime.now() if approved_by else None
            ))
            
            # Only update response_sent if actually sent (not just a draft)
            if mark_as_sent:
                cursor.execute("""
                    UPDATE processed_emails 
                    SET response_sent = 1 
                    WHERE email_id = ?
                """, (email_id,))
            
            logger.info(f"Saved response for email {email_id} (type: {response_type}, sent: {mark_as_sent})")
            return cursor.lastrowid
    
    def get_pending_review_emails(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get emails requiring manual review"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM processed_emails 
                WHERE status = 'pending_review' AND requires_review = 1 AND response_sent = 0
                ORDER BY processed_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_email_reviewed(
        self,
        email_id: str,
        reviewed_by: str
    ):
        """Mark email as reviewed by admin"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE processed_emails 
                SET reviewed_by = ?,
                    reviewed_at = ?,
                    requires_review = 0,
                    status = 'reviewed',
                    response_sent = 1
                WHERE email_id = ?
            """, (reviewed_by, datetime.now(), email_id))
            
            logger.info(f"Email {email_id} marked as reviewed by {reviewed_by}")
    
    def save_admin_action(
        self,
        email_id: str,
        admin_email: str,
        action_type: str,
        action_data: Optional[Dict] = None
    ):
        """Log admin action"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO admin_actions 
                (email_id, admin_email, action_type, action_data)
                VALUES (?, ?, ?, ?)
            """, (
                email_id, admin_email, action_type,
                json.dumps(action_data) if action_data else None
            ))
            
            logger.info(f"Admin action logged: {action_type} by {admin_email}")
    
    def get_analytics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics summary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    COUNT(*) as total_emails,
                    SUM(CASE WHEN response_sent = 1 AND requires_review = 0 THEN 1 ELSE 0 END) as auto_replied,
                    SUM(CASE WHEN requires_review = 1 THEN 1 ELSE 0 END) as manual_review,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(confidence_score) as avg_confidence,
                    AVG(processing_time_ms) as avg_processing_time_ms
                FROM processed_emails
            """
            
            params = []
            if start_date and end_date:
                query += " WHERE processed_at BETWEEN ? AND ?"
                params = [start_date, end_date]
            
            cursor.execute(query, params)
            result = cursor.fetchone()
            
            return dict(result) if result else {}
    
    def get_recent_emails(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently processed emails"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM processed_emails 
                ORDER BY processed_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Admin User Management Methods
    
    def create_admin_user(
        self,
        email: str,
        password_hash: str,
        name: str,
        role: str = "admin"
    ) -> int:
        """Create a new admin user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO admin_users (email, password_hash, name, role)
                VALUES (?, ?, ?, ?)
            """, (email, password_hash, name, role))
            
            logger.info(f"Created admin user: {email} with role: {role}")
            return cursor.lastrowid
    
    def get_admin_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get admin user by email"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM admin_users WHERE email = ?
            """, (email,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def get_admin_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get admin user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM admin_users WHERE id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def update_admin_last_login(self, user_id: int):
        """Update admin user's last login timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE admin_users 
                SET last_login = ? 
                WHERE id = ?
            """, (datetime.now(), user_id))
            
            logger.info(f"Updated last login for user ID: {user_id}")
    
    def update_admin_password(self, user_id: int, password_hash: str):
        """Update admin user's password"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE admin_users 
                SET password_hash = ?, updated_at = ? 
                WHERE id = ?
            """, (password_hash, datetime.now(), user_id))
            
            logger.info(f"Updated password for user ID: {user_id}")
    
    def deactivate_admin_user(self, user_id: int):
        """Deactivate admin user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE admin_users 
                SET is_active = 0, updated_at = ? 
                WHERE id = ?
            """, (datetime.now(), user_id))
            
            logger.info(f"Deactivated user ID: {user_id}")
    
    def list_admin_users(self) -> List[Dict[str, Any]]:
        """List all admin users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, email, name, role, is_active, last_login, created_at
                FROM admin_users 
                ORDER BY created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
