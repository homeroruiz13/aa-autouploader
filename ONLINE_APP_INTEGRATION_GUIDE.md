# Online App Integration Guide
## Complete Event Documentation for Real-Time Progress Tracking

Your online app will receive these Socket.IO events from the enhanced local process listener through ngrok:

---

## 📊 1. Progress Updates (`progressUpdate`)

**Event Name:** `progressUpdate`

**When Triggered:** At key milestones during processing

**Data Structure:**
```javascript
{
  percent: Number,    // Progress percentage (0-100)
  message: String     // Human-readable status message
}
```

**Complete Timeline of Progress Updates:**

### Initialization (0-10%)
```javascript
{ percent: 0, message: 'Initializing process' }
{ percent: 2, message: 'Creating directories' }
{ percent: 5, message: 'Directories created, saving CSV data' }
{ percent: 10, message: 'Starting image download and processing' }
```

### Image Processing Phase (15-65%)
```javascript
{ percent: 15, message: 'Downloading original image' }
{ percent: 20, message: 'Image downloaded and saved' }
{ percent: 25, message: 'Created tiled version' }
{ percent: 30, message: 'Uploaded to S3' }
{ percent: 35, message: 'Found Photoshop, starting processing' }
{ percent: 40, message: 'Starting Photoshop processing' }
{ percent: 60, message: 'Photoshop processing complete' }
{ percent: 65, message: 'Image processing complete' }
```

### PDF Generation Phase (70-92%)
```javascript
{ percent: 70, message: 'Starting PDF generation' }
{ percent: 70, message: 'Generating wrapping paper PDFs' }
{ percent: 75, message: 'Processing wrapping paper designs' }
{ percent: 80, message: 'Generating tablerunner PDFs' }
{ percent: 85, message: 'Processing tablerunner designs' }
{ percent: 90, message: 'PDF generation complete' }
{ percent: 92, message: 'PDFs uploaded to S3' }
```

### Shopify Update Phase (95-100%)
```javascript
{ percent: 95, message: 'Updating Shopify products' }
{ percent: 100, message: 'All processing complete' }
```

**Frontend Implementation Example:**
```javascript
socket.on('progressUpdate', (data) => {
    // Update progress bar
    document.getElementById('progress-bar').style.width = data.percent + '%';
    document.getElementById('progress-text').textContent = data.percent + '%';
    
    // Update status message
    document.getElementById('status-message').textContent = data.message;
    
    // Optional: Add progress history
    addToProgressHistory(data.percent, data.message);
});
```

---

## 📝 2. Process Logs (`processLog`)

**Event Name:** `processLog`

**When Triggered:** For every significant log line from Python scripts and system operations

**Data Structure:**
```javascript
String  // Direct log message
```

**Types of Logs You'll Receive:**

### System Logs
```javascript
"Start process request received"
"CSV data saved to D:\\Uploader Transfer\\aa-auto\\printpanels\\csv\\meta_file_list.csv"
"Starting Image Processing..."
"Image processing completed successfully"
"Starting PDF Generation..."
"PDF generation completed successfully"
```

### Python Script Logs
```javascript
// From images.py
"Image Processing: Processing CSV: D:\\...\\meta_file_list.csv"
"Image Processing: Using CSV delimiter: ,"
"Image Processing: Downloaded image from https://compoundfoundry.s3..."
"Image Processing: Tiled image saved to D:\\...\\image_tiled.png"
"Image Processing: Uploaded to https://aspenarlo.s3..."
"Image Processing: Found Photoshop at: C:\\Program Files\\Adobe\\..."
"Image Processing: Starting Photoshop JSX processing"
"Image Processing: PHOTOSHOP_COMPLETE"

// From illustrator_process.py
"PDF Generation: WRAPPING PAPER PDF GENERATOR"
"PDF Generation: Processing wrapping paper: ProductName"
"PDF Generation: TABLERUNNER PDF GENERATOR"
"PDF Generation: Processing tablerunner: ProductName"
"PDF Generation: PDF generation completed successfully"

// From process_products.py (if exists)
"Shopify Update: Starting Shopify image/metafield update..."
"Shopify Update: Processing product: ProductName"
"Shopify Update: {\"status\":\"processing\"}"
"Shopify Update: {\"status\":\"complete\"}"
```

### Error Logs
```javascript
"ERROR - Image Processing: Image not found for variant: AA123456"
"ERROR - PDF Generation: Failed to generate PDF for product"
"WARNING - Image Processing: Low resolution image detected"
```

**Frontend Implementation Example:**
```javascript
socket.on('processLog', (logLine) => {
    // Add to log display
    const logContainer = document.getElementById('log-container');
    const logEntry = document.createElement('div');
    
    // Style based on log type
    if (logLine.includes('ERROR')) {
        logEntry.className = 'log-error';
    } else if (logLine.includes('WARNING')) {
        logEntry.className = 'log-warning';
    } else {
        logEntry.className = 'log-info';
    }
    
    logEntry.textContent = new Date().toLocaleTimeString() + ' - ' + logLine;
    logContainer.appendChild(logEntry);
    
    // Auto-scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
});
```

---

## ✅ 3. Process Completion (`processComplete`)

**Event Name:** `processComplete`

**When Triggered:** When processing finishes (success or failure)

**Data Structure:**
```javascript
{
  success: Boolean,   // true if successful, false if failed
  error: String|null  // Error message if failed, null if successful
}
```

**Success Example:**
```javascript
{
  success: true,
  error: null
}
```

**Failure Examples:**
```javascript
{
  success: false,
  error: "Image Processing failed with exit code 1"
}

{
  success: false,
  error: "Python script exited with code 1: Image not found for any variant of: AA848519"
}

{
  success: false,
  error: "Failed to start Image Processing: Python executable not found"
}
```

**Frontend Implementation Example:**
```javascript
socket.on('processComplete', (data) => {
    if (data.success) {
        // Show success message
        showNotification('✅ Processing completed successfully!', 'success');
        
        // Hide progress bar
        document.getElementById('progress-container').style.display = 'none';
        
        // Show completion message
        document.getElementById('completion-status').innerHTML = 
            '<div class="success">✅ All processing complete!</div>';
            
        // Re-enable upload button
        document.getElementById('upload-btn').disabled = false;
        
    } else {
        // Show error message
        showNotification('❌ Processing failed: ' + data.error, 'error');
        
        // Show error in UI
        document.getElementById('completion-status').innerHTML = 
            '<div class="error">❌ Processing failed: ' + data.error + '</div>';
            
        // Re-enable upload button
        document.getElementById('upload-btn').disabled = false;
    }
});
```

---

## 🔗 4. Connection Events

### Connection Established
```javascript
socket.on('connect', () => {
    console.log('✅ Connected to local processor');
    // Show connection status
    document.getElementById('connection-status').textContent = 'Connected';
    document.getElementById('connection-status').className = 'connected';
});
```

### Connection Lost
```javascript
socket.on('disconnect', () => {
    console.log('❌ Disconnected from local processor');
    // Show disconnection status
    document.getElementById('connection-status').textContent = 'Disconnected';
    document.getElementById('connection-status').className = 'disconnected';
});
```

---

## 🎨 Complete Frontend Implementation Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Real-Time Image Processing</title>
    <style>
        .progress-container {
            width: 100%;
            background-color: #f0f0f0;
            border-radius: 10px;
            margin: 20px 0;
        }
        
        .progress-bar {
            height: 30px;
            background-color: #4CAF50;
            border-radius: 10px;
            text-align: center;
            line-height: 30px;
            color: white;
            transition: width 0.3s ease;
        }
        
        .log-container {
            height: 300px;
            overflow-y: scroll;
            border: 1px solid #ccc;
            padding: 10px;
            background-color: #f9f9f9;
            font-family: monospace;
        }
        
        .log-error { color: red; }
        .log-warning { color: orange; }
        .log-info { color: black; }
        
        .connected { color: green; }
        .disconnected { color: red; }
    </style>
</head>
<body>
    <h1>Image Processing Dashboard</h1>
    
    <!-- Connection Status -->
    <div>Status: <span id="connection-status" class="disconnected">Connecting...</span></div>
    
    <!-- Upload Form -->
    <form id="upload-form">
        <textarea id="csv-data" placeholder="Paste CSV data here..."></textarea>
        <button type="submit" id="upload-btn">Upload & Process Images</button>
    </form>
    
    <!-- Progress Display -->
    <div id="progress-container" class="progress-container" style="display: none;">
        <div id="progress-bar" class="progress-bar" style="width: 0%;">0%</div>
    </div>
    <div id="status-message"></div>
    <div id="completion-status"></div>
    
    <!-- Log Display -->
    <h3>Processing Logs</h3>
    <div id="log-container" class="log-container"></div>
    
    <script src="/socket.io/socket.io.js"></script>
    <script>
        const socket = io();
        
        // Connection events
        socket.on('connect', () => {
            document.getElementById('connection-status').textContent = 'Connected';
            document.getElementById('connection-status').className = 'connected';
        });
        
        socket.on('disconnect', () => {
            document.getElementById('connection-status').textContent = 'Disconnected';
            document.getElementById('connection-status').className = 'disconnected';
        });
        
        // Progress updates
        socket.on('progressUpdate', (data) => {
            const progressBar = document.getElementById('progress-bar');
            const statusMessage = document.getElementById('status-message');
            
            progressBar.style.width = data.percent + '%';
            progressBar.textContent = data.percent + '%';
            statusMessage.textContent = data.message;
            
            // Show progress container when processing starts
            if (data.percent > 0) {
                document.getElementById('progress-container').style.display = 'block';
            }
        });
        
        // Process logs
        socket.on('processLog', (logLine) => {
            const logContainer = document.getElementById('log-container');
            const logEntry = document.createElement('div');
            
            if (logLine.includes('ERROR')) {
                logEntry.className = 'log-error';
            } else if (logLine.includes('WARNING')) {
                logEntry.className = 'log-warning';
            } else {
                logEntry.className = 'log-info';
            }
            
            logEntry.textContent = new Date().toLocaleTimeString() + ' - ' + logLine;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        });
        
        // Process completion
        socket.on('processComplete', (data) => {
            const completionStatus = document.getElementById('completion-status');
            const uploadBtn = document.getElementById('upload-btn');
            
            if (data.success) {
                completionStatus.innerHTML = '<div style="color: green;">✅ Processing completed successfully!</div>';
            } else {
                completionStatus.innerHTML = '<div style="color: red;">❌ Processing failed: ' + data.error + '</div>';
            }
            
            uploadBtn.disabled = false;
            uploadBtn.textContent = 'Upload & Process Images';
        });
        
        // Form submission
        document.getElementById('upload-form').addEventListener('submit', (e) => {
            e.preventDefault();
            
            const csvData = document.getElementById('csv-data').value;
            const uploadBtn = document.getElementById('upload-btn');
            
            if (!csvData.trim()) {
                alert('Please enter CSV data');
                return;
            }
            
            // Reset UI
            document.getElementById('progress-container').style.display = 'none';
            document.getElementById('progress-bar').style.width = '0%';
            document.getElementById('status-message').textContent = '';
            document.getElementById('completion-status').innerHTML = '';
            document.getElementById('log-container').innerHTML = '';
            
            // Disable button and show processing
            uploadBtn.disabled = true;
            uploadBtn.textContent = 'Processing...';
            
            // Send to local processor
            socket.emit('startProcess', { csvData: csvData });
        });
    </script>
</body>
</html>
```

---

## 📋 Summary

Your online app will receive:

1. **📊 Real-time progress** (0-100%) with descriptive messages
2. **📝 Detailed logs** from every processing step  
3. **✅ Completion notifications** with success/error status
4. **🔗 Connection status** for local processor availability

This provides users with **complete visibility** into the processing workflow instead of blind countdown timers! 