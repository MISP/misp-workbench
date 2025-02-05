import time
import logging
import hashlib

from app.dependencies import get_minio_client
from starlette import status
import app.schemas.event as event_schemas
from app.schemas import object as object_schemas
import app.schemas.attribute as attribute_schemas
from app.repositories import objects as objects_repository
from sqlalchemy.orm import Session
from app.settings import Settings, get_settings
from fastapi import (
    HTTPException,
    File,
    UploadFile,
)

logger = logging.getLogger(__name__)


def upload_attachment_to_event(
    db: Session,
    event: event_schemas.Event,
    attachment: UploadFile = File(...),
    settings: Settings = get_settings()
) -> object_schemas.Object:

    try:
        # TODO get the object template from the json file
        file_object = object_schemas.ObjectCreate(
            name="file",
            template_uuid="688c46fb-5edb-40a3-8273-1af7923e2215",
            template_version=25,
            comment=attachment.filename,
            event_id=event.id,
            timestamp=int(time.time()),
        )

        filename_attribute = attribute_schemas.AttributeCreate(
            event_id=event.id,
            object_relation="filename",
            category="External analysis",
            type="filename",
            value=attachment.filename,
            timestamp=int(time.time()),
            distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
        )
        file_object.attributes.append(filename_attribute)

        # read file content
        file_content = attachment.file.read()

        # get file sha1
        sha1 = hashlib.sha1()
        sha1.update(file_content)
        sha1 = sha1.hexdigest()
        sha1_attribute = attribute_schemas.AttributeCreate(
            event_id=event.id,
            object_relation="sha1",
            category="External analysis",
            type="sha1",
            value=sha1,
            timestamp=int(time.time()),
            distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
        )
        file_object.attributes.append(sha1_attribute)

        # get file sha256
        sha256 = hashlib.sha256()
        sha256.update(file_content)
        sha256 = sha256.hexdigest()
        sha256_attribute = attribute_schemas.AttributeCreate(
            event_id=event.id,
            object_relation="sha256",
            category="External analysis",
            type="sha256",
            value=sha256,
            timestamp=int(time.time()),
            distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
        )
        file_object.attributes.append(sha256_attribute)

        # get file md5
        md5 = hashlib.md5()
        md5.update(file_content)
        md5 = md5.hexdigest()
        md5_attribute = attribute_schemas.AttributeCreate(
            event_id=event.id,
            object_relation="md5",
            category="External analysis",
            type="md5",
            value=md5,
            timestamp=int(time.time()),
            distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
        )
        file_object.attributes.append(md5_attribute)

        # get file size
        size = len(file_content)
        size_attribute = attribute_schemas.AttributeCreate(
            event_id=event.id,
            object_relation="size-in-bytes",
            category="External analysis",
            type="size-in-bytes",
            value=str(size),
            timestamp=int(time.time()),
            distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
        )
        file_object.attributes.append(size_attribute)

        db_file_object = objects_repository.create_object(db, file_object)

        # upload file to minio
        if settings.Storage.engine == "minio":
            MinioClient = get_minio_client()
            MinioClient.fput_object(
                settings.Storage.minio.bucket,
                sha256,
                attachment.file.file,
                attachment.filename,
            )

        # upload file to local storage
        if settings.Storage.engine == "local":
            with open(f"/tmp/attachments/{sha256}", "wb") as f:
                f.write(file_content)
                    
        return db_file_object

    except Exception as e:
        logger.error(f"Error uploading attachment for event: {event.uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading attachment",
        )
