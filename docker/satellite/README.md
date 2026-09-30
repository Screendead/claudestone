# redstone-satellite

A headless 26.3 satellite with sat1..sat6's settings (flat preset, distance 2, gamerules
off), libraries unpacked, world and every plot's chunks pre-generated, and a JDK AOT cache.
The build context is this folder plus `server/server.jar` (the legacy builder has no BuildKit):

    COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -cf - -C docker/satellite \
      Dockerfile server.properties pregen.sh start.sh -C ../../server server.jar \
      | docker --context desktop build -t redstone-satellite:26.3 -

Run (RCON only on the desktop's loopback), then tunnel from the laptop:

    docker --context desktop run -d --rm --name rsat1 -e RCON_PASSWORD=... \
      -p 127.0.0.1:25676:25575 redstone-satellite:26.3
    ssh -N -L 25676:127.0.0.1:25676 <user>@<desktop-host>

Level `testworld`; the data pack dir is `/srv/testworld/datapacks` (`docker cp` into it,
then `reload`). A TCP connect through the tunnel succeeds even with the server down, so
wait for an RCON login, not an open port. `MEMORY` (default 1G) and `JAVA_OPTS` are optional.

The harness (`redstone/docker_sats.py`) reaches the desktop as `REDSTONE_DOCKER_HOST`, else
the one line `user@host` in `server/docker_host` (gitignored, like the rest of `server/`).
With neither, the Docker backend is unavailable and the laptop satellites are used. The
`desktop` Docker context must point at the same host (`docker context create desktop
--docker host=ssh://<user>@<desktop-host>`), and `~/.ssh/config` needs `ControlMaster` for it.
