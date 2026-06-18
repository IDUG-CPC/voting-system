from django.db import models

class PresenterType(models.Model):
    presenter_type_code = models.CharField(db_column='PRESENTER_TYPE_CODE', primary_key=True, max_length=1)  # Field name made lowercase.
    presenter_type_desc = models.CharField(db_column='PRESENTER_TYPE_DESC', max_length=20, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'PRESENTER_TYPE'


class Subject(models.Model):
    subject_id = models.CharField(db_column='SUBJECT_ID', primary_key=True, max_length=1)  # Field name made lowercase.
    subject_desc = models.CharField(db_column='SUBJECT_DESC', max_length=15, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'SUBJECT'


class CurrentEvent(models.Model):
    session_event = models.CharField(db_column='SESSION_EVENT', primary_key=True, max_length=10)
    event_city = models.CharField(db_column='EVENT_CITY', max_length=30)
    event_date = models.CharField(db_column='EVENT_DATE', max_length=30)
    is_active = models.BooleanField(db_column='IS_ACTIVE')

    class Meta:
        managed = False
        db_table = 'CURRENT_EVENT'


class Session(models.Model):
    session_event = models.CharField(db_column='SESSION_EVENT', max_length=10)  # Field name made lowercase.
    session_code = models.CharField(db_column='SESSION_CODE', primary_key=True, max_length=5)  # Field name made lowercase.
    session_date = models.DateField(db_column='SESSION_DATE', blank=True, null=True)  # Field name made lowercase.
    session_start = models.TimeField(db_column='SESSION_START', blank=True, null=True)  # Field name made lowercase.
    session_end = models.TimeField(db_column='SESSION_END', blank=True, null=True)  # Field name made lowercase.
    session_number = models.CharField(db_column='SESSION_NUMBER', max_length=10, blank=True, null=True)  # Field name made lowercase.
    session_title = models.CharField(db_column='SESSION_TITLE', max_length=250, blank=True, null=True)  # Field name made lowercase.
    subject = models.ForeignKey('Subject', models.DO_NOTHING, db_column='SUBJECT_ID')  # Field name made lowercase.
    primary_presenter_firstname = models.CharField(db_column='PRIMARY_PRESENTER_FIRSTNAME', max_length=50, blank=True, null=True)  # Field name made lowercase.
    primary_presenter_lastname = models.CharField(db_column='PRIMARY_PRESENTER_LASTNAME', max_length=50, blank=True, null=True)  # Field name made lowercase.
    primary_presenter_company = models.CharField(db_column='PRIMARY_PRESENTER_COMPANY', max_length=50, blank=True, null=True)  # Field name made lowercase.
    secondary_presenter_firstname = models.CharField(db_column='SECONDARY_PRESENTER_FIRSTNAME', max_length=50, blank=True, null=True)  # Field name made lowercase.
    secondary_presenter_lastname = models.CharField(db_column='SECONDARY_PRESENTER_LASTNAME', max_length=50, blank=True, null=True)  # Field name made lowercase.
    secondary_presenter_company = models.CharField(db_column='SECONDARY_PRESENTER_COMPANY', max_length=50, blank=True, null=True)  # Field name made lowercase.
    presenter_type_code = models.ForeignKey(PresenterType, models.DO_NOTHING, db_column='PRESENTER_TYPE_CODE')  # Field name made lowercase.
    start_count = models.IntegerField(db_column='START_COUNT', null=True)  # Field name made lowercase.
    mid_count = models.IntegerField(db_column='MID_COUNT', null=True)  # Field name made lowercase.
    comments = models.CharField(db_column='COMMENTS', max_length=400, blank=True, null=True)  # Field name made lowercase.
    moderator_status_id = models.SmallIntegerField(db_column='MODERATOR_STATUS_ID')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'SESSION'
        unique_together = (('session_event', 'session_code'),)



class Moderator(models.Model):
    session_event = models.CharField(db_column='SESSION_EVENT', max_length=10 )  # Field name made lowercase.
    session_code = models.CharField(db_column='SESSION_CODE', primary_key=True, max_length=5)  # Field name made lowercase.
    moderator_name = models.CharField(db_column='MODERATOR_NAME', max_length=100, blank=True, null=True)  # Field name made lowercase.
    moderator_email = models.CharField(db_column='MODERATOR_EMAIL', max_length=50, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MODERATOR'
        unique_together = (('session_event', 'session_code'),)



class Moderators(models.Model):
    session_event = models.CharField(db_column='SESSION_EVENT', max_length=10, blank=True)  # Field name made lowercase.
    session_code = models.CharField(db_column='SESSION_CODE', primary_key=True, max_length=5, blank=True)  # Field name made lowercase.
    date = models.DateField(db_column='DATE', blank=True, null=True)  # Field name made lowercase.
    session_date = models.TextField(db_column='SESSION_DATE', blank=True, null=True)  # Field name made lowercase.
    session_time = models.TextField(db_column='SESSION_TIME', blank=True, null=True)  # Field name made lowercase.
    session_title = models.CharField(db_column='SESSION_TITLE', max_length=250, blank=True, null=True)  # Field name made lowercase.
    speaker = models.TextField(db_column='SPEAKER', blank=True, null=True)  # Field name made lowercase.
    moderator_name = models.CharField(db_column='MODERATOR_NAME', max_length=100, blank=True, null=True)  # Field name made lowercase.
    subject_desc = models.CharField(db_column='SUBJECT_DESC', max_length=15, blank=True, null=True)  # Field name made lowercase.
    search = models.TextField(db_column='SEARCH', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'MODERATORS'
        unique_together = (('session_event', 'session_code'),)


