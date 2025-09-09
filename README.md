# Sistem Absensi (Attendance System)

A modern Flask-based attendance system that integrates with ZK fingerprint devices and provides real-time data streaming, web interface, and API endpoints.

## Features

- **Real-time Data Streaming**: Automatic data capture from multiple ZK fingerprint devices
- **Web Dashboard**: Modern Bootstrap-based interface for viewing attendance logs
- **REST API**: Comprehensive API endpoints for integration with other systems
- **Database Support**: Both MySQL and SQL Server integration
- **Stored Procedures**: Support for complex attendance calculations
- **Export Functionality**: CSV export capabilities
- **Multi-device Support**: Handle multiple fingerprint devices simultaneously

## Project Structure

```
ABSENSI/
├── app/
│   ├── controllers/           # Request handlers (MVC Controllers)
│   │   ├── main_controller.py
│   │   └── api_controller.py
│   ├── models/               # Data layer (MVC Models)
│   │   ├── attendance.py
│   │   └── database.py
│   ├── services/             # Business logic layer
│   │   ├── attendance_service.py
│   │   └── streaming_service.py
│   ├── templates/            # Jinja2 templates (MVC Views)
│   │   ├── base.html
│   │   ├── index.html
│   │   └── users.html
│   ├── static/              # Static files (CSS, JS, images)
│   ├── routes.py            # URL routing and blueprints
│   └── __init__.py          # App factory
├── config/                  # Configuration files
│   ├── config.py           # Environment-based configuration
│   └── database.py         # Database connection management
├── scripts/                # Standalone scripts
│   ├── streaming_data.py   # Real-time data streaming
│   ├── automatic_update.py # Automatic FPLog updates
│   └── sync_attendance.py  # Manual sync utilities
├── tests/                  # Unit and integration tests
├── requirements.txt        # Python dependencies
├── run.py                 # Application entry point
└── README.md              # Project documentation
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ABSENSI
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env file with your database and device configurations
   ```

5. **Set up databases:**
   - Create MySQL database for log storage
   - Create SQL Server database for attendance processing
   - Run necessary table creation scripts

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

- **Flask Settings**: Debug mode, host, port
- **MySQL Database**: Connection details for log storage
- **SQL Server Database**: Connection details for attendance processing
- **Device Settings**: Fingerprint device configurations

### Database Setup

The system requires two databases:

1. **MySQL**: For real-time log storage (`log_absensi`, `FPLog` tables)
2. **SQL Server**: For attendance processing (`attrecords`, `workinghourrecs` tables)

## Usage

### Running the Web Application

```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Running Data Streaming

```bash
python scripts/streaming_data.py
```

### Running Automatic Updates

```bash
python scripts/automatic_update.py
```

## API Endpoints

### Attendance Records

- `POST /api/attrecord` - Execute attendance record procedure
- `GET /api/attrecord` - Get attendance records with pagination

### Working Hours

- `POST /api/spjamkerja` - Execute working hours calculation
- `GET /api/spjamkerja` - Get working hours data
- `GET /api/jamkerja/summary` - Get working hours summary

### Streaming Control

- `POST /api/streaming/start` - Start data streaming
- `POST /api/streaming/stop` - Stop data streaming
- `GET /api/streaming/status` - Get streaming status

### Data Summary

- `GET /api/summary` - Get attendance data summary

## API Usage Examples

### Execute Attendance Procedure

```bash
curl -X POST http://localhost:5000/api/attrecord \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-01-01", "end_date": "2025-01-31"}'
```

### Get Attendance Data

```bash
curl "http://localhost:5000/api/attrecord?start_date=2025-01-01&end_date=2025-01-31&page=1&per_page=20"
```

### Start Data Streaming

```bash
curl -X POST http://localhost:5000/api/streaming/start
```

## Device Configuration

Configure your ZK fingerprint devices in `app/services/streaming_service.py`:

```python
self.devices = [
    {
        'name': '104',
        'ip': '10.163.3.21',
        'port': 4370,
        'password': 1234567
    },
    # Add more devices as needed
]
```

## Development

### Project Architecture

This project follows the **MVC (Model-View-Controller)** pattern with additional service layer:

- **Models**: Handle data operations and database interactions
- **Views**: Jinja2 templates for web interface
- **Controllers**: Handle HTTP requests and responses
- **Services**: Business logic and complex operations

### Adding New Features

1. **New API Endpoint**:
   - Add method to appropriate controller
   - Add route in `app/routes.py`
   - Add business logic to service layer
   - Add data operations to model layer

2. **New Web Page**:
   - Create template in `app/templates/`
   - Add controller method
   - Add route for the page

### Running Tests

```bash
pytest tests/
```

## Deployment

### Production Deployment

1. **Set environment to production:**
   ```bash
   export FLASK_ENV=production
   ```

2. **Use WSGI server:**
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

3. **Configure reverse proxy** (nginx, Apache)

4. **Set up process management** (systemd, supervisor)

## Troubleshooting

### Common Issues

1. **Database Connection Errors**:
   - Check database credentials in `.env`
   - Ensure database servers are running
   - Verify network connectivity

2. **Device Connection Errors**:
   - Check device IP addresses and ports
   - Verify device passwords
   - Ensure devices are accessible on network

3. **Permission Errors**:
   - Check database user permissions
   - Verify table access rights

### Logs

Application logs are printed to console. For production, configure proper logging to files.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact the development team or create an issue in the repository.
