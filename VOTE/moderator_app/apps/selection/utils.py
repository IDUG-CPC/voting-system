import datetime

from django.db.models import Q

from django.db import connection
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError

from .models import Moderator, ModeratorThankyou, Session


def is_cpc_moderator(name):
    return (name or '').strip().upper() == 'CPC'


def is_valid_email(email):
    try:
        django_validate_email((email or '').strip())
        return True
    except ValidationError:
        return False


def get_moderator_identity(request):
    """Return (name, email) from session, or (None, None) if not identified."""
    name = (request.session.get('moderator_login_name') or '').strip() or None
    email = (request.session.get('moderator_login_email') or '').strip() or None
    return name, email


def is_moderator_identified(request):
    name, email = get_moderator_identity(request)
    if not name:
        return False
    if is_cpc_moderator(name):
        return True
    return bool(email)


def parse_moderator_fields(raw_name, raw_email):
    name = (raw_name or '').strip() or None
    email = (raw_email or '').strip() or None
    return name, email


def validate_moderator_fields(name, email):
    """
    Both filled, both empty (remove), or CPC with name only.
    Returns (is_valid, error_message).
    """
    has_name = bool(name)
    has_email = bool(email)

    if not has_name and not has_email:
        return True, None
    if is_cpc_moderator(name) and has_name:
        return True, None
    if has_name and has_email:
        if not is_valid_email(email):
            return False, 'Please enter a valid email address.'
        return True, None
    return False, (
        'Moderator name and email must both be filled, or both left empty to remove.'
    )


def find_moderator_schedule_conflict(session_event, session_code, moderator_email):
    """
    If this email already moderates another session on the same date with the
    same start time, return that session_code; otherwise None.
    """
    email = (moderator_email or '').strip()
    if not email or not session_code:
        return None

    target = Session.objects.filter(
        session_event=session_event,
        session_code=session_code,
    ).first()
    if not target or not target.session_date or not target.session_start:
        return None

    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT s."SESSION_CODE"
            FROM vote."SESSION" s
            INNER JOIN vote."MODERATOR" m
                ON m."SESSION_EVENT" = s."SESSION_EVENT"
               AND m."SESSION_CODE" = s."SESSION_CODE"
            WHERE s."SESSION_EVENT" = %s
              AND s."SESSION_CODE" <> %s
              AND s."SESSION_DATE" = %s
              AND s."SESSION_START" = %s
              AND m."MODERATOR_EMAIL" IS NOT NULL
              AND btrim(m."MODERATOR_EMAIL") <> ''
              AND lower(m."MODERATOR_EMAIL") = lower(%s)
            ORDER BY s."SESSION_CODE"
            LIMIT 1
            ''',
            [
                session_event,
                session_code,
                target.session_date,
                target.session_start,
                email,
            ],
        )
        row = cursor.fetchone()

    return row[0] if row else None


def filter_sessions_for_moderator(qs, session_event, moderator_name, moderator_email):
    """
    Keep unassigned sessions and sessions assigned to the logged-in moderator.
    CPC sees all sessions; normal moderators are matched by email identity.
    """
    if is_cpc_moderator(moderator_name):
        return qs

    if not moderator_email:
        return qs.none()

    my_codes = Moderator.objects.filter(
        session_event=session_event,
        moderator_email__iexact=moderator_email.strip(),
    ).values_list('session_code', flat=True)

    return qs.filter(Q(moderator_name__isnull=True) | Q(session_code__in=my_codes))


def record_moderator_thankyou_pending(session_event, moderator_email):
    """
    Track first-time moderator signup per email per event.
    Inserts a row with THANK_YOU_SENT=false; email sending will use this later.
    """
    email = (moderator_email or '').strip()
    if not email:
        return

    if ModeratorThankyou.objects.filter(
        session_event=session_event,
        moderator_email__iexact=email,
    ).exists():
        return

    # Composite PK table without surrogate id — use INSERT … ON CONFLICT for safety.
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO vote."MODERATOR_THANKYOU"
                ("SESSION_EVENT", "MODERATOR_EMAIL", "THANK_YOU_SENT", "SENT_AT")
            VALUES (%s, %s, FALSE, NULL)
            ON CONFLICT ("SESSION_EVENT", "MODERATOR_EMAIL") DO NOTHING
            ''',
            [session_event, email],
        )


def init_response_context(request):
    user = request.user

    context = {
        'user_info': {
            'id' : str(request.user),
            'last_name': request.user.last_name if request.user.is_authenticated else None,
            'first_name': request.user.first_name if request.user.is_authenticated else None,
        },
        'user_permissions': {
            'can_request_new_data': request.user.has_perm('tagsgen.owner'),
            'can_edit': request.user.has_perm('tagsgen.editor'),
            'can_create': request.user.has_perm('tagsgen.editor'),
            'can_view': request.user.has_perm('tagsgen.visitor'),
        }
    }
    return context



def retrieve_value_from_session(request, key):
    try:
        value = request.POST[key]
    except Exception as e:
        print('missing', str(e))
        value = None

    return value


class RequestParameters(object):
    pass