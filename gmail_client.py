"""
Gmail client module for AIMailer
Handles Gmail API authentication, email fetching, and sending with dynamic filtering
"""
import os
import base64
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import Config
from logger import get_logger
from utils import retry_with_backoff, EmailValidator

logger = get_logger("gmail_client")


class GmailAPIError(Exception):
    """Custom exception for Gmail API errors"""
    pass


class GmailClient:
    """Gmail API client with authentication and email operations"""
    
    def __init__(self):
        """Initialize Gmail client"""
        self.service = None
        self.authenticate()
    
    @retry_with_backoff(max_retries=Config.MAX_RETRIES, exceptions=(HttpError,))
    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Try to load existing token
        if os.path.exists(Config.GMAIL_TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(
                    Config.GMAIL_TOKEN_FILE,
                    Config.GMAIL_SCOPES
                )
                logger.info("Loaded existing Gmail credentials")
            except Exception as e:
                logger.warning(f"Failed to load token.json: {e}. Will re-authenticate.")
                if os.path.exists(Config.GMAIL_TOKEN_FILE):
                    os.remove(Config.GMAIL_TOKEN_FILE)
                creds = None
        
        # If no valid credentials, re-authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed Gmail credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(Config.GMAIL_CREDENTIALS_FILE):
                    raise GmailAPIError(
                        f"Credentials file not found: {Config.GMAIL_CREDENTIALS_FILE}"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GMAIL_CREDENTIALS_FILE,
                    Config.GMAIL_SCOPES
                )
                
                creds = flow.run_local_server(
                    port=0,
                    prompt='consent',
                    access_type='offline'
                )
                logger.info("Obtained new Gmail credentials")
            
            # Save credentials
            with open(Config.GMAIL_TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
                logger.info("Saved Gmail credentials to token.json")
        
        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail service authenticated successfully")
    
    def _build_email_query(self) -> str:
        """
        Build Gmail search query based on configuration
        
        Returns:
            Gmail search query string
        """
        query_parts = ["is:unread"]
        
        # Add sender filtering
        if Config.EMAIL_FILTER_MODE == "whitelist" and Config.EMAIL_WHITELIST:
            # Filter by whitelisted senders
            sender_query = " OR ".join(
                [f"from:{email}" for email in Config.EMAIL_WHITELIST]
            )
            query_parts.append(f"({sender_query})")
            logger.debug(f"Using whitelist filter: {Config.EMAIL_WHITELIST}")
        
        elif Config.EMAIL_FILTER_MODE == "blacklist" and Config.EMAIL_BLACKLIST:
            # Exclude blacklisted senders
            for email in Config.EMAIL_BLACKLIST:
                query_parts.append(f"-from:{email}")
            logger.debug(f"Using blacklist filter: {Config.EMAIL_BLACKLIST}")
        
        # Add label filtering if specified
        if Config.EMAIL_LABEL_FILTER:
            query_parts.append(f"label:{Config.EMAIL_LABEL_FILTER}")
            logger.debug(f"Using label filter: {Config.EMAIL_LABEL_FILTER}")
        
        query = " ".join(query_parts)
        logger.info(f"Built email query: {query}")
        return query
    
    def _get_email_body(self, payload: Dict) -> str:
        """
        Extract plain text body from Gmail payload
        Handles multipart emails
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Email body text
        """
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    return base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8", errors="ignore")
                
                # Check nested parts
                elif "parts" in part:
                    nested_body = self._get_email_body(part)
                    if nested_body:
                        return nested_body
        
        elif "data" in payload.get("body", {}):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="ignore")
        
        return ""
    
    @retry_with_backoff(max_retries=Config.MAX_RETRIES, exceptions=(HttpError,))
    def get_unread_emails(self, max_results: Optional[int] = None) -> List[Dict]:
        """
        Fetch unread emails based on filters
        
        Args:
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries
        """
        if not self.service:
            raise GmailAPIError("Gmail service not authenticated")
        
        max_results = max_results or Config.MAX_EMAILS_PER_RUN
        query = self._build_email_query()
        
        try:
            results = self.service.users().messages().list(
                userId="me",
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get("messages", [])
            
            if not messages:
                logger.info("No unread emails found")
                return []
            
            logger.info(f"Found {len(messages)} unread email(s)")
            
            unread_emails = []
            for msg in messages:
                try:
                    msg_data = self.service.users().messages().get(
                        userId="me",
                        id=msg["id"]
                    ).execute()
                    
                    payload = msg_data["payload"]
                    headers = {h["name"]: h["value"] for h in payload["headers"]}
                    
                    # Extract thread ID for reply threading
                    thread_id = msg_data.get("threadId")
                    
                    sender = headers.get("From", "")
                    subject = headers.get("Subject", "")
                    body = self._get_email_body(payload)
                    
                    # Validate and extract email address
                    sender_email = EmailValidator.extract_email_address(sender)
                    
                    if not sender_email:
                        logger.warning(f"Invalid sender email: {sender}")
                        continue
                    
                    # Sanitize body
                    body = EmailValidator.sanitize_email_body(body)
                    
                    unread_emails.append({
                        "id": msg["id"],
                        "thread_id": thread_id,
                        "sender": sender_email,
                        "sender_full": sender,
                        "subject": subject,
                        "body": body
                    })
                    
                    logger.debug(f"Processed email from {sender_email}: {subject}")
                
                except HttpError as e:
                    logger.error(f"Error fetching email {msg['id']}: {e}")
                    continue
            
            return unread_emails
        
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise GmailAPIError(f"Failed to fetch emails: {e}")
    
    @retry_with_backoff(max_retries=Config.MAX_RETRIES, exceptions=(HttpError,))
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None
    ) -> Dict:
        """
        Send email reply
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            thread_id: Optional thread ID to reply in existing thread
            in_reply_to: Optional Message-ID of original message
            references: Optional References header value
            
        Returns:
            Sent message metadata
        """
        if not self.service:
            raise GmailAPIError("Gmail service not authenticated")
        
        try:
            if html_body and Config.ENABLE_HTML_EMAILS:
                # Create multipart message
                message = MIMEMultipart('alternative')
                message['to'] = to
                message['subject'] = subject
                
                # Add plain text and HTML parts
                text_part = MIMEText(body, 'plain')
                html_part = MIMEText(html_body, 'html')
                
                message.attach(text_part)
                message.attach(html_part)
            else:
                # Create plain text message
                message = MIMEText(body)
                message['to'] = to
                message['subject'] = subject

            # For robust Gmail threading, include reply headers when available.
            if in_reply_to:
                message['In-Reply-To'] = in_reply_to
                message['References'] = references or in_reply_to
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Build send request body
            send_body = {"raw": raw}
            
            # Add thread ID if provided (for threading replies)
            if thread_id:
                send_body["threadId"] = thread_id
                logger.debug(f"Sending reply in thread: {thread_id}")
            
            send_result = self.service.users().messages().send(
                userId="me",
                body=send_body
            ).execute()
            
            logger.info(
                f"Sent email to {to}: {subject} "
                f"(thread: {thread_id or 'new'}, in-reply-to: {'yes' if in_reply_to else 'no'})"
            )
            return send_result
        
        except HttpError as e:
            logger.error(f"Error sending email to {to}: {e}")
            raise GmailAPIError(f"Failed to send email: {e}")
    
    @retry_with_backoff(max_retries=Config.MAX_RETRIES, exceptions=(HttpError,))
    def mark_as_read(self, message_id: str):
        """
        Mark email as read
        
        Args:
            message_id: Gmail message ID
        """
        if not self.service:
            raise GmailAPIError("Gmail service not authenticated")
        
        try:
            self.service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            
            logger.debug(f"Marked email {message_id} as read")
        
        except HttpError as e:
            logger.error(f"Error marking email {message_id} as read: {e}")
            raise GmailAPIError(f"Failed to mark email as read: {e}")
    
    def get_email_by_id(self, message_id: str) -> Optional[Dict]:
        """
        Get email by message ID
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Email dictionary or None
        """
        try:
            msg_data = self.service.users().messages().get(
                userId="me",
                id=message_id
            ).execute()
            
            payload = msg_data["payload"]
            headers = {h["name"]: h["value"] for h in payload["headers"]}
            
            return {
                "id": message_id,
                "thread_id": msg_data.get("threadId"),
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "message_id": headers.get("Message-ID", ""),
                "references": headers.get("References", ""),
                "body": self._get_email_body(payload)
            }
        
        except HttpError as e:
            logger.error(f"Error fetching email {message_id}: {e}")
            return None
