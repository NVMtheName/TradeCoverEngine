# Fixing Heroku Deployment Issues

## Current Issues

There are two main issues with the Heroku deployment:

1. **Dependency Conflicts**: 
   - The error shows that Flask-SQLAlchemy 3.0.3 requires Flask>=2.2, but the requirements file specifies Flask==2.0.1
   - This causes a dependency resolution conflict

2. **Deprecated Python Runtime Configuration**:
   - The `runtime.txt` file is deprecated in favor of `.python-version`
   - Python 3.9.13 should be updated to the latest 3.9.x version

## Solutions

### 1. Fix Requirements.txt

I've created a new `fixed_requirements.txt` file that resolves the dependency conflicts:
- Updated Flask to be >=2.2.0 (to satisfy Flask-SQLAlchemy's requirements)
- Updated Werkzeug to be >=2.2.0 (as newer Flask requires newer Werkzeug)
- Updated Flask-Login to be >=0.6.0 (for compatibility with newer Flask)
- Used minimum version requirements (>=) instead of pinned versions to allow more flexibility
- Added pytest-tap to ensure TAP testing works in all environments

To use this updated requirements file:

```bash
mv fixed_requirements.txt requirements.txt
git add requirements.txt
git commit -m "Update dependencies to resolve conflicts"
```

### 2. Update Python Runtime Configuration

I've created a `.python-version` file that follows the new recommended approach:
- Uses only the major Python version (3.9)
- This allows Heroku to automatically use the latest 3.9.x version (currently 3.9.22)
- Will receive security updates automatically

You should remove the deprecated `runtime.txt` file:

```bash
git rm runtime.txt
git add .python-version
git commit -m "Switch to .python-version for Python runtime specification"
```

### Full Deployment Fix

To fix your Heroku deployment completely:

1. Apply both changes above
2. Push to Heroku:
   ```bash
   git push heroku main
   ```

3. Verify the build completes successfully
4. Monitor the application for any issues

This should resolve the "Unable to install dependencies using pip" error and the Python runtime warnings.