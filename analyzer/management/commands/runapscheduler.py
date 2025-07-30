from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import time
from analyzer import utils

class Command(BaseCommand):
    help = "Runs the APScheduler for monitoring trades."

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        app_settings = utils.load_settings()

        interval_str = app_settings.get("update_interval", "15 Mins")
        if interval_str != "Disable":
            value, unit = interval_str.split()
            value = int(value)

            if 'Min' in unit:
                kwargs = {'minutes': value}
            elif 'Hour' in unit:
                kwargs = {'hours': value}
            else:
                kwargs = {'minutes': 15} # Default case

            scheduler.add_job(
                utils.monitor_trades, 'interval', **kwargs,
                args=[False], id='pl_monitor', replace_existing=True
            )
            self.stdout.write(self.style.SUCCESS(f"Scheduled P/L monitor to run every {value} {unit}."))

        scheduler.add_job(
            lambda: utils.monitor_trades(is_eod_report=True), 'cron',
            day_of_week='mon-fri', hour=15, minute=45, id='eod_report', replace_existing=True
        )
        self.stdout.write(self.style.SUCCESS("Scheduled EOD report."))
        self.stdout.write(self.style.SUCCESS("Starting scheduler... Press Ctrl+C to exit."))
        scheduler.start()

        try:
            while True:
                time.sleep(2)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS("Scheduler shut down successfully."))