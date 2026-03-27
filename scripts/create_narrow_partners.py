from accounts.models import PartnerCompany

partners = [
    ('Mikan', 'MIKN'),
    ('PMTC', 'PMTC'),
    ('Schoutteten', 'SCTN'),
    ('ACW', 'ACW'),
]
for name, code in partners:
    obj, created = PartnerCompany.objects.get_or_create(
        code=code,
        defaults={'name': name, 'is_standard': False}
    )
    status = 'Created' if created else 'Already exists'
    print(f'  {status}: {name} ({code}) [Narrow]')

print(f'\nDone. Total partner companies: {PartnerCompany.objects.count()}')
