from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from pontoon.base.models import Project
from pontoon.sync.models import SyncLog
from pontoon.sync.tasks import sync_project


class Command(BaseCommand):
    args = '<project_slug project_slug ...>'
    help = 'Synchronize database and remote repositories.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-commit',
            action='store_true',
            dest='no_commit',
            default=False,
            help='Do not commit changes to VCS'
        )

        parser.add_argument(
            '--no-pull',
            action='store_true',
            dest='no_pull',
            default=False,
            help='Do not pull new commits from VCS'
        )

        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            default=False,
            help='Always sync even if there are no changes'
        )

    def handle(self, *args, **options):
        """
        Collect the projects we want to sync and trigger worker jobs to
        sync each one.
        """
        sync_log = SyncLog.objects.create(start_time=timezone.now())

        projects = Project.objects.filter(disabled=False)
        if args:
            projects = projects.filter(slug__in=args)

        if len(projects) < 1:
            raise CommandError('No matching projects found.')

        for project in projects:
            if not project.can_commit:
                self.stdout.write(u'Skipping project {0}, cannot commit to repository.'
                                  .format(project.name))
            else:
                self.stdout.write(u'Scheduling sync for project {0}.'.format(project.name))
                sync_project.delay(
                    project.pk,
                    sync_log.pk,
                    no_pull=options['no_pull'],
                    no_commit=options['no_commit'],
                    force=options['force'],
                )
