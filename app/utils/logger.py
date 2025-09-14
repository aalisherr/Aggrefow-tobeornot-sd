import sys
from pathlib import Path
from loguru import logger


def safe_log_text(text):
    """Escape only loguru formatting characters, keep brackets intact"""
    if not isinstance(text, str):
        text = str(text)
    # Only escape loguru formatting braces, keep [] as they are
    text = text.replace('{', '{{').replace('}', '}}')
    return text


def setup_logging():
    """Configure structured logging"""

    def format_with_component(record):
        if log_data := record['extra'].get('exchange', '').capitalize():
            log_data += " "

        log_data += safe_log_text(record["message"]) #record['extra'].get('component', ''):

        # # Sanitize the message (only escape formatting chars)
        # safe_message = safe_log_text(record["message"])

        return f"<green>{record['time']:HH:mm:ss}</green> | {log_data}\n"

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        format=format_with_component,
        level="INFO"
    )

    # File handler - DEBUG and above
    logger.add(
        "logs/app.log",
        format=lambda
            record: f"{record['time']:YYYY-MM-DD HH:mm:ss} | {record['level']} | {record['extra'].get('component', 'unknown')} | {safe_log_text(record['message'])}\n",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )

    # Error file handler
    logger.add(
        "logs/errors.log",
        format=lambda
            record: f"{record['time']:YYYY-MM-DD HH:mm:ss} | {record['level']} | {record['extra'].get('component', 'unknown')} | {safe_log_text(record['message'])} | {record['exception']}\n",
        level="ERROR",
        rotation="5 MB",
        retention="30 days"
    )

    # Patch logger methods to use summary format by default and set component
    def _patch_logger_methods():
        """Patch logger methods to use summary format by default with component"""
        original_info = logger.info
        original_debug = logger.debug
        original_warning = logger.warning
        original_error = logger.error

        def patched_info(message, *args, **kwargs):
            # Set summary=True by default for info messages and add component
            extra = kwargs.get('extra', {})
            if 'summary' not in extra:
                extra['summary'] = True
            if 'component' not in extra:
                # Try to get component from calling module
                import inspect
                try:
                    frame = inspect.currentframe().f_back
                    module = inspect.getmodule(frame)
                    if module:
                        component = module.__name__.split('.')[-1]
                        if component != '__main__':
                            extra['component'] = component
                except:
                    extra['component'] = 'app'
            kwargs['extra'] = extra
            return original_info(message, *args, **kwargs)

        def patched_debug(message, *args, **kwargs):
            # Debug messages use detailed format by default
            extra = kwargs.get('extra', {})
            if 'summary' not in extra:
                extra['summary'] = False
            if 'component' not in extra:
                extra['component'] = 'debug'
            kwargs['extra'] = extra
            return original_debug(message, *args, **kwargs)

        def patched_warning(message, *args, **kwargs):
            # Warning messages use summary format by default
            extra = kwargs.get('extra', {})
            if 'summary' not in extra:
                extra['summary'] = True
            if 'component' not in extra:
                extra['component'] = 'warning'
            kwargs['extra'] = extra
            return original_warning(message, *args, **kwargs)

        def patched_error(message, *args, **kwargs):
            # Error messages use detailed format by default
            extra = kwargs.get('extra', {})
            if 'summary' not in extra:
                extra['summary'] = False
            if 'component' not in extra:
                extra['component'] = 'error'
            kwargs['extra'] = extra
            return original_error(message, *args, **kwargs)

        # Apply patches
        logger.info = patched_info
        logger.debug = patched_debug
        logger.warning = patched_warning
        logger.error = patched_error

    # Apply the patches
    _patch_logger_methods()
    logger.configure(extra={"summary": True, "component": "app"})

# # Alternative simpler approach: Configure default extras
# def setup_logging_simple():
#     """Simpler approach - configure default extras"""
#     # ... (same setup code as above) ...
#
#     # Configure default extra values
#     logger.configure(extra={"summary": True, "component": "app"})