# YouTube Trend Analyzer

A real-time trending video analysis tool utilizing YouTube Data API v3. You can search for videos by specific keywords and analyze trends based on view velocity. Features a modern GUI interface based on PySide6 and Google Drive cloud synchronization capabilities.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Known Issues](#known-issues)
- [License](#license)

## Introduction

YouTube Trend Analyzer is a cross-platform desktop application that leverages YouTube Data API v3 to search for videos based on keywords and analyze trends by examining view velocity. It features a modern dark theme UI using PySide6, search history management through SQLite database, and cloud synchronization functionality via Google Drive.

## Features

- **Real-time Keyword Search**: Fast and accurate video search using YouTube Data API v3
- **Trend Analysis**: Real-time trend analysis based on view velocity (views/upload time)
- **Advanced Filtering**: Precise filtering by subscriber count, view count, video duration, and other criteria
- **Shorts-only Search**: Separate search for YouTube Shorts videos under 1 minute
- **Database Management**: Automatic management of search history and exclusion lists via SQLite
- **Cloud Synchronization**: Automatic data backup/restore through Google Drive API
- **Modern UI**: Responsive dark theme interface based on PySide6
- **Data Export**: Export analysis results to text files

## Project Overview

This project is designed as a trend analysis tool for YouTube content creators and marketers. For optimal performance, the following system specifications are recommended:

### System Requirements

| Category         | Specification                              |
| ---------------- | ------------------------------------------ |
| Operating System | Windows 10/11, macOS 10.14+, Ubuntu 18.04+ |
| Python           | 3.8 or higher                              |
| Memory           | 4GB RAM or higher                          |
| Storage          | 500MB or more                              |
| Network          | Internet connection required               |

### Frameworks and Dependencies

| Framework/Library        | Version |
| ------------------------ | ------- |
| Python                   | 3.8+    |
| PySide6                  | ^6.5.0  |
| google-api-python-client | ^2.86.0 |
| google-auth-oauthlib     | ^1.0.0  |
| requests                 | ^2.31.0 |
| qtawesome                | ^1.2.3  |

### Project Structure

```
youtube_searcher/                          # Project root directory
├── main.py                               # Main application entry point
├── constants.py                          # Constants and UI stylesheet definitions
├── database.py                           # SQLite database management module
├── workers.py                            # Background task processing (API calls, sync)
│   ├── SearchWorker                      # YouTube API search worker
│   ├── SyncWorker                        # Google Drive sync worker
├── widgets.py                            # Custom UI widget components
│   ├── YouTubeSearchApp                  # Main application class
│   ├── FilterDialog                      # Filter settings dialog
│   ├── SettingsDialog                    # Settings dialog
├── requirements.txt                      # Python dependency package list
├── pyproject.toml                        # uv project configuration file
├── credentials.json                      # Google Drive API auth file (user-provided)
├── icons/                                # Application icons
│   ├── youtube.ico                       # Windows icon
│   ├── youtube.icns                      # macOS icon
└── README.md                             # Project documentation
```

## Installation

Follow these steps to install YouTube Trend Analyzer in your local environment.

### Prerequisites

Ensure the following are installed on your machine:

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- Git

### Setting Up the App

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd youtube_searcher
   ```

2. **Install dependencies**:

   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Start the app**:

   ```bash
   # Using uv
   uv run python main.py

   # Or regular Python
   python main.py
   ```

## Usage

Once the app is running, you'll be able to interact with the YouTube Trend Analyzer:

1. **API Key Setup**: Add your YouTube Data API v3 key in the application settings
2. **Keyword Search**: Enter keywords in the search field and set filter conditions
3. **Start Analysis**: Click "Start Analysis" to execute trend analysis
4. **View Results**: Check trending video list sorted by view velocity
5. **Export Data**: Save analysis results to text files

### Database Storage Location

The application automatically creates and manages a SQLite database file (`.youtube_analysis.db`) to store:
- Search history and analysis results
- API keys and settings
- Google Drive authentication tokens
- Video exclusion lists

**Storage locations by platform:**

| Platform | Database File Location |
|----------|------------------------|
| **Development** | Current working directory |
| **macOS (Built App)** | `~/Documents/.youtube_analysis.db` |
| **Windows (Built App)** | `%USERPROFILE%\Documents\.youtube_analysis.db` |
| **Linux (Built App)** | `~/Documents/.youtube_analysis.db` |

**⚠️ Security Notice**: The database file contains sensitive authentication information including Google Drive OAuth tokens and API keys. Do not share this file with others or store it in public repositories.

### Advanced Features

- **Shorts-only Search**: Filter videos under 1 minute using "Shorts Only" checkbox
- **Exclusion List Management**: Add unwanted channels or videos to exclusion list
- **Cloud Sync**: Enable Google Drive synchronization for data backup/restore

## Development

To work on the app or contribute to its development:

### Running the development environment

Use `uv run python main.py` to start the application in development mode for easy development.

### Building the app for production

To build the app for production, run the following command:

**Windows**:

```bash
uv add pyinstaller
uv run pyinstaller --onefile --windowed --name "YouTube-Trend-Analyzer" --icon=icons/youtube.ico main.py
```

**macOS**:

```bash
uv add pyinstaller
uv run pyinstaller --onefile --windowed --name "YouTube-Trend-Analyzer" --icon=icons/youtube.icns main.py
```

## Known Issues

- **API Quota Exceeded**: YouTube Data API v3 has daily quota limitations that may restrict usage
- **Authentication Expiry**: OAuth tokens may expire during Google Drive sync, requiring re-authentication
- **Performance Issues**: API response delays may occur during bulk searches on slower connections
- **UI Rendering**: Some low-spec systems may experience dark theme rendering delays

## License

This project is distributed under the MIT License.

---

**⚠️ Notice**: YouTube Data API v3 has daily quota limitations. Excessive usage may restrict API access for 24 hours.
