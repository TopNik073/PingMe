from typing import Protocol
from datetime import datetime


class EmailTemplate(Protocol):
    """Protocol for email templates"""
    subject: str
    body: str
    html: bool = False

    def render(self) -> str:
        """Render template to string"""
        ...


class TwoFactorAuthTemplate:
    """Template for 2FA verification code"""
    def __init__(self, code: str, username: str):
        self.subject = f"Your verification code: {code}"
        self.html = True
        self.body = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
            ">
                <div style="
                    max-width: 600px;
                    margin: 20px auto;
                    padding: 20px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h1 style="
                        color: #333;
                        margin-bottom: 20px;
                        font-size: 24px;
                    ">Email Verification</h1>
                    
                    <p style="
                        font-size: 16px;
                        color: #555;
                        margin-bottom: 20px;
                    ">Hi {username},</p>
                    
                    <p style="
                        font-size: 16px;
                        color: #555;
                        margin-bottom: 10px;
                    ">Your verification code is:</p>
                    
                    <div style="
                        background-color: #f8f9fa;
                        border: 1px solid #e9ecef;
                        border-radius: 4px;
                        padding: 15px;
                        margin: 20px 0;
                        text-align: center;
                    ">
                        <code style="
                            font-size: 32px;
                            font-weight: bold;
                            letter-spacing: 4px;
                            font-family: monospace;
                            color: #007bff;
                            user-select: all;
                            cursor: pointer;
                        ">{code}</code>
                    </div>
                    
                    <p style="
                        font-size: 14px;
                        color: #666;
                        margin-top: 20px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    ">
                        • This code will expire in 10 minutes<br>
                        • If you didn't request this code, please ignore this email<br>
                        • Click the code to copy it
                    </p>
                </div>
            </body>
        </html>
        """

    def render(self) -> str:
        """Render template to string"""
        return self.body
        