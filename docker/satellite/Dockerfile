# The context is these files plus server/server.jar; see README.md for the build command.
# Two stages so server.jar never lands in a layer of the final image (the legacy builder
# has no RUN --mount).
FROM eclipse-temurin:25-jre AS pregen
WORKDIR /srv
COPY server.jar /tmp/server.jar
COPY server.properties pregen.sh start.sh ./
RUN echo eula=true > eula.txt && sh pregen.sh && rm -rf pregen.sh logs

FROM eclipse-temurin:25-jre
WORKDIR /srv
COPY --from=pregen /srv /srv
EXPOSE 25565 25575
CMD ["sh", "/srv/start.sh"]
