import logging
import os
from celery import Celery
from ..repositories import servers as servers_repository
from ..settings import get_settings
from ..models.database import SessionLocal
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

celery = Celery()
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND")
logger = logging.getLogger(__name__)

@celery.task(name="server_pull")
def server_pull_by_id(server_id: int):
    logger.info("pull server_id=%s job started", server_id)
    servers_repository.pull_server_by_id(SessionLocal(), get_settings(), server_id)
    logger.info("pull server_id=%s job finished", server_id)

    return True
