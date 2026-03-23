# Stage 1: Builder
FROM python:3.12-slim AS builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git pkg-config \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir \
    numpy \
    pytest pytest-cov pytest-xdist pytest-timeout pytest-mock \
    ruff mypy hypothesis
# OpenSim is not pip-installable; install via conda or from source
# RUN conda install -c opensim-org opensim

# Stage 2: Runtime
FROM python:3.12-slim AS runtime
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*
ARG USER_NAME=athlete
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} ${USER_NAME} && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USER_NAME}
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
ENV PYTHONPATH="/workspace/src"
WORKDIR /workspace
COPY --chown=${USER_NAME}:${USER_NAME} src/ ./src/
COPY --chown=${USER_NAME}:${USER_NAME} tests/ ./tests/
COPY --chown=${USER_NAME}:${USER_NAME} pyproject.toml conftest.py ./
USER ${USER_NAME}
CMD ["/bin/bash"]

# Stage 3: Training
# Placeholder for future reinforcement-learning training pipeline.
# This stage extends the runtime image with RL dependencies (Gymnasium,
# Stable-Baselines3). A training script and reward function will be added
# once the musculoskeletal models are validated against OpenSim ground truth.
FROM runtime AS training
USER root
RUN pip install --no-cache-dir gymnasium>=0.29.0 stable-baselines3>=2.0.0
USER ${USER_NAME}
CMD ["/bin/bash"]
