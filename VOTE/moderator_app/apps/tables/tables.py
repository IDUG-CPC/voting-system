

from django_tables2 import tables, TemplateColumn
from django.utils.html import format_html

from ..selection.models import Moderators


class ModeratorsTable(tables.Table):
    session_date = tables.Column(verbose_name="Day", orderable=False)
    session_time = tables.Column(verbose_name="Time", orderable=False)
    session_code = tables.Column(verbose_name="Code", orderable=False)
    session_title = tables.Column(verbose_name="Title", orderable=False)
    speaker = tables.Column(verbose_name="Speaker(s)", orderable=False)
    subject_desc = tables.Column(verbose_name="Platform", orderable=False)
    moderator_name = tables.Column(verbose_name="Moderator", orderable=False)
    email_verification = tables.Column(verbose_name="Confirmed", orderable=False, empty_values=())

    search = tables.Column(verbose_name="")



    def render_search(self, value):
        return ""

    def render_email_verification(self, value, record):
        if value == 'verified':
            return format_html(
                '<i class="bi bi-check-lg text-dark" title="Email confirmed" '
                'aria-label="Email confirmed"></i>'
            )
        if value == 'pending':
            if getattr(record, 'can_resend_verification', False):
                return format_html(
                    '<a href="javascript:void(0);" onclick="resend_verification()" '
                    'class="text-primary" title="Email not confirmed — click to resend verification" '
                    'aria-label="Email not confirmed — click to resend verification">'
                    '<i class="bi bi-envelope-fill"></i></a>'
                )
            return format_html(
                '<i class="bi bi-envelope-fill text-primary" title="Email not confirmed" '
                'aria-label="Email not confirmed"></i>'
            )
        return ''

    Edit = TemplateColumn(template_name='tables/value_update.html', verbose_name="")


    class Meta:
        model = Moderators
        template_name = "tables/bootstrap5_prevnext.html"
        empty_text = "No results found."
        fields = (
            "session_date",
            "session_time",
            "session_code",
            "session_title",
            "speaker",
            "subject_desc",
            "moderator_name",
            "email_verification",
            "search"
        )
