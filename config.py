import os


class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "zubal_secret_key"
    )

    UPLOAD_FOLDER = "static/uploads"

    DEBUG = True

    CLOUDINARY_CLOUD_NAME = os.environ.get(
        "CLOUDINARY_CLOUD_NAME"
    )

    CLOUDINARY_API_KEY = os.environ.get(
        "CLOUDINARY_API_KEY"
    )

    CLOUDINARY_API_SECRET = os.environ.get(
        "CLOUDINARY_API_SECRET"
    )