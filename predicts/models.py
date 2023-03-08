from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.
class Predicts(models.Model):
    Date = models.DateField()
    Symbol = models.CharField(max_length=45, primary_key=True)
    Exchange = models.CharField(max_length=45)
    Prediction = models.IntegerField()

    class Meta:
        db_table = 'predicts_db'

    def __str__(self):
        return f'{self.Symbol}.{self.Exchange}:{str(self.Date)}={self.Prediction}'