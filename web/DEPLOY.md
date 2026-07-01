# Deploying to EC2 (Ubuntu, native Postgres)

Single EC2 instance running Nginx (TLS termination + reverse proxy), the
Next.js app under systemd, and Postgres installed natively on the same box.
No Docker involved — Postgres only needs to be reachable from `localhost`,
so there's no benefit to containerizing either piece here.

Assumes Ubuntu 22.04 or 24.04. Run everything below over SSH on the instance.

## 0. Security group

Only open what the internet needs to reach directly:

- `22` (SSH) — restrict to your IP if possible
- `80`, `443` (HTTP/HTTPS)

**Do not open `5432`.** Postgres should never be reachable from outside the
instance — the app talks to it over `localhost`, nothing else needs to.

## 1. System packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx postgresql postgresql-contrib certbot python3-certbot-nginx

# Node 22 LTS (next.js here requires >=20.9)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

## 2. Postgres — create the app role and database

Postgres listens on `localhost:5432` by default after `apt install` — leave
it that way.

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE mydatatalk WITH LOGIN PASSWORD 'CHANGE_ME';
CREATE DATABASE mydatatalk OWNER mydatatalk;
SQL
```

Use a real generated password (`openssl rand -base64 24`), not the
placeholder — it goes into `/etc/mydatatalk/web.env` in step 4.

## 3. App user and code

Run the app as a dedicated, unprivileged system user rather than root or
your own login — matches the `User=mydatatalk` in the systemd unit.

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin mydatatalk
sudo mkdir -p /opt/mydatatalk
sudo chown mydatatalk:mydatatalk /opt/mydatatalk

sudo -u mydatatalk git clone https://github.com/lakefrontai/aidataanalyst.git /opt/mydatatalk/src
cd /opt/mydatatalk/src/web
sudo -u mydatatalk npm ci
```

(`/opt/mydatatalk/web` referenced by the systemd unit is a symlink set up in
the redeploy step below — see step 6.)

## 4. Environment file

```bash
sudo mkdir -p /etc/mydatatalk
sudo cp deploy/web.env.example /etc/mydatatalk/web.env
sudo chown root:mydatatalk /etc/mydatatalk/web.env
sudo chmod 640 /etc/mydatatalk/web.env
sudo nano /etc/mydatatalk/web.env   # fill in the real DB password + AUTH_SECRET
```

Generate `AUTH_SECRET` with `openssl rand -base64 32`. Keep it stable across
deploys — rotating it invalidates every existing session.

## 5. Migrate, build, and link the release

```bash
cd /opt/mydatatalk/src/web
sudo -u mydatatalk env $(grep -v '^#' /etc/mydatatalk/web.env | xargs) npx prisma migrate deploy
sudo -u mydatatalk npm run build

sudo ln -sfn /opt/mydatatalk/src/web /opt/mydatatalk/web
```

## 6. systemd service

```bash
sudo cp deploy/mydatatalk-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mydatatalk-web
sudo systemctl status mydatatalk-web
```

## 7. Nginx + TLS

```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/mydatatalk.ai
sudo ln -s /etc/nginx/sites-available/mydatatalk.ai /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Point mydatatalk.ai's DNS A record at this instance's IP first, then:
sudo certbot --nginx -d mydatatalk.ai -d www.mydatatalk.ai
```

Certbot rewrites `nginx.conf` in place to add the HTTPS server block and a
redirect from port 80. It also sets up auto-renewal via a systemd timer —
verify with `sudo systemctl status certbot.timer`.

## Redeploying after a code change

```bash
cd /opt/mydatatalk/src && sudo -u mydatatalk git pull
cd web && sudo -u mydatatalk npm ci
sudo -u mydatatalk env $(grep -v '^#' /etc/mydatatalk/web.env | xargs) npx prisma migrate deploy
sudo -u mydatatalk npm run build
sudo systemctl restart mydatatalk-web
```

## Backups

Nothing here backs up the database automatically. At minimum, cron a nightly
`pg_dump`:

```bash
# /etc/cron.d/mydatatalk-backup
0 3 * * * postgres pg_dump mydatatalk | gzip > /var/backups/mydatatalk-$(date +\%Y\%m\%d).sql.gz
```

Ship those off-instance (S3, etc.) — a backup that lives on the same disk as
the database doesn't survive an instance failure.
