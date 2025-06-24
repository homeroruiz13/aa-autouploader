require('dotenv').config();
const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const AWS = require('aws-sdk');
const fetch = require('node-fetch');

// Configure AWS
AWS.config.update({
    region: process.env.AWS_REGION || 'us-east-2',
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
});

const s3 = new AWS.S3();

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Serve static files from the static directory
app.use(express.static('static'));
app.use(express.json({ limit: '50mb' }));

// Store active processes
const activeProcesses = new Map();

// Enhanced Progress Tracking Functions
function emitProgress(socket, percent, message, stage = null) {
    const progressData = {
        percent: Math.round(percent),
        message: message,
        timestamp: new Date().toISOString()
    };
    
    if (stage) {
        progressData.stage = stage;
    }
    
    console.log(`📊 Progress: ${percent}% - ${message}`);
    
    if (socket) {
        socket.emit('progressUpdate', progressData);
    }
    
    // Update active process
    const process = activeProcesses.get(socket?.id);
    if (process) {
        process.progress = percent;
        process.lastMessage = message;
        process.lastUpdate = new Date();
        if (stage) process.stage = stage;
    }
}

function emitLog(socket, message, type = 'info') {
    const logData = {
        message: message,
        type: type,
        timestamp: new Date().toISOString()
    };
    
    console.log(`📝 Log [${type}]: ${message}`);
    
    if (socket) {
        socket.emit('processLog', logData);
    }
}

function emitComplete(socket, success, error = null, data = null) {
    const completeData = {
        success: success,
        timestamp: new Date().toISOString()
    };
    
    if (error) {
        completeData.error = error;
    }
    
    if (data) {
        completeData.data = data;
    }
    
    console.log(`🎯 Complete: Success=${success}${error ? `, Error=${error}` : ''}`);
    
    if (socket) {
        socket.emit('processComplete', completeData);
    }
    
    // Update active process
    const process = activeProcesses.get(socket?.id);
    if (process) {
        process.status = success ? 'completed' : 'failed';
        process.endTime = new Date();
        if (error) process.error = error;
        if (data) process.resultData = data;
    }
}

function parseLogForProgress(output, currentStage) {
    let progressInfo = { percent: null, stage: currentStage };
    
    // Parse different types of progress indicators
    if (output.includes('Starting download') || output.includes('Downloading')) {
        progressInfo.percent = 15;
        progressInfo.stage = 'downloading';
    } else if (output.includes('PHOTOSHOP_START') || output.includes('Opening Photoshop')) {
        progressInfo.percent = 25;
        progressInfo.stage = 'photoshop_processing';
    } else if (output.includes('PHOTOSHOP_COMPLETE') || output.includes('Photoshop processing complete')) {
        progressInfo.percent = 55;
        progressInfo.stage = 'uploading_to_s3';
    } else if (output.includes('S3_UPLOAD_COMPLETE') || output.includes('Uploaded to S3')) {
        progressInfo.percent = 65;
        progressInfo.stage = 'pdf_generation';
    } else if (output.includes('PDF_START') || output.includes('Starting PDF generation')) {
        progressInfo.percent = 70;
        progressInfo.stage = 'wrapping_paper_pdf';
    } else if (output.includes('PDF_WRAPPING_COMPLETE') || output.includes('Wrapping paper PDF complete')) {
        progressInfo.percent = 80;
        progressInfo.stage = 'tablerunner_pdf';
    } else if (output.includes('PDF_TABLERUNNER_COMPLETE') || output.includes('Tablerunner PDF complete')) {
        progressInfo.percent = 90;
        progressInfo.stage = 'shopify_update';
    } else if (output.includes('SHOPIFY_UPDATE_START') || output.includes('Starting Shopify update')) {
        progressInfo.percent = 95;
        progressInfo.stage = 'shopify_update';
    } else if (output.includes('SHOPIFY_UPDATE_COMPLETE') || output.includes('Shopify update complete')) {
        progressInfo.percent = 100;
        progressInfo.stage = 'completed';
    }
    
    return progressInfo;
}

// Enhanced Python script runner with detailed progress tracking
function runPythonScriptWithProgress(scriptPath, args, socket, stage) {
    return new Promise((resolve, reject) => {
        const scriptName = path.basename(scriptPath, '.py');
        emitLog(socket, `Starting ${scriptName} script...`, 'info');
        
        const pythonPath = "C:\\Program Files\\Python313\\python.exe";
        
        const pythonProcess = spawn(pythonPath, [scriptPath, ...args], {
            env: { 
                ...process.env, 
                PYTHONUNBUFFERED: '1',
                AWS_ACCESS_KEY_ID: process.env.AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY: process.env.AWS_SECRET_ACCESS_KEY,
                AWS_REGION: process.env.AWS_REGION || 'us-east-2'
            }
        });
        
        let stdoutData = '';
        let stderrData = '';
        let currentProgress = 0;

        pythonProcess.stdout.on('data', (data) => {
            const output = data.toString().trim();
            if (!output) return;
            
            stdoutData += output + '\n';
            
            // Parse for progress
            const progressInfo = parseLogForProgress(output, stage);
            if (progressInfo.percent !== null && progressInfo.percent > currentProgress) {
                currentProgress = progressInfo.percent;
                emitProgress(socket, progressInfo.percent, output, progressInfo.stage);
            } else {
                emitLog(socket, output, 'info');
            }
        });

        pythonProcess.stderr.on('data', (data) => {
            const output = data.toString().trim();
            if (!output) return;
            
            stderrData += output + '\n';
            
            // Check if this is an actual error or just logging
            if (output.includes('ERROR -') || output.includes('CRITICAL -')) {
                emitLog(socket, output, 'error');
            } else if (output.includes('WARNING -')) {
                emitLog(socket, output, 'warning');
            } else {
                // Check for progress indicators in stderr too
                const progressInfo = parseLogForProgress(output, stage);
                if (progressInfo.percent !== null && progressInfo.percent > currentProgress) {
                    currentProgress = progressInfo.percent;
                    emitProgress(socket, progressInfo.percent, output, progressInfo.stage);
                } else {
                    emitLog(socket, output, 'info');
                }
            }
        });

        pythonProcess.on('error', (error) => {
            const errorMsg = `Failed to start ${scriptName}: ${error.message}`;
            emitLog(socket, errorMsg, 'error');
            reject(new Error(errorMsg));
        });

        pythonProcess.on('close', (code) => {
            emitLog(socket, `${scriptName} script exited with code ${code}`, code === 0 ? 'info' : 'warning');
            
            if (code === 0) {
                resolve({ stdout: stdoutData, stderr: stderrData });
            } else {
                const hasErrors = stderrData.split('\n').some(line => 
                    line.includes('ERROR -') || line.includes('CRITICAL -')
                );
                if (hasErrors) {
                    reject(new Error(`${scriptName} exited with code ${code}\nStderr: ${stderrData}`));
                } else {
                    resolve({ stdout: stdoutData, stderr: stderrData });
                }
            }
        });
    });
}

// Function to parse CSV data
function parseCSVData(csvData) {
    try {
        console.log('Parsing CSV data:', csvData);
        const lines = csvData.split('\n').filter(line => line.trim());
        return lines.map(line => {
            const [url, name, ...tags] = line.split(',').map(item => item.trim());
            return { url, name, tags: tags.filter(tag => tag) };
        });
    } catch (error) {
        console.error('Error parsing CSV data:', error);
        throw new Error(`Failed to parse CSV: ${error.message}`);
    }
}

// Function to generate unique product ID
function generateProductId() {
    const id = Math.floor(100000 + Math.random() * 900000);
    return `AA${id}`;
}

// Function to download image from S3
async function downloadImageFromS3(url, localPath) {
    try {
        console.log(`Downloading image from ${url} to ${localPath}`);
        const response = await fetch(url);
        const buffer = await response.buffer();
        fs.writeFileSync(localPath, buffer);
        console.log(`Successfully downloaded image to ${localPath}`);
        return localPath;
    } catch (error) {
        console.error('Error downloading image:', error);
        throw new Error(`Failed to download image: ${error.message}`);
    }
}

// Enhanced Function to process images and generate PDFs with detailed progress tracking
async function processImages(csvData, socket) {
    try {
        emitProgress(socket, 0, 'Initializing processing workflow...', 'initialization');
        emitLog(socket, 'Starting image processing with enhanced progress tracking', 'info');
        
        // Create timestamped directories
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const downloadDir = path.join(__dirname, 'Download', timestamp);
        const outputDir = path.join(__dirname, 'Output', timestamp);
        const printpanelsDir = path.join(__dirname, 'printpanels');
        const printpanelsOutputDir = path.join(printpanelsDir, 'output', timestamp);
        const csvDir = path.join(printpanelsDir, 'csv');
        
        emitProgress(socket, 5, 'Creating output directories...', 'initialization');
        
        // Ensure directories exist
        [downloadDir, outputDir, printpanelsOutputDir, csvDir].forEach(dir => {
            fs.mkdirSync(dir, { recursive: true });
        });

        // Save CSV data for both processes
        const csvPath = path.join(csvDir, 'meta_file_list.csv');
        fs.writeFileSync(csvPath, csvData);
        
        emitProgress(socket, 10, 'Starting image processing script...', 'image_processing');

        // Run Python script for image processing
        const imageScriptPath = path.join(__dirname, 'Scripts', 'images.py');
        emitLog(socket, `Executing: ${path.basename(imageScriptPath)}`, 'info');
        
        try {
            // Pass the CSV data directly to the Python script
            const { stdout: imageStdout } = await runPythonScriptWithProgress(imageScriptPath, [csvData], socket, 'image_processing');

            emitLog(socket, 'Image processing script completed successfully', 'info');

            // --------------------------------------------------------------
            // Extract processed product JSON from the images.py output
            // --------------------------------------------------------------
            let productListPath = null;
            try {
                emitProgress(socket, 67, 'Processing output data...', 'data_processing');
                
                const startTag = 'JSON_OUTPUT_START';
                const endTag = 'JSON_OUTPUT_END';
                const startIdx = imageStdout.indexOf(startTag);
                const endIdx = imageStdout.indexOf(endTag);

                if (startIdx !== -1 && endIdx !== -1 && endIdx > startIdx) {
                    const jsonString = imageStdout
                        .substring(startIdx + startTag.length, endIdx)
                        .trim();
                    const products = JSON.parse(jsonString);

                    // Save to a temporary JSON file for the next Python step
                    productListPath = path.join(csvDir, 'processed_products.json');
                    fs.writeFileSync(productListPath, JSON.stringify(products, null, 2));
                    emitLog(socket, `Saved processed product list (${products.length} products)`, 'info');
                } else {
                    emitLog(socket, 'Could not locate processed product JSON in images.py output', 'warning');
                }
            } catch (parseErr) {
                emitLog(socket, `Failed to parse product list: ${parseErr.message}`, 'error');
            }

            // Start PDF generation
            emitProgress(socket, 70, 'Starting PDF generation...', 'pdf_generation');
            const pdfScriptPath = path.join(__dirname, 'Scripts', 'illustrator_process.py');
            
            try {
                // Run PDF generation script
                await runPythonScriptWithProgress(pdfScriptPath, [csvPath], socket, 'pdf_generation');
                emitLog(socket, 'PDF generation completed successfully', 'info');

                // If we have a processed product list, run the Shopify update step
                if (productListPath) {
                    const processProductsScript = path.join(__dirname, 'process_products.py');
                    try {
                        emitProgress(socket, 95, 'Starting Shopify updates...', 'shopify_update');
                        await runPythonScriptWithProgress(processProductsScript, [productListPath], socket, 'shopify_update');
                        emitLog(socket, 'Shopify update script completed successfully', 'info');
                    } catch (ppErr) {
                        emitLog(socket, `Shopify update error: ${ppErr.message}`, 'error');
                        emitComplete(socket, false, `Shopify update failed: ${ppErr.message}`);
                        throw ppErr;
                    }
                } else {
                    emitLog(socket, 'Skipping Shopify update - no product data available', 'warning');
                }

                // Emit final completion event
                emitProgress(socket, 100, 'All processing completed successfully!', 'completed');
                emitComplete(socket, true, null, {
                    downloadDir,
                    outputDir,
                    printpanelsOutputDir,
                    csvPath,
                    timestamp
                });
                
                // Return the paths for use in the caller
                return { downloadDir, outputDir, printpanelsOutputDir, csvPath };
            } catch (pdfError) {
                emitLog(socket, `PDF generation failed: ${pdfError.message}`, 'error');
                emitComplete(socket, false, `PDF generation failed: ${pdfError.message}`);
                throw pdfError;
            }
        } catch (imageError) {
            emitLog(socket, `Image processing failed: ${imageError.message}`, 'error');
            emitComplete(socket, false, `Image processing failed: ${imageError.message}`);
            throw imageError;
        }
    } catch (error) {
        emitLog(socket, `Processing workflow failed: ${error.message}`, 'error');
        emitComplete(socket, false, `Processing workflow failed: ${error.message}`);
        throw error;
    }
}

// Enhanced Socket.IO connection handling with progress tracking
io.on('connection', (socket) => {
    console.log('🔌 Client connected:', socket.id);

    socket.on('startProcess', async (data) => {
        emitLog(socket, `Process request received from client ${socket.id}`, 'info');
        
        try {
            if (!data.csvData) {
                throw new Error('No CSV data provided');
            }

            // Store the process with enhanced tracking
            activeProcesses.set(socket.id, {
                startTime: new Date(),
                status: 'running',
                stage: 'initialization',
                progress: 0,
                lastUpdate: new Date(),
                lastMessage: 'Process started'
            });

            emitLog(socket, 'Processing workflow initiated', 'info');

            // Start processing and get output paths
            const resultPaths = await processImages(data.csvData, socket);

            emitLog(socket, 'All processing workflows completed successfully', 'info');
            
        } catch (error) {
            emitLog(socket, `Process failed: ${error.message}`, 'error');
            emitComplete(socket, false, error.message);
        }
    });

    // Optional: Add status inquiry endpoint
    socket.on('getProcessStatus', () => {
        const process = activeProcesses.get(socket.id);
        if (process) {
            socket.emit('processStatusResponse', {
                ...process,
                duration: new Date() - process.startTime
            });
        } else {
            socket.emit('processStatusResponse', {
                status: 'not_found',
                message: 'No active process found for this client'
            });
        }
    });

    socket.on('disconnect', () => {
        console.log('🔌 Client disconnected:', socket.id);
        activeProcesses.delete(socket.id);
    });
});

// Start server
const PORT = process.env.PORT || 3002;
server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log('Environment check:');
    console.log('- AWS_ACCESS_KEY_ID:', process.env.AWS_ACCESS_KEY_ID ? 'Set' : 'Not set');
    console.log('- AWS_SECRET_ACCESS_KEY:', process.env.AWS_SECRET_ACCESS_KEY ? 'Set' : 'Not set');
    console.log('- AWS_REGION:', process.env.AWS_REGION || 'us-east-2');
});
