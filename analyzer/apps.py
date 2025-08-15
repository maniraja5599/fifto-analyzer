from django.apps import AppConfig


class AnalyzerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analyzer"
    
    def ready(self):
        """P&L updater startup disabled - manual control only"""
        print("📝 P&L Updater available on-demand (automatic startup disabled)")
        # DISABLED: Automatic P&L updater startup removed for manual control
        # try:
        #     from .pnl_updater import pnl_updater
        #     pnl_updater.start_updater()
        #     print("🚀 P&L Updater started automatically (30-minute intervals)")
        # except Exception as e:
        #     print(f"❌ Failed to start P&L updater: {e}")
