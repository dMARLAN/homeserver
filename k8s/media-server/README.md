# Homeserver

A complete media server stack running on Kubernetes with automatic media management and streaming capabilities.

## Media Server Stack

### Components
- **Jellyfin** - Media streaming server
- **Jellyseerr** - Request management system with mobile-friendly interface
- **Radarr** - Movie download manager
- **Sonarr** - TV download manager 
- **Prowlarr** - Indexer manager
- **FlareSolverr** - Cloudflare proxy

### Directory Structure
All media server components are organized under `/mnt/media-server/`:
```
/mnt/media-server/
├── media/             # Shared media library (movies, TV shows)
├── downloads/         # Download staging area
├── jellyfin/config/   # Jellyfin configuration
├── jellyseerr/config/ # Jellyseerr configuration
├── radarr/config/     # Radarr configuration
├── sonarr/config/     # Sonarr configuration
└── prowlarr/config/   # Prowlarr configuration
```

### Deployment/Management

- `make deploy-media-server` (Deploys k3s stack)
- `make media-server-up` (Scales stack to 1)
- `make media-server-down` (Scales stack to 0)
- `make teardown-media-server` (Tears down k3s stack)

### Access Applications

- **Jellyfin (main)**: http://YOUR-NODE-IP:30096
- **Jellyseerr (mobile)**: http://YOUR-NODE-IP:30055
- **Prowlarr (indexers)**: http://YOUR-NODE-IP:30696
- **Radarr (movies)**: http://YOUR-NODE-IP:30878
- **Sonarr (shows)**: http://YOUR-NODE-IP:30989
- **FlareSolverr (cloudflare)**: http://YOUR-NODE-IP:30191

### Setup Process

1. **Configure Prowlarr**
   - Add indexers
   - Add apps (Radarr, Sonarr)
   - Add indexer proxy (FlareSolverr)

2. **Configure QBitTorrent**
   - Reset password

3. **Configure Radarr**
   - Connect to Prowlarr
   - Add download client
   - Set library path to `/movies`

4. **Configure Sonarr**
   - Connect to Prowlarr
   - Add download client
   - Set library path to `/tv`

5. **Configure Jellyseerr**
   - Connect to Jellyfin server
   - Connect to Radarr
   - Connect to Sonarr

6. **Access Jellyfin** (http://YOUR-NODE-IP:30096)
   - Complete initial setup
   - Add media libraries pointing to `/media`
