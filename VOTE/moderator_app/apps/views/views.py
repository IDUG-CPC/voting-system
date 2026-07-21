import json

from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
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
from ..selection.models import Moderators, CurrentEvent
from ..tables.tables import ModeratorsTable
from django_tables2 import RequestConfig


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

    if not is_mobile:
        paginate = {"per_page": 10}
        RequestConfig(request, paginate=paginate).configure(sessions)
    else:
        RequestConfig(request, paginate={"per_page": 9999}).configure(sessions)

    return sessions


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
    if not email and not is_cpc_moderator(name):
        return JsonResponse({'ok': False, 'message': 'Moderator email is required. It will be used to remind you of your sessions.'})
    if email and not is_valid_email(email):
        return JsonResponse({'ok': False, 'message': 'Please enter a valid email address.'})

    request.session['moderator_login_name'] = name
    request.session['moderator_login_email'] = email
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
        sessions = ModeratorsTable(sessions_items)

        if not is_mobile:
            request.GET = request.GET.copy()
            request.GET['page'] = page
            RequestConfig(request, paginate={"per_page": 10}).configure(sessions)
        else:
            RequestConfig(request, paginate={"per_page": 9999}).configure(sessions)

        return render(request, 'tables/table_moderator.html', {'items': sessions})

    return JsonResponse({'message': 'An error occurred'}, status=status.HTTP_400_BAD_REQUEST)
