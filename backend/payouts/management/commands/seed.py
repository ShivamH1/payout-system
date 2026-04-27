import uuid
from django.core.management.base import BaseCommand
from payouts.models import Merchant, BankAccount, LedgerEntry, Payout


MERCHANT_UUIDS = {
    'acme': '00000000-0000-0000-0000-000000000001',
    'buildfast': '00000000-0000-0000-0000-000000000002',
    'pixelperfect': '00000000-0000-0000-0000-000000000003',
}


class Command(BaseCommand):
    help = 'Seed the database with test merchants and data'

    def handle(self, *args, **options):
        merchants_data = [
            {
                'key': 'acme',
                'name': 'Acme Agency',
                'email': 'acme@example.com',
                'account_number': '1234567890',
                'ifsc_code': 'HDFC0001234',
                'account_holder_name': 'Acme Agency',
                'credits': [
                    {'amount': 1000000, 'description': 'Payment from customer XYZ'},
                    {'amount': 1000000, 'description': 'Payment from customer ABC'},
                    {'amount': 1000000, 'description': 'Payment from customer DEF'},
                    {'amount': 1000000, 'description': 'Payment from customer GHI'},
                    {'amount': 1000000, 'description': 'Payment from customer JKL'},
                ],
            },
            {
                'key': 'buildfast',
                'name': 'BuildFast Studio',
                'email': 'buildfast@example.com',
                'account_number': '0987654321',
                'ifsc_code': 'ICIC0001234',
                'account_holder_name': 'BuildFast Studio',
                'credits': [
                    {'amount': 625000, 'description': 'Payment from client A'},
                    {'amount': 625000, 'description': 'Payment from client B'},
                    {'amount': 625000, 'description': 'Payment from client C'},
                    {'amount': 625000, 'description': 'Payment from client D'},
                ],
            },
            {
                'key': 'pixelperfect',
                'name': 'PixelPerfect Labs',
                'email': 'pixelperfect@example.com',
                'account_number': '5678901234',
                'ifsc_code': 'SBIN0001234',
                'account_holder_name': 'PixelPerfect Labs',
                'credits': [
                    {'amount': 1333000, 'description': 'Payment from startup X'},
                    {'amount': 1333000, 'description': 'Payment from startup Y'},
                    {'amount': 1333000, 'description': 'Payment from startup Z'},
                    {'amount': 1333000, 'description': 'Payment from startup W'},
                    {'amount': 1333000, 'description': 'Payment from startup V'},
                    {'amount': 1333000, 'description': 'Payment from startup U'},
                ],
            },
        ]

        for data in merchants_data:
            merchant_uuid = uuid.UUID(MERCHANT_UUIDS[data['key']])

            merchant, created = Merchant.objects.get_or_create(
                id=merchant_uuid,
                defaults={'name': data['name'], 'email': data['email']}
            )
            if created:
                self.stdout.write(f'Created merchant: {merchant.name}')
            else:
                self.stdout.write(f'Merchant already exists: {merchant.name}')

            bank_account, created = BankAccount.objects.get_or_create(
                merchant=merchant,
                account_number=data['account_number'],
                defaults={
                    'ifsc_code': data['ifsc_code'],
                    'account_holder_name': data['account_holder_name'],
                }
            )
            if created:
                self.stdout.write(f'Created bank account for: {merchant.name}')

            for credit_data in data['credits']:
                LedgerEntry.objects.get_or_create(
                    merchant=merchant,
                    entry_type=LedgerEntry.EntryType.CREDIT,
                    amount_paise=credit_data['amount'],
                    description=credit_data['description'],
                )

        self.stdout.write(self.style.SUCCESS('Seed completed successfully!'))