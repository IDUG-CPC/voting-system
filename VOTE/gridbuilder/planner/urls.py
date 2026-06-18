from django.urls import path
from . import views
from . import views_excel
from . import views_csv

app_name = "planner"

urlpatterns = [
    path("", views.schedule_page, name="schedule"),
    path("export-excel/", views_excel.export_excel, name="export_excel"),
    path("api/csv-preview/", views_csv.csv_preview, name="csv_preview"),
    path("api/csv-import/", views_csv.csv_import, name="csv_import"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("api/day/<int:day>/", views.api_day, name="api_day"),
    path("api/assign/", views.api_assign, name="api_assign"),
    path("api/unassign/", views.api_unassign, name="api_unassign"),
    path("api/move/", views.api_move, name="api_move"),
    path("api/logs/", views.api_logs, name="api_logs"),
    path("api/undo/", views.api_undo, name="api_undo"),
    path("api/days/", views.api_days, name="api_days"),
    path("api/session-types/", views.api_session_types, name="api_session_types"),
    path("api/session-type-counts/", views.api_session_type_counts, name="api_session_type_counts"),
    path("api/logs/<int:log_id>/comment/", views.api_log_comment, name="api_log_comment"),
    path("api/save-slot-description/", views.save_slot_description, name="save_slot_description"),

]