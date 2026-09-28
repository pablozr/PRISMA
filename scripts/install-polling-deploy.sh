#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then
  echo "Run this setup as root" >&2
  exit 1
fi

source_dir=/opt/prisma-app/PRISMA/deploy/systemd
install -m 644 "$source_dir/prisma-deploy.service" /etc/systemd/system/prisma-deploy.service
install -m 644 "$source_dir/prisma-deploy.timer" /etc/systemd/system/prisma-deploy.timer
systemctl daemon-reload
systemctl enable --now prisma-deploy.timer
systemctl list-timers prisma-deploy.timer --no-pager
