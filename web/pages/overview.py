"""Overview page."""
from web import derive
from web.data import Data


def context(data: Data) -> dict:
    return {"consensus": derive.consensus(derive.consensus_components(data))}
