from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import time
from analyzer import utils

class Command(BaseCommand):
    help = "Runs the APScheduler for monitoring trades and automated chart generation."

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Kolkata'))
        app_settings = utils.load_settings()

        # Schedule P&L monitoring
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

        # Schedule EOD report
        scheduler.add_job(
            lambda: utils.monitor_trades(is_eod_report=True), 'cron',
            day_of_week='mon-fri', hour=15, minute=45, id='eod_report', replace_existing=True
        )
        self.stdout.write(self.style.SUCCESS("Scheduled EOD report."))

        # Schedule automated chart generation
        auto_gen_time = app_settings.get('auto_gen_time', '09:20')
        auto_gen_days = app_settings.get('auto_gen_days', [])
        
        if app_settings.get('enable_auto_generation', False) and auto_gen_days:
            try:
                hour, minute = auto_gen_time.split(':')
                hour, minute = int(hour), int(minute)
                
                # Validate time is within market hours (9:15 AM to 3:30 PM)
                if hour < 9 or (hour == 9 and minute < 15) or hour > 15 or (hour == 15 and minute > 30):
                    self.stdout.write(self.style.WARNING(f"Warning: Scheduled time {auto_gen_time} is outside market hours (9:15 AM - 3:30 PM)"))
                
                # Convert day names to scheduler format
                day_mapping = {
                    'monday': 'mon', 'tuesday': 'tue', 'wednesday': 'wed',
                    'thursday': 'thu', 'friday': 'fri', 'saturday': 'sat', 'sunday': 'sun'
                }
                scheduled_days = ','.join([day_mapping.get(day.lower(), day.lower()[:3]) for day in auto_gen_days])
                
                # Add main job
                scheduler.add_job(
                    utils.run_automated_chart_generation, 'cron',
                    day_of_week=scheduled_days, hour=hour, minute=minute, 
                    id='auto_chart_generation', replace_existing=True,
                    max_instances=1,  # Prevent overlapping executions
                    coalesce=True     # Combine missed executions
                )
                
                # Add a retry job 5 minutes later in case the main job fails
                retry_minute = (minute + 5) % 60
                retry_hour = hour + ((minute + 5) // 60)
                
                scheduler.add_job(
                    utils.run_automated_chart_generation, 'cron',
                    day_of_week=scheduled_days, hour=retry_hour, minute=retry_minute, 
                    id='auto_chart_generation_retry', replace_existing=True,
                    max_instances=1,
                    coalesce=True
                )
                
                self.stdout.write(self.style.SUCCESS(f"Scheduled automated chart generation at {auto_gen_time} (with retry at {retry_hour:02d}:{retry_minute:02d}) on {', '.join(auto_gen_days)}."))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to schedule automation: {str(e)}"))
        else:
            self.stdout.write(self.style.WARNING("Automated chart generation is disabled or no days configured."))

        self.stdout.write(self.style.SUCCESS("Starting scheduler... Press Ctrl+C to exit."))
        scheduler.start()

        try:
            while True:
                time.sleep(2)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS("Scheduler shut down successfully."))