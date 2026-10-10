FROM nikolaik/python-nodejs:python3.10-nodejs20

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# git is required to pip-install Kurigram from a git URL.
RUN apt-get update && \
    apt-get install -y --no-install-recommends git curl xz-utils ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Static ffmpeg + ffprobe (used for audio/video processing and streaming).
RUN curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    -o ffmpeg.tar.xz && \
    tar -xJf ffmpeg.tar.xz && \
    mv ffmpeg-*-static/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg*

COPY . /app/
WORKDIR /app/

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

CMD ["bash", "start"]
