// 🚀 ONLINE APP UPDATE GUIDE
// Add this code to your online app to work with enhanced server.js

// Connect to your ngrok URL (no change needed)
const socket = io('https://wp-upload.ngrok.app');

// ========================================
// 1. REAL-TIME PROGRESS (0-100%)
// ========================================
socket.on('progressUpdate', (data) => {
    console.log(`📊 Progress: ${data.percent}% - ${data.message}`);
    
    // Update your progress bar
    updateProgressBar(data.percent);
    
    // Update status message
    updateStatusMessage(data.message);
    
    // Update stage indicator
    updateStageIndicator(data.stage);
    
    // Example UI updates:
    // document.getElementById('progress-bar').style.width = data.percent + '%';
    // document.getElementById('status-text').textContent = data.message;
    // document.getElementById('stage-indicator').textContent = data.stage;
});

// ========================================
// 2. DETAILED LOGGING
// ========================================
socket.on('processLog', (data) => {
    console.log(`📝 [${data.type}] ${data.message}`);
    
    // Add to your log display
    addLogToDisplay(data.message, data.type);
    
    // Example: Color-coded logs
    const logColor = {
        'info': '#007bff',     // Blue
        'warning': '#ffc107',  // Yellow  
        'error': '#dc3545'     // Red
    };
    
    // Example UI update:
    // const logElement = document.createElement('div');
    // logElement.style.color = logColor[data.type];
    // logElement.textContent = `[${data.timestamp}] ${data.message}`;
    // document.getElementById('log-container').appendChild(logElement);
});

// ========================================
// 3. FINAL COMPLETION
// ========================================
socket.on('processComplete', (data) => {
    if (data.success) {
        console.log('✅ Processing completed successfully!');
        
        // Show success message
        showSuccessMessage('All processing completed!');
        
        // Display result data
        displayResults(data.data);
        
        // Example success UI:
        // document.getElementById('progress-container').style.display = 'none';
        // document.getElementById('success-container').style.display = 'block';
        // document.getElementById('download-links').innerHTML = generateDownloadLinks(data.data);
        
    } else {
        console.error('❌ Processing failed:', data.error);
        
        // Show error message
        showErrorMessage(data.error);
        
        // Example error UI:
        // document.getElementById('progress-container').style.display = 'none';
        // document.getElementById('error-container').style.display = 'block';
        // document.getElementById('error-message').textContent = data.error;
    }
});

// ========================================
// 4. START PROCESSING (NO CHANGE NEEDED)
// ========================================
// This trigger remains exactly the same:
function startProcessing(csvData) {
    socket.emit('startProcess', { csvData: csvData });
}

// ========================================
// 5. EXAMPLE UI UPDATE FUNCTIONS
// ========================================

function updateProgressBar(percent) {
    // Update your progress bar element
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
        progressBar.style.width = percent + '%';
        progressBar.textContent = percent + '%';
    }
}

function updateStatusMessage(message) {
    // Update your status message element
    const statusElement = document.getElementById('status-message');
    if (statusElement) {
        statusElement.textContent = message;
    }
}

function updateStageIndicator(stage) {
    // Update stage indicator (optional)
    const stageNames = {
        'initialization': 'Setting Up',
        'image_processing': 'Processing Images', 
        'data_processing': 'Processing Data',
        'pdf_generation': 'Creating PDFs',
        'shopify_update': 'Updating Shopify',
        'completed': 'Complete'
    };
    
    const stageElement = document.getElementById('current-stage');
    if (stageElement && stage) {
        stageElement.textContent = stageNames[stage] || stage;
    }
}

function addLogToDisplay(message, type) {
    // Add log entry to your log display
    const logContainer = document.getElementById('log-container');
    if (logContainer) {
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-${type}`;
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logContainer.appendChild(logEntry);
        
        // Auto-scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

function showSuccessMessage(message) {
    // Show your success UI
    alert('✅ ' + message); // Replace with your UI
}

function showErrorMessage(error) {
    // Show your error UI  
    alert('❌ Error: ' + error); // Replace with your UI
}

function displayResults(data) {
    // Display processing results
    console.log('Results:', data);
    
    // Example: Show download links
    // const downloadContainer = document.getElementById('download-links');
    // downloadContainer.innerHTML = `
    //     <h3>Processing Complete!</h3>
    //     <p>Download Directory: ${data.downloadDir}</p>
    //     <p>Output Directory: ${data.outputDir}</p>
    //     <p>Timestamp: ${data.timestamp}</p>
    // `;
}

// ========================================
// 6. OPTIONAL: GET PROCESS STATUS
// ========================================
function checkProcessStatus() {
    socket.emit('getProcessStatus');
}

socket.on('processStatusResponse', (status) => {
    console.log('Current process status:', status);
    // Use this for debugging or status displays
});

// ========================================
// 7. CONNECTION HANDLING
// ========================================
socket.on('connect', () => {
    console.log('🔌 Connected to enhanced server');
});

socket.on('disconnect', () => {
    console.log('🔌 Disconnected from server');
});

socket.on('connect_error', (error) => {
    console.error('❌ Connection failed:', error);
}); 