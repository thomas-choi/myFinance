# rebalance/models.py

from django.db import models
import pandas as pd
import json
import logging

class Weight(models.Model):
    date = models.DateField(null=True, blank=True)
    port_name = models.CharField(max_length=45, null=True, blank=True)
    risk_mes = models.CharField(max_length=10, null=True, blank=True)
    obj_type = models.CharField(max_length=10, null=True, blank=True)
    int_type = models.CharField(max_length=2, null=True, blank=True)
    weights = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'weights'
        app_label = 'trading'

    def __str__(self):
        return self.port_name

    def get_weights_list(self):
        """Convert weights JSON field to a list of key-value pairs"""
        if self.weights:
            try:
                weights_dict = self.weights
                logging.debug(f'weights_dict  type: {type(weights_dict)}')
                logging.debug(f'weights_dict: {weights_dict}')
                wlist = [(key, value) for key, value in weights_dict.items() if value != 0]
                logging.debug(f'wlist: {wlist}')
                return wlist
                # return list(weights_dict.items())
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def get_weights_df(self):
        """Convert weights JSON field to a list of key-value pairs"""
        if self.weights:
            try:
                weights_dict = self.weights
                logging.debug(f'weights_dict  type: {type(weights_dict)}')
                logging.debug(f'weights_dict: {weights_dict}')
                df = pd.DataFrame(weights_dict.items(), columns=['Symbol','weight'])
                df = df[df.weight != 0]
                df = df.sort_values(by=['Symbol'], ascending=True)
                df = df.set_index(['Symbol'])
                logging.debug(f'weights_df: {df}')
                return df
                # return list(weights_dict.items())
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    
    # Optionally, you can add a property decorator for easier access
    @property
    def weights_list(self):
        return self.get_weights_list()
