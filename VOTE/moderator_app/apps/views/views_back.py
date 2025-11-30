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
from ..selection.models import Moderators
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
    search = request.GET.get('search')
    if not search:
        search = request.session.get('currentSearch', '')

    # Save current search to session
    request.session['currentSearch'] = search

    # Filter queryset
    if search:
        sessions_items = Moderators.objects.filter(search__icontains=search).order_by('date', 'session_time', 'session_code')
    else:
        sessions_items = Moderators.objects.all().order_by('date', 'session_time', 'session_code')

    # Build table
    sessions = ModeratorsTable(sessions_items)
    RequestConfig(request, paginate={"per_page": 10}).configure(sessions)

    context = {
        'segment': 'moderator',
        'currentSearch': search,
        'items': sessions,  # Initial render of the table
    }

    template = loader.get_template('home/moderator.html')

    return HttpResponse(template.render(context, request))

    #return render(request, 'home/moderator.html', context)


def refresh_moderators(request):
    """
    Handles AJAX requests for table refresh (search / pagination).
    """
    if request.method == 'POST':
        x = RequestParameters()
        for key in ['url', 'search']:
            setattr(x, key, retrieve_value_from_session(request, key))

        request.session['currentSearch'] = x.search  # persist search

        # Determine pagination
        if 'page=' in x.url:
            pos = x.url.index('page=') + len('page=')
            page = x.url[pos:]
        else:
            page = 1

        # Filter queryset
        if x.search:
            sessions_items = Moderators.objects.filter(search__icontains=x.search).order_by('date', 'session_time', 'session_code')
        else:
            sessions_items = Moderators.objects.all().order_by('date', 'session_time', 'session_code')

        sessions = ModeratorsTable(sessions_items)
        RequestConfig(request, paginate={"per_page": 10}).configure(sessions)
        sessions.page = sessions.page.paginator.get_page(page)

        return render(request, 'tables/table_moderator.html', {'items': sessions})

    return JsonResponse({'message': 'An error occurred'}, status=status.HTTP_400_BAD_REQUEST)


