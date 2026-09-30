# redstone-satellite

A headless 26.3 satellite with sat1..sat6's settings (flat preset, distance 2, gamerules
off), libraries unpacked, world and every plot's chunks pre-generated, and a JDK AOT cache.
The build context is this folder plus `server/server.jar` (the legacy builder has no BuildKit):

    COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -cf - -C docker/satellite \
      Dockerfile server.properties pregen.sh start.sh -C ../../server server.jar \
      | docker -H ssh://<user>@<desktop-host> build -t redstone-satellite:26.3 -

(`python -m scripts.satellite_image` does this.)

Start and stop them with `python -m redstone.docker_sats {start,stop,status} [dsatN...]`
(or `python -m scripts.servers start docker`): each runs, without `--rm` so a crashed
server's log and crash reports are saved before removal, as

    docker -H ssh://<user>@<desktop-host> run -d --name dsat1 -e RCON_PASSWORD \
      -p 127.0.0.1:25676:25575 redstone-satellite:26.3

with RCON only on the desktop's loopback, forwarded to the laptop through the SSH master.

Level `testworld`; the data pack dir is `/srv/testworld/datapacks` (`docker cp` into it,
then `reload`). A TCP connect through the tunnel succeeds even with the server down, so
wait for an RCON login, not an open port. `MEMORY` (default 1G) and `JAVA_OPTS` are optional.

The harness (`redstone/docker_sats.py`) reaches the desktop as `REDSTONE_DOCKER_HOST`, else
the one line `user@host` in `server/docker_host` (gitignored, like the rest of `server/`).
With neither, the Docker backend is unavailable and the laptop satellites are used. Docker
is reached as `docker -H ssh://<host>`, so no Docker context is needed, and `~/.ssh/config`
needs `ControlMaster` for the host.
