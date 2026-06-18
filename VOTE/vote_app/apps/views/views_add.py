from django.template import loader
from django.shortcuts import redirect, render
from ..views.views_login import login
from ..score.utils import RequestParameters, retrieve_value_from_session, init_response_context
from ..score.models import Score, Session
from django.http import JsonResponse
from rest_framework import status

from ..tables.tables import ScoreTable
from django_tables2 import RequestConfig

from django.core.paginator import Paginator
from django.template.loader import render_to_string

from django.utils import timezone


def add_values(request):
    if request.user.is_authenticated:
        # retrieving parameters
        x = RequestParameters()  # generic class for request parameters

        for key in ['sessioncode', 'overall', 'speaker', 'material', 'expectation', 'comments' ]:
            setattr(x, key, retrieve_value_from_session(request, key))

        event = request.session_event

        # all()   ->  filter(session_event=event)

        # trying to insert
        sessioncode_id = Session.objects.get(session_event=event, session_code=x.sessioncode)
        new_eval = Score(session_event=sessioncode_id.session_event,
                         session_code=sessioncode_id.session_code,
                         overall_score=x.overall if x.overall else None,
                         speaker_score=x.speaker if x.speaker else None,
                         material_score=x.material if x.material else None,
                         level_score=x.expectation if x.expectation else None,
                         notes=x.comments if x.comments else None,
                         last_modified_by=request.user.username,
                         last_modified_timestamp=timezone.now()
                         )

        new_eval.save()

        context = init_response_context(request)
        context['message'] = 'OK'
        context['code'] = new_eval.overall_score

        return JsonResponse(context, status=status.HTTP_200_OK)



    else:
        return redirect(login)


def refresh_values(request):
    if not request.user.is_authenticated:
        print('out of session')
        content = {
            'message': 'Your session has expired. Please <a href="./login.html">login</a>'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)

    if request.method == 'POST':
        # retrieving parameters
        x = RequestParameters()  # generic class for request parameters

        for key in ['sessioncode', 'url']:
            setattr(x, key, retrieve_value_from_session(request, key))

        context = init_response_context(request)

        event = request.session_event

        # all()   ->  filter(session_event=event)

        if 'encode_values' in x.url and 'page=' in x.url:
            pos = x.url.index('page=') + len('page=')
            page = x.url[pos:]
            eval_items = Score.objects.filter(session_event=event).filter(session_code=x.sessioncode).order_by('-score_id')

            #paginator = Paginator(eval_items, 5)
            #items = paginator.get_page(page)

            evals = ScoreTable(eval_items)

            RequestConfig(request, paginate={"per_page": 5}).configure(evals)

            # paginator = Paginator(eval_items.page., 5)
            evals.page = evals.page.paginator.get_page(page)

        else:
            eval_items = Score.objects.filter(session_event=event).filter(session_code=x.sessioncode).order_by('-score_id')



            #eval_items.paginator.get_page(1)

            evals = ScoreTable(eval_items)

            RequestConfig(request, paginate={"per_page": 5}).configure(evals)



        context['items'] = evals

        session = Session.objects.filter(session_event=event).filter(session_code=x.sessioncode).first()
        session_title = session.session_title if session else None

        request.session['session_code'] = x.sessioncode
        request.session['session_title'] = session_title

        return render(request, 'tables/table_sessioneval.html', {'items': evals})
    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)


