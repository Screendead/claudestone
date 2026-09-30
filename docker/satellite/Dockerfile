# The context is these files plus server/server.jar; see README.md for the build command.
# Two stages so server.jar never lands in a layer of the final image (the legacy builder
# has no RUN --mount).
FROM eclipse-temurin:25-jre AS pregen
WORKDIR /srv
COPY server.jar /tmp/server.jar
COPY server.properties pregen.sh start.sh ./
RUN echo eula=true > eula.txt && sh pregen.sh && rm -rf pregen.sh logs

FROM eclipse-temurin:25-jre
# The harness runs each test in here, next to the server (redstone/remote.py); fileformat needs
# yaml. scripts.remote_run runs offline searches in throwaway containers of this image.
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-yaml python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --break-system-packages python-sat
WORKDIR /srv
COPY --from=pregen /srv /srv
EXPOSE 25565 25575
CMD ["sh", "/srv/start.sh"]
