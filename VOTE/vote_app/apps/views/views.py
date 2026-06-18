from django.shortcuts import render

from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect, render
from ..views.views_login import login

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django import template

import math

#from django.shortcuts import redirect, render
#from ..authentication.views import login_view as login

from ..score.utils import RequestParameters, retrieve_value_from_session, init_response_context
from .views_add import refresh_values

from ..score.models import Score, Session, BestSession, BestUserSession, Tracks
from ..tables.tables import ScoreTable
from django_tables2 import RequestConfig

from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import Substr


def index(request):
    if request.user.is_authenticated:
        context = init_response_context(request)
        context['segment'] = 'index'

        event = request.session_event

        # all()   ->  filter(session_event=event)

        check = Score.objects.filter(session_event=event).count()
        if check > 0:

            # encoded sessions
            encode_sessions = Score.objects.filter(session_event=event).values("session_code").annotate(total=Count("session_code")).count()
            sessions_nb = Session.objects.filter(session_event=event).count()
            session_percent = round((encode_sessions/sessions_nb)*100 , 2)

            context['encode_sessions'] = encode_sessions
            context['sessions_nb'] = sessions_nb
            context['session_percent'] = session_percent

            # best User session
            if BestUserSession.objects.filter(session_event=event).count() > 0:
                best_user_session = BestUserSession.objects.filter(session_event=event)

                context['best_user_sessioncode'] = best_user_session[0].session_code
                context['best_user_speaker'] = best_user_session[0].primary_presenter
                context['best_user_rating'] = round(best_user_session[0].rating, 4)
            else:
                context['best_user_sessioncode'] = "None"
                context['best_user_speaker'] = ""
                context['best_user_rating'] = 0.0000

            # best session
            if BestSession.objects.filter(session_event=event).count() > 0:
                best_session = BestSession.objects.filter(session_event=event)

                context['best_sessioncode'] = best_session[0].session_code
                context['best_speaker'] = best_session[0].primary_presenter
                context['best_rating'] = round(best_session[0].rating, 4)
            else:
                context['best_sessioncode'] = "None"
                context['best_speaker'] = ""
                context['best_rating'] = 0.0000


            #track summary
            track_summary = Session.objects.filter(session_event=event).annotate(first=Substr('session_code', 1, 1)).values('first').annotate(cnt=Count('session_code')).order_by('first')
            nb_per_session = Score.objects.filter(session_event=event).annotate(session=Substr('session_code', 1, 3)).values('session').annotate(cnt=Count('session_code')).order_by('session')

            i = 0
            for track in track_summary:
                track_summary[i]['nb'] = 0
                track_summary[i]['percent'] = 0
                count = 0
                for nb in nb_per_session:
                    if nb['session'][:1] == track['first']:
                        count += 1
                        track_summary[i]['nb'] = count
                        track_summary[i]['percent'] = round((count/track['cnt'])*100 , 2)
                        # track detail
                        detail = Tracks.objects.filter(session_event=event).annotate(first=Substr('session_code', 1, 1)).filter(first=track['first']).values().order_by('-rating')
                        track_summary[i]['detail'] = detail

                i += 1

            context['tracks'] = track_summary


        else:
            # encoded sessions
            context['encode_sessions'] = 0
            context['sessions_nb'] = Session.objects.filter(session_event=event).count()
            context['session_percent'] = 0

            # best user session
            context['best_user_sessioncode'] = "None"
            context['best_user_speaker'] = ""
            context['best_user_rating'] = 0.0000

            # best session
            context['best_sessioncode'] = "None"
            context['best_speaker'] = ""
            context['best_rating'] = 0.0000

            track_summary = Session.objects.filter(session_event=event).annotate(first=Substr('session_code', 1, 1)).values('first').annotate(cnt=Count('session_code')).order_by('first')
            i = 0
            for track in track_summary:
                track_summary[i]['nb'] = 0
                track_summary[i]['percent'] = 0
                i += 1

            context['tracks'] = track_summary



        template = loader.get_template('home/index.html')

        context['session_event'] = request.session_event

        return HttpResponse(template.render(context, request))
    else:
        return redirect(login)


def encode_values(request):
    if request.user.is_authenticated:
        if request.GET:

            try:
                session = request.GET['session']
            except Exception as e:
                session = None

            if session != None:
                sessioncode = session
            else:
                sessioncode = request.session['session_code']

            template = loader.get_template('home/encode_values.html')
            context = {'segment': 'encode', 'session_code': sessioncode}
            context['session_event'] = request.session_event
            return HttpResponse(template.render(context, request))

        else:
            template = loader.get_template('home/encode_values.html')
            context = {'segment': 'encode'}
            context['session_event'] = request.session_event
            return HttpResponse(template.render(context, request))
    else:
        return redirect(login)


def sessions(request):
    if request.user.is_authenticated:
        template = loader.get_template('home/sessions.html')
        context = {'segment': 'sessions'}
        context['session_event'] = request.session_event
        return HttpResponse(template.render(context, request))
    else:
        return redirect(login)


def moderator(request):
    if request.user.is_authenticated:
        template = loader.get_template('home/encode_moderator.html')
        context = {'segment': 'moderator'}
        context['session_event'] = request.session_event
        return HttpResponse(template.render(context, request))
    else:
        return redirect(login)