"""
Email tasks using Celery
"""
from celery import shared_task
from app.core.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

@shared_task(bind=True, max_retries=3)
def send_email_task(self, recipient: str, subject: str, body: str):
    """Send email task with retry logic"""
    try:
        # Simple SMTP email sending (would connect to actual email service in production)
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_USERNAME
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # In real implementation, you would connect to SMTP server here
        # For now, just log the attempt
        print(f"Sending email to {recipient}: {subject}")
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * 2 ** self.request.retries)

@shared_task(bind=True, max_retries=3)
def send_order_confirmation_email(self, user_email: str, order_id: int, order_details: dict):
    """Send order confirmation email task"""
    try:
        subject = f"Order Confirmation #{order_id}"
        body = f"""
        Thank you for your order #{order_id}!
        
        Order Details:
        {order_details}
        
        Expected delivery: 3-5 business days
        
        Best regards,
        E-Commerce Team
        """
        
        # This would actually send via SMTP in production
        print(f"Sending order confirmation to {user_email}")
        
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * 2 ** self.request.retries)