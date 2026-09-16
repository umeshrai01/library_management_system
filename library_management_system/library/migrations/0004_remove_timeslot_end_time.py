from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0003_alter_timeslot_options_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="timeslot",
            name="timeslot_end_must_be_after_start",
        ),
        migrations.AlterModelOptions(
            name="timeslot",
            options={"ordering": ["start_time", "name"]},
        ),
        migrations.RemoveField(
            model_name="timeslot",
            name="end_time",
        ),
    ]
