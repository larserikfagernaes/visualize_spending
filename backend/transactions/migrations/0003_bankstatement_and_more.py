# Generated by Django 5.1.7 on 2025-03-18 18:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_transaction_bank_account_id_transaction_is_forbidden_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankStatement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.CharField(max_length=255)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateField()),
                ('source_file', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.RenameField(
            model_name='transaction',
            old_name='created_at',
            new_name='imported_at',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='source_file',
        ),
        migrations.AlterField(
            model_name='transaction',
            name='tripletex_id',
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['tripletex_id'], name='transaction_triplet_8373be_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['date'], name='transaction_date_ad8c94_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['bank_account_id'], name='transaction_bank_ac_b2c48a_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['should_process'], name='transaction_should__af73ea_idx'),
        ),
        migrations.AddField(
            model_name='bankstatement',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bank_statements', to='transactions.category'),
        ),
    ]
