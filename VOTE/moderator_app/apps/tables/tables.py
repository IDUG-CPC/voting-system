

from django_tables2 import tables, TemplateColumn

from ..selection.models import Moderators


class ModeratorsTable(tables.Table):
    session_date = tables.Column(verbose_name="Day", orderable=False)
    session_time = tables.Column(verbose_name="Time", orderable=False)
    session_code = tables.Column(verbose_name="Code", orderable=False)
    session_title = tables.Column(verbose_name="Title", orderable=False)
    speaker = tables.Column(verbose_name="Speaker(s)", orderable=False)
    subject_desc = tables.Column(verbose_name="Platform", orderable=False)
    moderator_name = tables.Column(verbose_name="Moderator", orderable=False)

    search = tables.Column(verbose_name="")



    def render_search(self, value):
        return ""

    Edit = TemplateColumn(template_name='tables/value_update.html', verbose_name="")


    class Meta:
        model = Moderators
        template_name = "tables/bootstrap5_prevnext.html"
        fields = (
            "session_date",
            "session_time",
            "session_code",
            "session_title",
            "speaker",
            "subject_desc",
            "moderator_name",
            "search"
        )
