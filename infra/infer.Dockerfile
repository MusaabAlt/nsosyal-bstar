# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app

# Per-module requirements: AI/CLAUDE.md rule 6 gives each module its own file, and
# the core deliberately stays stdlib + pyyaml. All FOUR runtime files are needed —
# omitting m1/m2 puts those modules in degraded_modules, which the deploy gate fails.
# AI/training/* is excluded: training only, not runtime.
COPY AI/requirements.txt                     /tmp/req-core.txt
COPY AI/serving/requirements.txt             /tmp/req-serving.txt
COPY AI/modules/m1_lexicon/requirements.txt  /tmp/req-m1.txt
COPY AI/modules/m2_deobf/requirements.txt    /tmp/req-m2.txt
COPY AI/modules/m3_encoder/requirements.txt  /tmp/req-m3.txt

# torch FIRST, from the CPU index with --index-url (NOT --extra-index-url, which lets
# pip resolve the multi-GB CUDA wheel from PyPI). This is the form
# AI/modules/m3_encoder/requirements.txt itself prescribes.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.11.0

RUN pip install --no-cache-dir \
      -r /tmp/req-core.txt -r /tmp/req-serving.txt \
      -r /tmp/req-m1.txt -r /tmp/req-m2.txt -r /tmp/req-m3.txt

COPY AI/ /app/
RUN adduser --disabled-password --uid 10001 app && mkdir -p /models && chown app /models
USER app
EXPOSE 8001

# Binds 0.0.0.0, not the repo's 127.0.0.1: the Go container reaches this
# across the overlay network. Not published to the host.
CMD ["python", "-m", "uvicorn", "serving.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8001", "--no-access-log"]
