
from app.settings import Settings, get_settings
from app.services.minio import get_minio_client
import base64

def get_attachment(
    attachment_uuid: str,
    settings: Settings = get_settings(),
) -> bytes:
    if settings.Storage.engine == "minio":
        MinioClient = get_minio_client()

        data = MinioClient.get_object(settings.Storage.minio.bucket, attachment_uuid)
        return data.read()

    # get attachment from local storage
    if settings.Storage.engine == "local":
        with open(f"/tmp/attachments/{attachment_uuid}", "rb") as f:
            return f.read()
        

def get_b64_attachment(
    attachment_uuid: str,
    settings: Settings = get_settings(),
) -> str:
    file_content = get_attachment(attachment_uuid, settings)
    return base64.b64encode(file_content).decode("utf-8")