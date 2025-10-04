"""
Comprehensive cloud provider IPv6 support data
Including NAT-free egress and prefix delegation capabilities
"""

CLOUD_PROVIDERS = {
    'aws': {
        'name': 'Amazon Web Services (AWS)',
        'ipv6_support': 'Full',
        'status': 'Fully Enabled',
        'services': {
            'EC2': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': True,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Egress-only Internet Gateway',
                    'description': 'IPv6 instances can reach internet without NAT using egress-only IGW',
                    'cost': 'No data transfer charges for IPv6 egress',
                    'notes': 'Eliminates NAT Gateway costs for outbound IPv6 traffic'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'VPC IPv6 CIDR blocks',
                    'prefix_size': '/56 to VPC, /64 per subnet',
                    'description': 'AWS assigns /56 to VPC, subnets get /64',
                    'automatic': True,
                    'notes': 'Can request specific IPv6 CIDR or use AWS-provided'
                }
            },
            'ECS/EKS': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': True,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Direct IPv6 routing',
                    'description': 'Containers can communicate over IPv6 without NAT'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'CNI plugin',
                    'description': 'Automatic IPv6 assignment to pods/containers'
                }
            },
            'Lambda': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': False,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'VPC configuration',
                    'description': 'Lambda functions in VPC can use IPv6 egress'
                }
            },
            'S3': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'All regions support IPv6 for S3 access'
            },
            'CloudFront': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Automatic IPv6 support for all distributions'
            },
            'RDS': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Database instances support IPv6 connectivity'
            }
        },
        'documentation': 'https://docs.aws.amazon.com/vpc/latest/userguide/vpc-ipv6.html',
        'last_updated': '2025-10',
        'global_availability': True,
        'cost_benefits': 'Eliminates NAT Gateway costs (~$45/month per AZ), free IPv6 egress'
    },

    'gcp': {
        'name': 'Google Cloud Platform (GCP)',
        'ipv6_support': 'Full',
        'status': 'Fully Enabled',
        'services': {
            'Compute Engine': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': True,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Direct IPv6 routing',
                    'description': 'VMs with IPv6 can reach internet directly without Cloud NAT',
                    'cost': 'No NAT costs for IPv6 traffic',
                    'notes': 'Cloud NAT only needed for IPv4, IPv6 is direct'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'VPC subnet IPv6 ranges',
                    'prefix_size': '/64 per subnet',
                    'description': 'Each subnet gets /64, VMs get /96',
                    'automatic': True,
                    'notes': 'Google manages IPv6 allocation automatically'
                }
            },
            'GKE': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': False,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Native IPv6 routing',
                    'description': 'Pods can communicate over IPv6 without NAT'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'Kubernetes CNI',
                    'description': 'Automatic /96 to each pod from subnet /64'
                }
            },
            'Cloud Load Balancing': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Global and regional load balancers support IPv6'
            },
            'Cloud Functions': {
                'support': 'Partial',
                'dual_stack': True,
                'ipv6_only': False,
                'notes': 'VPC connector required for IPv6'
            },
            'Cloud Storage': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'All storage buckets accessible via IPv6'
            }
        },
        'documentation': 'https://cloud.google.com/vpc/docs/ipv6',
        'last_updated': '2025-10',
        'global_availability': True,
        'cost_benefits': 'No Cloud NAT costs for IPv6 traffic'
    },

    'azure': {
        'name': 'Microsoft Azure',
        'ipv6_support': 'Full',
        'status': 'Fully Enabled',
        'services': {
            'Virtual Machines': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': True,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Public IPv6 addresses',
                    'description': 'VMs with public IPv6 can egress directly',
                    'cost': 'No NAT Gateway costs for IPv6',
                    'notes': 'IPv6 public IPs are free, no egress charges'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'Virtual Network IPv6 ranges',
                    'prefix_size': '/64 per subnet, /48 per VNet',
                    'description': 'Azure provides /48 to VNet, /64 to subnets',
                    'automatic': True,
                    'notes': 'Can use custom IPv6 ranges or Azure-provided'
                }
            },
            'AKS': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': False,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Pod IPv6 addresses',
                    'description': 'Dual-stack clusters support direct IPv6 egress'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'Azure CNI',
                    'description': 'Pods get IPv6 from VNet address space'
                }
            },
            'Load Balancer': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Standard Load Balancer supports IPv6 frontend'
            },
            'App Service': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Web apps can bind to IPv6 addresses'
            },
            'Storage': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Blob, File, Queue storage support IPv6'
            }
        },
        'documentation': 'https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/ipv6-overview',
        'last_updated': '2025-10',
        'global_availability': True,
        'cost_benefits': 'Free IPv6 public IPs, eliminates NAT Gateway costs'
    },

    'digitalocean': {
        'name': 'DigitalOcean',
        'ipv6_support': 'Full',
        'status': 'Fully Enabled',
        'services': {
            'Droplets': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': False,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Public IPv6 addresses',
                    'description': 'All droplets get /128 IPv6 address automatically',
                    'cost': 'Free IPv6, no egress charges',
                    'notes': 'IPv6 enabled by default on all droplets'
                },
                'prefix_delegation': {
                    'supported': False,
                    'method': 'Single /128 per droplet',
                    'description': 'Each droplet gets single IPv6, no subnet delegation',
                    'notes': 'No native prefix delegation, single address only'
                }
            },
            'Kubernetes': {
                'support': 'Partial',
                'dual_stack': False,
                'notes': 'IPv4 only for DOKS clusters currently'
            },
            'Load Balancers': {
                'support': 'Partial',
                'dual_stack': True,
                'notes': 'Support IPv6 forwarding to droplets'
            },
            'Spaces': {
                'support': 'Partial',
                'dual_stack': True,
                'notes': 'Object storage accessible via IPv6'
            }
        },
        'documentation': 'https://docs.digitalocean.com/products/networking/ipv6/',
        'last_updated': '2025-10',
        'global_availability': True,
        'cost_benefits': 'Free IPv6 addresses for all droplets'
    },

    'linode': {
        'name': 'Linode (Akamai)',
        'ipv6_support': 'Full',
        'status': 'Fully Enabled',
        'services': {
            'Compute Instances': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': True,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Public IPv6 addresses',
                    'description': 'All instances get /128 IPv6 and /64 pool',
                    'cost': 'Free IPv6 addresses and traffic',
                    'notes': 'Can request additional IPv6 pools'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': '/64 and /56 IPv6 pools',
                    'prefix_size': '/64 or /56 pools per instance',
                    'description': 'Request /64 or /56 IPv6 pools for subnets',
                    'automatic': False,
                    'notes': 'Manual request for IPv6 pools via support/API'
                }
            },
            'LKE': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Kubernetes clusters support IPv6'
            },
            'NodeBalancers': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Load balancers support IPv6 frontend'
            },
            'Object Storage': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'S3-compatible storage accessible via IPv6'
            }
        },
        'documentation': 'https://www.linode.com/docs/guides/linux-static-ip-configuration/',
        'last_updated': '2025-10',
        'global_availability': True,
        'cost_benefits': 'Free IPv6 addresses and pools'
    },

    'oracle': {
        'name': 'Oracle Cloud Infrastructure (OCI)',
        'ipv6_support': 'Full',
        'status': 'Fully Enabled',
        'services': {
            'Compute': {
                'support': 'Full',
                'dual_stack': True,
                'ipv6_only': True,
                'nat_free_egress': {
                    'supported': True,
                    'method': 'Internet Gateway IPv6',
                    'description': 'IPv6 instances use Internet Gateway without NAT',
                    'cost': 'No NAT costs for IPv6',
                    'notes': 'IPv6 traffic routes directly via IGW'
                },
                'prefix_delegation': {
                    'supported': True,
                    'method': 'VCN IPv6 CIDR',
                    'prefix_size': '/56 to VCN, /64 per subnet',
                    'description': 'VCN gets /56, subnets get /64',
                    'automatic': True
                }
            },
            'OKE': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Kubernetes clusters support dual-stack'
            },
            'Load Balancers': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Flexible load balancers support IPv6'
            }
        },
        'documentation': 'https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/ipv6.htm',
        'last_updated': '2025-10',
        'global_availability': True,
        'cost_benefits': 'Always free tier includes IPv6'
    },

    'cloudflare': {
        'name': 'Cloudflare',
        'ipv6_support': 'Full',
        'status': 'Industry Leader',
        'services': {
            'CDN': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Automatic IPv6 support for all zones'
            },
            'Workers': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Edge computing with IPv6 support'
            },
            'R2 Storage': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Object storage accessible via IPv6'
            },
            'Load Balancing': {
                'support': 'Full',
                'dual_stack': True,
                'notes': 'Global load balancing supports IPv6'
            }
        },
        'documentation': 'https://developers.cloudflare.com/fundamentals/concepts/ipv6/',
        'last_updated': '2025-10',
        'global_availability': True,
        'ipv6_traffic_percentage': 36.0,
        'notes': 'Pioneer in IPv6 adoption, free IPv6 for all plans'
    }
}


def get_provider_summary(provider_key: str) -> dict:
    """Get summary information for a cloud provider"""
    provider = CLOUD_PROVIDERS.get(provider_key, {})

    nat_free_count = 0
    prefix_delegation_count = 0

    for service in provider.get('services', {}).values():
        if isinstance(service, dict):
            if service.get('nat_free_egress', {}).get('supported'):
                nat_free_count += 1
            if service.get('prefix_delegation', {}).get('supported'):
                prefix_delegation_count += 1

    return {
        'name': provider.get('name', ''),
        'ipv6_support': provider.get('ipv6_support', 'Unknown'),
        'services_count': len(provider.get('services', {})),
        'nat_free_services': nat_free_count,
        'prefix_delegation_services': prefix_delegation_count,
        'status': provider.get('status', 'Unknown')
    }
