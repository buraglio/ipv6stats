"""
Modular page architecture for IPv6 Dashboard
Each page is a separate module for better organization and maintainability
"""

from . import overview
from . import global_adoption
from . import cloud_services
from . import bgp_statistics

__all__ = ['overview', 'global_adoption', 'cloud_services', 'bgp_statistics']
