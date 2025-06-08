import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

def create_fingerprint_db(db_type: str = "memory"):
    if db_type == "memory":
        from abracadabra.InMemoryFingerprintDB import InMemoryFingerprintDB

        return InMemoryFingerprintDB()
    elif db_type == "gcp":
        from abracadabra.GCPFingerprintDB import GCPFingerprintDB

        return GCPFingerprintDB()
    else:
        raise ValueError(f"Unsupported DB type: {db_type}")
