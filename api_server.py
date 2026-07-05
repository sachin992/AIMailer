"""
Flask API server for AIMailer admin dashboard
Provides REST API for managing emails, reviewing responses, and viewing analytics
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from typing import Dict, Any

from config import Config
from logger import get_logger, setup_logging
from database import Database
from gmail_client import GmailClient
from ai_generator import AIGenerator
from monitoring import AnalyticsEngine
from templates import TemplateManager
from auth import (
    PasswordHasher, 
    PasswordValidator, 
    TokenManager, 
    AuthError,
    token_required,
    role_required
)

# Setup logging
setup_logging()
logger = get_logger("api_server")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Initialize components
db = Database(Config.DATABASE_PATH)
analytics = AnalyticsEngine(db)
gmail_client = None
ai_generator = None
template_manager = None


@app.before_request
def before_request():
    """Initialize components on first request"""
    global gmail_client, ai_generator, template_manager

    # Skip heavy initialization for health/auth endpoints
    if request.path.startswith('/api/auth') or request.path == '/api/health':
        return
    
    if gmail_client is None:
        try:
            gmail_client = GmailClient()
            ai_generator = AIGenerator()
            template_manager = TemplateManager()
            logger.info("API components initialized")
        except Exception as e:
            logger.error(f"Error initializing components: {e}")


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })


# =====================
# Authentication Routes
# =====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new admin user"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role', 'admin')
        if role not in ['admin', 'super_admin']:
            return jsonify({
                "success": False,
                "error": "Invalid role. Allowed roles: admin, super_admin"
            }), 400
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required"
            }), 400

        # Bootstrap behavior: first user can be created without auth.
        # After at least one user exists, only super_admin can register new users.
        existing_users = db.list_admin_users()
        if existing_users:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error": "Only super_admin can register new users"
                }), 403

            token = auth_header.split(' ', 1)[1]
            try:
                payload = TokenManager.verify_access_token(token)
            except AuthError as e:
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 401

            if payload.get('role') != 'super_admin':
                return jsonify({
                    "success": False,
                    "error": "Only super_admin can register new users"
                }), 403
        
        # Validate password strength
        is_valid, error_msg = PasswordValidator.validate(password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg
            }), 400
        
        # Check if user already exists
        existing_user = db.get_admin_user_by_email(email)
        if existing_user:
            return jsonify({
                "success": False,
                "error": "User with this email already exists"
            }), 409
        
        # Hash password
        password_hash = PasswordHasher.hash_password(password)
        
        # Create user
        user_id = db.create_admin_user(email, password_hash, name or email.split('@')[0], role)
        
        logger.info(f"New admin user registered: {email}")
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login and get JWT tokens"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "Email and password are required"
            }), 400
        
        # Get user from database
        user = db.get_admin_user_by_email(email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": "Invalid credentials"
            }), 401
        
        # Check if user is active
        if not user.get('is_active'):
            return jsonify({
                "success": False,
                "error": "Account is deactivated"
            }), 401
        
        # Verify password
        if not PasswordHasher.verify_password(password, user['password_hash']):
            return jsonify({
                "success": False,
                "error": "Invalid credentials"
            }), 401
        
        # Update last login
        db.update_admin_last_login(user['id'])
        
        # Generate tokens
        access_token = TokenManager.generate_access_token(
            user['id'], 
            user['email'], 
            user['role']
        )
        refresh_token = TokenManager.generate_refresh_token(
            user['id'], 
            user['email']
        )
        
        logger.info(f"User logged in: {email}")
        
        return jsonify({
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/refresh', methods=['POST'])
def refresh():
    """Refresh access token using refresh token"""
    try:
        data = request.json
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({
                "success": False,
                "error": "Refresh token is required"
            }), 400
        
        # Verify refresh token
        try:
            payload = TokenManager.verify_refresh_token(refresh_token)
        except AuthError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
        
        # Get user
        user = db.get_admin_user_by_id(payload['user_id'])
        
        if not user or not user.get('is_active'):
            return jsonify({
                "success": False,
                "error": "User not found or inactive"
            }), 401
        
        # Generate new access token
        access_token = TokenManager.generate_access_token(
            user['id'],
            user['email'],
            user['role']
        )
        
        return jsonify({
            "success": True,
            "access_token": access_token
        }), 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Get current user information"""
    try:
        user = db.get_admin_user_by_id(current_user['user_id'])
        
        if not user:
            return jsonify({
                "success": False,
                "error": "User not found"
            }), 404
        
        return jsonify({
            "success": True,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "is_active": user['is_active'],
                "last_login": user['last_login'],
                "created_at": user['created_at']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/auth/users', methods=['GET'])
@token_required
@role_required('super_admin')
def list_users(current_user):
    """List admin users (super_admin only)"""
    try:
        users = db.list_admin_users()
        return jsonify({
            "success": True,
            "count": len(users),
            "users": users
        }), 200
    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/config', methods=['GET'])
@token_required
def get_config(current_user):
    """Get configuration summary"""
    return jsonify({
        "config": Config.get_summary(),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/emails/pending-review', methods=['GET'])
@token_required
def get_pending_review_emails(current_user):
    """Get emails requiring manual review"""
    try:
        limit = request.args.get('limit', 50, type=int)
        emails = db.get_pending_review_emails(limit=limit)
        
        return jsonify({
            "success": True,
            "count": len(emails),
            "emails": emails
        })
    
    except Exception as e:
        logger.error(f"Error fetching pending emails: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/emails/recent', methods=['GET'])
@token_required
def get_recent_emails(current_user):
    """Get recently processed emails"""
    try:
        limit = request.args.get('limit', 20, type=int)
        emails = db.get_recent_emails(limit=limit)
        
        return jsonify({
            "success": True,
            "count": len(emails),
            "emails": emails
        })
    
    except Exception as e:
        logger.error(f"Error fetching recent emails: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/emails/<email_id>', methods=['GET'])
@token_required
def get_email_details(current_user, email_id: str):
    """Get detailed information about an email"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get email data
            cursor.execute(
                "SELECT * FROM processed_emails WHERE email_id = ?",
                (email_id,)
            )
            email = cursor.fetchone()
            
            if not email:
                return jsonify({
                    "success": False,
                    "error": "Email not found"
                }), 404
            
            # Get FAQ matches
            cursor.execute(
                "SELECT * FROM faq_matches WHERE email_id = ? ORDER BY rank",
                (email_id,)
            )
            faq_matches = [dict(row) for row in cursor.fetchall()]
            
            # Get responses
            cursor.execute(
                "SELECT * FROM responses WHERE email_id = ? ORDER BY created_at DESC",
                (email_id,)
            )
            responses = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                "success": True,
                "email": dict(email),
                "faq_matches": faq_matches,
                "responses": responses
            })
    
    except Exception as e:
        logger.error(f"Error fetching email details: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/emails/<email_id>/approve-and-send', methods=['POST'])
@token_required
def approve_and_send_response(current_user, email_id: str):
    """Approve and send a response for an email"""
    try:
        data = request.json
        # Use authenticated user's email
        admin_email = current_user['email']
        response_text = data.get('response_text')
        custom_response = data.get('custom_response', False)
        
        if not response_text:
            return jsonify({
                "success": False,
                "error": "Response text is required"
            }), 400
        
        # Get email details
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sender, subject, thread_id FROM processed_emails WHERE email_id = ?",
                (email_id,)
            )
            email_data = cursor.fetchone()
            
            if not email_data:
                return jsonify({
                    "success": False,
                    "error": "Email not found"
                }), 404
        
        sender = email_data['sender']
        subject = email_data['subject']
        # sqlite3.Row behaves like a mapping but does not implement .get()
        thread_id = email_data['thread_id'] if 'thread_id' in email_data.keys() else None
        in_reply_to = None
        references = None

        if gmail_client is None:
            return jsonify({
                "success": False,
                "error": "Email service is not initialized"
            }), 503

        # Fallback: if thread metadata is missing in DB, fetch from Gmail by message id.
        source_email = gmail_client.get_email_by_id(email_id)
        if source_email:
            thread_id = thread_id or source_email.get("thread_id")
            in_reply_to = source_email.get("message_id") or None
            references = source_email.get("references") or in_reply_to
        
        # Render template if HTML enabled
        html_body = None
        if Config.ENABLE_HTML_EMAILS and template_manager is not None:
            html_body = template_manager.render_template(response_text)
        
        # Send email (reply in thread)
        gmail_client.send_email(
            to=sender,
            subject=f"Re: {subject}",
            body=response_text,
            html_body=html_body,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            references=references
        )
        
        # Save response to database (mark as sent)
        db.save_response(
            email_id=email_id,
            response_text=response_text,
            response_type="manual" if custom_response else "approved",
            is_automatic=False,
            approved_by=admin_email,
            mark_as_sent=True
        )
        
        # Mark as reviewed
        db.mark_email_reviewed(email_id, admin_email)
        
        # Log admin action
        db.save_admin_action(
            email_id=email_id,
            admin_email=admin_email,
            action_type="approve_and_send",
            action_data={"custom_response": custom_response}
        )
        
        # Mark as read
        gmail_client.mark_as_read(email_id)
        
        logger.info(f"Admin {admin_email} approved and sent response for {email_id}")
        
        return jsonify({
            "success": True,
            "message": "Response sent successfully"
        })
    
    except Exception as e:
        logger.error(f"Error approving and sending response: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/emails/<email_id>/generate-response', methods=['POST'])
@token_required
def generate_custom_response(current_user, email_id: str):
    """Generate a custom response for an email"""
    try:
        data = request.json
        custom_instructions = data.get('instructions', '')
        
        # Get email body
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT body FROM processed_emails WHERE email_id = ?",
                (email_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    "success": False,
                    "error": "Email not found"
                }), 404
            
            user_query = result['body']
        
        # Generate response
        response = ai_generator.generate_custom_response(
            user_query=user_query,
            custom_instructions=custom_instructions
        )
        
        return jsonify({
            "success": True,
            "response": response
        })
    
    except Exception as e:
        logger.error(f"Error generating custom response: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/analytics/summary', methods=['GET'])
@token_required
def get_analytics_summary(current_user):
    """Get analytics summary"""
    try:
        period = request.args.get('period', 'weekly')
        
        if period == 'daily':
            summary = analytics.get_daily_summary()
        elif period == 'weekly':
            summary = analytics.get_weekly_summary()
        elif period == 'monthly':
            summary = analytics.get_monthly_summary()
        else:
            return jsonify({
                "success": False,
                "error": "Invalid period. Use: daily, weekly, or monthly"
            }), 400
        
        return jsonify({
            "success": True,
            "period": period,
            "summary": summary
        })
    
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/analytics/insights', methods=['GET'])
@token_required
def get_performance_insights(current_user):
    """Get performance insights"""
    try:
        insights = analytics.get_performance_insights()
        
        return jsonify({
            "success": True,
            "insights": insights
        })
    
    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/analytics/export', methods=['POST'])
@token_required
@role_required('admin', 'super_admin')
def export_analytics_report(current_user):
    """Export analytics report (admin only)"""
    try:
        output_file = analytics.export_analytics_report()
        
        return jsonify({
            "success": True,
            "file": output_file,
            "message": "Report exported successfully"
        })
    
    except Exception as e:
        logger.error(f"Error exporting report: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    port = Config.ADMIN_API_PORT
    logger.info(f"Starting API server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
