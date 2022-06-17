# misp-lite
This repository is a kind of [RiiR](https://transitiontech.ca/random/RIIR) exercise to implement MISP core components in a modern tech stack.

## API
* **FastAPI**: API
* **SQLAlchemy+Alembic+Pydantic**: ORM/Migrations/Data validation
* **PostgreSQL**: Data persistance
* **Redis**: Cache and Celery storage backend
* **Celery**: Task Queue / Background Jobs
* **ZeroMQ**: Message queue

### Structure
```
./
├─ api/
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

### Migrations
Migrations are managed by [Alembic](https://alembic.sqlalchemy.org).

#### Show migrations history
```console
docker-compose exec api poetry run alembic history
```
#### Upgrade to lastest
```console
$ docker-compose exec api poetry run alembic upgrade head
```
#### Downgrade to revision
```console
$ docker-compose exec api poetry run alembic downgrade [revision]
```

#### Help
```console
$ docker-compose exec api poetry run alembic help 
```

### Testing
```console
$ docker-compose --env-file=".env.test" up -d
...
$ docker-compose exec api poetry run pytest
=========================================================================================== test session starts ===========================================================================================
platform linux -- Python 3.9.12, pytest-7.1.2, pluggy-1.0.0
rootdir: /code
collected 1 item                                                                                                                                                                                          

app/test_main.py .                                                                                                                                                                                  [100%]

============================================================================================ 1 passed in 0.33s ============================================================================================
```


#### Debugging tests
1. Run:
    ```console
    docker-compose exec api poetry run python -m debugpy --listen 0.0.0.0:5677 --wait-for-client -m pytest app/tests/repositories
    ```

2. Press **F5** on VS Code and the IDE will connect to the remote debugpy port.

### Development and Debugging
This guide is for Visual Studio Code, but should work with other IDEs with minor adjustements.

First make sure Make sure the [Python VS Code extension](https://marketplace) is installed, then:


1. Launch the docker containers with the debug configuration:
    ```console
    $ docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
    ```
2. Add the following Python debug profile to VS Code: `.vscode/launch.json`
    ```json
    {
        "version": "0.2.0",
        "configurations": [
        {
            "name": "Pytest: Remote Attach",
            "type": "python",
            "request": "attach",
            "justMyCode": false,
            "connect": {
                "host": "localhost",
                "port": 5677
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}/api",
                    "remoteRoot": "/code"
                }
            ],
        },
            {
                "name": "Python: Remote Attach",
                "type": "python",
                "request": "attach",
                "port": 5678,
                "host": "localhost",
                "justMyCode": false,
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}/api",
                        "remoteRoot": "/code"
                    }
                ]
            },
            {
                "name": "Celery: Remote Attach",
                "type": "python",
                "request": "attach",
                "justMyCode": false,
                "connect": {
                    "host": "localhost",
                    "port": 5679
                },
                "pathMappings": [
                    {
                        "localRoot": "${workspaceFolder}/api",
                        "remoteRoot": "/code"
                    }
                ],
            },
        ]
    }
    ```

3. Press **F5** on VS Code and start adding breakpoints.

#### Code Style
The code of this project is checked and formatted by [flake8](https://github.com/PyCQA/flake8), [autoflake](https://github.com/PyCQA/autoflake), [pyupgrade](https://github.com/asottile/pyupgrade) and [black](https://github.com/psf/black).

To install the pre-commit hooks on your dev env, run:
```console
$ poetry run pre-commit install
```
To check the style before a commit, run:
```console
$ poetry run pre-commit run --all-files
```

### TODO

#### CRUD
- users ~~cr~~ud
- events ~~c~~r~~ud~~
- attributes ~~cr~~ud
- servers ~~cr~~ud
- roles ~~c~~r~~ud~~
- objects crud
- events reports crud

#### API
- `/api/v1` prefix for API

#### Sync
- Encrypted server authkey
- Server Pull:
  - event blocklists / org blocklists logic
  - protected events logic
  - event attribute updates
  - event object updates
  - breakOnDuplicate logic for attributes and objects
- Server Push
- Feeds fetch

#### Other
- autogenerated docs, pdoc3? readthedocs?
- check if we can link somehow PyMISP models and with SQLAlchemy models, example MISPEvent <-> Event
- create initial user / cli cmds
- add coverage and build pass badges

## Frontend
* Vue.js 3
* Bootstrap 5

### Structure
```
./
├─ api/
└─ frontend/
    └─ ...
```

### Deployment
#### Docker
To start the application run:

```console
$ docker-compose up -d
```

### Futher reading
* https://fastapi.tiangolo.com/deployment/docker/#container-images
* https://fastapi.tiangolo.com/tutorial/sql-databases/
* https://fastapi.tiangolo.com/tutorial/bigger-applications/
* https://fastapi.tiangolo.com/tutorial/background-tasks/
* https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/
* https://fastapi.tiangolo.com/advanced/security/
* https://fastapi.tiangolo.com/advanced/settings/


