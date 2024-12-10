# Morning Scripts Expert Knowledge Base

## Overview
Morning scripts are critical components of the TradeMan V1 system that handle essential tasks required at market open. These scripts ensure proper system initialization, data validation, and preparation for the trading day.

## Key Components

### 1. 0830_GoodMorning.sh
- Purpose: Primary initialization script for market open
- Key Functions:
  - System health checks
  - Service initialization
  - Market data feed setup
- Common Usage: `./0830_GoodMorning.sh`

### 2. TelegramOrderBot.py
- Purpose: Initializes Telegram bot for order management
- Features:
  - Order status monitoring
  - Alert notifications
  - Command processing
- Common Commands:
  - `/start` - Start the bot
  - `/status` - Check order status
  - `/positions` - View current positions

### 3. FundValidator.py
- Purpose: Validates available trading funds
- Checks:
  - Account balance verification
  - Margin requirements
  - Risk limits
- Important Parameters:
  - `--check-all`: Validate all accounts
  - `--detailed-report`: Generate detailed validation report

### 4. DailyLogin.py
- Purpose: Automated login to trading platforms
- Supported Platforms:
  - Zerodha
  - AliceBlue
  - Firstock
- Error Handling:
  - Connection timeout recovery
  - Session management
  - 2FA handling

### 5. MarketInfoUpdate.py
- Purpose: Updates market information database
- Data Points:
  - Index values
  - Market breadth
  - Sector performance
- Update Frequency: Every 5 minutes

### 6. AsmGsmAggregator.py
- Purpose: Aggregates ASM/GSM data
- Functions:
  - Surveillance measure updates
  - Risk category assessment
  - Trading restriction checks

### 7. DailyEquityCalc.py
- Purpose: Calculates daily equity positions
- Calculations:
  - P&L computation
  - Position sizing
  - Risk metrics

### 8. DailyInstrumentAggregator.py
- Purpose: Aggregates instrument data
- Features:
  - Price updates
  - Volume analysis
  - Technical indicators

## Common Issues and Solutions

1. Login Failures
   - Check network connectivity
   - Verify credentials
   - Clear browser cache
   - Restart authentication service

2. Data Synchronization Issues
   - Verify database connections
   - Check disk space
   - Reset data cache
   - Validate data integrity

3. System Resource Problems
   - Monitor CPU usage
   - Check memory allocation
   - Clear temporary files
   - Restart required services

## Best Practices

1. Execution Order
   - Always run GoodMorning.sh first
   - Complete fund validation before trading
   - Ensure market data is updated before strategies

2. Monitoring
   - Check log files regularly
   - Monitor system resources
   - Verify data accuracy
   - Track execution times

3. Error Recovery
   - Document error messages
   - Follow recovery procedures
   - Maintain backup systems
   - Test failover mechanisms

## Common Commands

```bash
# System initialization
./0830_GoodMorning.sh

# Fund validation
python FundValidator.py --check-all

# Market data update
python MarketInfoUpdate.py --force-update

# Position calculation
python DailyEquityCalc.py --detailed
```

## Related Documentation
- System Architecture Guide
- Trading Platform APIs
- Risk Management Procedures
- Emergency Response Protocols
