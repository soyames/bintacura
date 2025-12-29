from celery import shared_task
from django.core.management import call_command
from datetime import datetime
import os


@shared_task
def backup_database_task():
    backup_dir = "/tmp/BINTACURA_backups"
    os.makedirs(backup_dir, exist_ok=True)

    call_command("backup_database", output_dir=backup_dir)

    return f"Backup created at {datetime.now()}"


@shared_task
def cleanup_old_backups(days=30):
    from datetime import timedelta
    import glob

    backup_dir = "/tmp/BINTACURA_backups"
    cutoff_time = datetime.now() - timedelta(days=days)

    deleted_count = 0
    for backup_file in glob.glob(os.path.join(backup_dir, "BINTACURA_*.sql.gz")):
        file_time = datetime.fromtimestamp(os.path.getmtime(backup_file))
        if file_time < cutoff_time:
            os.remove(backup_file)
            deleted_count += 1

    return f"Deleted {deleted_count} old backups"

