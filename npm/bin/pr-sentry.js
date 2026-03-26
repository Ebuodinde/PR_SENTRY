#!/usr/bin/env node
/**
 * PR-Sentry CLI wrapper
 * Calls the Python CLI with the same arguments
 */

const { spawn } = require('child_process');
const path = require('path');

// Get the Python script path
const pythonScript = path.join(__dirname, '..', '..', 'cli.py');

// Spawn Python process with arguments
const python = spawn('python3', [pythonScript, ...process.argv.slice(2)], {
  stdio: 'inherit',
  env: process.env
});

python.on('error', (err) => {
  if (err.code === 'ENOENT') {
    console.error('Error: Python 3 is required but not found.');
    console.error('Please install Python 3 and try again.');
    process.exit(1);
  }
  console.error('Error:', err.message);
  process.exit(1);
});

python.on('close', (code) => {
  process.exit(code || 0);
});
