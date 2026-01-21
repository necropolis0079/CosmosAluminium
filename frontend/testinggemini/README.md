# CV Processing Testing UI

A simple, browser-based interface for testing the CV processing pipeline.

## Quick Start

### 1. Start the local server

```bash
cd D:\CA\repo\frontend\testing
python serve.py
```

Or using Python module:
```bash
python -m http.server 3000
```

### 2. Open in browser

Navigate to: `http://localhost:3000`

## Features

### CV Upload
- Drag & drop or click to upload
- Supported formats: PDF, DOCX, JPG, PNG
- Maximum file size: 10MB

### Progress Monitor
- Real-time status updates (polls every 2 seconds)
- Visual progress bar with percentage
- Step-by-step status indicators:
  1. Uploading
  2. Queued
  3. Extracting (text/OCR)
  4. Parsing (Claude AI)
  5. Mapping (taxonomy)
  6. Storing (PostgreSQL)
  7. Indexing (OpenSearch)
  8. Completed

### Query Interface
- Natural language queries in Greek or English
- Example queries:
  - "find candidates with CNC experience"
  - "show welders in Thessaloniki"
  - "who has ISO certifications?"
- Results displayed in tabular format
- View generated SQL (expandable)

## Configuration

Edit `app.js` to update the API endpoint:

```javascript
const CONFIG = {
    API_BASE: 'https://iw9oxe3w4b.execute-api.eu-north-1.amazonaws.com/v1',
    POLL_INTERVAL: 2000,  // ms
    MAX_POLL_TIME: 300000, // 5 minutes
};
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/test/upload` | POST | Get presigned S3 URL |
| `/test/status/{id}` | GET | Poll processing status |
| `/test/query` | POST | Execute NL query |

## Files

```
frontend/testing/
├── index.html      # Main HTML page
├── styles.css      # CSS styling
├── app.js          # JavaScript logic
├── serve.py        # Local server script
└── README.md       # This file
```

## Deployment

### Option A: Local only
Use `serve.py` for local testing.

### Option B: S3 Static Hosting
```bash
aws s3 cp . s3://your-bucket/ --recursive
```

### Option C: Amplify
Connect to GitLab for automatic deployment.

## Security Note

This UI is for **testing only**:
- No authentication required on /test/* routes
- Direct S3 uploads via presigned URLs
- No rate limiting on test endpoints

For production, use the authenticated `/query` endpoint with Cognito JWT.
