import json

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from ..selection.utils import (
    RequestParameters,
    retrieve_value_from_session,
    get_moderator_identity,
    is_moderator_identified,
    is_cpc_moderator,
    is_valid_email,
    filter_sessions_for_moderator,
)
from ..selection.models import (
    Moderators,
    CurrentEvent,
    Moderator,
    ModeratorEmailVerification,
)
from ..tables.tables import ModeratorsTable
from django_tables2 import RequestConfig
from ..selection.email_service import (
    create_initial_verification,
    resend_moderator_verification,
)


def _sessions_queryset(request, session_event, search):
    sessions_items = Moderators.objects.filter(session_event=session_event)

    if search:
        sessions_items = sessions_items.filter(search__icontains=search)
    sessions_items = sessions_items.order_by('date', 'session_time', 'session_code')

    login_name, login_email = get_moderator_identity(request)
    if is_moderator_identified(request):
        sessions_items = filter_sessions_for_moderator(
            sessions_items, session_event, login_name, login_email
        )
    else:
        sessions_items = sessions_items.none()

    return sessions_items


def _build_sessions_table(request, sessions_items, is_mobile=None):
    if is_mobile is None:
        is_mobile = request.headers.get('X-Mobile-View') == 'true'

    sessions = ModeratorsTable(sessions_items)
    login_name, _ = get_moderator_identity(request)
    if not is_cpc_moderator(login_name):
        sessions.columns.hide('email_verification')

    if not is_mobile:
        paginate = {"per_page": 10}
        RequestConfig(request, paginate=paginate).configure(sessions)
    else:
        RequestConfig(request, paginate={"per_page": 9999}).configure(sessions)

    _attach_email_verification_status(request, sessions)
    return sessions


def _attach_email_verification_status(request, sessions):
    """Attach display-only verification data to rows on the current page."""
    page = getattr(sessions, 'page', None)
    bound_rows = list(page.object_list) if page else []
    records = [bound_row.record for bound_row in bound_rows]
    if not records:
        return

    session_event = records[0].session_event
    assignments = Moderator.objects.filter(
        session_event=session_event,
        session_code__in=[record.session_code for record in records],
    ).values('session_code', 'moderator_email')
    email_by_code = {
        row['session_code']: (row['moderator_email'] or '').strip()
        for row in assignments
    }
    emails = [email for email in email_by_code.values() if email]
    if not emails:
        for record in records:
            record.email_verification = ''
            record.can_resend_verification = False
        return

    # The existing moderator records use case-insensitive email matching, so
    # build this map case-insensitively too.
    verifications = ModeratorEmailVerification.objects.filter(
        session_event=session_event,
    ).values('moderator_email', 'email_verified')
    verified_by_email = {
        (row['moderator_email'] or '').casefold(): row['email_verified']
        for row in verifications
    }
    _, login_email = get_moderator_identity(request)
    login_email = (login_email or '').casefold()

    for record in records:
        email = email_by_code.get(record.session_code, '')
        if not email:
            record.email_verification = ''
            record.can_resend_verification = False
            continue
        record.email_verification = (
            'verified' if verified_by_email.get(email.casefold(), False) else 'pending'
        )
        record.can_resend_verification = (
            record.email_verification == 'pending'
            and bool(login_email)
            and email.casefold() == login_email
        )


def _verification_url_builder(request):
    base_url = getattr(settings, 'EMAIL_VERIFICATION_BASE_URL', '').strip().rstrip('/')

    def build(token):
        path = reverse('verify_moderator_email', args=[token])
        return '%s%s' % (base_url, path) if base_url else request.build_absolute_uri(path)

    return build


def moderator(request):
    """
    Handles full page load for the moderator page.
    Includes search box and initial table render.
    """
    current_event = CurrentEvent.objects.filter(is_active=True).first()
    event_available = bool(current_event)

    search = request.GET.get('search')
    if not search:
        search = request.session.get('currentSearch', '')

    request.session['currentSearch'] = search

    sessions = None
    identified = is_moderator_identified(request)
    login_name, login_email = get_moderator_identity(request)
    email_confirmation_pending = False
    if event_available and identified and not is_cpc_moderator(login_name) and login_email:
        verification = ModeratorEmailVerification.objects.filter(
            session_event=current_event.session_event,
            moderator_email__iexact=login_email,
        ).first()
        email_confirmation_pending = not bool(verification and verification.email_verified)

    if event_available and identified:
        sessions_items = _sessions_queryset(request, current_event.session_event, search)
        sessions = _build_sessions_table(request, sessions_items)

    context = {
        'segment': 'moderator',
        'current_event': current_event,
        'moderator_available': event_available,
        'currentSearch': search,
        'is_identified': identified,
        'moderator_login_name': login_name,
        'moderator_login_email': login_email,
        'email_confirmation_pending': email_confirmation_pending,
        'show_email_verification_column': is_cpc_moderator(login_name),
        'email_verified_notice': request.GET.get('email_verified') == '1',
        'items': sessions if current_event and identified else None,
    }

    template = loader.get_template('home/moderator.html')
    return HttpResponse(template.render(context, request))


@require_http_methods(["POST"])
def moderator_login(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        name = (data.get('moderator_name') or '').strip()
        email = (data.get('moderator_email') or '').strip()
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'message': 'Invalid request.'}, status=400)

    if not name:
        return JsonResponse({'ok': False, 'message': 'Moderator name is required.'})
    # CPC is the internal special moderator and must never use an email address.
    if is_cpc_moderator(name):
        email = ''
    if not email and not is_cpc_moderator(name):
        return JsonResponse({'ok': False, 'message': 'Moderator email is required. It will be used to remind you of your sessions.'})
    if email and not is_valid_email(email):
        return JsonResponse({'ok': False, 'message': 'Please enter a valid email address.'})

    request.session['moderator_login_name'] = name
    request.session['moderator_login_email'] = email

    current_event = CurrentEvent.objects.filter(is_active=True).first()
    if current_event and email:
        create_initial_verification(
            current_event.session_event,
            name,
            email,
            current_event,
            _verification_url_builder(request),
        )
    return JsonResponse({'ok': True})


@require_http_methods(["POST"])
def moderator_logout(request):
    request.session.pop('moderator_login_name', None)
    request.session.pop('moderator_login_email', None)
    return JsonResponse({'ok': True})


def refresh_moderators(request):
    """
    Handles AJAX requests for table refresh (search / pagination).
    """
    if request.method == 'POST':
        current_event = CurrentEvent.objects.filter(is_active=True).first()
        if not current_event:
            return render(request, 'tables/moderator_unavailable.html')

        if not is_moderator_identified(request):
            return render(request, 'tables/table_moderator.html', {'items': ModeratorsTable([])})

        x = RequestParameters()
        for key in ['url', 'search']:
            setattr(x, key, retrieve_value_from_session(request, key))

        request.session['currentSearch'] = x.search or ''

        is_mobile = request.headers.get('X-Mobile-View') == 'true'

        if not is_mobile and x.url and 'page=' in x.url:
            pos = x.url.index('page=') + len('page=')
            page = x.url[pos:]
        else:
            page = 1

        sessions_items = _sessions_queryset(request, current_event.session_event, x.search or '')
        request.GET = request.GET.copy()
        request.GET['page'] = page
        sessions = _build_sessions_table(request, sessions_items, is_mobile=is_mobile)

        login_name, _ = get_moderator_identity(request)
        return render(
            request,
            'tables/table_moderator.html',
            {
                'items': sessions,
                'show_email_verification_column': is_cpc_moderator(login_name),
            },
        )

    return JsonResponse({'message': 'An error occurred'}, status=status.HTTP_400_BAD_REQUEST)


def verify_moderator_email(request, token):
    verification = ModeratorEmailVerification.objects.filter(
        verification_token=token,
    ).first()
    now = timezone.now()
    if not verification:
        return render(request, 'home/email_verification.html', {'status': 'invalid'})
    if verification.email_verified:
        return redirect('%s?email_verified=1' % reverse('moderator'))
    expires_at = verification.token_expires_at
    if expires_at and timezone.is_naive(expires_at):
        # The existing table deliberately uses TIMESTAMP WITHOUT TIME ZONE.
        # Django returns it as naive, while timezone.now() is aware.
        expires_at = timezone.make_aware(expires_at, timezone.utc)
    if not expires_at or expires_at < now:
        return render(request, 'home/email_verification.html', {'status': 'expired'})

    verification.email_verified = True
    verification.verified_at = now
    verification.save(
        update_fields=('email_verified', 'verified_at')
    )
    return redirect('%s?email_verified=1' % reverse('moderator'))


@require_http_methods(["POST"])
def resend_verification(request):
    name, email = get_moderator_identity(request)
    if not is_moderator_identified(request) or is_cpc_moderator(name) or not email:
        return JsonResponse({'message': 'Please sign in with your email address first.'}, status=403)

    current_event = CurrentEvent.objects.filter(is_active=True).first()
    if not current_event:
        return JsonResponse({'message': 'Moderator sign-up is currently unavailable.'}, status=400)

    sent, message = resend_moderator_verification(
        current_event.session_event,
        name,
        email,
        current_event,
        _verification_url_builder(request),
    )
    return JsonResponse({'ok': sent, 'message': message}, status=200 if sent else 400)
