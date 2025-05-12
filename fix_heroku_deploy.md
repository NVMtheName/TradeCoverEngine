# Fixing Heroku Deployment

This guide has been updated to address the deprecation of Heroku's hobby-dev PostgreSQL plan.

## Updated PostgreSQL Plan

Heroku has discontinued the `hobby-dev` PostgreSQL plan. All configurations have been updated to use the new `mini` plan instead.

The following files have been updated:
- app.json
- heroku.yml
- app.ci
- github_actions_deployment.md

## Deployment Instructions

To deploy to Heroku with the updated configuration:

1. Make sure you have the Heroku CLI installed and are logged in.

2. Create a new Heroku app:
   ```bash
   heroku create your-app-name
   ```

3. Add the PostgreSQL mini plan:
   ```bash
   heroku addons:create heroku-postgresql:mini -a your-app-name
   ```

4. Add QuotaGuard Static IP (for Schwab API access):
   ```bash
   heroku addons:create quotaguardstatic:starter -a your-app-name
   ```

5. Set required environment variables:
   ```bash
   heroku config:set SCHWAB_API_KEY=your_key -a your-app-name
   heroku config:set SCHWAB_API_SECRET=your_secret -a your-app-name
   heroku config:set FLASK_ENV=production -a your-app-name
   ```

6. Deploy using the Heroku Git remote:
   ```bash
   git push heroku main
   ```

## Alternative: Deploying with GitHub Actions

We've set up GitHub Actions workflows to handle CI/CD more reliably than Heroku CI. See the `github_actions_deployment.md` file for detailed instructions on setting up GitHub repository secrets and deploying with GitHub Actions.

The main advantages of the GitHub Actions approach:
- More reliable build process
- Customizable test environment
- Ability to deploy with a static IP address
- Better secret handling

## Troubleshooting

If you encounter issues with the PostgreSQL plan, try the following:

1. Check the current available plans:
   ```bash
   heroku addons:plans heroku-postgresql
   ```

2. If you need to upgrade an existing app:
   ```bash
   heroku addons:upgrade heroku-postgresql:mini -a your-app-name
   ```

3. If you receive an error about invalid app.json, make sure all files are updated to use the "mini" plan instead of "hobby-dev".