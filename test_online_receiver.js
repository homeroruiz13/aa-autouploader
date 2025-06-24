// Test script to simulate online app receiving updates from local processor
const { io } = require("socket.io-client");

// Connect to your ngrok endpoint (same as what the local processor connects to)
const socket = io("https://wp-upload.ngrok.app", {
    transports: ['websocket', 'polling'],
    upgrade: true,
    timeout: 20000,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});

console.log("🌐 Online app test client starting...");

socket.on('connect', () => {
    console.log('✅ Connected to ngrok endpoint:', socket.id);
    
    // Test trigger a process
    console.log('📤 Sending test process request...');
    socket.emit('startProcess', {
        csvData: "https://compoundfoundry.s3-us-east-2.amazonaws.com/wrappingpaper/new_uploads/AA848519.png,AA848519,wrapping-paper"
    });
});

socket.on('disconnect', () => {
    console.log('❌ Disconnected from ngrok endpoint');
});

// Listen for progress updates (NEW - these come from enhanced local processor)
socket.on('progressUpdate', (data) => {
    console.log(`📊 Progress: ${data.percent}% - ${data.message}`);
});

// Listen for detailed logs (NEW - these come from enhanced local processor)
socket.on('processLog', (logLine) => {
    console.log(`📝 Log: ${logLine}`);
});

// Listen for process completion (ENHANCED - now includes success/error info)
socket.on('processComplete', (data) => {
    if (data.success) {
        console.log('✅ Process completed successfully!');
    } else {
        console.log(`❌ Process failed: ${data.error}`);
    }
    console.log('🔄 Disconnecting test client...');
    socket.disconnect();
    process.exit(0);
});

// Keep the old event listeners for backward compatibility
socket.on('photoshopProgress', (data) => {
    console.log('🎨 Photoshop:', data.output?.trim());
});

socket.on('photoshopError', (data) => {
    console.log('🚨 Photoshop Error:', data.error?.trim());
});

socket.on('illustratorProgress', (data) => {
    console.log('📄 Illustrator:', data.output?.trim());
});

socket.on('illustratorError', (data) => {
    console.log('🚨 Illustrator Error:', data.error?.trim());
});

// Error handling
socket.on('connect_error', (error) => {
    console.error('❌ Connection error:', error.message);
});

// Keep alive
socket.on('ping', () => {
    socket.emit('pong');
});

setTimeout(() => {
    console.log('⏰ Test timeout reached, disconnecting...');
    socket.disconnect();
    process.exit(1);
}, 300000); // 5 minute timeout 