from rest_framework import status
from django.shortcuts import redirect, render
from django.http import JsonResponse

from ..selection.models import Moderators, Moderator, Session
from ..selection.utils import init_response_context


def get_modal_edit_value(request):
    if request.method == 'POST':
        session_id = request.POST.get('session_id')

        mod = Moderators.objects.all().filter(session_code=session_id)

        if len(mod) == 1:

            context = init_response_context(request)

            context['session_id'] = session_id

            context['session_date'] = mod[0].session_date
            context['session_time'] = mod[0].session_time
            context['session_title'] = mod[0].session_title
            context['speaker'] = mod[0].speaker
            context['platform'] = mod[0].subject_desc
            context['moderator_name'] = mod[0].moderator_name

            ses = Moderator.objects.all().filter(session_code=session_id)
            if len(ses) == 1:
                context['moderator_email'] = ses[0].moderator_email

            return render(request, 'modal/modal_value_edit.html', context)
        else:
            content = {
                'message': 'An error occured - No data'
            }
            return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)


def update_modal_edit_value(request):
    if request.method == 'POST':
        session_id = request.POST.get('session_id')

        mod = Moderator.objects.all().filter(session_code=session_id)

        if len(mod) == 1:
            for i in mod:
                i.moderator_name = request.POST.get('moderator_name') if request.POST.get('moderator_name') != '' else None
                i.moderator_email = request.POST.get('moderator_email') if request.POST.get('moderator_email') != '' else None
                i.save()

            if request.POST.get('moderator_name') != '' or request.POST.get('moderator_email') != '':
                ses = Session.objects.all().filter(session_code=session_id)
                if len(ses) == 1:
                    for i in ses:
                        i.moderator_status_id = 1
                        i.save()
            else:
                ses = Session.objects.all().filter(session_code=session_id)
                if len(ses) == 1:
                    for i in ses:
                        i.moderator_status_id = 0
                        i.save()

                mod.delete()

            context = init_response_context(request)
            context['message'] = 'OK'

            return JsonResponse(context, status=status.HTTP_200_OK)
        else:
            if request.POST.get('moderator_name') != '' or request.POST.get('moderator_email') != '':
                mod = Moderator.objects.create(
                    session_event="EMEA2025",
                    session_code=session_id,
                    moderator_name = request.POST.get('moderator_name') if request.POST.get('moderator_name') != '' else None,
                    moderator_email = request.POST.get('moderator_email') if request.POST.get('moderator_email') != '' else None
                )


                ses = Session.objects.all().filter(session_code=session_id)
                if len(ses) == 1:
                    for i in ses:
                        i.moderator_status_id = 1
                        i.save()



            context = init_response_context(request)
            context['message'] = 'OK'

            return JsonResponse(context, status=status.HTTP_200_OK)
    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)

