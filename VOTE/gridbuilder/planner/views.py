import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from collections import defaultdict

from .models import (
    Session, CalendarSlot, CalendarLayout,
    CalendarTimeSlot, ActionLog, CalendarColumnHeader,
    PlannerDay, SessionType, SpecialSessionType, Subject,
    Topic, SessionTopic,
)
from django.db.models import Count, Q
import uuid
from django.utils import timezone

def _log_cell_to_list(layout, session):
    # e.g. "D3 (SESS-197) →"
    return f"{layout.label} ({session.session_code}) →"

def _log_session_to_cell(session, layout):
    # e.g. "SESS-197 → D3"
    return f"{session.session_code} → {layout.label}"

def _now_iso():
    return timezone.now().isoformat()


def _event_code(request):
    """Current event (EMEA/NA) from session; default EMEA for guests."""
    return request.session.get("event_code", "EMEA")


def _used_session_ids(event_code):
    """IDs of sessions already assigned anywhere for this event."""
    return list(
        CalendarSlot.objects.filter(event_code=event_code)
        .exclude(session__isnull=True)
        .values_list("session_id", flat=True)
    )

@require_http_methods(["GET"])
def api_session_type_counts(request):
    event_code = _event_code(request)
    # Use this event's session type IDs (NA has different IDs than EMEA)
    type_ids = list(
        SessionType.objects.filter(event_code=event_code).values_list("id", flat=True)
    )
    if not type_ids:
        return JsonResponse({"counts": {}})

    qs = (
        CalendarSlot.objects
        .filter(
            event_code=event_code,
            session__isnull=False,
            session__session_type_id__in=type_ids,
        )
        .values("session__session_type_id")
        .annotate(cnt=Count("id"))
    )
    # Use string keys so JSON and JS lookups match (dataset.typeId is string)
    counts = {str(row["session__session_type_id"]): row["cnt"] for row in qs}
    # Ensure every type has a key (0 if none assigned)
    for tid in type_ids:
        counts.setdefault(str(tid), 0)

    # IBM: split by subject into IBM-z/OS and IBM-LUW (same logic for EMEA and NA)
    ibm_type = SessionType.objects.filter(
        event_code=event_code, name__iexact="IBM"
    ).first()
    if ibm_type:
        base_ibm = CalendarSlot.objects.filter(
            event_code=event_code,
            session__isnull=False,
            session__session_type_id=ibm_type.id,
        )
        # z/OS: match subject_code or subject_desc containing z/os or zos
        subj_zos = (
            Subject.objects.filter(event_code=event_code)
            .filter(
                Q(subject_code__icontains="z/os")
                | Q(subject_desc__icontains="z/os")
                | Q(subject_code__icontains="zos")
                | Q(subject_desc__icontains="zos")
            )
            .first()
        )
        # LUW: match subject_code or subject_desc containing luw
        subj_luw = (
            Subject.objects.filter(event_code=event_code)
            .filter(
                Q(subject_code__icontains="luw") | Q(subject_desc__icontains="luw")
            )
            .first()
        )
        ibm_zos = (
            base_ibm.filter(session__subject_id=subj_zos.subject_id).count()
            if subj_zos
            else 0
        )
        ibm_luw = (
            base_ibm.filter(session__subject_id=subj_luw.subject_id).count()
            if subj_luw
            else 0
        )
        counts["ibm_zos"] = ibm_zos
        counts["ibm_luw"] = ibm_luw

    return JsonResponse({"counts": counts})

def _slots_payload(day: int, event_code: str):
    layouts = CalendarLayout.objects.filter(
        day=day, event_code=event_code, visible=True
    )
    slots = CalendarSlot.objects.select_related(
        "layout", "session", "session__session_type", "session__subject",
        "special_session_type",
    ).filter(layout__day=day, layout__event_code=event_code)
    slot_map = {s.layout_id: s for s in slots}
    result = {}
    for lay in layouts:
        s = slot_map.get(lay.id)
        if not s:
            result[str(lay.id)] = None
            continue
        if s.session:
            sess = s.session
            result[str(lay.id)] = {
                "id": sess.id,
                "code": sess.session_code,
                "title": sess.title,
                "speaker_first": sess.speaker_first_name,
                "speaker_last": sess.speaker_last_name,
                "speaker_full": sess.speaker_full_name(),
                "speaker_company": sess.speaker_company,
                "session_type": sess.session_type.name,
                "session_type_id": sess.session_type_id,
                "subject": sess.subject.subject_code,
                "color": sess.session_type.color,
                "is_special": False,
            }
        elif s.special_session_type:
            st = s.special_session_type
            result[str(lay.id)] = {
                "is_special": True,
                "special_type_id": st.id,
                "special_type_name": st.name,
                "color": st.color or "#e7f1ff",
                "description": s.description or "",
                "layout_id": lay.id,
            }
        else:
            result[str(lay.id)] = None
    return result

def _require_auth_json(request):
    """Return JsonResponse(403) if not authenticated, else None."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "message": "Authentication required."}, status=403)
    return None


# ---------- auth ----------
@require_http_methods(["POST"])
def login_view(request):
    try:
        data = json.loads(request.body)
        username = (data.get("username") or "").strip()
        password = (data.get("password") or "")
    except Exception:
        return JsonResponse({"ok": False, "message": "Invalid request."}, status=400)
    if not username:
        return JsonResponse({"ok": False, "message": "Username required."}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"ok": False, "message": "Invalid username or password."}, status=200)
    login(request, user)
    # Set event from user's group: NA if in NA group, else EMEA
    group_names = set(user.groups.values_list("name", flat=True))
    request.session["event_code"] = "NA" if "NA" in group_names else "EMEA"
    return JsonResponse({"ok": True})


@require_http_methods(["POST", "GET"])
def logout_view(request):
    logout(request)
    return redirect("planner:schedule")


# ---------- page ----------
def schedule_page(request):
    event_code = _event_code(request)
    sessions_qs = (
        Session.objects.filter(event_code=event_code)
        .select_related("session_type", "subject")
        .order_by("-rating")
    )
    sessions = list(sessions_qs)
    session_ids = [s.id for s in sessions]
    st_map = defaultdict(list)
    for sid, tid in SessionTopic.objects.filter(
        session_id__in=session_ids
    ).values_list("session_id", "topic_id"):
        st_map[sid].append(tid)
    for s in sessions:
        s.topic_ids_str = ",".join(str(t) for t in st_map.get(s.id, []))

    special_session_types = list(
        SpecialSessionType.objects.filter(event_code=event_code)
        .order_by("name")
        .values("id", "name", "color")
    )
    session_types = list(
        SessionType.objects.filter(event_code=event_code)
        .order_by("id")
        .values("id", "name", "color")
    )
    topics = list(
        Topic.objects.filter(event_code=event_code)
        .order_by("code")
        .values("id", "code")
    )
    subjects = list(
        Subject.objects.filter(event_code=event_code)
        .order_by("subject_code")
        .values("subject_id", "subject_code", "subject_desc")
    )
    return render(
        request,
        "planner/planner.html",
        {
            "sessions": sessions,
            "special_session_types": special_session_types,
            "session_types": session_types,
            "topics": topics,
            "subjects": subjects,
            "is_authenticated": request.user.is_authenticated,
            "event_code": event_code,
        },
    )


@require_http_methods(["GET"])
def api_session_types(request):
    event_code = _event_code(request)
    types = (
        SessionType.objects
        .filter(event_code=event_code)
        .order_by("id")
        .values("id", "name", "color")
    )
    return JsonResponse({"types": list(types)})


@require_http_methods(["GET"])
def api_days(request):
    event_code = _event_code(request)
    days = (
        PlannerDay.objects.filter(event_code=event_code)
        .order_by("id")
        .values("id", "day")
    )
    return JsonResponse({"days": list(days)})


# ---------- API: day ----------
@require_http_methods(["GET"])
def api_day(request, day):
    """
    Return all layout cells (visible + hidden) for the given day,
    including colspan/rowspan info so merged cells render properly.
    """
    event_code = _event_code(request)
    # 1️⃣ include ALL layout rows (visible + hidden)
    layouts = (
        CalendarLayout.objects
        .filter(day=day, event_code=event_code)
        .select_related("time_slot")
        .order_by("time_slot__order", "track")
    )

    # 2️⃣ collect slots + safe session info
    slots = {}
    slot_qs = CalendarSlot.objects.select_related(
        "session", "session__session_type", "session__subject", "special_session_type"
    ).filter(layout__day=day, layout__event_code=event_code)
    for slot in slot_qs:
        if slot.session:
            s = slot.session
            slots[slot.layout.id] = {
                "id": s.id,
                "code": s.session_code or "",
                "title": s.title or "",
                "speaker_full": getattr(s, "speaker_full_name", lambda: "")(),
                "speaker_company": getattr(s, "speaker_company", "") or "",
                "subject": (s.subject.subject_code or "") if s.subject else "",
                "color": s.session_type.color,
                "session_type_id": s.session_type_id,
                "is_special": False,
            }
        elif slot.special_session_type:
            st = slot.special_session_type
            slots[slot.layout.id] = {
                "is_special": True,
                "special_type_id": st.id,
                "special_type_name": st.name,
                "color": st.color or "#e7f1ff",
                "description": slot.description or "",
                "layout_id": slot.layout.id,
            }
        else:
            slots[slot.layout.id] = {}

    # 3️⃣ list of used session IDs
    used_sessions = _used_session_ids(event_code)

    # 4️⃣ track headers
    headers = list(
        CalendarColumnHeader.objects.filter(event_code=event_code).values(
            "track", "subject", "room_name"
        )
    )

    # 5️⃣ serialize layout (keep visible + hidden)
    layout_data = []
    for l in layouts:
        ts = l.time_slot
        layout_data.append({
            "id": l.id,
            "label": l.label or "",
            "track": l.track,
            "type": l.type,
            "time_label": ts.label or "",
            "time_start": ts.start_time.strftime("%H:%M") if ts.start_time else "",
            "time_end": ts.end_time.strftime("%H:%M") if ts.end_time else "",
            "time_slot_id": ts.id,
            "colspan": l.colspan,
            "rowspan": l.rowspan,
            "visible": l.visible,
        })

    return JsonResponse({
        "layout": layout_data,
        "slots": slots,
        "used_sessions": used_sessions,
        "headers": headers,
    })


# ---------- API: assign ----------
@require_http_methods(["POST"])
@transaction.atomic
def api_assign(request):
    if err := _require_auth_json(request):
        return err
    try:
        data = json.loads(request.body)
        layout_id = int(data["layout_id"])
        transaction_id = data.get("transaction_id") or str(uuid.uuid4())
        session_id = data.get("session_id")
        special_session_type_id = data.get("special_session_type_id")
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    if not session_id and not special_session_type_id:
        return HttpResponseBadRequest("Provide session_id or special_session_type_id")
    if session_id and special_session_type_id:
        return HttpResponseBadRequest("Provide only one of session_id or special_session_type_id")

    event_code = _event_code(request)
    layout = (
        CalendarLayout.objects
        .filter(event_code=event_code)
        .select_related("time_slot")
        .select_for_update()
        .get(id=layout_id)
    )
    slot, _ = CalendarSlot.objects.select_for_update().get_or_create(
        layout=layout, defaults={"event_code": event_code}
    )
    logs = []

    if special_session_type_id:
        # Assign special type (e.g. PSP) – can be placed multiple times; no conflict check
        special_type = SpecialSessionType.objects.get(
            id=special_session_type_id, event_code=event_code
        )
        # If target had a session, log unassign
        if slot.session:
            prev = slot.session
            log_obj = ActionLog.objects.create(
                message=f"{layout.label} ({prev.session_code}) →",
                action_type="unassign",
                event_code=event_code,
                layout=layout,
                session=prev,
                day=layout.day,
                track=layout.track,
                transaction_id=transaction_id,
            )
            logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
        elif slot.special_session_type:
            prev_st = slot.special_session_type
            log_obj = ActionLog.objects.create(
                message=f"{layout.label} ({prev_st.name}) →",
                action_type="unassign",
                event_code=event_code,
                layout=layout,
                special_session_type=prev_st,
                day=layout.day,
                track=layout.track,
                transaction_id=transaction_id,
                slot_description=slot.description,
            )
            logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})

        slot.session = None
        slot.special_session_type = special_type
        slot.description = None
        slot.save()
        log_obj = ActionLog.objects.create(
            message=f"{special_type.name} → {layout.label}",
            action_type="assign",
            event_code=event_code,
            layout=layout,
            special_session_type=special_type,
            day=layout.day,
            track=layout.track,
            transaction_id=transaction_id,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
        return JsonResponse({
            "ok": True,
            "logs": logs,
            "slots": _slots_payload(layout.day_id, event_code),
            "used_sessions": _used_session_ids(event_code),
            "transaction_id": transaction_id,
        })

    # Normal session assign
    session_id = int(session_id)
    session = Session.objects.get(id=session_id, event_code=event_code)

    target_session = CalendarSlot.objects.filter(
        event_code=event_code,
        layout=layout,
        session__speaker_first_name=session.speaker_first_name,
        session__speaker_last_name=session.speaker_last_name,
    ).first()
    if not target_session:
        conflict_session = CalendarSlot.objects.filter(
            event_code=event_code,
            layout__day__id=layout.day.id,
            layout__time_slot__id=layout.time_slot.id,
            session__speaker_first_name=session.speaker_first_name,
            session__speaker_last_name=session.speaker_last_name,
        ).exclude(session=session)
        if conflict_session.exists():
            return JsonResponse({
                "ok": False,
                "message": f"The speaker {session.speaker_full_name()} is already assigned to another session at this time.",
                "logs": []
            })

    other = (
        CalendarSlot.objects
        .filter(event_code=event_code)
        .select_related("layout__time_slot", "session")
        .filter(session=session)
        .exclude(layout=layout)
        .first()
    )
    if other and other.session:
        log_obj = ActionLog.objects.create(
            message=f"{other.layout.label} ({session.session_code}) →",
            action_type="unassign",
            event_code=event_code,
            layout=other.layout,
            session=session,
            day=other.layout.day,
            track=other.layout.track,
            transaction_id=transaction_id,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
        other.session = None
        other.special_session_type = None
        other.description = None
        other.save()

    if slot.session and slot.session != session:
        prev = slot.session
        log_obj = ActionLog.objects.create(
            message=f"{layout.label} ({prev.session_code}) →",
            action_type="unassign",
            event_code=event_code,
            layout=layout,
            session=prev,
            day=layout.day,
            track=layout.track,
            transaction_id=transaction_id,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
    if slot.special_session_type:
        prev_st = slot.special_session_type
        log_obj = ActionLog.objects.create(
            message=f"{layout.label} ({prev_st.name}) →",
            action_type="unassign",
            event_code=event_code,
            layout=layout,
            special_session_type=prev_st,
            day=layout.day,
            track=layout.track,
            transaction_id=transaction_id,
            slot_description=slot.description,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})

    slot.session = session
    slot.special_session_type = None
    slot.description = None
    slot.save()
    log_obj = ActionLog.objects.create(
        message=f"{session.session_code} → {layout.label}",
        action_type="assign",
        event_code=event_code,
        layout=layout,
        session=session,
        day=layout.day,
        track=layout.track,
        transaction_id=transaction_id,
    )
    logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})

    return JsonResponse({
        "ok": True,
        "logs": logs,
        "slots": _slots_payload(layout.day_id, event_code),
        "used_sessions": _used_session_ids(event_code),
        "transaction_id": transaction_id,
    })

# ---------- API: unassign ----------
@require_http_methods(["POST"])
@transaction.atomic
def api_unassign(request):
    if err := _require_auth_json(request):
        return err
    try:
        data = json.loads(request.body)
        layout_id = int(data["layout_id"])
        transaction_id = data.get("transaction_id") or str(uuid.uuid4())
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    event_code = _event_code(request)
    layout = (
        CalendarLayout.objects
        .filter(event_code=event_code)
        .select_related("time_slot")
        .select_for_update()
        .get(id=layout_id)
    )
    slot = CalendarSlot.objects.select_for_update().filter(layout=layout).first()
    logs = []

    if slot and (slot.session or slot.special_session_type):
        if slot.session:
            current_session = slot.session
            log_obj = ActionLog.objects.create(
                message=f"{layout.label} ({current_session.session_code}) →",
                action_type="unassign",
                event_code=event_code,
                layout=layout,
                session=current_session,
                day=layout.day,
                track=layout.track,
                transaction_id=transaction_id,
            )
        else:
            current_st = slot.special_session_type
            log_obj = ActionLog.objects.create(
                message=f"{layout.label} ({current_st.name}) →",
                action_type="unassign",
                event_code=event_code,
                layout=layout,
                special_session_type=current_st,
                day=layout.day,
                track=layout.track,
                transaction_id=transaction_id,
                slot_description=slot.description,
            )
        logs.append({
            "id": log_obj.id,
            "time": log_obj.timestamp.isoformat(),
            "message": log_obj.message,
            "comment": log_obj.comment or "",
        })
        slot.session = None
        slot.special_session_type = None
        slot.description = None
        slot.save()

    return JsonResponse({
        "ok": True,
        "logs": logs,
        "slots": _slots_payload(layout.day_id, event_code),
        "used_sessions": _used_session_ids(event_code),
        "transaction_id": transaction_id,
    })


# ---------- API: move (calendar → calendar in one request, one transaction_id for undo) ----------
@require_http_methods(["POST"])
@transaction.atomic
def api_move(request):
    if err := _require_auth_json(request):
        return err
    """
    Move from one calendar cell to another in one request.
    One transaction_id for all log entries so undo reverts the full move (unassign source + assign target).
    """
    try:
        data = json.loads(request.body)
        source_layout_id = int(data["source_layout_id"])
        target_layout_id = int(data["target_layout_id"])
        transaction_id = data.get("transaction_id") or str(uuid.uuid4())
        session_id = data.get("session_id")
        special_session_type_id = data.get("special_session_type_id")
    except (KeyError, TypeError, ValueError):
        return HttpResponseBadRequest("Invalid payload: need source_layout_id, target_layout_id, and session_id or special_session_type_id")

    if not session_id and not special_session_type_id:
        return HttpResponseBadRequest("Provide session_id or special_session_type_id")
    if session_id and special_session_type_id:
        return HttpResponseBadRequest("Provide only one of session_id or special_session_type_id")
    if source_layout_id == target_layout_id:
        return HttpResponseBadRequest("source and target must differ")

    event_code = _event_code(request)
    source_layout = (
        CalendarLayout.objects
        .filter(event_code=event_code)
        .select_related("time_slot")
        .select_for_update()
        .get(id=source_layout_id)
    )
    target_layout = (
        CalendarLayout.objects
        .filter(event_code=event_code)
        .select_related("time_slot")
        .select_for_update()
        .get(id=target_layout_id)
    )
    logs = []
    moved_description = None  # when moving a special session, carry over its description

    # 1) Unassign source
    source_slot = CalendarSlot.objects.select_for_update().filter(layout=source_layout).first()
    if source_slot and (source_slot.session or source_slot.special_session_type):
        if source_slot.session:
            prev = source_slot.session
            log_obj = ActionLog.objects.create(
                message=f"{source_layout.label} ({prev.session_code}) →",
                action_type="unassign",
                event_code=event_code,
                layout=source_layout,
                session=prev,
                day=source_layout.day,
                track=source_layout.track,
                transaction_id=transaction_id,
            )
        else:
            prev_st = source_slot.special_session_type
            if special_session_type_id and prev_st.id == int(special_session_type_id):
                moved_description = source_slot.description
            log_obj = ActionLog.objects.create(
                message=f"{source_layout.label} ({prev_st.name}) →",
                action_type="unassign",
                event_code=event_code,
                layout=source_layout,
                special_session_type=prev_st,
                day=source_layout.day,
                track=source_layout.track,
                transaction_id=transaction_id,
                slot_description=source_slot.description,
            )
        logs.append({
            "id": log_obj.id,
            "time": log_obj.timestamp.isoformat(),
            "message": log_obj.message,
            "comment": log_obj.comment or "",
        })
        source_slot.session = None
        source_slot.special_session_type = None
        source_slot.description = None
        source_slot.save()

    # 2) Assign target (reuse same logic as api_assign for target slot)
    target_slot, _ = CalendarSlot.objects.select_for_update().get_or_create(
        layout=target_layout, defaults={"event_code": event_code}
    )
    layout = target_layout  # for _slots_payload and log layout

    if special_session_type_id:
        special_type = SpecialSessionType.objects.get(
            id=special_session_type_id, event_code=event_code
        )
        if target_slot.session:
            prev = target_slot.session
            log_obj = ActionLog.objects.create(
                message=f"{layout.label} ({prev.session_code}) →",
                action_type="unassign",
                event_code=event_code,
                layout=layout,
                session=prev,
                day=layout.day,
                track=layout.track,
                transaction_id=transaction_id,
            )
            logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
        elif target_slot.special_session_type:
            prev_st = target_slot.special_session_type
            log_obj = ActionLog.objects.create(
                message=f"{layout.label} ({prev_st.name}) →",
                action_type="unassign",
                event_code=event_code,
                layout=layout,
                special_session_type=prev_st,
                day=layout.day,
                track=layout.track,
                transaction_id=transaction_id,
                slot_description=target_slot.description,
            )
            logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
        target_slot.session = None
        target_slot.special_session_type = special_type
        target_slot.description = moved_description
        target_slot.save()
        log_obj = ActionLog.objects.create(
            message=f"{special_type.name} → {layout.label}",
            action_type="assign",
            event_code=event_code,
            layout=layout,
            special_session_type=special_type,
            day=layout.day,
            track=layout.track,
            transaction_id=transaction_id,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
        return JsonResponse({
            "ok": True,
            "logs": logs,
            "slots": _slots_payload(layout.day_id, event_code),
            "used_sessions": _used_session_ids(event_code),
            "transaction_id": transaction_id,
        })

    # Normal session
    session_id = int(session_id)
    session = Session.objects.get(id=session_id, event_code=event_code)
    target_session = CalendarSlot.objects.filter(
        event_code=event_code,
        layout=target_layout,
        session__speaker_first_name=session.speaker_first_name,
        session__speaker_last_name=session.speaker_last_name,
    ).first()
    if not target_session:
        conflict = CalendarSlot.objects.filter(
            event_code=event_code,
            layout__day=target_layout.day,
            layout__time_slot=target_layout.time_slot,
            session__speaker_first_name=session.speaker_first_name,
            session__speaker_last_name=session.speaker_last_name,
        ).exclude(session=session)
        if conflict.exists():
            return JsonResponse({
                "ok": False,
                "message": f"The speaker {session.speaker_full_name()} is already assigned to another session at this time.",
                "logs": logs,
            })
    if target_slot.session and target_slot.session != session:
        prev = target_slot.session
        log_obj = ActionLog.objects.create(
            message=f"{layout.label} ({prev.session_code}) →",
            action_type="unassign",
            event_code=event_code,
            layout=layout,
            session=prev,
            day=layout.day,
            track=layout.track,
            transaction_id=transaction_id,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
    if target_slot.special_session_type:
        prev_st = target_slot.special_session_type
        log_obj = ActionLog.objects.create(
            message=f"{layout.label} ({prev_st.name}) →",
            action_type="unassign",
            event_code=event_code,
            layout=layout,
            special_session_type=prev_st,
            day=layout.day,
            track=layout.track,
            transaction_id=transaction_id,
        )
        logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
    target_slot.session = session
    target_slot.special_session_type = None
    target_slot.description = None
    target_slot.save()
    log_obj = ActionLog.objects.create(
        message=f"{session.session_code} → {layout.label}",
        action_type="assign",
        event_code=event_code,
        layout=layout,
        session=session,
        day=layout.day,
        track=layout.track,
        transaction_id=transaction_id,
    )
    logs.append({"id": log_obj.id, "time": log_obj.timestamp.isoformat(), "message": log_obj.message, "comment": log_obj.comment or ""})
    return JsonResponse({
        "ok": True,
        "logs": logs,
        "slots": _slots_payload(layout.day_id, event_code),
        "used_sessions": _used_session_ids(event_code),
        "transaction_id": transaction_id,
    })


# ---------- API: logs ----------
@require_http_methods(["GET"])
def api_logs(request):
    """Return all logs, oldest first (for full persistent history)."""
    event_code = _event_code(request)
    logs = (
        ActionLog.objects.filter(event_code=event_code)
        .select_related("session")
        .only("timestamp", "message", "session")
        .order_by("timestamp")
    )
    data = []
    for log in logs:
        s = log.session
        session_code = s.session_code if s else ""
        data.append({
            "id": log.id,
            "time": log.timestamp.isoformat(),
            "message": log.message,
            "comment": log.comment or "",
            "session": session_code,
        })
    return JsonResponse({"logs": data})

# ---------- API: undo (robust, metadata-based) ----------
@require_http_methods(["POST"])
@transaction.atomic
def api_undo(request):
    if err := _require_auth_json(request):
        return err
    event_code = _event_code(request)
    # 1️⃣ Find latest transaction_id for this event
    last_tx = (
        ActionLog.objects.filter(event_code=event_code)
        .order_by("-timestamp")
        .values_list("transaction_id", flat=True)
        .first()
    )

    if not last_tx:
        return JsonResponse({"ok": False, "message": "Nothing left to undo."})

    # 2️⃣ Get all logs for this transaction (reverse order!)
    logs = (
        ActionLog.objects.filter(event_code=event_code, transaction_id=last_tx)
        .select_related("layout", "session", "special_session_type")
        .order_by("-timestamp")
    )

    undone_logs = []

    for log in logs:
        layout = log.layout
        session = log.session
        special_type = log.special_session_type

        if log.action_type == "assign" and layout:
            CalendarSlot.objects.filter(layout=layout).delete()
            undone_logs.append({
                "time": timezone.now().isoformat(),
                "message": f"Undo: cleared {layout.label}",
            })

        elif log.action_type == "unassign" and layout and (session or special_type):
            defaults = {}
            if session:
                defaults["session"] = session
                defaults["special_session_type"] = None
                defaults["description"] = None
                msg = f"Undo: restored {session.session_code} → {layout.label}"
            else:
                defaults["special_session_type"] = special_type
                defaults["session"] = None
                defaults["description"] = getattr(log, "slot_description", None)
                msg = f"Undo: restored {special_type.name} → {layout.label}"
            CalendarSlot.objects.update_or_create(layout=layout, defaults=defaults)
            undone_logs.append({"time": timezone.now().isoformat(), "message": msg})

    # 3️⃣ Delete all logs of this transaction
    ActionLog.objects.filter(transaction_id=last_tx).delete()

    # 4️⃣ Recompute used sessions for this event
    used_sessions = _used_session_ids(event_code)

    return JsonResponse({
        "ok": True,
        "logs": undone_logs,
        "used_sessions": used_sessions,
    })


@require_http_methods(["POST"])
def api_log_comment(request, log_id):
    if err := _require_auth_json(request):
        return err
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "message": "Invalid JSON"}, status=400)

    comment = (payload.get("comment") or "").strip()

    event_code = _event_code(request)
    try:
        log = ActionLog.objects.get(pk=log_id, event_code=event_code)
    except ActionLog.DoesNotExist:
        return JsonResponse({"ok": False, "message": "Log entry not found"}, status=404)

    if comment:
        log.comment = comment
        log.commented_at = timezone.now()
    else:
        log.comment = None
        log.commented_at = None

    log.save(update_fields=["comment", "commented_at"])

    return JsonResponse({
        "ok": True,
        "log_id": log.id,
        "comment": log.comment or "",
        "commented_at": log.commented_at.isoformat() if log.commented_at else None,
    })

@require_http_methods(["POST"])
def save_slot_description(request):
    """Save description on a CalendarSlot (for special session types only)."""
    if err := _require_auth_json(request):
        return err
    try:
        data = json.loads(request.body)
        layout_id = int(data["layout_id"])
        new_description = (data.get("description") or "").strip()
        event_code = _event_code(request)
        slot = CalendarSlot.objects.filter(
            layout_id=layout_id, event_code=event_code
        ).select_related("special_session_type").get()
        if not slot.special_session_type:
            return JsonResponse({"ok": False, "message": "Slot is not a special session."}, status=400)
        slot.description = new_description or None
        slot.save(update_fields=["description"])
        return JsonResponse({"ok": True, "message": "Description saved."}, status=200)
    except (KeyError, ValueError, CalendarSlot.DoesNotExist):
        return JsonResponse({"ok": False, "message": "Slot not found."}, status=404)