from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    CLOUDFLARE_ACCOUNT_ID: str
    CLOUDFLARE_R2_ACCESS_KEY_ID: str
    CLOUDFLARE_R2_SECRET_ACCESS_KEY: str

    # R2 bucket configuration
    R2_BUCKET_NAME: str
    R2_NAMESPACE: str

    @property
    def R2_ENDPOINT_URL(self) -> str:
        """Generate the R2 endpoint URL."""
        return f"https://{self.CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"


settings = Settings()  # type: ignore
