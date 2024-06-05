# misp-lite
This repository is a kind of [RiiR](https://transitiontech.ca/random/RIIR) exercise to implement MISP core components in a modern tech stack.

## API / backend
* See: [README.md](api/README.md)

## Frontend
* See: [README.md](frontend/README.md)

## Production
TODO

## Development

1. Start API dev server:
    ```console
    git submodule update --init --recursive
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml --env-file=".env.dev" up --build
    ```

2. Start Frontend dev server: 
    ```console
    cd frontend/ 
    npm run dev
    ```

## Deployment
### Docker
To start the application run:

```console
$ docker-compose up -d
```

## Ideas
* Suggest tags/taxonomies using AI/ML
