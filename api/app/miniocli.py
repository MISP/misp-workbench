from minio import Minio
from app.settings import get_settings


Settings = get_settings()

if Settings.Storage.engine == "minio":
    MinioClient = Minio(
        Settings.Storage.minio.host,
        access_key=Settings.Storage.minio.access_key,
        secret_key=Settings.Storage.minio.secret_key,
        secure=Settings.Storage.minio.secure,
    )
    found = MinioClient.bucket_exists(Settings.Storage.minio.bucket)

    if not found:
        MinioClient.make_bucket(Settings.Storage.minio.bucket)
else:
    MinioClient = None
