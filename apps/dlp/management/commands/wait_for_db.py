import time
import logging
from django.db import connections
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Django command to wait for the database to be available."""

    def handle(self, *args, **options):
        self.stdout.write("Waiting for the database to be available...")
        db_conn = None
        while not db_conn:
            try:
                db_conn = connections["default"]
                db_conn.cursor()
            except OperationalError:
                self.stdout.write("Database not ready, waiting...")
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS("Database is ready!"))
