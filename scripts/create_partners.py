from accounts.models import PartnerCompany

partners = [
    ('Mak', 'MAK'),
    ('Andropol', 'ADPL'),
    ('Matchmaster', 'MTCH'),
    ('Wuxi', 'WUXI'),
    ('Mahavir Spinfab', 'MVSF'),
    ('Miranda', 'MRDA'),
    ('Optimum Digital', 'OPDG'),
]
for name, code in partners:
    obj, created = PartnerCompany.objects.get_or_create(
        code=code,
        defaults={'name': name, 'is_standard': True}
    )
    status = 'Created' if created else 'Already exists'
    print(f'  {status}: {name} ({code})')

print(f'\nDone. Total partner companies: {PartnerCompany.objects.count()}')
