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
        self.body = fr"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    @keyframes fadeInUp {{
                        from {{
                            opacity: 0;
                            transform: translate(-50%, 10px);
                        }}
                        to {{
                            opacity: 1;
                            transform: translate(-50%, 0);
                        }}
                    }}

                    @keyframes fadeOut {{
                        from {{
                            opacity: 1;
                        }}
                        to {{
                            opacity: 0;
                        }}
                    }}

                    .tooltip-show {{
                        animation: fadeInUp 0.3s ease forwards;
                    }}

                    .tooltip-hide {{
                        animation: fadeOut 0.3s ease forwards;
                    }}
                </style>
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
                    background-color: #424B3B;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h1 style="
                        color: #C4C4C4;
                        margin-bottom: 20px;
                        font-size: 24px;
                    ">Email Verification</h1>

                    <p style="
                        font-size: 16px;
                        color: #a2b18a;
                        margin-bottom: 20px;
                    ">Hi {username},</p>

                    <p style="
                        font-size: 16px;
                        color: #A2B18A;
                        margin-bottom: 10px;
                    ">Your verification code is:</p>

                    <div style="
                        background-color: #CADDAD;
                        border-radius: 4px;
                        padding: 15px;
                        margin: 20px 0;
                        text-align: center;
                        position: relative;
                    ">
                        <code style="
                            font-size: 32px;
                            font-weight: bold;
                            letter-spacing: 4px;
                            font-family: monospace;
                            color: #424B3B;
                            user-select: none;
                            cursor: pointer;
                        "
                        id="code"
                        onclick="copyCode()">{code}</code>
                        <div id="tooltip" style="
                            position: absolute;
                            bottom: -30px;
                            left: 50%;
                            transform: translateX(-50%);
                            background-color: #333;
                            color: white;
                            padding: 5px 10px;
                            border-radius: 4px;
                            font-size: 16px;
                            display: none;
                            opacity: 0;
                        ">Copied!</div>
                    </div>

                    <p style="
                        font-size: 14px;
                        color: #C4C4C4;
                        margin-top: 20px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    ">
                        • This code will expire in 10 minutes<br>
                        • If you didn't request this code, please ignore this email<br>
                        • Click the code to copy it
                    </p>
                </div>

                <script>
                    function copyCode() {{
                        const code = document.getElementById('code').textContent;
                        const tooltip = document.getElementById('tooltip');
                        
                        navigator.clipboard.writeText(code).then(() => {{
                            tooltip.style.display = 'block';
                            tooltip.classList.remove('tooltip-hide');
                            tooltip.classList.add('tooltip-show');
                            
                            setTimeout(() => {{
                                tooltip.classList.remove('tooltip-show');
                                tooltip.classList.add('tooltip-hide');
                                setTimeout(() => {{
                                    tooltip.style.display = 'none';
                                    tooltip.classList.remove('tooltip-hide');
                                }}, 300);
                            }}, 2000);
                        }});
                    }}
                </script>
            </body>
        </html>
        """

    def render(self) -> str:
        """Render template to string"""
        return self.body
        