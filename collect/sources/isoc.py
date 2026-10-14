"""Internet Society Pulse (opt-in). Needs an account and API key.

Without ISOC_PULSE_API_KEY the runner marks this source "not configured" and never
calls fetch(). The API client is written once the owner has a key (spec Amendment 1,
Follow-ups).
"""
from collect.registry import MONTH, Context, source


@source("isoc_pulse", MONTH, title="Internet Society Pulse API (opt-in)",
        url="https://pulse.internetsociety.org/en/api/", requires_env=("ISOC_PULSE_API_KEY",))
def fetch(ctx: Context) -> dict:
    raise NotImplementedError("ISOC Pulse API client not written yet; see spec Amendment 1, Follow-ups")
