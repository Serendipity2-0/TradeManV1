# Release Notes - Version 1.1.1

## Features

### Asynchronous Order Placement
- Implemented async order placement across all brokers, improving system responsiveness and efficiency.

### Enhanced Stock Calculations and Order Management
- Added short, mid, and long-term stock calculations for more comprehensive analysis.
- Implemented order placement and three patterns of stoploss orders based on these calculations, providing more flexible risk management options.

### Improved Infrastructure
- Created separate databases for Debt, Equity, and Derivatives modules, enhancing data isolation and management.
- Implemented script execution via supervisor module with Celery, improving process management and scalability.

### API Enhancements
- Developed FastAPI endpoints for User API, supporting both User and Admin pages, providing a more robust and efficient API interface.

## Bug Fixes

- Fixed: Added "segment_type" in firstock_adapter for the equity module when placing orders, ensuring correct order placement.
- Fixed: Integrated MPWizard thread with the existing Kiteconnect thread for LTP fetching, improving data consistency.
- Fixed: Ensured Zerodha adapter doesn't use async Kiteconnect class for operations after market hours, preventing potential errors.

## Improvements

### Code Quality and Structure
- Added pre-commit hooks to enforce code formatting standards, ensuring consistent code style across the project.
- Restructured folders under Debt, Equity, and Derivatives modules for better organization and maintainability.

### Testing
- Implemented unit tests and integration testing for scripts, improving code reliability and maintainability.

## Roadmap

1. Database Migration: Transition from SQLite3 to PostgreSQL database for improved performance and scalability.
2. Order Execution: Implement Order Executor endpoint for FastAPI to enable order placement from the admin page.
3. Notification System: Revamp of notification and report center for better user communication.
4. Margin Management: Creation of a margin center utility to check margins and place orders, reducing order failure rates.

---

Thank you for using our software. For any issues or suggestions, please open an issue in the GitHub repository.