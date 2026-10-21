from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application
    APP_ENV: str = "development"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # SAP Business Accelerator Hub Sandbox
    SAP_API_KEY: str = Field(..., description="API key from SAP Business Accelerator Hub")
    SAP_SANDBOX_BASE_URL: str = Field(
        default="https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap",
        description="Base URL for S/4HANA OData sandbox services",
    )

    # AWS Bedrock
    AWS_REGION: str = "ap-southeast-2"
    AWS_ACCESS_KEY_ID: str = Field(..., description="AWS Access Key")
    AWS_SECRET_ACCESS_KEY: str = Field(..., description="AWS Secret Key")
    AWS_BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    AWS_BEDROCK_EMBEDDING_ID: str = "amazon.titan-embed-text-v2:0"

    # Storage & Persistence
    CHROMA_PERSIST_DIRECTORY: str = "./data/vector_store"
    CHECKPOINT_DB_PATH: str = "./data/checkpoints.sqlite"


settings = Settings()