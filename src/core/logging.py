import json
import logging
from logging.handlers import RotatingFileHandler
from typing import Any

import structlog

from src.core.config import settings


def setup_logging(level: int | str) -> None:
    handlers = []

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    handlers.append(console_handler)

    file_handler = RotatingFileHandler(
        settings.LOGS_DIR / f'{settings.APP_NAME}.log',
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )

    file_handler.setLevel(level)
    handlers.append(file_handler)

    logging.basicConfig(
        format='%(message)s',
        handlers=handlers,
        level=level,
    )


def get_logger(name: str, level: int | str = settings.LOG_LEVEL) -> structlog.BoundLogger:
    setup_logging(level)
    render_method = structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt=settings.LOG_DATE_FORMAT, utc=True),
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            mask_sensitive_data,
            render_method,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(name)


def mask_sensitive_data(  # noqa
    logger: structlog.BoundLogger, _method_name: str, event_dict: dict[str, Any]
) -> Any:
    """Recursively mask sensitive data"""
    PARAM_PARTS_WITH_VALUE = 2

    def _mask_data(data: Any) -> Any:  # noqa
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Check if key should be masked first
                if key in settings.LOG_SENSITIVE_DATA:
                    result[key] = 'SENSITIVE DATA'
                # Try to parse JSON strings
                elif isinstance(value, str):
                    stripped = value.strip()
                    if any(
                        (
                            stripped.startswith('{') and stripped.endswith('}'),
                            stripped.startswith('[') and stripped.endswith(']'),
                        )
                    ):
                        try:
                            parsed = json.loads(value)
                            masked = _mask_data(parsed)
                            # Serialize back to string to preserve original format
                            result[key] = json.dumps(masked, ensure_ascii=False)
                        except json.JSONDecodeError:
                            # If JSON parsing fails, check if it's a query string
                            if key == 'query':
                                params = value.split('&')
                                if len(params) == 0 or params[0] == '':
                                    result[key] = value
                                else:
                                    temp = {}
                                    for param in params:
                                        # Split only on the first "=" to handle values that contain "="
                                        parts = param.split('=', 1)
                                        if len(parts) == PARAM_PARTS_WITH_VALUE:
                                            param_name, param_value = parts
                                            temp[param_name] = param_value
                                        elif len(parts) == 1:
                                            # Parameter without value (e.g., "flag" instead of "flag=true")
                                            temp[parts[0]] = ''
                                    result[key] = _mask_data(temp)
                            else:
                                result[key] = value
                    elif key == 'query':
                        params = value.split('&')
                        if len(params) == 0 or params[0] == '':
                            result[key] = value
                        else:
                            temp = {}
                            for param in params:
                                # Split only on the first "=" to handle values that contain "="
                                parts = param.split('=', 1)
                                if len(parts) == PARAM_PARTS_WITH_VALUE:
                                    param_name, param_value = parts
                                    temp[param_name] = param_value
                                elif len(parts) == 1:
                                    # Parameter without value (e.g., "flag" instead of "flag=true")
                                    temp[parts[0]] = ''
                            result[key] = _mask_data(temp)
                    else:
                        result[key] = value
                elif isinstance(value, dict | list):
                    result[key] = _mask_data(value)
                else:
                    result[key] = value
            return result

        if isinstance(data, list):
            return [_mask_data(item) for item in data]

        return data

    if 'context' in event_dict:
        event_dict['context'] = _mask_data(event_dict['context'])

    return event_dict
