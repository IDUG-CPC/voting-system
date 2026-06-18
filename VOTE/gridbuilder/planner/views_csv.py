"""
CSV import from Sessionboard: file selection, preview (stats + sample), and later full import.
"""
import csv
import io

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie


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
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
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
        })

    headers = rows[0]
    data_rows = rows[1:]
    row_count = len(data_rows)
    col_count = len(headers)
    sample_rows = data_rows[:3]

    return JsonResponse({
        "row_count": row_count,
        "col_count": col_count,
        "headers": headers,
        "rows": sample_rows,
    })
