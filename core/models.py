from django.db import models

class Status(models.Model):

    name = models.CharField(max_length=50, unique=True, verbose_name="Status Name")
    is_active= models.BooleanField(default=True, verbose_name="Is Active?")

    class Meta:
        verbose_name = "Status"
        verbose_name_plural = "Statuses"

    def __str__(self):
        return self.name
    
class Country(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Country Name")
    iso_code = models.CharField(max_length=3, unique=True, verbose_name="ISO Code") 

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name

class Currency(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Currency Name")
    code = models.CharField(max_length=3, unique=True, verbose_name="Currency Code") 
    symbol = models.CharField(max_length=5, verbose_name="Symbol") 

    class Meta:
        verbose_name = "Currency"
        verbose_name_plural = "Currencies"

    def __str__(self):
        return f"{self.name} ({self.code})"

class ExchangeRate(models.Model):
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='exchange_rates', verbose_name="Currency")
    date = models.DateField(verbose_name="Date") 
    rate = models.DecimalField(max_digits=18, decimal_places=6, verbose_name="Exchange Rate")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        unique_together = ('currency', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.currency.symbol} - {self.date}: {self.rate}"
