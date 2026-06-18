from rest_framework import status
from django.shortcuts import redirect, render
from django.http import JsonResponse

from ..score.models import Score
from ..score.utils import init_response_context

from django.utils import timezone

def get_modal_edit_value(request):
    if request.method == 'POST':
        sessioneval_id = request.POST.get('sessioneval_id')

        event = request.session_event

        # all()   ->  filter(session_event=event)

        evals = Score.objects.filter(session_event=event).filter(score_id=sessioneval_id)

        if len(evals) == 1:

            context = init_response_context(request)

            context['sessioneval_id'] = sessioneval_id

            context['overall'] = evals[0].overall_score
            context['speaker'] = evals[0].speaker_score
            context['material'] = evals[0].material_score
            context['expectation'] = evals[0].level_score
            context['comments'] = evals[0].notes

            return render(request, 'modal/modal_value_edit.html', context)
        else:
            content = {
                'message': 'An error occured - No data'
            }
            return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        content = {
            'message': 'An error occured - Not logged in'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)


def update_modal_edit_value(request):
    if request.method == 'POST':
        sessioneval_id = request.POST.get('sessioneval_id')

        event = request.session_event

        # all()   ->  filter(session_event=event)

        evals = Score.objects.filter(session_event=event).filter(score_id=sessioneval_id)

        if len(evals) == 1:

            for i in evals:
                i.overall_score = request.POST.get('overall') if request.POST.get('overall') != '' else None
                i.speaker_score = request.POST.get('speaker') if request.POST.get('speaker') != '' else None
                i.material_score = request.POST.get('material') if request.POST.get('material') != '' else None
                i.level_score = request.POST.get('expectation') if request.POST.get('expectation') != '' else None
                i.notes = request.POST.get('comments') if request.POST.get('comments') != '' else None
                i.last_modified_by = request.user.username
                i.last_modified_timestamp = timezone.now()
                i.save()

            context = init_response_context(request)
            context['message'] = 'OK'

            return JsonResponse(context, status=status.HTTP_200_OK)
        else:
            content = {
                'message': 'An error occured - No data'
            }
            return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        content = {
            'message': 'An error occured - Not logged in'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)


def get_modal_delete_value(request):
    if request.method == 'POST':
        sessioneval_id = request.POST.get('sessioneval_id')

        event = request.session_event

        # all()   ->  filter(session_event=event)

        evals = Score.objects.filter(session_event=event).filter(score_id=sessioneval_id)

        if len(evals) == 1:

            context = init_response_context(request)

            context['sessioneval_id'] = sessioneval_id

            context['overall'] = evals[0].overall_score
            context['speaker'] = evals[0].speaker_score
            context['material'] = evals[0].material_score
            context['expectation'] = evals[0].level_score
            context['comments'] = evals[0].notes

            return render(request, 'modal/modal_value_delete.html', context)
        else:
            content = {
                'message': 'An error occured - No data'
            }
            return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        content = {
            'message': 'An error occured - Not logged in'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)



def delete_modal_edit_value(request):
    if request.method == 'POST':
        sessioneval_id = request.POST.get('sessioneval_id')

        event = request.session_event

        # all()   ->  filter(session_event=event)

        evals = Score.objects.filter(session_event=event).filter(score_id=sessioneval_id)

        if len(evals) == 1:

            evals.delete()

            context = init_response_context(request)
            context['message'] = 'OK'

            return JsonResponse(context, status=status.HTTP_200_OK)
        else:
            content = {
                'message': 'An error occured - No data'
            }
            return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
    else:
        content = {
            'message': 'An error occured - Not logged in'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
