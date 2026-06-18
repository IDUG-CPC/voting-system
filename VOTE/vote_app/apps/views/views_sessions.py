from django.template import loader
from django.shortcuts import redirect, render
from ..views.views_login import login
from ..score.utils import RequestParameters, retrieve_value_from_session, init_response_context
from ..score.models import Moderators, Session
from django.http import JsonResponse
from rest_framework import status

from ..tables.tables import SessionTable
from django_tables2 import RequestConfig

from django.core.paginator import Paginator
from django.template.loader import render_to_string


def refresh_sessions(request):
    if not request.user.is_authenticated:
        print('out of session')
        content = {
            'message': 'Your session has expired. Please <a href="./login.html">login</a>'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST':
        # retrieving parameters
        x = RequestParameters()  # generic class for request parameters

        for key in ['url']:
            setattr(x, key, retrieve_value_from_session(request, key))

        context = init_response_context(request)

        event = request.session_event

        # all()   ->  filter(session_event=event)

        if 'sessions' in x.url and 'page=' in x.url:
            pos = x.url.index('page=') + len('page=')
            page = x.url[pos:]
            sessions_items = Moderators.objects.filter(session_event=event).order_by('date', 'session_time', 'session_code')

            sessions = SessionTable(sessions_items)

            RequestConfig(request, paginate={"per_page": 10}).configure(sessions)

            sessions.page = sessions.page.paginator.get_page(page)

        else:
            sessions_items = Moderators.objects.filter(session_event=event).order_by('date', 'session_time', 'session_code')

            sessions = SessionTable(sessions_items)

            RequestConfig(request, paginate={"per_page": 10}).configure(sessions)

        return render(request, 'tables/table_session.html', {'items': sessions})
    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)


def check_session_code(request):
    if request.method == 'POST':
        # retrieving parameters
        x = RequestParameters()  # generic class for request parameters

        for key in ['sessioncode']:
            setattr(x, key, retrieve_value_from_session(request, key))

        context = init_response_context(request)

        event = request.session_event

        # all()   ->  filter(session_event=event)

        session = Session.objects.filter(session_event=event).filter(session_code=x.sessioncode).values()
        moderator = Moderators.objects.filter(session_event=event).filter(session_code=x.sessioncode).values()

        if session:
            context['exists'] = True
            context['title'] = session[0]['session_title']

            context['speaker'] = moderator[0]['speaker']
            context['subject'] = moderator[0]['subject_desc']

            context['attendees'] = session[0]['start_count']
            context['attendees20'] = session[0]['mid_count']
            context['comments'] = session[0]['comments']
        else:
            context['exists'] = False

        context['message'] = 'OK'

        return JsonResponse(context, status=status.HTTP_200_OK)
    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)


def update_attendees(request):
    if request.method == 'POST':
        # retrieving parameters
        x = RequestParameters()  # generic class for request parameters

        for key in ['sessioncode', 'attendees', 'attendees20']:
            setattr(x, key, retrieve_value_from_session(request, key))

        context = init_response_context(request)

        event = request.session_event

        # all()   ->  filter(session_event=event)

        session = Session.objects.get(session_event=event,session_code=x.sessioncode)

        if session:
            #session.start_count = x.attendees if x.attendees else None
            #session.mid_count = x.attendees20 if x.attendees20 else None
            #session.save()

            updated = (
                Session.objects
                .filter(session_event=event, session_code=x.sessioncode)
                .update(
                    start_count=int(x.attendees) if x.attendees else None,
                    mid_count=int(x.attendees20) if x.attendees20 else None,
                )
            )

            if updated == 1:
                context['message'] = 'OK'

                return JsonResponse(context, status=status.HTTP_200_OK)
            else:
                content = {
                    'message': 'An error occured'
                }
                return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)

        else:
            content = {
                'message': 'An error occured'
            }
            return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)

