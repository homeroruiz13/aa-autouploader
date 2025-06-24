# Enhanced Local Processor with Ngrok Integration

## Overview
This setup allows your local image processing workflow to send real-time progress updates and logs to your online app through ngrok. Instead of blind countdown timers, users will see exactly what's happening during processing.

## Key Components

### 1. Enhanced Local Process Listener (`local_process_listener.js`)
- Connects to your ngrok endpoint via Socket.IO
- Provides detailed progress tracking (0-100%)
- Emits real-time logs from Python scripts
- Parses Python output for meaningful milestones
- Handles errors gracefully

### 2. Event Types Sent to Online App

#### Progress Updates
```javascript
socket.emit('progressUpdate', { 
    percent: 45, 
    message: 'Starting Photoshop processing' 
});
```

#### Process Logs
```javascript
socket.emit('processLog', 'Image Processing: Downloaded image from S3');
```

#### Completion Events
```javascript
socket.emit('processComplete', { 
    success: true,
    error: null // or error message if failed
});
```

## How to Use

### Step 1: Start Your Local Process Listener
```bash
# Install dependencies (if not already done)
npm install

# Start the enhanced local processor
npm run listener
# OR
node local_process_listener.js
```

You should see:
```
🚀 Local process listener started. Waiting for connections...
📡 Connecting to: https://wp-upload.ngrok.app
✅ Local processor connected to ngrok: [socket-id]
```

### Step 2: Update Your Online App
Your online app needs to listen for these new events:

```javascript
// In your online app's client-side JavaScript
socket.on('progressUpdate', (data) => {
    // Update progress bar
    updateProgressBar(data.percent);
    // Update status message
    updateStatusMessage(data.message);
});

socket.on('processLog', (logLine) => {
    // Add to log display
    appendToLogDisplay(logLine);
});

socket.on('processComplete', (data) => {
    if (data.success) {
        showSuccessMessage('Processing completed successfully!');
    } else {
        showErrorMessage(`Processing failed: ${data.error}`);
    }
});
```

### Step 3: Test the Integration
```bash
# Test that your online app receives updates
node test_online_receiver.js
```

## Progress Milestones

The system tracks these key milestones:

### Image Processing (0-65%)
- **15%**: Downloading original image
- **20%**: Image downloaded and saved
- **25%**: Created tiled version
- **30%**: Uploaded to S3
- **35%**: Found Photoshop, starting processing
- **40%**: Starting Photoshop processing
- **60%**: Photoshop processing complete
- **65%**: Image processing complete

### PDF Generation (70-92%)
- **70%**: Generating wrapping paper PDFs
- **75%**: Processing wrapping paper designs
- **80%**: Generating tablerunner PDFs
- **85%**: Processing tablerunner designs
- **90%**: PDF generation complete
- **92%**: PDFs uploaded to S3

### Shopify Update (95-100%)
- **95%**: Updating Shopify products
- **100%**: All processing complete

## Error Handling

The system provides three levels of logging:
- **INFO**: Normal processing steps
- **WARNING**: Non-critical issues
- **ERROR**: Critical failures that stop processing

Errors are automatically sent to your online app with context about what failed.

## Customization

### Adding New Progress Milestones
Edit the `parseLogForProgress()` function in `local_process_listener.js`:

```javascript
function parseLogForProgress(logLine) {
    // Add your custom milestone detection
    if (logLine.includes('Your custom log message')) {
        return { percent: 50, message: 'Your custom milestone' };
    }
    
    // ... existing milestones
}
```

### Adjusting Python Script Detection
The system automatically detects these Python scripts:
- `images.py` - Image processing
- `illustrator_process.py` - PDF generation
- `process_products.py` - Shopify updates (optional)

### Connecting to Different Ngrok URLs
Update the `SERVER_URL` in `local_process_listener.js`:
```javascript
const SERVER_URL = "https://your-new-ngrok-url.ngrok.app";
```

## Troubleshooting

### Connection Issues
```bash
# Check if ngrok is running
curl https://wp-upload.ngrok.app/socket.io/

# Verify the local listener is connecting
node local_process_listener.js
```

### Python Script Errors
- Check that Python scripts exist in the expected locations
- Verify Python path is correct (line 10 in local_process_listener.js)
- Check that all required Python dependencies are installed

### Missing Progress Updates
- Verify your Python scripts output the expected log messages
- Check the `parseLogForProgress()` function for the exact strings to match
- Use the test script to verify events are being emitted

## Files Modified/Created

1. ✅ `local_process_listener.js` - Enhanced with progress tracking
2. ✅ `package.json` - Added socket.io-client dependency and npm script
3. ✅ `test_online_receiver.js` - Test script for online app integration
4. ✅ `SETUP_NGROK_INTEGRATION.md` - This documentation

## Next Steps

1. **Start the local listener** and verify connection to ngrok
2. **Update your online app** to listen for the new events
3. **Test with a real processing job** to see progress updates
4. **Customize progress milestones** based on your specific Python script outputs
5. **Add visual progress indicators** in your online app UI

The enhanced system provides much better user experience with real-time visibility into the processing workflow! 