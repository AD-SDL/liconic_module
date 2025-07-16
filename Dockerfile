FROM ghcr.io/ad-sdl/madsci:latest

LABEL org.opencontainers.image.source=https://github.com/AD-SDL/liconic_module
LABEL org.opencontainers.image.description="Drivers and REST API's for the liconic devices"
LABEL org.opencontainers.image.licenses=MIT

#########################################
# Module specific logic goes below here #
#########################################

RUN mkdir -p liconic_module

COPY ./src liconic_module/src
COPY ./README.md liconic_module/README.md
COPY ./pyproject.toml liconic_module/pyproject.toml

RUN --mount=type=cache,target=/root/.cache \
    pip install -e ./liconic_module

RUN usermod -aG dialout madsci

CMD ["python", "liconic_module/src/liconic_rest_node.py"]

#########################################
