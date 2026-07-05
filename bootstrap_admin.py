from database import Database
from config import Config
from auth import PasswordHasher

EMAIL = "admin@aimailer.local"
PASSWORD = "Admin@12345"
NAME = "Admin"
ROLE = "super_admin"

db = Database(Config.DATABASE_PATH)
existing = db.get_admin_user_by_email(EMAIL)
if existing:
    user_id = existing["id"]
    created = False
else:
    password_hash = PasswordHasher.hash_password(PASSWORD)
    user_id = db.create_admin_user(EMAIL, password_hash, NAME, ROLE)
    created = True

print(f"CREATED={created}")
print(f"USER_ID={user_id}")
print(f"EMAIL={EMAIL}")
print(f"PASSWORD={PASSWORD}")
print(f"ROLE={ROLE}")
