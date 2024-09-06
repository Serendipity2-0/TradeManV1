# Software Design Nomenclature

## 1. Brokers
- Zerodha
- Firstock

## 2. Strategy Types
### 2.1 Place order and exit the script
1. Execute script using Celery for required calculations:
   - Determine market status (bearish/bullish)
   - Analyze historic data
2. Wait for entry time (declared in strategy entry params in database)
3. Fetch exchange tokens for main order and hedge order (if applicable)
4. Calculate stop-loss price based on main order LTP (if required)
5. Prepare order details and send as a single list to place order function
6. Record order ID and relevant information in Firebase

### 2.2 Continuously monitor the instrument
1. Execute script using Celery for required calculations:
   - Determine market status (bearish/bullish)
   - Analyze historic data
2. Obtain entry points for instrument monitoring
3. Place orders when market reaches specified levels
4. Add main order token to instrument monitor class with trigger points (if monitoring required)
5. Record order ID and relevant information in Firebase

## 3. Post-Order Processing
1. Validate orders from broker with Firebase records
2. Fetch average price for each order
3. Remove extra and failed orders (with empty average price) from database
4. Calculate PnL, tax, and net PnL using entry and exit prices
5. Store calculations in database
6. Clear orders with both entry and exit
7. Move holding orders to holdings database

## 4. Strategies
### 4.1 Place order and exit the script
- ShortTerm
- MidTerm
- LongTerm
- ExpiryTrader
- GoldenCoin
- OvernightFutures
- Om
- Namaha

### 4.2 Continuously monitor the instrument
- AmiPy
- ExpiryTrader