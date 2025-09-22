# Fingerprint Attendance System - Copilot Instructions

This document provides essential guidance for AI agents working on this codebase.

## Architecture Overview

The system is a Flask application designed to ingest attendance data from two types of fingerprint devices and process it into a central SQL Server database.

1.  **Real-Time Ingestion (`StreamingService`)**: The core of the real-time data flow is `app/services/streaming_service.py`. This service runs in a background thread and uses two different methods for data collection:
    *   **ZKTeco Devices**: Connects directly via TCP and listens for real-time attendance events (push). It uses the `pyzk` library.
    *   **Fingerspot API Devices**: Polls a vendor-specific HTTP API at a regular interval to fetch new records (pull). It uses the `requests` library.

2.  **Batch Synchronization (`SyncService`)**: `app/services/sync_service.py` acts as a safety net. It's designed to be run manually or on a schedule to fetch historical data from devices, ensuring no data is lost if the streaming service was down.

3.  **Data Access Layer (`AttendanceModel`)**: All database interactions are centralized in `app/models/attendance.py`. This model contains all SQL queries for inserting data, checking for duplicates, and managing the attendance queue. **Do not write raw SQL queries in controllers or services; add a new method to this model instead.**

4.  **Asynchronous Processing Queue (`attendance_queues`)**: Raw attendance records are first inserted into the `attendance_queues` table. A separate, long-running worker process, initiated by `run_worker.py`, reads from this table to perform heavier processing. This prevents the real-time `StreamingService` from being blocked.

## Key Conventions & Patterns

-   **Duplicate Checking is Critical**: The system **never deletes data** before syncing. It uses a "check-then-insert" pattern.
    -   **FPLog Duplicates**: Checked in `check_fplog_duplicate` based on `PIN`, `Date` (to the minute), and `Status`.
    -   **Queue Duplicates**: Checked in `check_attendance_queue_duplicate` based on `PIN`, `Date` (to the minute), and `Machine`.
    -   When adding streaming data, always use the `..._if_not_duplicate` methods from `AttendanceModel`.

-   **Employee ID is `attid`**: The primary identifier for an employee in the `employees` table is `attid`. The codebase frequently uses a variable named `fpid` to hold this value after looking it up.
    -   **Pattern**: Use the `_get_fpid_by_pin` method in the services to query the `employees` table for the `attid` using the employee's `pin`.
    -   **Example (`streaming_service.py`)**: `fpid = self._get_fpid_by_pin(pin)`

-   **Status Code Translation**: Raw punch codes from devices (e.g., 0, 1, 3) are translated into meaningful statuses (e.g., "Masuk", "Pulang"). This logic is centralized in `app/utils/status_helper.py` and relies on mappings defined in `config/devices.py`. When adding a new device or status, update `config/devices.py`.

-   **Configuration Hub**: All device-specific settings (IP, port, API keys, status rules) are located in `config/devices.py`. Database connection strings are in `config/database.py`.

## Developer Workflows

-   **Running the Web Application (Development)**:
    ```bash
    python app.py
    ```

-   **Running the Background Worker**: This must be run in a separate terminal to process the attendance queue.
    ```bash
    python run_worker.py
    ```

-   **Running in Production**: The production environment uses a WSGI server. The command is likely in `start_production.bat`.
    ```bash
    # Example using waitress
    waitress-serve --host 0.0.0.0 --port 5000 wsgi:app
    ```

-   **Debugging**: The services use Python's `logging` module. Check the console output for real-time logs. Persistent logs are stored in the `logs/` directory.
