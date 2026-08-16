from django.core.management.base import BaseCommand

from apps.selection.email_service import send_moderator_reminders


class Command(BaseCommand):
    help = (
        'Send moderator reminder emails for sessions on today + REMINDER_DAYS_AHEAD '
        '(one email per moderator listing all sessions that day).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=None,
            help='Override REMINDER_DAYS_AHEAD (e.g. 64 for a local test).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send now, bypassing the active event’s REMINDER_SEND_HOUR check.',
        )

    def handle(self, *args, **options):
        summary = send_moderator_reminders(
            days_ahead=options.get('days_ahead'),
            force=options.get('force', False),
        )
        self.stdout.write(self.style.SUCCESS(summary['message']))
        if summary.get('errors'):
            self.stderr.write(
                self.style.ERROR('Completed with %s error(s).' % summary['errors'])
            )
