import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    # AWS / Bedrock
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "mistral.mistral-small-2402-v1:0"
    )

    # Microsoft Fabric SQL endpoint
    FABRIC_SERVER: str = os.getenv("FABRIC_SERVER", "")
    FABRIC_DATABASE: str = os.getenv("FABRIC_DATABASE", "")

    # Service principal auth
    FABRIC_TENANT_ID: str = os.getenv("FABRIC_TENANT_ID", "")
    FABRIC_CLIENT_ID: str = os.getenv("FABRIC_CLIENT_ID", "")
    FABRIC_CLIENT_SECRET: str = os.getenv("FABRIC_CLIENT_SECRET", "")

    # Username/password auth (fallback)
    FABRIC_USERNAME: str = os.getenv("FABRIC_USERNAME", "")
    FABRIC_PASSWORD: str = os.getenv("FABRIC_PASSWORD", "")

    # App behaviour
    MAX_ROWS_DISPLAY: int = int(os.getenv("MAX_ROWS_DISPLAY", "50"))
    MAX_SCHEMA_TABLES: int = int(os.getenv("MAX_SCHEMA_TABLES", "100"))

    def validate(self) -> List[str]:
        errors = []
        if not self.AWS_ACCESS_KEY_ID:
            errors.append("AWS_ACCESS_KEY_ID is not set")
        if not self.AWS_SECRET_ACCESS_KEY:
            errors.append("AWS_SECRET_ACCESS_KEY is not set")
        if not self.FABRIC_SERVER:
            errors.append("FABRIC_SERVER is not set")
        if not self.FABRIC_DATABASE:
            errors.append("FABRIC_DATABASE is not set")
        has_sp = self.FABRIC_TENANT_ID and self.FABRIC_CLIENT_ID and self.FABRIC_CLIENT_SECRET
        has_up = self.FABRIC_USERNAME and self.FABRIC_PASSWORD
        if not has_sp and not has_up:
            errors.append(
                "Fabric auth missing: set either service principal "
                "(FABRIC_TENANT_ID/CLIENT_ID/CLIENT_SECRET) or "
                "username/password (FABRIC_USERNAME/FABRIC_PASSWORD)"
            )
        return errors


config = Config()
