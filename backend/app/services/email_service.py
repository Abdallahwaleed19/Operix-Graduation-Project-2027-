"""
app/services/email_service.py
Transactional email delivery service for user invitations, registration approval
requests, and account activation notifications.
Supports Resend HTTPS API (recommended for cloud production) and SMTP fallback.
Never logs invitation tokens or secrets.
"""
from email.message import EmailMessage
import logging
import smtplib
from typing import Iterable

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

_RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    """Sends transactional emails via Resend API or SMTP when configured."""

    @staticmethod
    def is_resend_configured() -> bool:
        return bool(settings.RESEND_API_KEY)

    @staticmethod
    def is_smtp_configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)

    @staticmethod
    def is_configured() -> bool:
        return EmailService.is_resend_configured() or EmailService.is_smtp_configured()

    @staticmethod
    def send_email(
        to_email: str | Iterable[str],
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> bool:
        recipients = [to_email] if isinstance(to_email, str) else [e for e in to_email if e]
        if not recipients:
            return False

        # 1. Prefer Resend HTTPS API when RESEND_API_KEY is configured
        if EmailService.is_resend_configured():
            sender = settings.RESEND_FROM_EMAIL or settings.SMTP_FROM_EMAIL or "onboarding@resend.dev"
            payload: dict = {
                "from": f"Operix Platform <{sender}>",
                "to": recipients,
                "subject": subject,
                "text": text_body,
            }
            if html_body:
                payload["html"] = html_body
            try:
                resp = httpx.post(
                    _RESEND_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=15.0,
                )
                if 200 <= resp.status_code < 300:
                    logger.info("Email '%s' delivered via Resend to %d recipient(s).", subject, len(recipients))
                    return True
                logger.error(
                    "Resend API returned HTTP %s for '%s': %s",
                    resp.status_code,
                    subject,
                    resp.text[:300],
                )
                return False
            except Exception as exc:
                logger.error("Failed to send email '%s' via Resend: %s", subject, exc)
                return False

        # 2. Fallback to SMTP when configured
        if not EmailService.is_smtp_configured():
            logger.warning(
                "Email provider is not configured (set RESEND_API_KEY or SMTP_USER/SMTP_PASSWORD). "
                "Skipping email '%s' to %d recipient(s).",
                subject,
                len(recipients),
            )
            return False

        sender = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"Operix Platform <{sender}>"
        msg["To"] = ", ".join(recipients)
        msg.set_content(text_body)
        if html_body:
            msg.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Email '%s' delivered via SMTP to %d recipient(s).", subject, len(recipients))
            return True
        except Exception as exc:
            logger.error("Failed to send email '%s' via SMTP: %s", subject, exc)
            return False

    @staticmethod
    def send_invite_email(
        *,
        to_email: str,
        full_name: str,
        role_name: str,
        factory_name: str,
        invite_token: str | None = None,
    ) -> bool:
        base_url = settings.FRONTEND_APP_URL.rstrip("/")
        action_url = (
            f"{base_url}/accept-invite?token={invite_token}"
            if invite_token
            else f"{base_url}/login"
        )
        subject = f"You are invited to {factory_name} on Operix"
        text_body = (
            f"Hello {full_name},\n\n"
            f"You have been invited to join {factory_name} on Operix as {role_name}.\n"
            f"Set your password and activate your account at: {action_url}\n"
            f"This link expires in 7 days and can only be used once.\n\n"
            f"Operix Industrial AI Safety Platform"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #1e3a5f; margin-top: 0;">You're invited to Operix</h2>
          <p>Hello <strong>{full_name}</strong>,</p>
          <p>An administrator has invited you to join <strong>{factory_name}</strong> as <strong>{role_name}</strong>.</p>
          <p style="margin: 24px 0;">
            <a href="{action_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Accept Invitation &amp; Set Password
            </a>
          </p>
          <p style="color: #64748b; font-size: 12px;">This single-use link expires in 7 days. If you weren't expecting this invitation, you can ignore this email.</p>
        </div>
        """
        return EmailService.send_email(to_email, subject, text_body, html_body)

    @staticmethod
    def send_registration_request_to_admins(
        *,
        admin_emails: list[str],
        applicant_name: str,
        applicant_email: str,
        role_name: str,
        factory_name: str,
    ) -> bool:
        review_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/settings/users"
        subject = f"[Operix] New account approval request: {applicant_name}"
        text_body = (
            f"Hello Administrator,\n\n"
            f"A new user has requested an account on Operix ({factory_name}):\n"
            f"- Name: {applicant_name}\n"
            f"- Email: {applicant_email}\n"
            f"- Requested Role: {role_name}\n\n"
            f"Please review and approve or reject this request in Users & Roles:\n"
            f"{review_url}\n"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #1e3a5f; margin-top: 0;">New Account Approval Request</h2>
          <p>A new user has registered and is waiting for your approval to access <strong>{factory_name}</strong>:</p>
          <ul style="line-height: 1.7;">
            <li><strong>Name:</strong> {applicant_name}</li>
            <li><strong>Email:</strong> {applicant_email}</li>
            <li><strong>Requested Role:</strong> {role_name}</li>
          </ul>
          <p style="margin: 24px 0;">
            <a href="{review_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Review in Users &amp; Roles
            </a>
          </p>
        </div>
        """
        return EmailService.send_email(admin_emails, subject, text_body, html_body)

    @staticmethod
    def send_password_reset_email(
        *,
        to_email: str,
        full_name: str,
        reset_token: str,
    ) -> bool:
        base_url = settings.FRONTEND_APP_URL.rstrip("/")
        reset_url = f"{base_url}/reset-password?token={reset_token}"
        subject = "Reset your Operix password"
        text_body = (
            f"Hello {full_name},\n\n"
            f"You requested a password reset for your Operix account.\n"
            f"Click the link below to set a new password:\n"
            f"{reset_url}\n\n"
            f"This link expires in 1 hour and can only be used once.\n"
            f"If you did not request this, you can safely ignore this email.\n\n"
            f"Operix Industrial AI Safety Platform"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #1e3a5f; margin-top: 0;">Reset Your Password</h2>
          <p>Hello <strong>{full_name}</strong>,</p>
          <p>We received a request to reset the password for your Operix account.</p>
          <p style="margin: 24px 0;">
            <a href="{reset_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Reset Password
            </a>
          </p>
          <p style="color: #64748b; font-size: 12px;">This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email — your password won't change.</p>
        </div>
        """
        return EmailService.send_email(to_email, subject, text_body, html_body)

    @staticmethod
    def send_account_approved_email(
        *,
        to_email: str,
        full_name: str,
        role_name: str,
        factory_name: str,
    ) -> bool:
        login_url = f"{settings.FRONTEND_APP_URL.rstrip('/')}/login"
        subject = f"Your Operix account for {factory_name} has been approved"
        text_body = (
            f"Hello {full_name},\n\n"
            f"Your Operix account for {factory_name} ({role_name}) has been approved by an administrator.\n"
            f"You can now sign in at: {login_url}\n"
        )
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 10px;">
          <h2 style="color: #15803d; margin-top: 0;">Account Approved</h2>
          <p>Hello <strong>{full_name}</strong>,</p>
          <p>Your account for <strong>{factory_name}</strong> (role: <strong>{role_name}</strong>) has been approved.</p>
          <p style="margin: 24px 0;">
            <a href="{login_url}" style="background: #1e3a5f; color: #fff; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: 600;">
              Sign in to Operix
            </a>
          </p>
        </div>
        """
        return EmailService.send_email(to_email, subject, text_body, html_body)
