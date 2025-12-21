from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inspections", "0009_add_separate_name_fields"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="lotevaluation",
            constraint=models.UniqueConstraint(
                fields=("lot",), name="unique_lot_evaluation_per_lot"
            ),
        ),
    ]


