# Advanced Usage

## Step-by-step instructions for running as a Github action

### Fork the repository

Click the fork button at the top of this repository page, as seen on the below image. This will create your own version of the repository, including your own set of github actions

![fork](./readme_images/fork.png)

### Modify the configuration file

Modify `config.yaml` by cloning the respository and merging your changes

### Create and Fetch your API Keys 

- Create or fetch your API key for [OpenAI](https://platform.openai.com/account/api-keys). Note: you will need an OpenAI account.
![fork](./readme_images/openai.png)

- Create or fetch your API key for [SendGrid](https://app.SendGrid.com/settings/api_keys). You will need a SendGrid account. The free tier will generally suffice. Make sure to [verify your sender identity](https://docs.sendgrid.com/for-developers/sending-email/sender-identity).

### Set the secrets for the github action

Go to the Settings tab on the top of this page, and then the "Actions" menu under "Secrets and variables":

![settings](./readme_images/settings.png)

Create a new repository secret for each of the following using the button in the below image:
- `OPENAI_API_KEY`
- `SENDGRID_API_KEY`
- `FROM_EMAIL`
- `TO_EMAIL`

![secret](./readme_images/secrets.png)

### Manually trigger the action, or wait until the scheduled trigger

Go to the actions tab, and then click on "Daily Workflow" and "Run Workflow"

![trigger](./readme_images/trigger.png)

## Additional Configuration

- If you want a different schedule than Sunday through Thursday at 1:25PM UTC, then modify the file `.github/workflows/daily_pipeline.yaml` 


## Alternative Usage

Running `src/action.py` will generate an HTML file that can then be emailed. The following alternative usage methods all use that pattern

### Running as a github action with SMTP credentials.

An alternative way to get started using this repository is to:

1. Fork the repository
2. Modify `config.yaml` and merge the changes into your main branch. If you want a different schedule than Sunday through Thursday at 1:25PM UTC, then also modify the file `.github/workflows/daily_pipeline.yaml`
3. Create or fetch your API key for [OpenAI](https://platform.openai.com/account/api-keys).
4. Find your email provider's SMTP settings and set the secret `MAIL_CONNECTION` to that. It should be in the form `smtp://user:password@server:port` or `smtp+starttls://user:password@server:port`. Alternatively, if you are using Gmail, you can set `MAIL_USERNAME` and `MAIL_PASSWORD` instead, using an [application password](https://support.google.com/accounts/answer/185833).
5. Set the following secrets [(under settings, Secrets and variables, repository secrets)](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository):
   - `OPENAI_API_KEY`
   - `MAIL_CONNECTION` (see above)
   - `MAIL_PASSWORD` (only if you don't have `MAIL_CONNECTION` set)
   - `MAIL_USERNAME` (only if you don't have `MAIL_CONNECTION` set)
   - `FROM_EMAIL`
   - `TO_EMAIL`
6. Manually trigger the action or wait until the scheduled action takes place.

### Running as a github action without emails 

If you do not wish to create a SendGrid account or use your email authentication, the action will also emit an artifact containing the HTML output. Simply do not create the SendGrid or SMTP secrets.

You can access this digest as part of the github action artifact.

![artifact](./readme_images/artifact.png)

### Running from the command line

If you do not wish to fork this repository, and would prefer to clone and run it locally instead:

1. Install the requirements in `src/requirements.txt`
2. Modify the configuration file `config.yaml`
3. Create or fetch your API key for [OpenAI](https://platform.openai.com/account/api-keys).
4. Create or fetch your API key for [SendGrid](https://app.SendGrid.com/settings/api_keys) (optional, if you want the script to email you)
5. Set the following secrets as environment variables: 
   - `OPENAI_API_KEY`
   - `SENDGRID_API_KEY` (only if using SendGrid)
   - `FROM_EMAIL` (only if using SendGrid. Note that this value must match the email you used to create the SendGrid Api Key.)
   - `TO_EMAIL` (only if using SendGrid)
6. Run `python action.py`.
7. If you are not using SendGrid, the html of the digest will be written to `digest.html`. You can then use your favorite webbrowser to view it.

You may want to use something like crontab to schedule the digest.
