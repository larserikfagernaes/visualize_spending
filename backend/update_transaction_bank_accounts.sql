-- Update transactions with bank account references
-- Execute this SQL script with SQLite: sqlite3 db.sqlite3 < update_transaction_bank_accounts.sql

-- Update transactions for bank account 1 (Personal Account - 82642706)
UPDATE transactions_transaction
SET bank_account_id = 1
WHERE account_id = '82642706' AND bank_account_id IS NULL;

-- Update transactions for bank account 2 (SP-GenerellDrift - 136638262)
UPDATE transactions_transaction
SET bank_account_id = 2
WHERE account_id = '136638262' AND bank_account_id IS NULL;

-- Update transactions for bank account 3 (Ekstraordinært innovasjon - 101139825)
UPDATE transactions_transaction
SET bank_account_id = 3
WHERE account_id = '101139825' AND bank_account_id IS NULL;

-- Update transactions for bank account 4 (SP-Tech - 136637859)
UPDATE transactions_transaction
SET bank_account_id = 4
WHERE account_id = '136637859' AND bank_account_id IS NULL;

-- Update transactions for bank account 5 (SP-Ops - 136636846)
UPDATE transactions_transaction
SET bank_account_id = 5
WHERE account_id = '136636846' AND bank_account_id IS NULL;

-- Update transactions for bank account 6 (SP-Business - 136637861)
UPDATE transactions_transaction
SET bank_account_id = 6
WHERE account_id = '136637861' AND bank_account_id IS NULL;

-- Update transactions for bank account 7 (old_account_1 - 115716450)
UPDATE transactions_transaction
SET bank_account_id = 7
WHERE account_id = '115716450' AND bank_account_id IS NULL;

-- Update transactions for bank account 8 (SP-holding - 136638260)
UPDATE transactions_transaction
SET bank_account_id = 8
WHERE account_id = '136638260' AND bank_account_id IS NULL;

-- Count updated transactions for each bank account
SELECT 'Transactions updated:' AS info;

SELECT 
    ba.id AS bank_account_id,
    ba.name AS bank_account_name,
    COUNT(t.id) AS transaction_count
FROM 
    transactions_transaction t
    JOIN transactions_bankaccount ba ON t.bank_account_id = ba.id
GROUP BY 
    t.bank_account_id
ORDER BY 
    transaction_count DESC; 