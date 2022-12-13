import logging
import os

from app.database import SessionLocal
from app.repositories import events as events_repository
from app.repositories import servers as servers_repository
from app.repositories import users as users_repository
from app.settings import get_settings
from celery import Celery

celery = Celery()
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND")
logger = logging.getLogger(__name__)

db = SessionLocal()


@celery.task
def server_pull_by_id(server_id: int, user_id: int):
    logger.info("pull server_id=%s job started", server_id)

    user = users_repository.get_user_by_id(db, user_id)
    if user is None:
        raise Exception("User not found")

    servers_repository.pull_server_by_id(db, get_settings(), server_id, user)
    logger.info("pull server_id=%s job finished", server_id)

    return True


@celery.task
def handle_created_attribute(attribute: dict):
    logger.info("handling created attribute id=%s job started", attribute["id"])

    events_repository.increment_attribute_count(db, attribute["event_id"])

    return True


@celery.task
def handle_deleted_attribute(attribute: dict):
    logger.info("handling deleted attribute id=%s job started", attribute["id"])

    events_repository.decrement_attribute_count(db, attribute["event_id"])

    return True
