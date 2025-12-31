# Backup and Restore Procedures

This document provides procedures for backing up and restoring AfterResume data.

## Table of Contents

1. [Backup Strategy](#backup-strategy)
2. [PostgreSQL Backup](#postgresql-backup)
3. [MinIO Backup](#minio-backup)
4. [Backup Verification](#backup-verification)
5. [Restore Procedures](#restore-procedures)
6. [Disaster Recovery](#disaster-recovery)
7. [Automated Backup Setup](#automated-backup-setup)

---

## Backup Strategy

### What to Back Up

**Critical Data:**
- PostgreSQL database (all application data)
- MinIO buckets (user uploads, job artifacts)
- Environment configuration (`.env`, `dokploy.env`)
- SSL certificates (if self-managed)

**Backup Frequency:**
- **Daily**: Full database backup
- **Hourly**: Incremental database backup (if supported)
- **Weekly**: Full MinIO bucket backup
- **Before deployments**: Manual snapshot

**Retention Policy:**
- Daily backups: Keep 30 days
- Weekly backups: Keep 12 weeks
- Monthly backups: Keep 12 months

---

## PostgreSQL Backup

### Manual Full Backup

```bash
# Using pg_dump (recommended)
docker compose -f backend/docker-compose.yml exec postgres \
  pg_dump -U postgres -d afterresume -F c -b -v -f /backup/afterresume_$(date +%Y%m%d_%H%M%S).dump

# Copy backup out of container
docker compose -f backend/docker-compose.yml cp \
  postgres:/backup/afterresume_YYYYMMDD_HHMMSS.dump \
  ./backups/db/
```

### Using pg_dumpall (for all databases)

```bash
docker compose -f backend/docker-compose.yml exec postgres \
  pg_dumpall -U postgres -f /backup/all_databases_$(date +%Y%m%d_%H%M%S).sql
```

### Automated Daily Backup Script

Create `scripts/backup_postgres.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/afterresume/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/afterresume_$TIMESTAMP.dump"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Run backup
docker compose -f /path/to/backend/docker-compose.yml exec -T postgres \
  pg_dump -U postgres -d afterresume -F c -b -v -f /tmp/backup.dump

# Copy backup out
docker compose -f /path/to/backend/docker-compose.yml cp \
  postgres:/tmp/backup.dump \
  $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove old backups
find $BACKUP_DIR -name "*.dump.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### Set Up Cron Job

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/scripts/backup_postgres.sh >> /var/log/afterresume_backup.log 2>&1
```

---

## MinIO Backup

### Manual Bucket Backup

```bash
# Using mc (MinIO Client)
# Install mc: https://min.io/docs/minio/linux/reference/minio-mc.html

# Configure mc
mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Backup specific bucket
mc mirror --preserve local/user-uploads ./backups/minio/user-uploads_$(date +%Y%m%d)

# Backup all buckets
mc mirror --preserve local ./backups/minio/full_$(date +%Y%m%d)
```

### Automated MinIO Backup Script

Create `scripts/backup_minio.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/var/backups/afterresume/minio"
TIMESTAMP=$(date +%Y%m%d)
RETENTION_DAYS=90

# Create backup directory
mkdir -p $BACKUP_DIR

# Configure mc
mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# Backup critical buckets
for BUCKET in user-uploads job-artifacts public-shares; do
  echo "Backing up bucket: $BUCKET"
  mc mirror --preserve local/$BUCKET $BACKUP_DIR/${BUCKET}_${TIMESTAMP}
done

# Remove old backups
find $BACKUP_DIR -type d -name "*_*" -mtime +$RETENTION_DAYS -exec rm -rf {} +

echo "MinIO backup completed: $BACKUP_DIR"
```

### Set Up Weekly Cron Job

```bash
# Edit crontab
crontab -e

# Add weekly backup on Sunday at 3 AM
0 3 * * 0 /path/to/scripts/backup_minio.sh >> /var/log/afterresume_minio_backup.log 2>&1
```

---

## Backup Verification

### Automated Verification Script

Create `scripts/verify_backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.dump>"
  exit 1
fi

echo "Verifying backup: $BACKUP_FILE"

# Decompress if needed
if [[ $BACKUP_FILE == *.gz ]]; then
  gunzip -c $BACKUP_FILE > /tmp/backup_to_verify.dump
  BACKUP_FILE=/tmp/backup_to_verify.dump
fi

# Verify backup file integrity
pg_restore --list $BACKUP_FILE > /dev/null 2>&1

if [ $? -eq 0 ]; then
  echo "✓ Backup verification successful"
  exit 0
else
  echo "✗ Backup verification FAILED"
  exit 1
fi
```

### Manual Verification Steps

1. **Check backup file exists and is not empty:**
   ```bash
   ls -lh ./backups/db/afterresume_*.dump.gz
   ```

2. **Verify backup file integrity:**
   ```bash
   ./scripts/verify_backup.sh ./backups/db/afterresume_20250101_020000.dump.gz
   ```

3. **Test restore to temporary database (recommended):**
   ```bash
   # Create test database
   docker compose -f backend/docker-compose.yml exec postgres \
     psql -U postgres -c "CREATE DATABASE afterresume_test;"
   
   # Restore to test database
   gunzip -c ./backups/db/afterresume_20250101_020000.dump.gz | \
     docker compose -f backend/docker-compose.yml exec -T postgres \
     pg_restore -U postgres -d afterresume_test -v
   
   # Verify data
   docker compose -f backend/docker-compose.yml exec postgres \
     psql -U postgres -d afterresume_test -c "\dt"
   
   # Drop test database
   docker compose -f backend/docker-compose.yml exec postgres \
     psql -U postgres -c "DROP DATABASE afterresume_test;"
   ```

---

## Restore Procedures

### PostgreSQL Full Restore

**⚠️ WARNING: This will replace the current database. Back up first!**

```bash
# 1. Stop backend services
docker compose -f backend/docker-compose.yml stop backend-api backend-worker

# 2. Drop existing database (DESTRUCTIVE)
docker compose -f backend/docker-compose.yml exec postgres \
  psql -U postgres -c "DROP DATABASE afterresume;"

# 3. Create fresh database
docker compose -f backend/docker-compose.yml exec postgres \
  psql -U postgres -c "CREATE DATABASE afterresume;"

# 4. Restore from backup
gunzip -c ./backups/db/afterresume_20250101_020000.dump.gz | \
  docker compose -f backend/docker-compose.yml exec -T postgres \
  pg_restore -U postgres -d afterresume -v

# 5. Restart services
docker compose -f backend/docker-compose.yml start backend-api backend-worker

# 6. Verify
docker compose -f backend/docker-compose.yml exec backend-api \
  python manage.py check
```

### MinIO Restore

```bash
# 1. Restore specific bucket
mc mirror --preserve --overwrite \
  ./backups/minio/user-uploads_20250101 \
  local/user-uploads

# 2. Verify restore
mc ls local/user-uploads
```

### Point-in-Time Recovery

For point-in-time recovery, use PostgreSQL WAL archiving:

1. **Enable WAL archiving** in `postgresql.conf`:
   ```
   wal_level = replica
   archive_mode = on
   archive_command = 'cp %p /backup/wal_archive/%f'
   ```

2. **Base backup + WAL replay** (advanced - see PostgreSQL docs)

---

## Disaster Recovery

### Complete System Rebuild

1. **Provision new infrastructure** (servers, Docker, networking)

2. **Restore configuration:**
   ```bash
   # Copy environment files
   cp /backup/env/dokploy.env ./
   cp /backup/env/.env ./backend/
   
   # Restore SSL certificates (if applicable)
   cp /backup/ssl/* /etc/ssl/afterresume/
   ```

3. **Start services with empty state:**
   ```bash
   docker compose -f backend/docker-compose.yml up -d postgres minio redis
   ```

4. **Wait for services to be ready:**
   ```bash
   docker compose -f backend/docker-compose.yml exec postgres pg_isready
   docker compose -f backend/docker-compose.yml exec redis redis-cli ping
   ```

5. **Restore PostgreSQL:**
   ```bash
   gunzip -c /backup/db/afterresume_latest.dump.gz | \
     docker compose -f backend/docker-compose.yml exec -T postgres \
     pg_restore -U postgres -d afterresume -v
   ```

6. **Restore MinIO:**
   ```bash
   mc mirror --preserve /backup/minio/user-uploads_latest local/user-uploads
   mc mirror --preserve /backup/minio/job-artifacts_latest local/job-artifacts
   ```

7. **Start application services:**
   ```bash
   docker compose -f backend/docker-compose.yml up -d backend-api backend-worker
   ```

8. **Verify system health:**
   ```bash
   curl http://localhost:8000/healthz
   ```

### Recovery Time Objective (RTO) and Recovery Point Objective (RPO)

**Target RTO:** 4 hours (time to restore service)
**Target RPO:** 24 hours (maximum data loss)

With hourly backups: RPO can be reduced to 1 hour.

---

## Automated Backup Setup

### Complete Backup Solution

Create `scripts/backup_all.sh`:

```bash
#!/bin/bash
set -e

BACKUP_BASE="/var/backups/afterresume"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_BASE/logs/backup_$TIMESTAMP.log"

mkdir -p $BACKUP_BASE/logs

{
  echo "=== AfterResume Backup Started: $(date) ==="
  
  # PostgreSQL backup
  echo "Backing up PostgreSQL..."
  /path/to/scripts/backup_postgres.sh
  
  # MinIO backup (weekly only)
  if [ $(date +%u) -eq 7 ]; then
    echo "Backing up MinIO (weekly)..."
    /path/to/scripts/backup_minio.sh
  fi
  
  # Verify latest backup
  echo "Verifying backup..."
  LATEST_BACKUP=$(ls -t $BACKUP_BASE/postgres/*.dump.gz | head -1)
  /path/to/scripts/verify_backup.sh $LATEST_BACKUP
  
  # Upload to remote storage (optional)
  # aws s3 sync $BACKUP_BASE s3://afterresume-backups/
  
  echo "=== Backup Completed: $(date) ==="
} >> $LOG_FILE 2>&1

# Email notification (optional)
# mail -s "AfterResume Backup Report" admin@example.com < $LOG_FILE
```

### Monitoring Backup Health

```bash
# Check last backup age
find /var/backups/afterresume/postgres -name "*.dump.gz" -mtime -1 | wc -l

# Should return 1 (one backup in last 24 hours)
# If returns 0, backup may have failed
```

---

## Human TODOs

- [ ] **Set up automated daily PostgreSQL backups** (cron job + script)
- [ ] **Set up weekly MinIO backups** (cron job + script)
- [ ] **Configure off-site backup storage** (AWS S3, Google Cloud Storage, or similar)
- [ ] **Test restore procedure quarterly** (verify backups work)
- [ ] **Set up backup monitoring alerts** (alert if backup fails or is too old)
- [ ] **Document disaster recovery contact list** (who to call, escalation)
- [ ] **Encrypt backups at rest** (GPG or similar)
- [ ] **Enable PostgreSQL WAL archiving** for point-in-time recovery (optional)
- [ ] **Set up backup verification automation** (monthly automated restore test)

---

## Emergency Contacts

**Database Issues:**
- DBA: [Name] - [Email] - [Phone]

**Infrastructure Issues:**
- DevOps Lead: [Name] - [Email] - [Phone]

**After-Hours Emergency:**
- On-Call Rotation: [Phone/Pager]
