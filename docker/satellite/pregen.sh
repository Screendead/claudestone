#!/bin/sh
# Image build only: unpack the bundled libraries, generate the world, set the gamerules
# scripts/servers.py sets, generate every plot's chunks, and record an AOT cache.
set -eu
cd /srv
java -jar /tmp/server.jar --help >/dev/null
{ find libraries -name '*.jar' | sort; echo versions/26.3/server-26.3.jar; } | paste -sd: > classpath
mkfifo /tmp/console
java -Xmx1G -XX:AOTCacheOutput=/srv/server.aot -Xlog:aot=error -cp "$(cat classpath)" net.minecraft.server.Main nogui \
    < /tmp/console > /tmp/pregen.log 2>&1 &
pid=$!
exec 3>/tmp/console
wait_for() {
    until grep -q "$1" /tmp/pregen.log; do
        kill -0 $pid 2>/dev/null || { cat /tmp/pregen.log; exit 1; }
        sleep 1
    done
}
wait_for 'Done ('
for rule in advance_time advance_weather spawn_mobs; do echo "gamerule $rule false" >&3; done
# Chunks x 8..21, z -17..20 cover every plot in redstone/plots.py (256 chunks per command).
for z in "-272 -81" "-80 127" "128 335"; do set -- $z; echo "forceload add 128 $1 351 $2" >&3; done
until grep -q pregen-loaded /tmp/pregen.log; do
    echo "execute if loaded 128 56 -272 if loaded 351 56 -272 if loaded 128 56 335 if loaded 351 56 335 if loaded 240 56 32 run say pregen-loaded" >&3
    sleep 2
done
echo "forceload remove all" >&3
echo "stop" >&3
wait $pid
cat /tmp/pregen.log
