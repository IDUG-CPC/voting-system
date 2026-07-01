"""
CSV import from Sessionboard: file selection, preview (stats + sample), and full import.
Replace-all: DELETE rows for event (actionlog, calendarslot, session_topic, session), then INSERT all sessions from CSV.
Merge: skip existing session_code values; insert only new sessions (preserves grid assignments and logs).
"""
import csv
import io
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import connection, transaction

from .models import PlannerCompany, Session, SessionTopic, Subject, Topic


def _db_schema():
    """Schema name from Django DB options (e.g. grid) so raw SQL hits the same tables as ORM."""
    opts = settings.DATABASES.get("default", {}).get("OPTIONS", {})
    opt_str = opts.get("options", "")
    m = re.search(r"search_path=(\w+)", opt_str)
    return m.group(1) if m else "public"


# CSV header (exact) -> planner_session field name or special handling
CSV_SESSION_MAP = {
    "Title": "title",
    "Friendly ID": "session_code",
    "Status": "status",
    "Description": "description",
    "Submitter": "submitter",
    "Speakers": "speakers",
    "Audience": "audience",
    "Session Type": "session_type_label",
    "This presentation ...": "presentation",
    "Learning Objective 1": "objective_1",
    "Speaker 1: Email": "speaker_1_email",
    "Speaker 1: First Name": "speaker_1_first_name",
    "Speaker 1: Last Name": "speaker_1_last_name",
    "Speaker 1: Job Title": "speaker_1_title",
    "Speaker 1: Company Name": "speaker_1_company",
    "Speaker 1: I am a First-Time Presenter.": "speaker_1_first_time",
    "Speaker 2: Email": "speaker_2_email",
    "Speaker 2: First Name": "speaker_2_first_name",
    "Speaker 2: Last Name": "speaker_2_last_name",
    "Speaker 2: Job Title": "speaker_2_title",
    "Speaker 2: Company Name": "speaker_2_company",
    "Speaker 2: I am a First-Time Presenter.": "speaker_2_first_time",
    "Average Rating": "rating",
    "(1) Field: Internal Comments (Aggregated)": "internal_comments",
    "(1) Field: External Comments (Aggregated)": "external_comments",
}
CSV_COL_SUBJECT = "Subject"
CSV_COL_TAGS = "Tags"


def _default_session_type_id_for_event(event_code):
    """When no planner_company row matches: User type — id 1 (EMEA), 10 (NA)."""
    return 10 if (event_code or "").strip().upper() == "NA" else 1


def _load_planner_company_mappings(event_code):
    """
    Rows for this event, longest `company` first so longer substrings win (e.g. 'software engineering' before 'sap').
    """
    rows = list(
        PlannerCompany.objects.filter(event_code=event_code).values_list(
            "company", "session_type_id"
        )
    )
    rows.sort(key=lambda pair: len((pair[0] or "").strip()), reverse=True)
    return rows


def _session_type_id_from_company(company_val, event_code, mappings):
    """
    If a mapping's company (lowercase) appears as a substring of the speaker company string, use its session_type_id.
    Otherwise default session type id for the event. Empty company → default.
    """
    default_id = _default_session_type_id_for_event(event_code)
    if not company_val or not str(company_val).strip():
        return default_id
    company_lower = str(company_val).strip().lower()
    for company, session_type_id in mappings:
        needle = (company or "").strip().lower()
        if needle and needle in company_lower:
            return int(session_type_id)
    return default_id


@ensure_csrf_cookie
@require_http_methods(["POST"])
def csv_preview(request):
    """
    Accept an uploaded CSV file; return row count, column count, headers, and first 3 data rows.
    Parses with Python csv module (handles quoted fields, commas and newlines inside quotes).
    """
    file_obj = request.FILES.get("file")
    if not file_obj:
        return JsonResponse({"error": "No file uploaded."}, status=400)

    name = (file_obj.name or "").lower()
    if not name.endswith(".csv"):
        return JsonResponse({"error": "File must be a .csv file."}, status=400)

    try:
        raw = file_obj.read()
    except Exception as e:
        return JsonResponse({"error": f"Could not read file: {e}"}, status=400)

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return JsonResponse({"error": "File must be UTF-8 encoded."}, status=400)

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return JsonResponse({
            "row_count": 0,
            "col_count": 0,
            "headers": [],
            "rows": [],
            "current_session_count": 0,
            "new_count": 0,
            "existing_count": 0,
            "dummy_count": 0,
        })

    headers = rows[0]
    data_rows = rows[1:]
    col_count = len(headers)
    sample_rows = data_rows[:3]
    event_code = _event_code_from_request(request)
    stats = _import_stats(headers, data_rows, event_code)

    return JsonResponse({
        "row_count": stats["row_count"],
        "col_count": col_count,
        "headers": headers,
        "rows": sample_rows,
        "current_session_count": stats["current_session_count"],
        "new_count": stats["new_count"],
        "existing_count": stats["existing_count"],
        "dummy_count": stats["dummy_count"],
    })


def _parse_csv_file(file_obj):
    """Read and decode CSV file; return (headers, data_rows) or raise. Uses utf-8-sig to strip BOM if present."""
    raw = file_obj.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("File must be UTF-8 encoded.")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _event_code_from_request(request):
    """Event code (EMEA/NA) from session; default EMEA."""
    return request.session.get("event_code", "EMEA")


def _row_get(row, col_index, header, default=""):
    """Get cell value from row by header name; return default if missing."""
    i = col_index.get(header)
    if i is None or i >= len(row):
        return default
    val = row[i]
    return val.strip() if val is not None and isinstance(val, str) else default


def _is_dummy_session_title(title):
    """Sessionboard placeholder rows (title starts with 'dummy session', case-insensitive)."""
    return bool(title) and title.strip().lower().startswith("dummy session")


def _dummy_sessions_suffix(count):
    if count <= 0:
        return ""
    noun = "session" if count == 1 else "sessions"
    return f" {count} dummy {noun} ignored."


def _import_stats(headers, data_rows, event_code):
    """Counts for preview UI and merge-mode import (duplicate Friendly IDs in CSV count as skipped)."""
    col_index = {h.strip(): i for i, h in enumerate(headers)}

    def get(row, header, default=""):
        return _row_get(row, col_index, header, default)

    existing_codes = set(
        Session.objects.filter(event_code=event_code).values_list("session_code", flat=True)
    )
    seen_in_csv = set()
    new_count = 0
    skipped_count = 0
    dummy_count = 0

    for row in data_rows:
        session_code = get(row, "Friendly ID", "").strip()
        if not session_code:
            continue
        title = get(row, "Title", "").strip()
        if title and _is_dummy_session_title(title):
            dummy_count += 1
            continue
        if session_code in seen_in_csv:
            skipped_count += 1
            continue
        seen_in_csv.add(session_code)
        if session_code in existing_codes:
            skipped_count += 1
        else:
            new_count += 1

    return {
        "row_count": len(data_rows),
        "current_session_count": len(existing_codes),
        "new_count": new_count,
        "existing_count": skipped_count,
        "dummy_count": dummy_count,
    }


def _replace_all_from_request(request):
    """POST replace_all: default False (merge) when absent."""
    return request.POST.get("replace_all", "0") in ("1", "true", "True", "on")


@ensure_csrf_cookie
@require_http_methods(["POST"])
def csv_import(request):
    """
    Accept an uploaded CSV file and INSERT sessions + session_topic from CSV.
    replace_all (default true): DELETE event data first, then insert all rows.
    replace_all false: merge only — skip existing session_code values and duplicate Friendly IDs in CSV.
    """
    file_obj = request.FILES.get("file")
    if not file_obj:
        return JsonResponse({"error": "No file uploaded."}, status=400)

    name = (file_obj.name or "").lower()
    if not name.endswith(".csv"):
        return JsonResponse({"error": "File must be a .csv file."}, status=400)

    try:
        headers, data_rows = _parse_csv_file(file_obj)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    event_code = _event_code_from_request(request)
    if not event_code:
        return JsonResponse({"error": "Event (EMEA/NA) not set for this user."}, status=400)

    replace_all = _replace_all_from_request(request)

    # Build header -> column index (strip headers for matching)
    col_index = {h.strip(): i for i, h in enumerate(headers)}

    def get(row, header, default=""):
        return _row_get(row, col_index, header, default)

    schema = _db_schema()
    with transaction.atomic():
        if replace_all:
            with connection.cursor() as cursor:
                cursor.execute(
                    f'DELETE FROM "{schema}".planner_actionlog WHERE event_code = %s',
                    [event_code],
                )
                cursor.execute(
                    f'DELETE FROM "{schema}".planner_calendarslot WHERE event_code = %s',
                    [event_code],
                )
                cursor.execute(
                    f'DELETE FROM "{schema}".planner_session_topic WHERE session_id IN (SELECT id FROM "{schema}".planner_session WHERE event_code = %s)',
                    [event_code],
                )
                cursor.execute(
                    f'DELETE FROM "{schema}".planner_session WHERE event_code = %s',
                    [event_code],
                )

        inserted = 0
        skipped = 0
        dummy_ignored = 0
        seen_in_csv = set()
        company_mappings = _load_planner_company_mappings(event_code)
        for row in data_rows:
            session_code_val = get(row, "Friendly ID", "").strip()
            if not session_code_val:
                continue
            title_val = get(row, "Title", "").strip()
            if not title_val:
                continue
            if _is_dummy_session_title(title_val):
                dummy_ignored += 1
                continue

            if not replace_all:
                if session_code_val in seen_in_csv:
                    skipped += 1
                    continue
                seen_in_csv.add(session_code_val)
                if Session.objects.filter(
                    event_code=event_code, session_code=session_code_val
                ).exists():
                    skipped += 1
                    continue

            # subject_id: lookup planner_subject by subject_code + event_code
            subject_raw = get(row, CSV_COL_SUBJECT, "").strip()
            try:
                subject = Subject.objects.get(subject_code=subject_raw, event_code=event_code)
            except Subject.DoesNotExist:
                return JsonResponse({
                    "error": f"Subject not found for code '{subject_raw}' (event {event_code}). Row session_code={session_code_val!r}.",
                }, status=400)

            # session_type_id: planner_company substring match (Speaker 1 company) → session_type_id; else default per event
            company_val = get(row, "Speaker 1: Company Name", "").strip()
            session_type_id = _session_type_id_from_company(
                company_val, event_code, company_mappings
            )

            # rating: use 0.00 if empty
            rating_str = get(row, "Average Rating", "").strip()
            try:
                rating = Decimal(rating_str) if rating_str else Decimal("0.00")
            except (InvalidOperation, TypeError):
                rating = Decimal("0.00")

            session_kw = {
                "event_code": event_code,
                "session_code": session_code_val,
                "title": title_val,
                "subject_id": subject.subject_id,
                "rating": rating,
                "session_type_id": session_type_id,
            }
            for csv_header, field_name in CSV_SESSION_MAP.items():
                if field_name == "rating":
                    continue
                val = get(row, csv_header, "")
                f = Session._meta.get_field(field_name)
                session_kw[field_name] = (val[: f.max_length] if val and getattr(f, "max_length", None) else (val or None))

            if not (session_kw.get("status") or "").strip():
                session_kw["status"] = "Pending"

            new_session = Session.objects.create(**session_kw)

            # Tags -> planner_session_topic (split by comma, lookup Topic by code + event_code)
            tags_str = get(row, CSV_COL_TAGS, "").strip()
            if tags_str:
                for tag_name in (t.strip() for t in tags_str.split(",") if t.strip()):
                    try:
                        topic = Topic.objects.get(code=tag_name, event_code=event_code)
                    except Topic.DoesNotExist:
                        return JsonResponse({
                            "error": f"Topic not found for code '{tag_name}' (event {event_code}). Row session_code={session_code_val!r}.",
                        }, status=400)
                    SessionTopic.objects.create(session=new_session, topic=topic)
            inserted += 1

    dummy_suffix = _dummy_sessions_suffix(dummy_ignored)
    if replace_all:
        message = f"Import completed. {inserted} sessions imported.{dummy_suffix}"
    else:
        message = f"Import completed. {inserted} new sessions added, {skipped} skipped.{dummy_suffix}"
    return JsonResponse({"message": message})
