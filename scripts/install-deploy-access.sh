#!/usr/bin/env bash
# One-time setup on the Hostinger VPS. The public key is safe to keep in Git;
# the matching private key is held only by GitHub Actions and the local owner.
set -euo pipefail

if [[ "$(id -u)" != 0 ]]; then
  echo "Run this setup as root" >&2
  exit 1
fi

backend_dir=/opt/prisma-app/PRISMA
install -m 755 "$backend_dir/scripts/prisma-deploy-ssh" /usr/local/sbin/prisma-deploy-ssh
install -d -m 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

deploy_key='command="/usr/local/sbin/prisma-deploy-ssh",restrict ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILj96HeGmXre3XHTEYQwOEdf9OVeNdykrgR3XPflQj8j prisma-github-actions'
if ! grep -Fqx "$deploy_key" /root/.ssh/authorized_keys; then
  printf '%s\n' "$deploy_key" >> /root/.ssh/authorized_keys
fi

echo "Restricted GitHub Actions deploy key installed"
