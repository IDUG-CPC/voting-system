from django.db import models
from django.utils import timezone
import uuid


class ActionLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=timezone.now)
    action_type = models.CharField(max_length=20)
    message = models.CharField(max_length=300)
    event_code = models.CharField(max_length=10, default="EMEA")
    day = models.ForeignKey('PlannerDay', models.DO_NOTHING, db_column='day')
    track = models.CharField(max_length=1, blank=True, null=True)
    layout = models.ForeignKey('CalendarLayout', models.DO_NOTHING, blank=True, null=True)
    session = models.ForeignKey('Session', models.DO_NOTHING, blank=True, null=True)
    special_session_type = models.ForeignKey(
        'SpecialSessionType', models.DO_NOTHING, blank=True, null=True
    )
    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    comment = models.TextField(blank=True, null=True)
    commented_at = models.DateTimeField(blank=True, null=True)
    slot_description = models.TextField(blank=True, null=True)  # CalendarSlot.description when unassigning special, for undo

    class Meta:
        managed = False
        db_table = 'planner_actionlog'
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%H:%M:%S} {self.message}"


class CalendarColumnHeader(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    track = models.CharField(max_length=1)
    subject = models.CharField(max_length=100)
    room_name = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = 'planner_calendarcolumnheader'
        ordering = ["track"]
        unique_together = (("event_code", "track"),)

    def __str__(self):
        return f"{self.track}: {self.subject} / {self.room_name}"


class CalendarLayout(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    day = models.ForeignKey('PlannerDay', models.DO_NOTHING, db_column='day')
    track = models.CharField(max_length=1)
    rowspan = models.SmallIntegerField()
    colspan = models.SmallIntegerField()
    visible = models.BooleanField()
    type = models.CharField(max_length=20)
    label = models.CharField(max_length=100, blank=True, null=True)
    time_slot = models.ForeignKey('CalendarTimeSlot', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'planner_calendarlayout'
        unique_together = (('day', 'label', 'time_slot'),)
        ordering = ["day", "time_slot__order", "track"]

    def __str__(self):
        return f"Day{self.day} {self.track} [{self.time_slot.label}]"


class SpecialSessionType(models.Model):
    """Placeholder types for the calendar (e.g. PSP). Not from Session table; can be placed multiple times."""
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default="#e7f1ff")

    class Meta:
        managed = False
        db_table = "planner_specialsessiontype"

    def __str__(self):
        return self.name


class CalendarSlot(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    layout = models.OneToOneField(CalendarLayout, models.DO_NOTHING)
    session = models.ForeignKey('Session', models.DO_NOTHING, blank=True, null=True)
    special_session_type = models.ForeignKey(
        'SpecialSessionType', models.DO_NOTHING, blank=True, null=True
    )
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'planner_calendarslot'

    def __str__(self):
        if self.session:
            return f"{self.layout} -> {self.session}"
        if self.special_session_type:
            return f"{self.layout} -> {self.special_session_type.name}"
        return f"{self.layout} -> Empty"



class CalendarTimeSlot(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    day = models.ForeignKey('PlannerDay', models.DO_NOTHING, db_column='day')
    order = models.SmallIntegerField()
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    label = models.CharField(max_length=80, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'planner_calendartimeslot'
        unique_together = (('day', 'order'),)
        ordering = ["day", "order"]

    def __str__(self):
        if self.start_time and self.end_time:
            return f"Day{self.day} {self.start_time:%H:%M}-{self.end_time:%H:%M}"
        return f"Day{self.day} {self.label or '?'}"


class PlannerDay(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    day = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'planner_day'


class Subject(models.Model):
    subject_id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    subject_code = models.CharField(max_length=10, blank=True, null=True)
    subject_desc = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'planner_subject'


class Topic(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    code = models.CharField(max_length=120)

    class Meta:
        managed = False
        db_table = "planner_topic"
        ordering = ["code"]
        unique_together = (("event_code", "code"),)

    def __str__(self):
        return self.code


class SessionTopic(models.Model):
    """Many-to-many: Session <-> Topic."""
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey("Session", models.CASCADE, db_column="session_id")
    topic = models.ForeignKey("Topic", models.CASCADE, db_column="topic_id")

    class Meta:
        managed = False
        db_table = "planner_session_topic"
        unique_together = (("session", "topic"),)


class Session(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    session_code = models.CharField(max_length=20)
    title = models.CharField(max_length=250)
    speaker_first_name = models.CharField(max_length=100, blank=True, null=True)
    speaker_last_name = models.CharField(max_length=100, blank=True, null=True)
    speaker_company = models.CharField(max_length=200, blank=True, null=True)
    session_type = models.ForeignKey('SessionType', models.DO_NOTHING)
    subject = models.ForeignKey('Subject', models.DO_NOTHING)
    rating = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        managed = False
        db_table = 'planner_session'
        unique_together = (("event_code", "session_code"),)

    def speaker_full_name(self):
        first = self.speaker_first_name or ""
        last = self.speaker_last_name or ""
        return f"{first} {last}".strip()

    def __str__(self):
        return f"{self.session_code} - {self.title}"


class SessionType(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_code = models.CharField(max_length=10, default="EMEA")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20)
    description = models.TextField()

    class Meta:
        managed = False
        db_table = 'planner_sessiontype'

    def __str__(self):
        return self.name