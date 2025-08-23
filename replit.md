# Overview

This is a French invoice generator web application built with Flask. The system allows users to upload Excel files containing client data and automatically generates PDF invoices in French. The application features a company settings management system where users can configure business details like company name, address, tax information, and default pricing. It processes Excel data to create professional invoices with French language support, including number-to-words conversion for amounts.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework
- **Flask-based MVC architecture** - Uses Flask as the primary web framework with template-based rendering
- **Template inheritance** - Implements Jinja2 templates with a base template for consistent UI
- **Bootstrap UI framework** - Uses Bootstrap with dark theme for responsive frontend design

## Database Layer
- **SQLAlchemy ORM** - Uses Flask-SQLAlchemy for database abstraction
- **Model-based data structure** - Company settings stored in CompanySettings model
- **Database flexibility** - Configured to support both SQLite (default) and PostgreSQL via environment variables
- **Connection management** - Implements connection pooling and health checks

## File Processing
- **Excel file handling** - Processes .xlsx and .xls files using pandas
- **Secure file uploads** - Implements file validation, secure filename handling, and size limits
- **Temporary file management** - Uses system temp directory for uploaded files

## PDF Generation
- **ReportLab integration** - Generates professional PDF invoices using ReportLab
- **French localization** - Includes number-to-words conversion in French
- **A4 format standard** - Uses standard A4 page size for invoice generation

## Application Structure
- **Modular design** - Separates models, main application logic, and entry point
- **Environment-based configuration** - Uses environment variables for sensitive settings
- **Logging system** - Implements comprehensive logging for debugging and monitoring

# External Dependencies

## Core Dependencies
- **Flask** - Web framework and routing
- **Flask-SQLAlchemy** - Database ORM and migrations
- **pandas** - Excel file processing and data manipulation
- **ReportLab** - PDF generation and document formatting
- **Werkzeug** - File upload security and utilities

## Frontend Dependencies
- **Bootstrap 5.3.2** - UI framework and responsive design
- **Font Awesome 6.0.0** - Icon library for enhanced UX
- **Custom CSS** - Additional styling for invoice-specific UI elements

## Database Support
- **SQLite** - Default database for development
- **PostgreSQL** - Production database option via DATABASE_URL environment variable

## File Format Support
- **Excel files** - .xlsx and .xls format processing
- **PDF output** - Professional invoice document generation

## Configuration
- **Environment variables** - SESSION_SECRET and DATABASE_URL for deployment flexibility
- **Temporary file system** - System temp directory for file upload processing