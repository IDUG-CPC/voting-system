import logging
import os
import secrets
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.image import MIMEImage
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import connection, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape

from .models import (
    CurrentEvent,
    EmailTemplate,
    ModeratorEmailVerification,
    ModeratorThankyou,
)
from .utils import record_moderator_thankyou_pending

logger = logging.getLogger(__name__)

THANKYOU_TEMPLATE_CODE = 'thankyou'
REMINDER_TEMPLATE_CODE = 'reminder'
VERIFICATION_TEMPLATE_CODE = 'verification'
LOGO_CONTENT_ID = 'idug-logo'


def _apply_placeholders(text, context):
    if text is None:
        return ''
    result = text
    for key, value in context.items():
        result = result.replace('{%s}' % key, str(value if value is not None else ''))
    return result


def _build_plain_text(body_text, event_city, event_date):
    header_parts = []
    if event_city:
        header_parts.append(str(event_city))
    if event_date:
        header_parts.append(str(event_date))
    header = '\n'.join(header_parts)
    if header:
        return '%s\n\n%s' % (header, body_text)
    return body_text


def _attach_logo(message):
    logo_path = getattr(settings, 'EMAIL_LOGO_PATH', '') or ''
    if not logo_path or not os.path.isfile(logo_path):
        logger.warning('Email logo not found at %s', logo_path)
        return False

    with open(logo_path, 'rb') as logo_file:
        logo = MIMEImage(logo_file.read())
    logo.add_header('Content-ID', '<%s>' % LOGO_CONTENT_ID)
    logo.add_header('Content-Disposition', 'inline', filename=os.path.basename(logo_path))
    message.attach(logo)
    return True


def _attach_file(message, attachment_name):
    if not attachment_name:
        return
    attachment_dir = getattr(settings, 'EMAIL_ATTACHMENT_DIR', '') or ''
    path = os.path.join(attachment_dir, attachment_name)
    if not os.path.isfile(path):
        logger.warning('Email attachment not found at %s', path)
        return
    message.attach_file(path)


def send_template_email(template_code, to_email, placeholders, event_city=None, event_date=None):
    """
    Send a multipart email (plain + HTML with CID logo) using EMAIL_TEMPLATE.
    Returns True on success, False otherwise.
    """
    if not getattr(settings, 'EMAIL_ENABLED', False):
        logger.info('EMAIL_ENABLED is False — skip sending %s to %s', template_code, to_email)
        return False

    to_email = (to_email or '').strip()
    if not to_email:
        return False

    template = EmailTemplate.objects.filter(template_code=template_code).first()
    if not template:
        logger.error('EMAIL_TEMPLATE row not found for code=%s', template_code)
        return False

    subject = _apply_placeholders(template.subject, placeholders)
    body_text = _apply_placeholders(template.body_text, placeholders)
    body_html = _apply_placeholders(template.body_html, placeholders)

    plain = _build_plain_text(body_text, event_city, event_date)
    html = render_to_string(
        'email/layout.html',
        {
            'subject': subject,
            'event_city': event_city or '',
            'event_date': event_date or '',
            'body_html': body_html,
        },
    )

    message = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html, 'text/html')
    message.mixed_subtype = 'related'
    _attach_logo(message)
    _attach_file(message, template.attachment_name)

    message.send(fail_silently=False)
    return True


def mark_thankyou_sent(session_event, moderator_email):
    email = (moderator_email or '').strip()
    if not email:
        return
    ModeratorThankyou.objects.filter(
        session_event=session_event,
        moderator_email__iexact=email,
        thank_you_sent=False,
    ).update(thank_you_sent=True, sent_at=timezone.now())


def maybe_send_moderator_thankyou(session_event, moderator_name, moderator_email, current_event):
    """
    Ensure a MODERATOR_THANKYOU row exists; send thank-you once per email per event.
    SMTP runs in a background thread so signup is not blocked.
    Signup succeeds even if SMTP fails (row stays pending for a later retry).
    """
    email = (moderator_email or '').strip()
    if not email:
        return

    record_moderator_thankyou_pending(session_event, email)

    pending = ModeratorThankyou.objects.filter(
        session_event=session_event,
        moderator_email__iexact=email,
    ).first()
    if not pending or pending.thank_you_sent:
        return

    placeholders = {
        'moderator_name': (moderator_name or '').strip(),
        'event_city': getattr(current_event, 'event_city', '') or '',
        'event_date': getattr(current_event, 'event_date', '') or '',
    }
    event_city = placeholders['event_city']
    event_date = placeholders['event_date']

    def _send_in_background():
        try:
            sent = send_template_email(
                THANKYOU_TEMPLATE_CODE,
                email,
                placeholders,
                event_city=event_city,
                event_date=event_date,
            )
            if sent:
                mark_thankyou_sent(session_event, email)
        except Exception:
            logger.exception(
                'Failed to send thank-you email to %s for event %s',
                email,
                session_event,
            )
        finally:
            connection.close()

    transaction.on_commit(
        lambda: threading.Thread(target=_send_in_background, daemon=True).start()
    )


def _new_verification_token():
    return secrets.token_urlsafe(48)


def _send_verification_in_background(email, placeholders, event_city, event_date):
    try:
        send_template_email(
            VERIFICATION_TEMPLATE_CODE,
            email,
            placeholders,
            event_city=event_city,
            event_date=event_date,
        )
    except Exception:
        logger.exception('Failed to send verification email to %s', email)
    finally:
        connection.close()


def send_moderator_verification(
    moderator_name, moderator_email, current_event, verification_url
):
    """Queue the separate verification email after its token has been saved."""
    email = (moderator_email or '').strip()
    if not email:
        return

    placeholders = {
        'moderator_name': (moderator_name or '').strip(),
        'verification_url': verification_url,
        'event_city': getattr(current_event, 'event_city', '') or '',
        'event_date': getattr(current_event, 'event_date', '') or '',
    }
    transaction.on_commit(
        lambda: threading.Thread(
            target=_send_verification_in_background,
            args=(
                email,
                placeholders,
                placeholders['event_city'],
                placeholders['event_date'],
            ),
            daemon=True,
        ).start()
    )


def create_initial_verification(
    session_event,
    moderator_name,
    moderator_email,
    current_event,
    verification_url_builder,
):
    """Create and send one verification email for a new event/email combination."""
    email = (moderator_email or '').strip()
    if not email:
        return False

    verification = ModeratorEmailVerification.objects.filter(
        session_event=session_event,
        moderator_email__iexact=email,
    ).first()
    if verification:
        return False

    token = _new_verification_token()
    now = timezone.now()
    verification = ModeratorEmailVerification.objects.create(
        session_event=session_event,
        moderator_email=email,
        email_verified=False,
        verification_token=token,
        token_expires_at=now + timedelta(
            days=getattr(settings, 'EMAIL_VERIFICATION_TOKEN_DAYS', 7)
        ),
        verification_sent=True,
        sent_at=now,
    )
    send_moderator_verification(
        moderator_name,
        email,
        current_event,
        verification_url_builder(verification.verification_token),
    )
    return True


def resend_moderator_verification(
    session_event,
    moderator_name,
    moderator_email,
    current_event,
    verification_url_builder,
):
    """Replace a pending token and queue another verification email."""
    email = (moderator_email or '').strip()
    verification = ModeratorEmailVerification.objects.filter(
        session_event=session_event,
        moderator_email__iexact=email,
    ).first()
    if not verification or verification.email_verified:
        return False, 'Your email address is already confirmed.'

    now = timezone.now()
    cooldown = getattr(settings, 'EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS', 60)
    sent_at = verification.sent_at
    if sent_at and timezone.is_naive(sent_at):
        sent_at = timezone.make_aware(sent_at, timezone.utc)
    if sent_at and (now - sent_at).total_seconds() < cooldown:
        return False, 'Please wait a minute before requesting another verification email.'

    token = _new_verification_token()
    verification.verification_token = token
    verification.token_expires_at = now + timedelta(
        days=getattr(settings, 'EMAIL_VERIFICATION_TOKEN_DAYS', 7)
    )
    verification.verification_sent = True
    verification.sent_at = now
    verification.save(
        update_fields=(
            'verification_token',
            'token_expires_at',
            'verification_sent',
            'sent_at',
        )
    )
    send_moderator_verification(
        moderator_name, email, current_event, verification_url_builder(token)
    )
    return True, 'A verification email has been sent.'


def _format_session_parts(session_start, session_title, session_code):
    return {
        'code': (session_code or '').strip(),
        'time': session_start.strftime('%H:%M') if session_start else '',
        'title': (session_title or '').strip(),
    }


def _format_session_line(parts):
    return '%s %s - %s' % (parts['code'], parts['time'], parts['title'])


def _format_sessions_html(sessions):
    if not sessions:
        return ''
    rows = []
    for parts in sessions:
        rows.append(
            '<tr>'
            '<td valign="top" style="white-space:nowrap;padding:2px 8px 2px 0;border:none;">'
            '<strong>%s</strong></td>'
            '<td valign="top" style="white-space:nowrap;padding:2px 8px 2px 0;border:none;"><strong>%s</strong></td>'
            '<td valign="top" style="padding:2px 0;border:none;">%s</td>'
            '</tr>'
            % (escape(parts['code']), escape(parts['time']), escape(parts['title']))
        )
    return (
        '<div style="margin-left:24px;">'
        '<table border="0" cellpadding="0" cellspacing="0" width="100%%" '
        'style="border-collapse:collapse;border:none;">'
        '%s'
        '</table>'
        '</div>'
    ) % '\n'.join(rows)


def _format_sessions_text(sessions):
    return '\n'.join(_format_session_line(parts) for parts in sessions)


def _reminder_already_sent(session_event, moderator_email, session_date):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT 1
            FROM vote."MODERATOR_REMINDER"
            WHERE "SESSION_EVENT" = %s
              AND lower("MODERATOR_EMAIL") = lower(%s)
              AND "SESSION_DATE" = %s
              AND "REMINDER_SENT" = TRUE
            LIMIT 1
            ''',
            [session_event, moderator_email, session_date],
        )
        return cursor.fetchone() is not None


def _mark_reminder_sent(session_event, moderator_email, session_date):
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            INSERT INTO vote."MODERATOR_REMINDER"
                ("SESSION_EVENT", "MODERATOR_EMAIL", "SESSION_DATE", "REMINDER_SENT", "SENT_AT")
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT ("SESSION_EVENT", "MODERATOR_EMAIL", "SESSION_DATE")
            DO UPDATE SET
                "REMINDER_SENT" = TRUE,
                "SENT_AT" = EXCLUDED."SENT_AT"
            ''',
            [session_event, moderator_email, session_date, timezone.now()],
        )


def _load_moderators_for_session_date(session_event, session_date):
    """Return dict email -> {name, lines} for assigned moderators on that date."""
    with connection.cursor() as cursor:
        cursor.execute(
            '''
            SELECT
                m."MODERATOR_EMAIL",
                m."MODERATOR_NAME",
                s."SESSION_DATE",
                s."SESSION_START",
                s."SESSION_TITLE",
                s."SESSION_CODE"
            FROM vote."MODERATOR" m
            INNER JOIN vote."SESSION" s
                ON m."SESSION_EVENT" = s."SESSION_EVENT"
               AND m."SESSION_CODE" = s."SESSION_CODE"
            WHERE m."SESSION_EVENT" = %s
              AND s."SESSION_DATE" = %s
              AND m."MODERATOR_EMAIL" IS NOT NULL
              AND btrim(m."MODERATOR_EMAIL") <> ''
            ORDER BY m."MODERATOR_EMAIL", s."SESSION_START", s."SESSION_CODE"
            ''',
            [session_event, session_date],
        )
        rows = cursor.fetchall()

    grouped = defaultdict(lambda: {'name': '', 'sessions': []})
    for email, name, s_date, s_start, s_title, s_code in rows:
        email_key = (email or '').strip()
        if not email_key:
            continue
        entry = grouped[email_key]
        if not entry['name'] and name:
            entry['name'] = name.strip()
        entry['sessions'].append(_format_session_parts(s_start, s_title, s_code))
    return grouped


def _send_reminder_email(to_email, html_placeholders, text_placeholders, event_city=None, event_date=None):
    """Like send_template_email but with separate placeholder maps for HTML vs text."""
    if not getattr(settings, 'EMAIL_ENABLED', False):
        return False

    to_email = (to_email or '').strip()
    if not to_email:
        return False

    template = EmailTemplate.objects.filter(template_code=REMINDER_TEMPLATE_CODE).first()
    if not template:
        logger.error('EMAIL_TEMPLATE row not found for code=%s', REMINDER_TEMPLATE_CODE)
        return False

    subject = _apply_placeholders(template.subject, text_placeholders)
    body_text = _apply_placeholders(template.body_text, text_placeholders)
    body_html = _apply_placeholders(template.body_html, html_placeholders)

    plain = _build_plain_text(body_text, event_city, event_date)
    html = render_to_string(
        'email/layout.html',
        {
            'subject': subject,
            'event_city': event_city or '',
            'event_date': event_date or '',
            'body_html': body_html,
        },
    )

    message = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    message.attach_alternative(html, 'text/html')
    message.mixed_subtype = 'related'
    _attach_logo(message)
    _attach_file(message, template.attachment_name)
    message.send(fail_silently=False)
    return True


def _event_local_now(current_event):
    """Current time in the active event timezone (EVENT_TIMEZONE)."""
    tz_name = (getattr(current_event, 'event_timezone', None) or '').strip() or 'Europe/Brussels'
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning('Invalid EVENT_TIMEZONE %r — falling back to Europe/Brussels', tz_name)
        try:
            tz = ZoneInfo('Europe/Brussels')
        except ZoneInfoNotFoundError:
            return timezone.localtime()
    return datetime.now(tz)


def _event_local_today(current_event):
    """Calendar 'today' in the active event timezone (EVENT_TIMEZONE)."""
    return _event_local_now(current_event).date()


def send_moderator_reminders(days_ahead=None, force=False):
    """
    Send N-days-ahead reminder emails for the active event at its local send hour.
    ``force`` bypasses the local-time check for manual testing.
    Returns a summary dict: {target_date, sent, skipped, errors, message}.
    """
    summary = {
        'target_date': None,
        'sent': 0,
        'skipped': 0,
        'errors': 0,
        'message': '',
    }

    if not getattr(settings, 'EMAIL_ENABLED', False):
        summary['message'] = 'EMAIL_ENABLED is False — nothing sent.'
        logger.info(summary['message'])
        return summary

    current_event = CurrentEvent.objects.filter(is_active=True).first()
    if not current_event:
        summary['message'] = 'No active CURRENT_EVENT — nothing sent.'
        logger.info(summary['message'])
        return summary

    event_now = _event_local_now(current_event)
    reminder_send_hour = int(getattr(settings, 'REMINDER_SEND_HOUR', 22))
    if not 0 <= reminder_send_hour <= 23:
        raise ValueError('REMINDER_SEND_HOUR must be between 0 and 23.')
    if not force and event_now.hour != reminder_send_hour:
        summary['message'] = (
            'Current event time is %s; reminders are scheduled for %02d:00 — nothing sent.'
            % (event_now.strftime('%Y-%m-%d %H:%M %Z'), reminder_send_hour)
        )
        logger.info(summary['message'])
        return summary

    if days_ahead is None:
        days_ahead = getattr(settings, 'REMINDER_DAYS_AHEAD', 1)
    days_ahead = int(days_ahead)

    today = event_now.date()
    target_date = today + timedelta(days=days_ahead)
    summary['target_date'] = target_date

    grouped = _load_moderators_for_session_date(current_event.session_event, target_date)
    if not grouped:
        summary['message'] = 'No moderated sessions found for %s.' % target_date
        logger.info(summary['message'])
        return summary

    for email, data in grouped.items():
        if _reminder_already_sent(current_event.session_event, email, target_date):
            summary['skipped'] += 1
            continue

        sessions = data['sessions']
        session_date_str = target_date.isoformat()
        text_placeholders = {
            'moderator_name': data['name'] or email,
            'event_city': current_event.event_city or '',
            'event_date': current_event.event_date or '',
            'session_date': session_date_str,
            'session_date_display': '%s %s' % (
                target_date.strftime('%B'), target_date.day
            ),
            'sessions': _format_sessions_text(sessions),
        }
        html_placeholders = dict(text_placeholders)
        html_placeholders['sessions'] = _format_sessions_html(sessions)

        try:
            sent = _send_reminder_email(
                email,
                html_placeholders,
                text_placeholders,
                event_city=current_event.event_city or '',
                event_date=current_event.event_date or '',
            )
            if sent:
                _mark_reminder_sent(current_event.session_event, email, target_date)
                summary['sent'] += 1
            else:
                summary['skipped'] += 1
        except Exception:
            summary['errors'] += 1
            logger.exception(
                'Failed to send reminder to %s for %s / %s',
                email,
                current_event.session_event,
                target_date,
            )

    summary['message'] = (
        'Reminders for %s: sent=%s skipped=%s errors=%s'
        % (target_date, summary['sent'], summary['skipped'], summary['errors'])
    )
    logger.info(summary['message'])
    return summary
