"""Starter content for the pilot topics.

Written by the AI development assistant (Claude) while building the platform, so there is
something real to review before the AI provider is connected. It is imported as *drafts* with
origin "starter": an admin must review and publish it, and it can be regenerated with the
platform's own generator at any time. Every Python lab here is executed by the test suite.
"""

from app.content.starter import (
    activation_functions,
    neural_network_fundamentals,
    optimizers,
    regression,
    supervised_learning,
    unsupervised_learning,
)

TOPICS = [
    supervised_learning,
    unsupervised_learning,
    regression,
    neural_network_fundamentals,
    activation_functions,
    optimizers,
]

STARTER_NOTE = (
    "Starter content written by the AI development assistant (Claude) for the pilot. "
    "Review it like any AI draft before publishing."
)
STARTER_MODEL = "claude-opus-5-5 (development assistant)"
