import logging
import colorlog


def setup_global_logging(level):
    """
    Sets up a global colored logger for the entire application.
    This function should be called once, typically at the start of your application.
    """
    # Define the custom format for the colored log messages
    # Each part of the format can have its own color.
    # The %(log_color)s and %(reset)s are special colorlog placeholders.
    log_format = (
        "%(white)s[%(asctime)s] %(log_color)s%(levelname)-6s%(reset)s "
        "%(white)s%(name)-8s - %(reset)s"
        "%(message)s"
    )

    # Define a dictionary for custom colors based on log level
    # These colors are applied to %(log_color)s
    log_colors = {
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }

    # Create a colored formatter instance
    formatter = colorlog.ColoredFormatter(
        log_format,
        log_colors=log_colors,
        # You can also add secondary colors for specific fields if needed
        # secondary_log_colors={
        #     'message': {
        #         'ERROR': 'red',
        #         'CRITICAL': 'red'
        #     }
        # }
    )

    # Get the root logger. This is the logger that all other loggers inherit from
    # if they don't have their own handlers.
    logger = logging.getLogger()

    # Set the logging level. Messages below this level will be ignored.
    logger.setLevel(level)

    # Create a stream handler (to output logs to the console)
    # This ensures that logs go to stdout/stderr.
    handler = logging.StreamHandler()

    # Set the formatter for the handler
    handler.setFormatter(formatter)

    # Add the handler to the logger
    # Check if the handler is already added to prevent duplicate messages
    if not any(
        isinstance(h, logging.StreamHandler) and h.formatter == formatter
        for h in logger.handlers
    ):
        logger.addHandler(handler)

    # You can optionally disable propagation to the root logger if you have specific
    # child loggers that you want to handle separately.
    # For a global setup where all logs go through this, it's often not needed.
    # logger.propagate = False

    # print("Global colored logging setup complete!")
