from src.AbstractFingerprintDB import AbstractFingerprintDB


def create_fingerprint_db(db_type="memory"):
    if db_type == "memory":
        from src.InMemoryFingerprintDB import InMemoryFingerprintDB

        return InMemoryFingerprintDB()
    elif db_type == "gcp":
        # import and return GCP version (later)
        pass
    else:
        raise ValueError(f"Unsupported DB type: {db_type}")
