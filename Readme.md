# Google oAuth Assignment 

## Overview
This project is a comprehensive backend template that integrates the following technologies using Django:

- **Google OAuth 2.0 API** for user authentication.
- **WebSocket** for real-time communication between users.

## Features

### 1. Google Authentication Flow
- Endpoint to initiate the Google OAuth authentication flow.
- Callback URL to receive authentication data from Google.
- Returns authentication data in response.

### 2. Google Drive Integration
- Endpoint to connect a user's Google Drive.
- Functionality to upload files to Google Drive.
- Option to fetch and download files locally from Google Drive.

### 3. WebSocket for Real-Time User Chat
- WebSocket implementation for real-time chat between two preconfigured users.
- Messages are sent and received instantly.

## Installation and Setup
### Prerequisites
- Python 3.x
- Django
- PostgreSQL or SQLite (for database)
- Google OAuth Credentials (Client ID, Client Secret)

### Setup Instructions
1. **Clone the repository**
   ```sh
   git clone https://github.com/yourusername/backend-dev-assignment.git
   cd backend-dev-assignment
   ```
2. **Create and activate a virtual environment**
   ```sh
   python -m venv venv
   source venv/bin/activate  
   venv\Scripts\activate  
   ```
3. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
4. **Set up environment variables**
   Create a `.env` file and add the following:
   ```env
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback/
   SECRET_KEY=your_django_secret_key
   ```
5. **Run migrations**
   ```sh
   python manage.py migrate
   ```
6. **Start the Django development server**
   ```sh
   python manage.py runserver
   ```

## API Endpoints

### Google Authentication
- **Initiate Authentication**: `GET /google/login/`
- **Callback URL**: `GET /google/callback/`

### Google Drive Integration
- **Connect Google Drive**: `POST /drive/connect/`
- **Upload File to Drive**: `POST /drive/upload/`
- **Fetch Files from Drive**: `GET /drive/files/`
- **Download File from Drive**: `GET /drive/download/<file_id>/`

### WebSocket Chat
- **WebSocket Connection**: `ws://localhost:8000/ws/chat/`
- **Real-time messaging between two users**

### Deployment
- **Deployment Link**: [https://google-oauth-django.onrender.com](https://google-oauth-django.onrender.com)
