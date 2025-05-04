#!/usr/bin/env python3
from django.core.management.base import BaseCommand
from transactions.models import Transaction

class Command(BaseCommand):
    help = 'Count and show sample unmatched transactions'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=5,
                          help='Number of sample transactions to show')

    def handle(self, *args, **options):
        limit = options.get('limit', 5)
        
        # Count unmatched transactions
        unmatched_count = Transaction.objects.filter(supplier__isnull=True).count()
        self.stdout.write(f"Found {unmatched_count} unmatched transactions")
        
        # Show sample transactions
        self.stdout.write("\nSample unmatched transactions:")
        for tx in Transaction.objects.filter(supplier__isnull=True)[:limit]:
            self.stdout.write(f"ID: {tx.id}, Description: {tx.description}") 