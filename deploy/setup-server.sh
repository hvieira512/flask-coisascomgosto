#!/bin/sh
# Sets up a fresh Ubuntu server to run the shop, start to finish. From your own
# machine, in the project folder:
#
#     ssh root@SERVER sh -s coisascomgosto.pt < deploy/setup-server.sh
#
# Installs Docker, makes a `deploy` user for the site and for the deploy job,
# clones main under /srv, writes a .env with freshly generated secrets, starts
# the stack, and prints the one key to put in GitHub. Safe to run again: every
# step checks before it acts.
set -eu

DOMAIN="${1:?usage: setup-server.sh DOMAIN}"
REPO=https://github.com/hvieira512/flask-coisascomgosto.git
DIR=/srv/coisascomgosto

export DEBIAN_FRONTEND=noninteractive
command -v git >/dev/null || { apt-get update -q && apt-get install -y -q git; }
# Docker from Docker's own script: Ubuntu's package lags behind.
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh

# The site runs as `deploy`, which may use Docker but has no password and no
# sudo. It gets root's SSH keys, so the key that opened root opens it too.
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash --groups docker deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
[ -f /home/deploy/.ssh/authorized_keys ] \
    || install -m 600 -o deploy -g deploy /root/.ssh/authorized_keys /home/deploy/.ssh/authorized_keys

[ -d "$DIR" ] || { install -d -o deploy -g deploy "$DIR" && su deploy -c "git clone -q $REPO $DIR"; }

# .env from the documented template, with secrets of its own. Written once:
# the database password in it is the database's.
if [ ! -f "$DIR/.env" ]; then
    secret() { openssl rand -base64 48 | tr -d '/+=' | cut -c1-40; }
    cp "$DIR/.env.example" "$DIR/.env"
    sed -i \
        -e "s|^APP_ENV=.*|APP_ENV=production|" \
        -e "s|^APP_DEBUG=.*|APP_DEBUG=false|" \
        -e "s|^APP_KEY=.*|APP_KEY=base64:$(openssl rand -base64 32)|" \
        -e "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$(secret)|" \
        -e "s|^MYSQL_PASSWORD=.*|MYSQL_PASSWORD=$(secret)|" \
        -e "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=$(secret)|" \
        -e "s|^# SERVER_NAME=.*|SERVER_NAME=$DOMAIN, www.$DOMAIN|" \
        "$DIR/.env"
    chown deploy:deploy "$DIR/.env"
    chmod 600 "$DIR/.env"
fi

# A key of its own for the deploy job. The private half goes into the GitHub
# secret DEPLOY_SSH_KEY; it is printed once, below, and otherwise never leaves
# the server.
if [ ! -f /home/deploy/.ssh/github-deploy ]; then
    su deploy -c "ssh-keygen -q -t ed25519 -N '' -C github-deploy -f /home/deploy/.ssh/github-deploy"
    cat /home/deploy/.ssh/github-deploy.pub >> /home/deploy/.ssh/authorized_keys
fi

su deploy -c "cd $DIR && docker compose -f compose.prod.yml up -d --build"

ADDRESS=$(curl -fsS https://api.ipify.org || hostname -I | cut -d' ' -f1)
cat <<EOF

Done. The site is up and answers at https://$DOMAIN as soon as the DNS points
at $ADDRESS.

In GitHub, Settings > Secrets and variables > Actions, add:

  Variables   DEPLOY_HOST = $ADDRESS
              DEPLOY_USER = deploy
  Secret      DEPLOY_SSH_KEY = everything between the lines below, BEGIN and END included

EOF
cat /home/deploy/.ssh/github-deploy
