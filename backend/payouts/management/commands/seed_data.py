"""
Seed script: populates the database with test merchants, bank accounts, and credit history.

Creates 3 merchants:
  - Acme Design Studio:  ₹2,50,000 from 8 credits
  - Pixel Forge Labs:    ₹1,00,000 from 5 credits, 1 completed payout of ₹25,000
  - Cloud Nine Agency:   ₹50,000 from 3 credits, 1 failed payout (funds returned)

Each merchant gets a Django User for JWT auth (password: "testpass123").
"""
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from payouts.models import Merchant, BankAccount, LedgerEntry, Payout


class Command(BaseCommand):
    help = 'Seed database with test merchants, bank accounts, and transaction history'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Seeding database...'))

        with transaction.atomic():
            # --- Merchant A: Acme Design Studio ---
            user_a, _ = User.objects.get_or_create(
                username='acme',
                defaults={'email': 'acme@example.com'}
            )
            user_a.set_password('testpass123')
            user_a.save()

            merchant_a, _ = Merchant.objects.get_or_create(
                user=user_a,
                defaults={
                    'business_name': 'Acme Design Studio',
                    'email': 'acme@example.com',
                }
            )

            bank_a = BankAccount.objects.get_or_create(
                merchant=merchant_a,
                account_number='1234567890123456',
                defaults={
                    'ifsc_code': 'HDFC0001234',
                    'account_holder_name': 'Acme Design Studio Pvt Ltd',
                    'is_primary': True,
                }
            )[0]

            # 8 credit entries totaling ₹2,50,000 (25,000,000 paise)
            credit_amounts_a = [
                (5000000, 'Payment from client: GlobalTech Inc', 30),
                (3500000, 'Payment from client: StartupXYZ', 25),
                (2000000, 'Payment from client: MediaHouse Co', 20),
                (4500000, 'Payment from client: RetailBrand Ltd', 15),
                (3000000, 'Payment from client: FinanceApp Inc', 12),
                (2500000, 'Payment from client: HealthTech Solutions', 8),
                (1500000, 'Payment from client: EduPlatform', 5),
                (3000000, 'Payment from client: SaaSCorp', 2),
            ]

            for amount, desc, days_ago in credit_amounts_a:
                LedgerEntry.objects.get_or_create(
                    merchant=merchant_a,
                    description=desc,
                    defaults={
                        'entry_type': 'credit',
                        'amount_paise': amount,
                    }
                )

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Merchant A: {merchant_a.business_name} (user: acme / testpass123)'
            ))

            # --- Merchant B: Pixel Forge Labs ---
            user_b, _ = User.objects.get_or_create(
                username='pixelforge',
                defaults={'email': 'hello@pixelforge.dev'}
            )
            user_b.set_password('testpass123')
            user_b.save()

            merchant_b, _ = Merchant.objects.get_or_create(
                user=user_b,
                defaults={
                    'business_name': 'Pixel Forge Labs',
                    'email': 'hello@pixelforge.dev',
                }
            )

            bank_b1 = BankAccount.objects.get_or_create(
                merchant=merchant_b,
                account_number='9876543210987654',
                defaults={
                    'ifsc_code': 'ICIC0005678',
                    'account_holder_name': 'Pixel Forge Labs LLP',
                    'is_primary': True,
                }
            )[0]

            bank_b2 = BankAccount.objects.get_or_create(
                merchant=merchant_b,
                account_number='5555666677778888',
                defaults={
                    'ifsc_code': 'SBIN0009012',
                    'account_holder_name': 'Rahul Sharma (Founder)',
                    'is_primary': False,
                }
            )[0]

            # 5 credits totaling ₹1,25,000 (12,500,000 paise)
            credit_amounts_b = [
                (3000000, 'Payment from client: TravelApp Inc', 20),
                (2500000, 'Payment from client: GameStudio Pro', 15),
                (2000000, 'Payment from client: CryptoExchange Ltd', 10),
                (3000000, 'Payment from client: FoodDelivery Co', 7),
                (2000000, 'Payment from client: RealEstateTech', 3),
            ]

            for amount, desc, days_ago in credit_amounts_b:
                LedgerEntry.objects.get_or_create(
                    merchant=merchant_b,
                    description=desc,
                    defaults={
                        'entry_type': 'credit',
                        'amount_paise': amount,
                    }
                )

            # 1 completed payout of ₹25,000
            payout_b, created = Payout.objects.get_or_create(
                merchant=merchant_b,
                amount_paise=2500000,
                status='completed',
                defaults={
                    'bank_account': bank_b1,
                    'attempts': 1,
                    'last_attempted_at': timezone.now() - timedelta(days=2),
                }
            )
            if created:
                LedgerEntry.objects.create(
                    merchant=merchant_b,
                    entry_type='hold',
                    amount_paise=2500000,
                    reference_id=payout_b.id,
                    description=f'Funds held for payout {str(payout_b.id)[:8]}',
                )
                LedgerEntry.objects.create(
                    merchant=merchant_b,
                    entry_type='release',
                    amount_paise=2500000,
                    reference_id=payout_b.id,
                    description=f'Hold released for completed payout {str(payout_b.id)[:8]}',
                )
                LedgerEntry.objects.create(
                    merchant=merchant_b,
                    entry_type='debit',
                    amount_paise=2500000,
                    reference_id=payout_b.id,
                    description=f'Payout settled to bank {str(payout_b.id)[:8]}',
                )

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Merchant B: {merchant_b.business_name} (user: pixelforge / testpass123)'
            ))

            # --- Merchant C: Cloud Nine Agency ---
            user_c, _ = User.objects.get_or_create(
                username='cloudnine',
                defaults={'email': 'team@cloudnine.agency'}
            )
            user_c.set_password('testpass123')
            user_c.save()

            merchant_c, _ = Merchant.objects.get_or_create(
                user=user_c,
                defaults={
                    'business_name': 'Cloud Nine Agency',
                    'email': 'team@cloudnine.agency',
                }
            )

            bank_c = BankAccount.objects.get_or_create(
                merchant=merchant_c,
                account_number='1111222233334444',
                defaults={
                    'ifsc_code': 'UTIB0003456',
                    'account_holder_name': 'Cloud Nine Digital Agency',
                    'is_primary': True,
                }
            )[0]

            # 3 credits totaling ₹50,000 (5,000,000 paise)
            credit_amounts_c = [
                (2000000, 'Payment from client: E-Commerce Giant', 14),
                (1500000, 'Payment from client: LogisticsTech', 7),
                (1500000, 'Payment from client: EdTech Startup', 3),
            ]

            for amount, desc, days_ago in credit_amounts_c:
                LedgerEntry.objects.get_or_create(
                    merchant=merchant_c,
                    description=desc,
                    defaults={
                        'entry_type': 'credit',
                        'amount_paise': amount,
                    }
                )

            # 1 failed payout of ₹15,000 (funds returned)
            payout_c, created = Payout.objects.get_or_create(
                merchant=merchant_c,
                amount_paise=1500000,
                status='failed',
                defaults={
                    'bank_account': bank_c,
                    'attempts': 2,
                    'last_attempted_at': timezone.now() - timedelta(days=1),
                }
            )
            if created:
                LedgerEntry.objects.create(
                    merchant=merchant_c,
                    entry_type='hold',
                    amount_paise=1500000,
                    reference_id=payout_c.id,
                    description=f'Funds held for payout {str(payout_c.id)[:8]}',
                )
                LedgerEntry.objects.create(
                    merchant=merchant_c,
                    entry_type='release',
                    amount_paise=1500000,
                    reference_id=payout_c.id,
                    description=f'Funds returned — payout {str(payout_c.id)[:8]} failed',
                )

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Merchant C: {merchant_c.business_name} (user: cloudnine / testpass123)'
            ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))
        self.stdout.write('')
        self.stdout.write('  Login credentials (all passwords: testpass123):')
        self.stdout.write('    acme       → Acme Design Studio    (₹2,50,000)')
        self.stdout.write('    pixelforge → Pixel Forge Labs      (₹1,00,000)')
        self.stdout.write('    cloudnine  → Cloud Nine Agency     (₹50,000)')
