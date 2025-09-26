# Telegram Bot Manager

## Overview
The Telegram Bot Manager is a system designed to manage multiple Telegram bots for various clients. Each client can have multiple bots running 24/7, allowing for independent management and interaction with each bot. This project provides a web interface and API for easy bot management.

## Features
- Manage multiple Telegram bots for each client.
- Start and stop bots independently.
- Monitor bot status and interactions.
- Webhook management for real-time updates.
- User-friendly dashboard for clients to interact with their bots.

## Project Structure
```
telegram-bot-manager
├── src
│   ├── app.py                # Entry point of the application
│   ├── models                # Contains data models
│   │   ├── client.py         # Client model
│   │   ├── bot.py            # Bot model
│   │   └── payment.py        # Payment model
│   ├── services              # Business logic services
│   │   ├── bot_manager.py    # Manages bot lifecycle
│   │   ├── client_service.py  # Handles client operations
│   │   └── webhook_service.py # Manages webhook interactions
│   ├── api                   # API routes and middleware
│   │   ├── routes            # API route definitions
│   │   ├── middleware.py      # Middleware functions
│   ├── bot_runners           # Bot runners for Telegram bots
│   ├── database              # Database connection and migrations
│   ├── utils                 # Utility functions and classes
│   └── templates             # HTML templates for the dashboard
├── tests                     # Unit tests for the application
├── config                    # Configuration settings
├── requirements.txt          # Project dependencies
├── docker-compose.yml        # Docker configurations
├── Dockerfile                # Docker image build instructions
├── .env.example              # Example environment variables
├── .gitignore                # Git ignore file
└── README.md                 # Project documentation
```

## Installation
1. Clone the repository:
   ```
   git clone <repository-url>
   cd telegram-bot-manager
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up the environment variables by copying `.env.example` to `.env` and filling in the necessary values.

4. Run the application:
   ```
   python src/app.py
   ```

## Usage
- Access the web dashboard to manage your bots.
- Use the API endpoints to programmatically manage clients and bots.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.