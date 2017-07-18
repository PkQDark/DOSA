from django.db import models
from django.db.models import Sum
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from pytz import timezone
from local_admin.models import Company, CompanyUser, Device

kiev = timezone('Europe/Kiev')


class KeyOwner(models.Model):
    name = models.CharField(max_length=40, default='')
    car = models.CharField(max_length=40, default='')
    keys = models.CharField(max_length=16, unique=True)
    company = models.ForeignKey(Company)
    comment = models.TextField(null=True, blank=True)


class FuelType(models.Model):
    name = models.CharField(max_length=40)
    company = models.ForeignKey(Company)
    comment = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (("name", "company"),)


class Cistern(models.Model):
    CISTERN_TYPES = (('box', 'куб'),
                     ('hc', 'горизонтальный цилиндр'),
                     ('vc', 'вертикальный цилиндр'))
    start_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    max_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    cistern_type = models.CharField(max_length=3, choices=CISTERN_TYPES)
    fuel = models.ForeignKey(FuelType)
    name = models.CharField(max_length=20, default='')
    dev = models.OneToOneField(Device)

    def save(self, *args, **kwargs):
        if self.start_volume > self.max_volume:
            raise ValueError('Начальное значение не может превышать максимальное')
        else:
            super(Cistern, self).save(*args, **kwargs)


class Database(models.Model):
    user = models.ForeignKey(KeyOwner)
    dosed = models.DecimalField(decimal_places=2, max_digits=15)
    date_time = models.DateTimeField()
    add = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    cistern_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    fuel_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    dev = models.ForeignKey(Device)
    delete = models.BooleanField(default=False)

    class Meta:
        ordering = ["date_time"]


class UpDosed(models.Model):
    user = models.ForeignKey(CompanyUser)
    date_time = models.DateTimeField()
    volume = models.DecimalField(decimal_places=2, max_digits=15)
    dev = models.ForeignKey(Device)
    comment = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["date_time"]


class DayLimit(models.Model):
    start_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    cur_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    start_date = models.DateTimeField()
    key_owner = models.OneToOneField(KeyOwner, primary_key=True)

    def recalc(self, *args, **kwargs):
        today = kiev.localize(datetime.combine(datetime.now().date(), datetime.min.time()))
        if self.start_date < today:
            self.start_date = today
        ent = Database.objects.filter(user=self.key_owner, date_time__gte=self.start_date).count()
        if ent > 0:
            self.cur_volume = self.start_volume - Database.objects.filter(user=self.key_owner,
                                                                          date_time__gte=self.start_date).aggregate(
                Sum('dosed'))['dosed__sum']
        else:
            self.cur_volume = self.start_volume
        super(DayLimit, self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        ent = Database.objects.filter(user=self.key_owner, date_time__gte=self.start_date).count()
        if ent > 0:
            self.cur_volume = self.start_volume - Database.objects.filter(user=self.key_owner,
                                                                          date_time__gte=self.start_date).aggregate(
                Sum('dosed'))['dosed__sum']
        else:
            self.cur_volume = self.start_volume
        super(DayLimit, self).save(*args, **kwargs)


class WeekLimit(models.Model):
    start_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    cur_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    start_date = models.DateTimeField()
    key_owner = models.OneToOneField(KeyOwner, primary_key=True)

    def recalc(self, *args, **kwargs):
        today = kiev.localize(datetime.combine(datetime.now().date(), datetime.min.time()))
        while self.start_date <= today - timedelta(days=7):
            self.start_date += timedelta(days=7)
        ent = Database.objects.filter(user=self.key_owner, date_time__gte=self.start_date).count()
        if ent > 0:
            self.cur_volume = self.start_volume - Database.objects.filter(user=self.key_owner,
                                                                          date_time__gte=self.start_date).aggregate(
                Sum('dosed'))['dosed__sum']
        else:
            self.cur_volume = self.start_volume
        super(WeekLimit, self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        ent = Database.objects.filter(user=self.key_owner, date_time__gte=self.start_date).count()
        if ent > 0:
            self.cur_volume = self.start_volume - Database.objects.filter(user=self.key_owner,
                                                                          date_time__gte=self.start_date).aggregate(
                Sum('dosed'))['dosed__sum']
        else:
            self.cur_volume = self.start_volume
        super(WeekLimit, self).save(*args, **kwargs)


class MonthLimit(models.Model):
    start_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    cur_volume = models.DecimalField(decimal_places=2, max_digits=15, default=0)
    start_date = models.DateTimeField()
    key_owner = models.OneToOneField(KeyOwner, primary_key=True)

    def recalc(self, *args, **kwargs):
        today = kiev.localize(datetime.combine(datetime.now().date(), datetime.min.time()))
        while self.start_date <= today - relativedelta(months=1):
            self.start_date += relativedelta(months=1)
        ent = Database.objects.filter(user=self.key_owner, date_time__gte=self.start_date).count()
        if ent > 0:
            self.cur_volume = self.start_volume - Database.objects.filter(user=self.key_owner,
                                                                          date_time__gte=self.start_date).aggregate(
                Sum('dosed'))['dosed__sum']
        else:
            self.cur_volume = self.start_volume
        super(MonthLimit, self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        ent = Database.objects.filter(user=self.key_owner, date_time__gte=self.start_date).count()
        if ent > 0:
            self.cur_volume = self.start_volume - Database.objects.filter(user=self.key_owner,
                                                                          date_time__gte=self.start_date).aggregate(
                Sum('dosed'))['dosed__sum']
        else:
            self.cur_volume = self.start_volume
        super(MonthLimit, self).save(*args, **kwargs)
