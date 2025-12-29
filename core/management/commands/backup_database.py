import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = "Créer une sauvegarde de la base de données"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default="/tmp/BINTACURA_backups",
            help="Répertoire de sortie pour les sauvegardes",
        )

    def handle(self, *args, **options):
        output_dir = options["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(output_dir, f"BINTACURA_{timestamp}.sql")

        db_settings = settings.DATABASES["default"]

        cmd = [
            "mysqldump",
            f"--user={db_settings['USER']}",
            f"--password={db_settings['PASSWORD']}",
            f"--host={db_settings['HOST']}",
            f"--port={db_settings['PORT']}",
            db_settings["NAME"],
        ]

        self.stdout.write(f"Création de la sauvegarde: {backup_file}")

        try:
            with open(backup_file, "w") as f:
                subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE)

            subprocess.run(["gzip", backup_file], check=True)
            backup_file_gz = f"{backup_file}.gz"

            file_size = os.path.getsize(backup_file_gz) / (1024 * 1024)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Sauvegarde créée avec succès: {backup_file_gz} ({file_size:.2f} MB)"
                )
            )
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f"Erreur lors de la sauvegarde: {e.stderr.decode()}")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur: {str(e)}"))

