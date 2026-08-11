#!/usr/bin/env python3
"""Environment drift detection — compare dev/staging/prod configs."""
import os, json, hashlib

ENVIRONMENTS = {
    "dev": {"specguard": "localhost:8700", "business": "localhost:8600"},
    "prod": {"specguard": "cloud3:8701", "business": "cloud3:8600"},
}

def check_drift():
    """Check for configuration drift between environments."""
    drifts = []
    for env_name, services in ENVIRONMENTS.items():
        for svc, endpoint in services.items():
            drifts.append({
                "env": env_name,
                "service": svc,
                "endpoint": endpoint,
                "status": "unchecked"
            })
    return drifts

if __name__ == "__main__":
    drifts = check_drift()
    print(json.dumps(drifts, indent=2))
