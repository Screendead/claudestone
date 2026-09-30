#!/bin/sh
set -eu
: "${RCON_PASSWORD:?pass -e RCON_PASSWORD}"
grep -v '^rcon.password=' server.properties > server.properties.new
echo "rcon.password=$RCON_PASSWORD" >> server.properties.new
mv server.properties.new server.properties
exec java -Xmx"${MEMORY:-1G}" -XX:AOTCache=/srv/server.aot ${JAVA_OPTS:-} \
    -cp "$(cat classpath)" net.minecraft.server.Main nogui
