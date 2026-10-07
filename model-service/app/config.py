from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Hugging Face repo and file that hold the YOLOv8-cls weights.
    HF_REPO_ID: str = "W4ashabii/waste_classifier"
    HF_FILENAME: str = "best.pt"
    # Local weights path. If the file exists it is used as-is (no network);
    # otherwise the weights are downloaded from Hugging Face into WEIGHTS_DIR.
    WEIGHTS_PATH: str = ""
    WEIGHTS_DIR: str = "weights"
    IMAGE_SIZE: int = 224
    # "cpu", "cuda", "cuda:0", ... Empty lets ultralytics pick.
    DEVICE: str = ""
    # Max upload size in bytes.
    MAX_IMAGE_BYTES: int = 10 * 1024 * 1024


settings = Settings()
