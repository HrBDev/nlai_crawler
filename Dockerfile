FROM ghcr.io/astral-sh/uv:alpine

WORKDIR /usr/app

ENV UV_NO_DEV=1

COPY . .

RUN uv sync

CMD [ "uv", "run", "./src/main.py" ]