"""Entry module for the graph fixture."""

import package_a.utils
from package_b import utils
from package_a.mod import helper


def run():
    """Start the app."""
    return helper()
