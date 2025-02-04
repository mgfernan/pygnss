# Development guide

This repository uses Docker and Docker Compose as a development environment.
In order to launch a development container review that you have the right environment variables set up
and run the following command:

```shell
docker-compose run pygnss
```

This will install dependencies defined in setup.cfg and run a bash command inside the container.

In order to run the test just launch pytest:

```shell
pytest
```

No environment variables required for Linux, Windows requires to set the path to the source code in the docker-compose file.
