FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git cmake g++ ninja-build ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH="/opt/venv/bin:$PATH"

# Build the patched Luau runtime required by the deobfuscator.
RUN python3 deobf/build_luau.py --portable \
    && cmake -S /tmp/nonexistent -B /tmp/ignore 2>/dev/null || true

# The build script creates the patched luau runtime. Build the remaining Luau
# targets too, then copy luau-ast into the expected bin/ location when present.
RUN set -eux; \
    test -x deobf/bin/luau; \
    find /tmp -type f -name 'luau-ast' -o -name 'luau-ast.exe' 2>/dev/null | head -1 | xargs -r -I{} cp {} deobf/bin/luau-ast; \
    test -f deobf/bin/luau-ast || { echo 'luau-ast was not produced; build target required'; exit 1; }

CMD ["python3", "bot.py"]
