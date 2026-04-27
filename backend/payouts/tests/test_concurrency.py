import unittest
import threading
from django.test import TestCase
from django.db import connection
from payouts.models import Merchant, LedgerEntry, Payout, BankAccount
from payouts.services import request_payout, get_merchant_balance, InsufficientBalanceError


@unittest.skipIf(connection.vendor != 'postgresql', "Concurrency test requires PostgreSQL")
class ConcurrencyTest(TestCase):
    def setUp(self):
        self.merchant = Merchant.objects.create(name='Test', email='test@test.com')
        self.bank_account = BankAccount.objects.create(
            merchant=self.merchant,
            account_number='1234567890',
            ifsc_code='HDFC0001234',
            account_holder_name='Test',
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type='credit',
            amount_paise=10000,
            description='Seed credit',
        )

    def test_concurrent_payouts_only_one_succeeds(self):
        """
        Two simultaneous 6000 paise requests against a 10000 paise balance.
        Exactly one must succeed and one must fail.
        """
        results = []
        errors = []

        def make_request(key):
            try:
                try:
                    payout = request_payout(
                        merchant_id=self.merchant.id,
                        amount_paise=6000,
                        bank_account_id=self.bank_account.id,
                        idempotency_key=key,
                    )
                    results.append('success')
                except InsufficientBalanceError:
                    results.append('failed')
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=make_request, args=('key-1',))
        t2 = threading.Thread(target=make_request, args=('key-2',))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"Unexpected errors: {errors}")
        self.assertEqual(results.count('success'), 1)
        self.assertEqual(results.count('failed'), 1)

        balance = get_merchant_balance(self.merchant.id)
        self.assertEqual(balance['available_paise'], 4000)
        self.assertEqual(balance['held_paise'], 6000)