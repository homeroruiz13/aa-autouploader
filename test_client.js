const { io } = require("socket.io-client");

// Connect to the local server
const socket = io("http://localhost:3002");

socket.on("connect", () => {
  console.log("Connected to server");
  
  // Test data for AA848519
  const testData = {
    csvData: "https://compoundfoundry.s3-us-east-2.amazonaws.com/wrappingpaper/new_uploads/AA848519.png,AA848519,wrapping-paper"
  };
  
  console.log("Sending test data:", testData);
  socket.emit("startProcess", testData);
});

// Listen for processing status updates
socket.on("processStatus", (data) => {
  console.log(`Processing status - Stage: ${data.stage}, Progress: ${data.progress}%`);
  console.log("Message:", data.message);
});

// Listen for image processing updates
socket.on("imageProcessingComplete", (data) => {
  console.log("Image processing complete:", data);
});

socket.on("imageProcessingError", (data) => {
  console.error("Image processing error:", data);
});

// Listen for PDF generation updates
socket.on("pdfGenerationComplete", (data) => {
  console.log("PDF generation complete:", data);
});

socket.on("pdfGenerationError", (data) => {
  console.error("PDF generation error:", data);
});

// Listen for final completion
socket.on("processComplete", (data) => {
  console.log("All processing complete:", data);
  console.log("Output directories:", {
    downloadDir: data.data.downloadDir,
    outputDir: data.data.outputDir,
    printpanelsOutputDir: data.data.printpanelsOutputDir,
    csvPath: data.data.csvPath
  });
  // Close the connection after completion
  socket.disconnect();
  process.exit(0);
});

// Listen for any errors
socket.on("processError", (data) => {
  console.error("Process error:", data);
  socket.disconnect();
  process.exit(1);
});

// Handle disconnection
socket.on("disconnect", () => {
  console.log("Disconnected from server");
});

console.log("Test client started..."); 