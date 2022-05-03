# MISP3
This repository is a kind of [RiiR](http://web.archive.org/web/20220201102732/https://transitiontech.ca/random/RIIR) exercise to implement MISP core components in a modern tech stack.

## Backend
* **FastAPI**: API
* **PostgreSQL**: Data persistance (with use of JSONB)
* **SQlAlchemy+Alembic+Pydantic**: ORM/Migrations/Data validation
* **Redis**: Cache
* **Celery**: Task Queue / Background Jobs
* **ZeroMQ**: Message queue

### Structure
```
./
├─ backend/
│  └─ app/
│     ├─ models/
│     ├─ repositories/
│     ├─ routers/
│     ├─ schemas/
│     ├─ main.py
│     ├─ database.py
│     ├─ dependencies.py
│     └─ main.py
└─ frontend/
```

* `models/`: Where the SQLAlchemy models are defined, these models are used for creating the SQL tables, each file represents a table.
* `repositories/`: Where the methods that interact directly with the database via SQLAlchmy ORM live, each file clusters the methods related to a given model.
*  `routers/`: Where the FastAPI endpoints are defined, each file represents a resource.
*  `schemas/`: FastAPI models lie, these define the API contracts that are used in OpenAPI spec generation and `Pydantic` validation rules.
*  `database.py`: Database and SQLAchemy bootstraping.
*  `dependencies.py`: Global stuff here, could be refactored.
*  `main.py`: FastAPI entrypoint, routers for all resources are included here.

## Frontend
* Vue.js 3
* Bootstrap 5

### Structure
```
./
├─ backend/
└─ frontend/
    └─ ...
```

### Deployment
#### Docker
To start the application run:

```
$ docker-compose up -d
```

### Futher reading
* https://fastapi.tiangolo.com/deployment/docker/#container-images
* https://fastapi.tiangolo.com/tutorial/sql-databases/
* https://fastapi.tiangolo.com/tutorial/bigger-applications/
* https://fastapi.tiangolo.com/tutorial/security/


