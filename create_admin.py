"""
Create default admin user

Run this script to create the default admin user:
    python create_admin.py

Default credentials:
    Email: admin@gmail.com
    Password: admin123
    Username: admin
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.crud.user_crud import get_user_by_email, get_user_by_username
from app.models.user import User
from app.core.security import get_password_hash


async def create_admin_user():
    """Create default admin user if not exists."""
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin already exists
            admin_by_email = await get_user_by_email(db, "admin@gmail.com")
            admin_by_username = await get_user_by_username(db, "admin")
            
            if admin_by_email or admin_by_username:
                print("❌ Admin user already exists!")
                print("   Email: admin@gmail.com")
                print("   Username: admin")
                return
            
            # Create admin user
            admin = User(
                username="admin",
                email="admin@gmail.com",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True
            )
            
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            
            print("✅ Admin user created successfully!")
            print("   Email: admin@gmail.com")
            print("   Username: admin")
            print("   Password: admin123")
            print("   Is Superuser: True")
            print("\n🔐 You can now login with these credentials")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating admin user: {e}")
            raise


if __name__ == "__main__":
    print("Creating default admin user...")
    print("=" * 50)
    asyncio.run(create_admin_user())
    print("=" * 50)
