-- Update internal transfers for transactions containing 'OPPGAVE KontoreguleringAviant AS'
UPDATE transactions_transaction
SET is_internal_transfer = 1
WHERE description LIKE '%OPPGAVE KontoreguleringAviant AS%'
AND is_internal_transfer = 0;

-- Output how many transactions were updated
SELECT 'Updated ' || changes() || ' transactions as internal transfers.'; 