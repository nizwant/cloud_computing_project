def create_fingerprint_db(db_type: str = "memory"):
    if db_type == "memory":
        from src.abracadabra.InMemoryFingerprintDB import InMemoryFingerprintDB
        return InMemoryFingerprintDB()
    elif db_type == "gcp":
        from src.abracadabra.GCPFingerprintDB import GCPFingerprintDB
        return GCPFingerprintDB()
    else:
        raise ValueError(f"Unsupported DB type: {db_type}")
