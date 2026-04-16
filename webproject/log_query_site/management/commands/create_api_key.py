import hashlib
import secrets

from django.core.management.base import BaseCommand, CommandError

from log_query_site.models import APIKey


class Command(BaseCommand):
    help = 'Generate a new API key for CSV loader authentication'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Human-readable label for this key')

    def handle(self, *args, **options):
        name = options['name'].strip()
        if not name:
            raise CommandError('--name cannot be empty')

        raw_key = secrets.token_hex(32)
        prefix = raw_key[:8]
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        if APIKey.objects.filter(prefix=prefix).exists():
            raise CommandError('Prefix collision — please run the command again')

        api_key = APIKey.objects.create(name=name, prefix=prefix, key_hash=key_hash)

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Save this key now — it cannot be recovered later:'))
        self.stdout.write(self.style.SUCCESS(f'  {raw_key}'))
        self.stdout.write('')
        self.stdout.write(f'Name:   {api_key.name}')
        self.stdout.write(f'Prefix: {api_key.prefix}...')
        self.stdout.write(f'ID:     {api_key.id}')
        self.stdout.write('')
        self.stdout.write('Set in the loader environment:')
        self.stdout.write(f'  export LOG_DB_API_KEY={raw_key}')
        self.stdout.write('')
