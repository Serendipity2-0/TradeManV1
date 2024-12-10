# Evening Scripts Expert Knowledge Base

## Overview
Evening scripts in TradeMan V1 are responsible for end-of-day operations, trade reconciliation, report generation, and system cleanup. These scripts ensure proper market closure procedures and prepare the system for the next trading day.

## Key Components

### 1. SweepOrders
- Purpose: Cleanup and reconciliation of day's orders
- Functions:
  - Cancel pending orders
  - Reconcile executed orders
  - Update order database
- Common Usage: `python sweep_orders.py --force-close`

### 2. DailyTradeBookValidator
- Purpose: Validates day's trading activity
- Validations:
  - Trade execution accuracy
  - P&L calculations
  - Position reconciliation
- Key Features:
  - Cross-broker validation
  - Trade log analysis
  - Discrepancy reporting

### 3. EODTradeDBLogging
- Purpose: End-of-day database updates
- Operations:
  - Trade data archival
  - Performance metrics calculation
  - Database optimization
- Important Parameters:
  - `--compress-logs`: Compress old log files
  - `--backup`: Create backup before processing

### 4. EODDailyReports
- Purpose: Generate end-of-day reports
- Report Types:
  - Trading summary
  - P&L statement
  - Risk metrics
  - Position summary
- Distribution Methods:
  - Email delivery
  - Telegram notifications
  - Database storage

### 5. TickerDB
- Purpose: Market data archival
- Functions:
  - Tick data compression
  - OHLC data generation
  - Data integrity checks

## Common Issues and Solutions

1. Trade Reconciliation Errors
   - Check broker APIs
   - Verify trade logs
   - Manual reconciliation process
   - Contact broker support

2. Report Generation Issues
   - Verify data sources
   - Check disk space
   - Update templates
   - Reset report cache

3. Database Problems
   - Backup verification
   - Index optimization
   - Space management
   - Connection pooling

## Best Practices

1. Execution Sequence
   - Complete all trades before sweep
   - Validate before logging
   - Generate reports after validation
   - Archive data last

2. Data Validation
   - Cross-check multiple sources
   - Verify calculations
   - Document discrepancies
   - Maintain audit trail

3. System Cleanup
   - Archive old logs
   - Clear temporary files
   - Optimize databases
   - Reset counters

## Common Commands

```bash
# Order sweep
python sweep_orders.py --force-close

# Trade validation
python trade_validator.py --detailed-check

# Report generation
python generate_reports.py --all

# Database maintenance
python db_maintenance.py --optimize
```

## Emergency Procedures

1. Failed Trade Settlement
   - Document unsettled trades
   - Contact broker immediately
   - Prepare contingency funds
   - Update risk management

2. System Failure
   - Switch to backup systems
   - Preserve current state
   - Document failure point
   - Execute recovery plan

3. Data Loss Prevention
   - Regular backups
   - Redundant storage
   - Version control
   - Audit logging

## Performance Monitoring

1. Execution Time
   - Track script duration
   - Monitor resource usage
   - Optimize bottlenecks
   - Set time limits

2. Data Quality
   - Validate calculations
   - Check data integrity
   - Monitor error rates
   - Track success rates

## Related Documentation
- EOD Procedures Manual
- Database Management Guide
- Report Templates
- Recovery Procedures
