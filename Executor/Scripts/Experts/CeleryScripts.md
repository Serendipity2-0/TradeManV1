# Celery Scripts Expert Knowledge Base

## Overview
Celery Scripts in TradeMan V1 manage distributed task execution, background processing, and task queue management. These scripts ensure efficient processing of trading operations, data updates, and system maintenance tasks.

## Key Components

### 1. Task Management
- **V1_poetry_app.py**
  - Purpose: Main Celery application configuration
  - Features:
    - Task registration
    - Queue configuration
    - Worker management
    - Task routing

### 2. Task Types

#### Trading Tasks
- Order execution
- Position updates
- Risk calculations
- Strategy execution

#### Data Tasks
- Market data updates
- Database maintenance
- Cache management
- Log rotation

#### System Tasks
- Health checks
- Resource monitoring
- Cleanup operations
- Backup procedures

## Configuration

### 1. Celery Configuration
```python
# celeryconfig.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/1'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
enable_utc = True
```

### 2. Task Settings
- Retry policies
- Timeout limits
- Priority levels
- Concurrency settings

### 3. Queue Configuration
- Queue definitions
- Routing rules
- Worker assignments
- Rate limits

## Common Commands

### Task Management
```bash
# Start Celery worker
celery -A V1_poetry_app worker --loglevel=INFO

# Clear all tasks
python clear_tasks.py --all

# Monitor tasks
celery -A V1_poetry_app flower

# Run specific task
python run_task.py --task-name update_market_data
```

### Worker Management
```bash
# Start multiple workers
celery multi start w1 w2 -A V1_poetry_app

# Stop workers
celery multi stop w1 w2

# Restart workers
celery multi restart w1 w2 -A V1_poetry_app
```

## Task Patterns

### 1. Periodic Tasks
- Market data updates
- System health checks
- Report generation
- Cache cleanup

### 2. Event-Driven Tasks
- Order execution
- Position updates
- Alert generation
- Log processing

### 3. Chained Tasks
- Strategy execution
- Data processing pipelines
- Report generation
- System maintenance

## Monitoring

### 1. Task Monitoring
- Task status
- Execution time
- Error rates
- Queue length

### 2. Worker Monitoring
- CPU usage
- Memory consumption
- Task throughput
- Error handling

### 3. System Monitoring
- Queue health
- Broker status
- Backend status
- Network connectivity

## Error Handling

### 1. Task Retries
```python
@app.task(bind=True, max_retries=3)
def retry_task(self):
    try:
        # Task logic
        pass
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

### 2. Error Reporting
- Error logging
- Alert generation
- Status updates
- Recovery procedures

### 3. Recovery Procedures
- Task resubmission
- Worker restart
- Queue cleanup
- System reset

## Best Practices

### 1. Task Design
- Idempotency
- Atomic operations
- Error handling
- Status tracking

### 2. Queue Management
- Queue segregation
- Priority assignment
- Rate limiting
- Dead letter queues

### 3. Resource Management
- Worker scaling
- Memory management
- CPU allocation
- Disk usage

## Troubleshooting

### Common Issues
1. Task Failures
   - Check task logs
   - Verify input data
   - Review error messages
   - Test task isolation

2. Worker Issues
   - Check system resources
   - Verify broker connection
   - Review worker logs
   - Test worker isolation

3. Queue Problems
   - Monitor queue length
   - Check message routing
   - Verify message format
   - Test queue health

## Emergency Procedures

### 1. System Overload
- Stop non-critical tasks
- Scale workers
- Clear queues
- Monitor resources

### 2. Data Corruption
- Stop affected tasks
- Backup data
- Clean queues
- Restore system

### 3. Service Outage
- Switch to backup
- Document incident
- Notify stakeholders
- Execute recovery

## Related Documentation
- Celery Configuration Guide
- Task Development Manual
- Monitoring Setup Guide
- Recovery Procedures
