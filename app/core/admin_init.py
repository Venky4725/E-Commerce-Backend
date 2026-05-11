"""
Admin user initialization

This module creates the default admin user on application startup if it doesn't exist.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.core.security import get_password_hash
from app.crud.user_crud import get_user_by_username, get_user_by_email

logger = logging.getLogger(__name__)

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@gmail.com"
DEFAULT_ADMIN_PASSWORD = "admin123"


async def create_default_admin(db: AsyncSession) -> None:
    """
    Create default admin user if it doesn't exist.
    
    Default credentials:
        Username: admin
        Email: admin@gmail.com
        Password: admin123
        is_superuser: True
    """
    try:
        # Check if admin already exists by username
        existing_admin = await get_user_by_username(db, DEFAULT_ADMIN_USERNAME)
        if existing_admin:
            logger.info(f"✅ Admin user already exists: {DEFAULT_ADMIN_USERNAME}")
            return
        
        # Check if admin already exists by email
        existing_admin_email = await get_user_by_email(db, DEFAULT_ADMIN_EMAIL)
        if existing_admin_email:
            logger.info(f"✅ Admin user already exists with email: {DEFAULT_ADMIN_EMAIL}")
            return
        
        # Create admin user
        admin_user = User(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True
        )
        
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
        
        logger.info("=" * 70)
        logger.info("🎉 DEFAULT ADMIN USER CREATED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info(f"   Username:     {DEFAULT_ADMIN_USERNAME}")
        logger.info(f"   Email:        {DEFAULT_ADMIN_EMAIL}")
        logger.info(f"   Password:     {DEFAULT_ADMIN_PASSWORD}")
        logger.info(f"   Is Admin:     True")
        logger.info(f"   Is Superuser: True")
        logger.info("=" * 70)
        logger.info("⚠️  IMPORTANT: Change the admin password after first login!")
        logger.info("=" * 70)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error creating default admin user: {e}")
        raise
