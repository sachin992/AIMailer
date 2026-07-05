"""
Authentication module for AIMailer Admin Dashboard
Provides secure authentication with JWT tokens, password hashing, and role-based access
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify

from logger import get_logger

logger = get_logger("auth")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


class AuthError(Exception):
    """Authentication error"""
    pass


class PasswordHasher:
    """Password hashing utilities using bcrypt"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password as string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            password: Plain text password
            hashed_password: Hashed password to verify against
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


class PasswordValidator:
    """Password strength validation"""
    
    @staticmethod
    def validate(password: str) -> tuple[bool, Optional[str]]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        # Check for special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        return True, None


class TokenManager:
    """JWT token generation and validation"""
    
    @staticmethod
    def generate_access_token(user_id: int, email: str, role: str) -> str:
        """
        Generate JWT access token
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            
        Returns:
            JWT token string
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"Access token generated for user: {email}")
        return token
    
    @staticmethod
    def generate_refresh_token(user_id: int, email: str) -> str:
        """
        Generate JWT refresh token
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            JWT refresh token string
        """
        payload = {
            "user_id": user_id,
            "email": email,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.info(f"Refresh token generated for user: {email}")
        return token
    
    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthError(f"Invalid token: {str(e)}")
    
    @staticmethod
    def verify_access_token(token: str) -> Dict[str, Any]:
        """
        Verify access token
        
        Args:
            token: JWT access token
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthError: If token is invalid
        """
        payload = TokenManager.decode_token(token)
        
        if payload.get("type") != "access":
            raise AuthError("Invalid token type")
        
        return payload
    
    @staticmethod
    def verify_refresh_token(token: str) -> Dict[str, Any]:
        """
        Verify refresh token
        
        Args:
            token: JWT refresh token
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthError: If token is invalid
        """
        payload = TokenManager.decode_token(token)
        
        if payload.get("type") != "refresh":
            raise AuthError("Invalid token type")
        
        return payload


def token_required(f):
    """
    Decorator to protect routes with JWT authentication
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected_route(current_user):
            return jsonify(current_user)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                # Bearer token format: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    "success": False,
                    "error": "Invalid Authorization header format"
                }), 401
        
        if not token:
            return jsonify({
                "success": False,
                "error": "Authentication token is missing"
            }), 401
        
        try:
            # Verify token
            payload = TokenManager.verify_access_token(token)
            current_user = {
                "user_id": payload["user_id"],
                "email": payload["email"],
                "role": payload["role"]
            }
            
        except AuthError as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
        
        # Pass current_user to the route
        return f(current_user, *args, **kwargs)
    
    return decorated


def role_required(*allowed_roles):
    """
    Decorator to check user role
    
    Usage:
        @app.route('/admin-only')
        @token_required
        @role_required('admin', 'super_admin')
        def admin_route(current_user):
            return jsonify({"message": "Admin access granted"})
    """
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            user_role = current_user.get("role")
            
            if user_role not in allowed_roles:
                return jsonify({
                    "success": False,
                    "error": f"Access denied. Required role: {', '.join(allowed_roles)}"
                }), 403
            
            return f(current_user, *args, **kwargs)
        
        return decorated
    return decorator
