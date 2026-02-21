# Docker Desktop Installation Guide

## macOS

### Prerequisites
- macOS 12 (Monterey) or later
- At least 4GB RAM

### Steps

1. **Download Docker Desktop**
   - Visit [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
   - Click **Download for Mac**
   - Choose the correct chip version:
     - **Apple Silicon** (M1/M2/M3/M4) — for Macs with Apple chips
     - **Intel** — for older Intel-based Macs

2. **Install**
   - Open the downloaded `.dmg` file
   - Drag the **Docker** icon to the **Applications** folder
   - Launch Docker from Applications or Spotlight (`Cmd+Space` → type `Docker`)

3. **Complete Setup**
   - Accept the service agreement
   - Choose a configuration (personal use is free)
   - Docker will request your system password to install the helper tool

4. **Verify Installation**
   ```bash
   docker --version
   docker run hello-world
   ```

---

## Windows

### Prerequisites
- Windows 10 64-bit (Build 19041+) or Windows 11
- At least 4GB RAM
- Virtualization enabled in BIOS/UEFI

### Option A: WSL 2 Backend (Recommended)

1. **Enable WSL 2 first**
   Open PowerShell as Administrator and run:
   ```powershell
   wsl --install
   ```
   Restart your computer when prompted.

2. **Download Docker Desktop**
   - Visit [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
   - Click **Download for Windows**

3. **Install**
   - Run the `Docker Desktop Installer.exe`
   - Ensure **"Use WSL 2 instead of Hyper-V"** is checked
   - Follow the prompts and restart when finished

4. **Verify Installation**
   Open PowerShell or Command Prompt:
   ```powershell
   docker --version
   docker run hello-world
   ```

### Option B: Hyper-V Backend

1. **Enable Hyper-V**
   Open PowerShell as Administrator:
   ```powershell
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
   ```
   Restart your computer.

2. Follow **steps 2–4 from Option A**, but leave **"Use WSL 2"** unchecked during installation.

---

## Post-Installation (Both Platforms)

### Test your setup
```bash
# Pull and run a test container
docker run hello-world

# Check running containers
docker ps

# Check all containers
docker ps -a
```

### Common first commands
```bash
docker pull ubuntu          # Download an image
docker images               # List local images
docker run -it ubuntu bash  # Run interactive container
docker stop <container-id>  # Stop a running container
docker rm <container-id>    # Remove a container
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| "Hardware virtualization not enabled" | Enable VT-x/AMD-V in BIOS settings |
| WSL 2 not found (Windows) | Run `wsl --install` in Admin PowerShell |
| Docker daemon not starting | Restart Docker Desktop from the system tray |
| Permission denied (macOS) | Ensure Docker.app is in `/Applications`, not `~/Downloads` |
| Port already in use | Run `docker ps` to find conflicting containers and stop them |