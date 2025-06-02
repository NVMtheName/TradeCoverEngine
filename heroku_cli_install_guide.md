# Heroku CLI Installation Guide for Arbion Deployment

## Installation Methods

### Method 1: Official Package Managers (Recommended)

#### macOS
```bash
brew tap heroku/brew && brew install heroku
```

#### Windows
Download installer from: https://cli-assets.heroku.com/install.sh

#### Ubuntu/Debian
```bash
curl https://cli-assets.heroku.com/install-ubuntu.sh | sh
```

### Method 2: Tarball Installation (Manual)

#### Linux x64
```bash
cd /tmp
curl -L https://cli-assets.heroku.com/channels/stable/heroku-linux-x64.tar.xz | tar -xJ
sudo mv heroku /usr/local/lib/
sudo ln -s /usr/local/lib/heroku/bin/heroku /usr/local/bin/heroku
```

#### macOS
```bash
cd /tmp
curl -L https://cli-assets.heroku.com/channels/stable/heroku-darwin-x64.tar.xz | tar -xJ
sudo mv heroku /usr/local/lib/
sudo ln -s /usr/local/lib/heroku/bin/heroku /usr/local/bin/heroku
```

### Method 3: NPM Installation
```bash
npm install -g heroku
```

## Verification

After installation, verify the CLI works:
```bash
heroku --version
heroku login
```

## Quick Deployment for Arbion

Once Heroku CLI is installed:

1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Create Application**
   ```bash
   heroku create your-arbion-app-name
   ```

3. **Add Database**
   ```bash
   heroku addons:create heroku-postgresql:essential-0
   ```

4. **Set Environment Variables**
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set SESSION_SECRET=$(openssl rand -base64 32)
   heroku config:set OPENAI_API_KEY=your_key_here
   heroku config:set SCHWAB_API_KEY=your_schwab_key_here
   heroku config:set SCHWAB_API_SECRET=your_schwab_secret_here
   ```

5. **Deploy**
   ```bash
   git add .
   git commit -m "Deploy Arbion to Heroku"
   git push heroku main
   ```

6. **Initialize Database**
   ```bash
   heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

Your Arbion platform will be live at: `https://your-arbion-app-name.herokuapp.com`