# How to Set Up Global RC Command on Host Machine

This guide explains how to install the RC command globally on your host machine, separate from the OpenHands development environment.

## Overview

This process allows you to:
- Keep the OpenHands directory and its virtual environment untouched
- Install a global `rc` command that uses your production CrewAI project
- Have the global command survive if you delete the development/workbench directory
- Maintain separation between development and production environments

## Prerequisites

- You have a CrewAI project in `/home/ubuntu/environment/rscrew` (or your preferred location)
- The project has a `pyproject.toml` file with RC command configuration
- You have Python and pip available on the host system

## Step-by-Step Process

### 1. Navigate to Your Production CrewAI Project

```bash
cd /home/ubuntu/environment/rscrew
```

### 2. Install the Project Globally

Install the project to your system/user Python environment (NOT the OpenHands virtual environment):

```bash
pip install -e .
```

**Note**: Use `pip` (not `uv pip`) to install to the system Python environment.

### 3. Find the Installation Location

Check where the RC command was installed:

```bash
which rc
```

This will typically be something like:
- `/home/ubuntu/.local/bin/rc` (user installation)
- `/usr/local/bin/rc` (system installation)

### 4. Update Your PATH

Edit your shell configuration files to use the new RC location:

#### Option A: Edit .bashrc
```bash
nano ~/.bashrc
```

#### Option B: Edit .profile
```bash
nano ~/.profile
```

**Remove** any existing OpenHands PATH entries:
```bash
# Remove this line if it exists:
export PATH="/home/ubuntu/environment/openhands/.venv/bin:$PATH"
```

**Add** the new global installation path:
```bash
# Add this line (adjust path based on step 3 results):
export PATH="/home/ubuntu/.local/bin:$PATH"
```

### 5. Apply the Changes

Reload your shell configuration:

```bash
source ~/.bashrc
# or
source ~/.profile
```

**OR** restart your terminal session.

### 6. Verify the Setup

Test that the global RC command works:

```bash
# Check which RC command is being used
which rc

# Test the command
rc --help

# Test from any directory
cd /tmp
rc Please analyze this directory
```

## Result

After completing these steps:

- ✅ Global `rc` command uses your production CrewAI project
- ✅ Command works from any directory on the host machine
- ✅ OpenHands development environment remains untouched
- ✅ Global command survives if you delete the workbench directory
- ✅ Complete separation between development and production environments

## Troubleshooting

### Command Not Found
- Verify the installation completed successfully
- Check that the installation path is in your PATH
- Restart your terminal session

### Wrong Project Being Used
- Use `which rc` to verify you're using the correct installation
- Check that the new PATH entry comes before any old entries
- Ensure you removed old PATH entries from shell config files

### Permission Issues
- If using system installation, you may need `sudo pip install -e .`
- User installation (`pip install --user -e .`) is recommended for personal use

## Maintenance

To update the global RC command:
1. Navigate to your production project directory
2. Make your changes
3. The installation will automatically use the updated code (due to `-e` flag)

To completely remove:
```bash
pip uninstall rscrew
```