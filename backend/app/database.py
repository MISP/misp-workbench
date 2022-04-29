import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

print(os.environ['HOME'])

SQLALCHEMY_DATABASE_URL = "postgresql://%s:%s@%s/misp" % (
    os.environ['POSTGRES_USER'], os.environ['POSTGRES_PASSWORD'], os.environ['POSTGRES_HOSTNAME'])

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
