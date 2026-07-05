"""
Email template manager for AIMailer
Handles email template loading and rendering
"""
import os
from typing import Dict, Optional
from pathlib import Path

from config import Config
from logger import get_logger

logger = get_logger("templates")


class TemplateManager:
    """Manages email templates"""
    
    def __init__(self):
        """Initialize template manager"""
        self.template_folder = Path(Config.EMAIL_TEMPLATE_FOLDER)
        self._ensure_template_folder()
    
    def _ensure_template_folder(self):
        """Ensure template folder exists"""
        if not self.template_folder.exists():
            logger.warning(f"Template folder not found: {self.template_folder}")
            self.template_folder.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created template folder: {self.template_folder}")
    
    def load_template(self, template_name: Optional[str] = None) -> str:
        """
        Load email template
        
        Args:
            template_name: Name of template file (default: default.html)
            
        Returns:
            Template content as string
        """
        template_name = template_name or Config.DEFAULT_EMAIL_TEMPLATE
        template_path = self.template_folder / template_name
        
        try:
            if not template_path.exists():
                logger.warning(f"Template not found: {template_path}")
                return self._get_default_template()
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            logger.debug(f"Loaded template: {template_name}")
            return template_content
        
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            return self._get_default_template()
    
    def render_template(
        self,
        content: str,
        greeting: str = "Dear User,",
        signature: str = "Thank you for contacting us.",
        template_name: Optional[str] = None
    ) -> str:
        """
        Render email template with content
        
        Args:
            content: Main email content
            greeting: Email greeting
            signature: Email signature
            template_name: Template to use
            
        Returns:
            Rendered HTML email
        """
        template = self.load_template(template_name)
        
        # Replace placeholders
        rendered = template.replace("{{GREETING}}", greeting)
        rendered = rendered.replace("{{CONTENT}}", self._format_content(content))
        rendered = rendered.replace("{{SIGNATURE}}", signature)
        
        logger.debug("Rendered email template")
        return rendered
    
    def _format_content(self, content: str) -> str:
        """
        Format plain text content for HTML display
        
        Args:
            content: Plain text content
            
        Returns:
            HTML-formatted content
        """
        # Convert line breaks to <br> tags
        content = content.replace('\n', '<br>')
        
        # Wrap paragraphs
        paragraphs = content.split('<br><br>')
        formatted_paragraphs = [
            f'<p>{para}</p>' for para in paragraphs if para.strip()
        ]
        
        return ''.join(formatted_paragraphs)
    
    def _get_default_template(self) -> str:
        """
        Get default fallback template
        
        Returns:
            Default HTML template
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .greeting { margin-bottom: 15px; }
        .content { margin-bottom: 20px; }
        .signature { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="greeting">{{GREETING}}</div>
        <div class="content">{{CONTENT}}</div>
        <div class="signature">{{SIGNATURE}}<br>Support Team</div>
    </div>
</body>
</html>
"""
    
    def create_plain_text_email(
        self,
        content: str,
        greeting: str = "Dear User,",
        signature: str = "Thank you for contacting us."
    ) -> str:
        """
        Create plain text email (fallback)
        
        Args:
            content: Email content
            greeting: Email greeting
            signature: Email signature
            
        Returns:
            Plain text email
        """
        return f"{greeting}\n\n{content}\n\n{signature}\n\nBest regards,\nSupport Team"
