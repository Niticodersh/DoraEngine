"""Email delivery utility using Gmail SMTP.

Setup (one-time):
  1. Enable 2-Step Verification on your Google account:
     https://myaccount.google.com/security
  2. Create an App Password (select "Mail" + "Windows Computer"):
     https://myaccount.google.com/apppasswords
  3. Add to your .env file:
       GMAIL_USER=your_gmail@gmail.com
       GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   ← 16-char app password

If these vars are not set, email sending is skipped and the reset link is
returned in the API response (dev mode) so the flow still works locally.
"""
from __future__ import annotations

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from utils.config import get_secret


def _get_smtp_creds() -> tuple[str, str] | None:
    user = get_secret("GMAIL_USER", "")
    pw = get_secret("GMAIL_APP_PASSWORD", "")
    if user and pw:
        return user, pw
    return None


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Sends a password-reset email via Gmail SMTP.

    Returns True if sent, False if skipped (creds not configured).
    Raises on SMTP errors.
    """
    creds = _get_smtp_creds()
    if not creds:
        return False  # Dev mode — caller should return dev_reset_url instead

    gmail_user, gmail_app_password = creds

    subject = "Reset your DoraEngine password"

    html_body = f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Reset your DoraEngine password</title>
</head>
<body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:40px 20px;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0"
               style="background:#1a1d27;border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:36px 40px;text-align:center;">
              <div style="font-size:28px;font-weight:800;color:#fff;letter-spacing:-0.5px;">DoraEngine</div>
              <div style="color:rgba(255,255,255,0.75);font-size:13px;margin-top:4px;">Autonomous AI Research Agent</div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h1 style="margin:0 0 12px;color:#f1f5f9;font-size:22px;font-weight:700;">Reset your password</h1>
              <p style="margin:0 0 28px;color:#94a3b8;font-size:15px;line-height:1.6;">
                We received a request to reset the password for your DoraEngine account
                (<strong style="color:#cbd5e1;">{to_email}</strong>).<br/><br/>
                Click the button below to choose a new password. This link expires in
                <strong style="color:#a5b4fc;">30 minutes</strong>.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 auto 32px;">
                <tr>
                  <td style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:10px;">
                    <a href="{reset_url}"
                       style="display:inline-block;padding:14px 36px;color:#fff;font-size:15px;
                              font-weight:600;text-decoration:none;letter-spacing:0.2px;">
                      Reset my password →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:0 0 8px;color:#64748b;font-size:12px;">
                Button not working? Copy and paste this link into your browser:
              </p>
              <p style="margin:0 0 32px;word-break:break-all;">
                <a href="{reset_url}" style="color:#818cf8;font-size:12px;">{reset_url}</a>
              </p>

              <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:0 0 28px;" />

              <p style="margin:0;color:#475569;font-size:12px;line-height:1.6;">
                If you didn't request this, you can safely ignore this email — your password
                won't change. For security, this link can only be used once.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px;background:#13151f;text-align:center;">
              <p style="margin:0;color:#334155;font-size:11px;">
                © 2025 DoraEngine · Built by Nitish Bhardwaj
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    plain_body = (
        f"Reset your DoraEngine password\n\n"
        f"Click the link below to reset your password (expires in 30 minutes):\n\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, ignore this email."
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"DoraEngine <{gmail_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, to_email, msg.as_string())

    return True


def send_signup_otp_email(to_email: str, otp: str) -> bool:
    """
    Sends a beautifully formatted OTP email via Gmail SMTP for new signups.
    Returns True if sent, False if skipped (creds not configured).
    """
    creds = _get_smtp_creds()
    if not creds:
        return False  # Dev mode

    gmail_user, gmail_app_password = creds
    subject = f"{otp} is your DoraEngine verification code"

    html_body = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:20px;font-family:sans-serif;background:#0f1117;color:#fff;">
  <div style="max-width:500px;margin:0 auto;background:#1a1d27;padding:30px;border-radius:12px;border:1px solid rgba(255,255,255,0.08);text-align:center;">
    <h1 style="margin:0 0 10px;font-size:20px;font-weight:700;">Verify your email</h1>
    <p style="color:#94a3b8;font-size:15px;line-height:1.5;">Use the following 6-digit code to complete your DoraEngine sign up.</p>
    <div style="background:rgba(255,255,255,0.05);border:1px dashed rgba(255,255,255,0.2);padding:15px;font-size:28px;letter-spacing:6px;font-weight:bold;color:#8b5cf6;border-radius:8px;margin:20px 0;">{otp}</div>
    <p style="color:#64748b;font-size:13px;">This code will expire in 10 minutes.</p>
  </div>
</body>
</html>
"""

    plain_body = f"Verify your DoraEngine email.\n\nYour code is: {otp}\n\nThis code expires in 10 minutes."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"DoraEngine <{gmail_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, to_email, msg.as_string())

    return True
