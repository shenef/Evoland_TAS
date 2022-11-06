# This needs to be before the other imports in case they decide to log things when imported
import log_init

# This sets up console and file logging (should only be called once)
log_init.initialize_logging("Evoland")

# Libraries
import logging

# Core files
import controller

logger = logging.getLogger(__name__)


# Main entry point of TAS
if __name__ == "__main__":
    logger.info("Hello world")
    c = controller.handle()

    c.set_button("btn_x", 1)
    c.set_button("btn_x", 0)
