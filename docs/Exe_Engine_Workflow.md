# Software Workflow Documentation

## 1. Morning Pre-market

### 1.1 Account Login and Access Token Update
- Login to individual accounts
- Update access tokens in Firebase

### 1.2 Fund Validation
- Compare our fund calculations with broker calculations
- If mismatch detected, send Discord message

### 1.3 Market Info Parameters Update
- Update market information parameters in Firebase

### 1.4 Instrument Aggregator
- Update expiry dates and strike prices for derivatives
- Update exchange tokens for equity
- Each broker(broker platform) has its own identifier to fetch stock details

### 1.5 ASM/GSM Instrument Aggregator
- Fetch updated list of stocks under ASM/GSM
- Mark these stocks to be skipped in trading

### 1.6 Equity Calculation
- Calculate stocks to buy for the day

## 2. Strategies During Market

### 2.1 Strategy Execution
- Each strategy has specific entry and exit times
- Celery scripts set up to execute at designated times

### 2.2 Strategy Behavior
- Some strategies place orders and close
- Others continue running until manually closed

### 2.3 Example: Expiry Trader Strategy
1. Update market info parameters
2. Execute at 9:18 AM
3. Calculate:
   - ATM strike price
   - Option type (based on market info)
   - Stoploss
   - Hedge order
4. Calculate stoploss price for main order
5. Determine strike price, option type, and expiry for 3 orders
6. Fetch exchange token from database
7. Create order details for all orders
8. Retrieve users opted for this strategy
9. Place orders asynchronously
10. Update Firebase with order details (order ID, tax, entry time, etc.)
11. Send Discord notification for failed orders

## 3. EOD After Market

### 3.1 Order Sweeping
- Cancel stoploss orders
- Place market orders for stoploss

### 3.2 Tradebook Validator
- Segregate orders placed by system vs. users
- For system orders: fetch average price and update in Firebase
- Delete orders without average price from Firebase

### 3.3 Trade Logging
- Log completed trades in database
- Include entry price, exit price, and other details
- Delete orders after calculation from Firebase

### 3.4 Ticker DB Script
- Store option data in PostgreSQL

### 3.5 EOD Reporting
- Generate daily trade reports
- Include holdings value
- Prepare consolidated admin report with all client trading data