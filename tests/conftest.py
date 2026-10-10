"""Test configuration: offline guard + dummy LOCAL token.

The golden regression runs the LOCAL app in-process (no sockets). Any attempt
to open a network connection fails the test, so the original can never be hit.
The token used here is a dummy for the local app; real tokens are never read.
"""
import os

import pytest

from tools import golden_lib as gl


@pytest.fixture(scope="session", autouse=True)
def _offline_and_local_token():
    gl.block_network()
    os.environ["FRONTIER_TOKEN"] = gl.LOCAL_TEST_TOKEN
    yield
