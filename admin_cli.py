"""
Admin User Management CLI
Create, list, and manage admin users for AIMailer dashboard
"""
import sys
import getpass
from database import Database
from auth import PasswordHasher, PasswordValidator
from config import Config
from logger import setup_logging, get_logger

setup_logging()
logger = get_logger("admin_cli")

db = Database(Config.DATABASE_PATH)


def create_admin():
    """Create a new admin user interactively"""
    print("\n" + "="*60)
    print("CREATE NEW ADMIN USER")
    print("="*60 + "\n")
    
    # Get email
    email = input("Email: ").strip()
    if not email or '@' not in email:
        print("❌ Invalid email address")
        return
    
    # Check if user exists
    existing_user = db.get_admin_user_by_email(email)
    if existing_user:
        print(f"❌ User with email {email} already exists")
        return
    
    # Get name
    name = input("Name (optional, press Enter to use email prefix): ").strip()
    if not name:
        name = email.split('@')[0]
    
    # Get password
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")
    
    if password != password_confirm:
        print("❌ Passwords don't match")
        return
    
    # Validate password
    is_valid, error_msg = PasswordValidator.validate(password)
    if not is_valid:
        print(f"❌ {error_msg}")
        return
    
    # Get role
    print("\nAvailable roles:")
    print("  1. admin (standard admin)")
    print("  2. super_admin (full access)")
    role_choice = input("Select role (1 or 2) [default: 1]: ").strip() or "1"
    
    role = "super_admin" if role_choice == "2" else "admin"
    
    # Confirm
    print(f"\n📝 Creating user:")
    print(f"   Email: {email}")
    print(f"   Name: {name}")
    print(f"   Role: {role}")
    confirm = input("\nProceed? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    # Hash password and create user
    try:
        password_hash = PasswordHasher.hash_password(password)
        user_id = db.create_admin_user(email, password_hash, name, role)
        
        print(f"\n✅ Admin user created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print("\n🔐 You can now login with these credentials")
        
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        logger.error(f"Error creating admin user: {e}")


def list_admins():
    """List all admin users"""
    print("\n" + "="*60)
    print("ADMIN USERS LIST")
    print("="*60 + "\n")
    
    try:
        users = db.list_admin_users()
        
        if not users:
            print("No admin users found.")
            return
        
        print(f"{'ID':<5} {'Email':<30} {'Name':<20} {'Role':<12} {'Active':<8} {'Last Login'}")
        print("-" * 110)
        
        for user in users:
            last_login = user['last_login'] or 'Never'
            if user['last_login']:
                last_login = last_login[:19]  # Trim timestamp
            
            status = '✓' if user['is_active'] else '✗'
            
            print(f"{user['id']:<5} {user['email']:<30} {user['name']:<20} {user['role']:<12} {status:<8} {last_login}")
        
        print()
        
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        logger.error(f"Error listing admin users: {e}")


def deactivate_admin():
    """Deactivate an admin user"""
    print("\n" + "="*60)
    print("DEACTIVATE ADMIN USER")
    print("="*60 + "\n")
    
    email = input("Email of user to deactivate: ").strip()
    
    user = db.get_admin_user_by_email(email)
    if not user:
        print(f"❌ User not found: {email}")
        return
    
    if not user['is_active']:
        print(f"❌ User is already deactivated")
        return
    
    print(f"\n⚠️  Deactivating user:")
    print(f"   Email: {user['email']}")
    print(f"   Name: {user['name']}")
    confirm = input("\nProceed? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    try:
        db.deactivate_admin_user(user['id'])
        print(f"✅ User deactivated: {email}")
    except Exception as e:
        print(f"❌ Error: {e}")


def change_password():
    """Change admin user password"""
    print("\n" + "="*60)
    print("CHANGE ADMIN PASSWORD")
    print("="*60 + "\n")
    
    email = input("Email: ").strip()
    
    user = db.get_admin_user_by_email(email)
    if not user:
        print(f"❌ User not found: {email}")
        return
    
    # Get new password
    password = getpass.getpass("New Password: ")
    password_confirm = getpass.getpass("Confirm Password: ")
    
    if password != password_confirm:
        print("❌ Passwords don't match")
        return
    
    # Validate password
    is_valid, error_msg = PasswordValidator.validate(password)
    if not is_valid:
        print(f"❌ {error_msg}")
        return
    
    try:
        password_hash = PasswordHasher.hash_password(password)
        db.update_admin_password(user['id'], password_hash)
        print(f"✅ Password updated for {email}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main CLI menu"""
    while True:
        print("\n" + "="*60)
        print("AIMAILER ADMIN MANAGEMENT")
        print("="*60)
        print("\n1. Create new admin user")
        print("2. List all admin users")
        print("3. Deactivate admin user")
        print("4. Change admin password")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            create_admin()
        elif choice == '2':
            list_admins()
        elif choice == '3':
            deactivate_admin()
        elif choice == '4':
            change_password()
        elif choice == '5':
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid option")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
