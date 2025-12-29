import subprocess
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Restaurer la base de données depuis une sauvegarde"

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file",
            type=str,
            help="Chemin vers le fichier de sauvegarde (.sql ou .sql.gz)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Forcer la restauration sans confirmation",
        )

    def handle(self, *args, **options):
        backup_file = options["backup_file"]
        force = options["force"]

        if not os.path.exists(backup_file):
            self.stdout.write(self.style.ERROR(f"Fichier introuvable: {backup_file}"))
            return

        if not force:
            confirmation = input(
                "ATTENTION: Cette opération va écraser la base de données. "
                "Continuer? (oui/non): "
            )
            if confirmation.lower() != "oui":
                self.stdout.write("Restauration annulée")
                return

        db_settings = settings.DATABASES["default"]

        self.stdout.write(f"Restauration depuis: {backup_file}")

        try:
            if backup_file.endswith(".gz"):
                with subprocess.Popen(
                    ["gunzip", "-c", backup_file], stdout=subprocess.PIPE
                ) as gunzip_proc:
                    cmd = [
                        "mysql",
                        f"--user={db_settings['USER']}",
                        f"--password={db_settings['PASSWORD']}",
                        f"--host={db_settings['HOST']}",
                        f"--port={db_settings['PORT']}",
                        db_settings["NAME"],
                    ]
                    subprocess.run(
                        cmd,
                        stdin=gunzip_proc.stdout,
                        check=True,
                        stderr=subprocess.PIPE,
                    )
            else:
                cmd = [
                    "mysql",
                    f"--user={db_settings['USER']}",
                    f"--password={db_settings['PASSWORD']}",
                    f"--host={db_settings['HOST']}",
                    f"--port={db_settings['PORT']}",
                    db_settings["NAME"],
                ]
                with open(backup_file, "r") as f:
                    subprocess.run(cmd, stdin=f, check=True, stderr=subprocess.PIPE)

            self.stdout.write(self.style.SUCCESS("Restauration terminée avec succès"))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f"Erreur lors de la restauration: {e.stderr.decode()}")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erreur: {str(e)}"))
