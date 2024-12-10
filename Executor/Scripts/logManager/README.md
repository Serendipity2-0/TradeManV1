# LogManager Module

## Overview
The LogManager module provides comprehensive testing and monitoring tools for the TradeMan V1 project. It includes scripts for testing API endpoints, database connections, and Docker container health monitoring.

## Features
- **API Endpoint Testing**: Automated testing of FastAPI endpoints with retry mechanism and detailed reporting
- **Database Connection Testing**: Connection testing for both PostgreSQL and MongoDB databases
- **Docker Health Monitoring**: Container health checks, resource monitoring, and log analysis
- **Configurable Environment**: All settings manageable through environment variables
- **Detailed Reporting**: Comprehensive test reports with timestamps and metrics

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
- Copy logManager.env.template to logManager.env (if not exists)
- Update the values in logManager.env according to your environment

## Configuration

The module uses environment variables for configuration. Key settings in `logManager.env`:

### API Configuration
- `API_BASE_URL`: Base URL for API testing
- `API_VERSION`: API version
- `API_TIMEOUT`: Request timeout in seconds

### Docker Configuration
- `DOCKER_CONTAINERS_TO_MONITOR`: Comma-separated list of container names
- `DOCKER_LOG_LINES`: Number of log lines to retrieve
- `DOCKER_HEALTH_CHECK_INTERVAL`: Health check interval in seconds

### Database Configuration
- PostgreSQL settings (`POSTGRES_*`)
- MongoDB settings (`MONGO_*`)

### Logging Configuration
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `LOG_FORMAT`: Log message format
- `LOG_FILE_PATH`: Path to log file

## Usage

### API Endpoint Testing
```bash
python api_endpoint_tester.py
```
Tests all configured API endpoints and generates a detailed report.

### Database Connection Testing
```bash
python db_connection_tester.py
```
Tests connections to configured databases and reports their status.

### Docker Health Monitoring
```bash
python docker_health_check.py
```
Monitors Docker container health, resources, and logs.

## Reports

All scripts generate detailed reports that include:
- Timestamp of test execution
- Success/failure status
- Response times
- Error messages (if any)
- Resource usage statistics (for Docker)

Reports are saved in the configured `REPORT_PATH` directory with timestamps.

## Logging

The module uses Python's logging framework with the following features:
- Configurable log levels
- File and console output
- Timestamp and context information
- JSON formatting support

## Error Handling

All scripts include:
- Retry mechanisms for transient failures
- Detailed error reporting
- Graceful degradation
- Comprehensive error logging

## Best Practices

1. **Configuration Management**
   - Keep sensitive information in environment variables
   - Use appropriate timeouts and retry counts
   - Regular review and updates of monitoring thresholds

2. **Monitoring**
   - Regular execution of health checks
   - Review of generated reports
   - Alert setup for critical failures

3. **Maintenance**
   - Regular updates of dependencies
   - Periodic review of logging patterns
   - Adjustment of thresholds based on system growth

## Contributing

1. Follow the project's coding standards
2. Add appropriate logging statements
3. Update documentation for any changes
4. Add unit tests for new features

## Troubleshooting

Common issues and solutions:

1. **API Connection Failures**
   - Verify API_BASE_URL configuration
   - Check network connectivity
   - Verify API service is running

2. **Database Connection Issues**
   - Verify database credentials
   - Check database service status
   - Confirm network access to database ports

3. **Docker Monitoring Problems**
   - Verify Docker daemon is running
   - Check container name configuration
   - Confirm sufficient permissions

## Support

For issues and support:
1. Check the error logs in the configured log directory
2. Review the generated reports
3. Consult the project documentation
4. Contact the development team

## License

This module is part of the TradeMan V1 project and follows its licensing terms.
