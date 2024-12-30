# rebalance/db_routers.py

class TradingRouter:
    """
    A router to control all database operations on models in the
    Trading application.
    """
    route_app_labels = {'trading'}

    def db_for_read(self, model, **hints):
        """
        Attempts to read trading models go to trading db.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'trading'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write trading models go to trading db.
        """
        if model._meta.app_label in self.route_app_labels:
            return 'trading'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the trading app is involved.
        """
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Ensure that the trading app's models get created on the right database.
        """
        if app_label in self.route_app_labels:
            return db == 'trading'
        return None
