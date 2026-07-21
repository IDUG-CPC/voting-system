from rest_framework import status
from django.shortcuts import redirect, render
from django.http import JsonResponse

from ..selection.models import Moderators, Moderator, Session, CurrentEvent
from ..selection.utils import (
    init_response_context,
    get_moderator_identity,
    is_moderator_identified,
    record_moderator_thankyou_pending,
    parse_moderator_fields,
    validate_moderator_fields,
)


def get_modal_edit_value(request):
    if request.method == 'POST':
        if not is_moderator_identified(request):
            return JsonResponse({'message': 'Please sign in with your name and email first.'}, status=403)

        session_id = request.POST.get('session_id')
        is_mobile = request.headers.get('X-Mobile-View') == 'true'

        current_event = CurrentEvent.objects.filter(is_active=True).first()
        if not current_event:
            return JsonResponse({'message': 'An error occurred - No data'}, status=400)

        session_event = current_event.session_event

        mod = Moderators.objects.filter(session_event=session_event, session_code=session_id)

        if len(mod) == 1:
            context = init_response_context(request)

            ses = Moderator.objects.filter(session_event=session_event, session_code=session_id).first()
            login_name, login_email = get_moderator_identity(request)

            is_assigned = bool(mod[0].moderator_name)

            if is_assigned:
                moderator_name = mod[0].moderator_name
                moderator_email = ses.moderator_email if ses else ''
            else:
                moderator_name = login_name or ''
                moderator_email = login_email or ''

            context.update({
                'session_id': session_id,
                'session_date': mod[0].session_date,
                'session_time': mod[0].session_time,
                'session_title': mod[0].session_title,
                'speaker': mod[0].speaker,
                'platform': mod[0].subject_desc,
                'moderator_name': moderator_name,
                'moderator_email': moderator_email,
                'is_assigned': is_assigned,
            })

            # Choose template
            template_name = (
                'modal/modal_value_edit_mobile.html'
                if is_mobile
                else 'modal/modal_value_edit.html'
            )

            return render(request, template_name, context)

        return JsonResponse({'message': 'An error occurred - No data'}, status=400)

    return JsonResponse({'message': 'An error occurred'}, status=400)


def update_modal_edit_value(request):
    if request.method == 'POST':
        if not is_moderator_identified(request):
            return JsonResponse({'message': 'Please sign in with your name and email first.'}, status=403)

        session_id = request.POST.get('session_id')

        current_event = CurrentEvent.objects.filter(is_active=True).first()
        if not current_event:
            return JsonResponse({'message': 'An error occurred - No data'}, status=400)

        session_event = current_event.session_event

        moderator_name, moderator_email = parse_moderator_fields(
            request.POST.get('moderator_name'),
            request.POST.get('moderator_email'),
        )

        is_valid, error_message = validate_moderator_fields(moderator_name, moderator_email)
        if not is_valid:
            return JsonResponse({'message': error_message}, status=400)

        mod = Moderator.objects.filter(session_event=session_event, session_code=session_id).first()

        if not moderator_name and not moderator_email:
            if mod:
                Moderator.objects.filter(
                    session_event=session_event,
                    session_code=session_id,
                ).update(moderator_name=None, moderator_email=None)

            Session.objects.filter(
                session_event=session_event,
                session_code=session_id,
            ).update(moderator_status_id=0)

        else:
            if mod:
                Moderator.objects.filter(
                    session_event=session_event,
                    session_code=session_id,
                ).update(
                    moderator_name=moderator_name,
                    moderator_email=moderator_email,
                )
            else:
                Moderator.objects.create(
                    session_event=session_event,
                    session_code=session_id,
                    moderator_name=moderator_name,
                    moderator_email=moderator_email,
                )
                if moderator_email:
                    record_moderator_thankyou_pending(session_event, moderator_email)

            Session.objects.filter(
                session_event=session_event,
                session_code=session_id,
            ).update(moderator_status_id=1)

        context = init_response_context(request)
        context['message'] = 'OK'

        return JsonResponse(context, status=status.HTTP_200_OK)

    else:
        content = {
            'message': 'An error occured'
        }
        return JsonResponse(content, status=status.HTTP_400_BAD_REQUEST)
