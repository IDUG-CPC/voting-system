from django.shortcuts import render

from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect, render

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django import template

import math

#from django.shortcuts import redirect, render
#from ..authentication.views import login_view as login

from ..selection.utils import RequestParameters, retrieve_value_from_session, init_response_context
from ..selection.models import Moderators, CurrentEvent
from django.http import JsonResponse
from rest_framework import status

from ..tables.tables import ModeratorsTable
from django_tables2 import RequestConfig

from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import Substr



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

    # Save current search to session
    request.session['currentSearch'] = search

    unassigned = request.GET.get('unassigned')
    if not unassigned:
        unassigned = request.session.get('unassigned', '0')

    unassigned = unassigned == '1'

    sessions = None  # default when unavailable

    if event_available:
        sessions_items = Moderators.objects.filter(session_event=current_event.session_event)

        # Filter queryset
        if search:
            sessions_items = sessions_items.filter(search__icontains=search).order_by('date', 'session_time', 'session_code')
        else:
            sessions_items = sessions_items.all().order_by('date', 'session_time', 'session_code')

        if unassigned:
            sessions_items = sessions_items.filter(moderator_name__isnull=True)

        # Build table
        sessions = ModeratorsTable(sessions_items)
        # Decide pagination only for table (desktop)
        paginate = {"per_page": 10}
        if request.headers.get('X-Mobile-View') == 'true':
            paginate = {}  # Show all in mobile
        RequestConfig(request, paginate=paginate).configure(sessions)



    context = {
        'segment': 'moderator',
        'current_event': current_event,
        'moderator_available': event_available,
        'currentSearch': search,
        'unassigned': unassigned,
        'items': sessions if current_event else None,
    }

    template = loader.get_template('home/moderator.html')

    return HttpResponse(template.render(context, request))

    #return render(request, 'home/moderator.html', context)


def refresh_moderators(request):
    """
    Handles AJAX requests for table refresh (search / pagination).
    """
    if request.method == 'POST':
        current_event = CurrentEvent.objects.filter(is_active=True).first()
        if not current_event:
            # Return the unavailable fragment
            return render(request, 'tables/moderator_unavailable.html')


        x = RequestParameters()
        for key in ['url', 'search', 'unassigned']:
            setattr(x, key, retrieve_value_from_session(request, key))

        request.session['currentSearch'] = x.search  # persist search

        unassigned = x.unassigned == '1'

        # Detect mobile view from header
        is_mobile = request.headers.get('X-Mobile-View') == 'true'

        # Determine pagination only if NOT mobile
        if not is_mobile and 'page=' in x.url:
            pos = x.url.index('page=') + len('page=')
            page = x.url[pos:]
        else:
            page = 1

        sessions_items = Moderators.objects.filter(session_event=current_event.session_event)

        # Filter queryset
        if x.search:
            sessions_items = sessions_items.filter(search__icontains=x.search).order_by('date', 'session_time', 'session_code')
        else:
            sessions_items = sessions_items.all().order_by('date', 'session_time', 'session_code')

        if unassigned:
            sessions_items = sessions_items.filter(moderator_name__isnull=True)


        # Build table
        sessions = ModeratorsTable(sessions_items)

        if not is_mobile:
            # Set pagination for desktop
            request.GET = request.GET.copy()
            request.GET['page'] = page
            RequestConfig(request, paginate={"per_page": 10}).configure(sessions)
        else:
            # No pagination for mobile
            RequestConfig(request, paginate={"per_page": 9999}).configure(sessions)  # Or just don’t paginate at all

        return render(request, 'tables/table_moderator.html', {'items': sessions})

    return JsonResponse({'message': 'An error occurred'}, status=status.HTTP_400_BAD_REQUEST)



