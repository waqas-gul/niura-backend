import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "noreply@niura.io"
EMAIL_PASSWORD = "9<44W2d&TP>m3dV>"

def send_reset_email(to_email: str, reset_link: str):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = "Password Reset Request"

    body = f"""
    Hi,

    To reset your password, click the following link:

    {reset_link}

    If you did not request a password reset, please ignore this email.
    """

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_forgot_password_code(to_email: str, code: str, expiry_minutes: int = 5):
    """Send 6-digit verification code for password reset using HTML template"""
    msg = MIMEMultipart("alternative")
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = "Reset Your Niura Password"

    # HTML template
    html_body = f"""<!DOCTYPE html>
<html lang="en" style="margin:0; padding:0;">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <style>
    :root {{ color-scheme: light dark; }}
    @media (prefers-color-scheme: dark) {{
      .bg-page {{ background:#0b0c10 !important; }}
      .card {{ background:#0e1117 !important; box-shadow:none !important; }}
      .text {{ color:#e5e7eb !important; }}
      .muted {{ color:#9aa4b2 !important; }}
      .divider {{ border-top-color:#273043 !important; }}
      .codebox {{ background:#141a22 !important; border-color:#2a3447 !important; color:#e5e7eb !important; }}
      .btn {{ background:#6366F1 !important; color:#ffffff !important; }}
      .link {{ color:#818cf8 !important; }}
      .hdr {{ background:linear-gradient(135deg,#4F46E5,#6366F1) !important; }}
    }}
    @media only screen and (max-width:600px){{
      .container{{ width:100% !important; border-radius:0 !important; }}
      .px{{ padding-left:20px !important; padding-right:20px !important; }}
    }}
    a.btn:hover {{ opacity:.92 !important; }}
  </style>
</head>
<body class="bg-page" style="margin:0; padding:0; background:#f5f7fb; font-family:Arial, Helvetica, sans-serif;">

  <!-- Preheader (hidden) -->
  <div style="display:none; max-height:0; overflow:hidden; opacity:0;">
    Your Niura verification code is {code}. It expires in {expiry_minutes} minutes.
  </div>

  <!-- Page -->
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" class="bg-page" style="background:#f5f7fb;">
    <tr>
      <td align="center" style="padding:40px 16px;">

        <!-- Card -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px; background:#ffffff; margin:0 auto; border-radius:12px; box-shadow:0 6px 16px rgba(0,0,0,0.08);" class="container card">
          <!-- Header -->
          <tr>
            <td class="hdr" style="background:linear-gradient(135deg,#4F46E5,#6366F1); padding:30px; text-align:center; border-top-left-radius:12px; border-top-right-radius:12px;">
              <!-- Niura logo centered -->
              <img src="https://images.crunchbase.com/image/upload/c_pad,h_256,w_256,f_auto,q_auto:eco,dpr_1/36d67535382f4b69adb4e873d9447454" alt="Niura" width="100" height="100" style="display:block; margin:0 auto 12px; border:0; outline:0; border-radius:8px;">
              <h1 style="color:#ffffff; margin:0; font-size:22px; font-weight:700;">Reset Your Password</h1>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td class="px text" style="padding:26px 40px 0 40px; color:#1f2937;">
              <p style="font-size:16px; line-height:1.6; margin:0 0 16px 0;">
                We received a request to reset your password. Use this verification code to continue:
              </p>

              <!-- Code Box -->
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td class="codebox" style="background:#f3f5f9; text-align:center; padding:20px; border-radius:8px; border:1px solid #e6ebf2; margin:16px 0;">
                    <div style="font-size:26px; font-weight:800; letter-spacing:6px; color:#4F46E5; font-family:Menlo,Consolas,Monaco,monospace;">
                      {code}
                    </div>

                  </td>
                </tr>
              </table>
<center>
              <p class="muted" style="font-size:14px; color:#6b7280; line-height:1.6; margin:16px 0 0 0;">
                If you didn't request this, you can safely ignore this email.
              </p><br>
              </center>
            </td>
          </tr>
          

          <!-- Divider -->
          <tr>
            <td style="padding:0 40px;">
              <hr class="divider" style="border:none; border-top:1px solid #e8ecf4; margin:0;">
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:18px 20px; text-align:center; font-size:12px; color:#888888;">
              &copy; 2025 Niura Corporation. All rights reserved.<br><br>
              <a href="https://cdn.prod.website-files.com/6696eab638e8c317127f8e0d/66a010f128935ada175f606f_TERMS%20OF%20USE%20(Have%20Lawyer%20Review%20Later)%20Last%20Updated%2012_19_2023.pdf" class="link" style="color:#6366F1; text-decoration:none;">Privacy Policy</a> ·
              <a href="https://www.niura.io/contact" class="link" style="color:#6366F1; text-decoration:none;">Support</a>
            </td>
          </tr>
        </table>
        <!-- /Card -->

        <!-- Socials (below the card) -->
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:600px; margin:12px auto 0;">
          <tr>
            <td align="center" style="font-size:12px; color:#6b7280; padding:8px 0;">
              <a href="https://www.niura.io" style="text-decoration:none; color:#6b7280; margin:0 10px;">Website</a> ·
              <a href="https://www.linkedin.com/company/niura" style="text-decoration:none; color:#6b7280; margin:0 10px;">LinkedIn</a> ·
              <a href="https://www.instagram.com/niura.io/?hl=en" style="text-decoration:none; color:#6b7280; margin:0 10px;">Instagram</a>
            </td>
          </tr>
        </table>

      </td>
    </tr>
  </table>
</body>
</html>"""

    # Plain text fallback
    text_body = f"""
    Hi,

    Your password reset verification code is:

    {code}

    This code will expire in {expiry_minutes} minutes.

    If you did not request a password reset, please ignore this email.

    Thank you,
    Niura Team
    """

    # Attach both text and HTML versions
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
