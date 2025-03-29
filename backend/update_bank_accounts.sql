-- Update bank accounts with names from bank_account_map.json
-- Execute this SQL script with SQLite: sqlite3 db.sqlite3 < update_bank_accounts.sql

-- Update 136638262 to SP-GenerellDrift
UPDATE transactions_bankaccount
SET name = 'SP-GenerellDrift'
WHERE account_number = '136638262';

-- Update 136637859 to SP-Tech
UPDATE transactions_bankaccount
SET name = 'SP-Tech'
WHERE account_number = '136637859';

-- Update 82642706 to Innovasjon Norge Konto
UPDATE transactions_bankaccount
SET name = 'Innovasjon Norge Konto' 
WHERE account_number = '82642706';

-- Update 101139825 to Ekstraordinært innovasjon
UPDATE transactions_bankaccount
SET name = 'Ekstraordinært innovasjon'
WHERE account_number = '101139825';

-- Update 136637861 to SP-Business
UPDATE transactions_bankaccount
SET name = 'SP-Business'
WHERE account_number = '136637861';

-- Update 136636846 to SP-Ops
UPDATE transactions_bankaccount
SET name = 'SP-Ops'
WHERE account_number = '136636846';

-- Update 115716450 to old_account_1 (marked as ignore but updating anyway)
UPDATE transactions_bankaccount
SET name = 'old_account_1'
WHERE account_number = '115716450';

-- Update 136638260 to SP-holding
UPDATE transactions_bankaccount
SET name = 'SP-holding'
WHERE account_number = '136638260'; 