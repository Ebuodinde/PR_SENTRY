/**
 * Check Python installation after npm install
 */

const { execSync } = require('child_process');

try {
  execSync('python3 --version', { stdio: 'pipe' });
  console.log('✓ Python 3 found');
} catch (e) {
  try {
    execSync('python --version', { stdio: 'pipe' });
    console.log('✓ Python found');
  } catch (e2) {
    console.warn('⚠ Python not found. PR-Sentry requires Python 3.');
    console.warn('  Install Python 3 from https://python.org');
  }
}

try {
  execSync('pip3 show anthropic httpx python-dotenv', { stdio: 'pipe' });
  console.log('✓ Python dependencies found');
} catch (e) {
  console.log('Installing Python dependencies...');
  try {
    execSync('pip3 install anthropic httpx python-dotenv', { stdio: 'inherit' });
    console.log('✓ Dependencies installed');
  } catch (e2) {
    console.warn('⚠ Could not install dependencies. Run manually:');
    console.warn('  pip3 install anthropic httpx python-dotenv');
  }
}
