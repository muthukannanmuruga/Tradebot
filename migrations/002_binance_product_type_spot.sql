-- Migration: Change Binance product_type from "I" to "SPOT"
-- Date: 2026-02-25
-- Reason: Use proper crypto terminology (SPOT/MARGIN) instead of reusing Upstox codes (I/D/MTF)

-- Update Portfolio table
-- Binance pairs don't contain '|' separator (Upstox format: NSE_EQ|INE...)
UPDATE portfolio 
SET product_type = 'SPOT' 
WHERE pair NOT LIKE '%|%' 
  AND product_type = 'I';

-- Update Trade table
-- Binance pairs don't contain '|' separator (Upstox format: NSE_EQ|INE...)
UPDATE trades 
SET product_type = 'SPOT'
WHERE pair NOT LIKE '%|%' 
  AND product_type = 'I';

-- Update BotMetrics table
UPDATE bot_metrics 
SET product_type = 'SPOT'
WHERE market = 'binance' 
  AND product_type = 'I';

-- Verify the changes
SELECT 'Portfolio' as table_name, pair, product_type 
FROM portfolio 
WHERE pair NOT LIKE '%|%'
UNION ALL
SELECT 'BotMetrics' as table_name, market as pair, product_type 
FROM bot_metrics 
WHERE market = 'binance';
