# Libraries and Core Files
import logging

import controller

logger = logging.getLogger(__name__)


class Evoland1Controller:
    def __init__(self):
        self.handle = controller.handle()


_controller = Evoland1Controller()


def handle():
    return _controller
