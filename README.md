# Personalized-Arxiv-digest
This repo aims to provide a better daily digest for newly published arxiv papers based on your own research interests and descriptions.

## What this repo does

Staying up to date on [arxiv](https://arxiv.org) papers can take a considerable amount of time, with on the order of hundreds of new papers each day to filter through. There is an [official daily digest service](https://info.arxiv.org/help/subscribe.html), however large subtopics like [cs.AI](https://arxiv.org/list/cs.AI/recent) still have 50-100 papers a day. Determining if these papers are relevant and important to you means reading through the title and abstract.

This repository provides a way to have this daily digest sorted by relevance via large language models:

* You modify the configuration file `config.yaml` with an arxiv topic, some set of subtopics, and a natural language statement about the type of papers you are interested in
* The code pulls all the abstracts for papers in those subtopics and ranks how relevant they are to your interest on a scale of 1-10 using gpt-3.5-turbo. 
* The code then emits an HTML digest listing all the relevant papers, and optionally emails it to you using [SendGrid](https://sendgrid.com). You will need to have a SendGrid account with an API key for this functionality to work


### Some examples:

- Topic: Computer Science
- Categories: Artificial Intelligence, Computation and Language 
- Interest: 
  - Large language model pretraining and finetunings
  - Multimodal machine learning
  - Do not care about specific application, for example, information extraction, summarization, etc.
  - Not interested in paper focus on specific languages, e.g., Arabic, Chinese, etc.

![example1](./readme_images/example_1.png)


- Topic: Quantitative Finance
- Interest: "making lots of money"

![example2](./readme_images/example_2.png)

## Usage

### Running as a github action using SendGrid.

The recommended way to get started using this repository is to:

1. Fork the repository
2. Modify `config.yaml` and merge the changes into your main branch. If you want a different schedule than Sunday through Thursday at 1:25PM UTC, then also modify the file `.github/workflows/daily_pipeline.yaml`
3. Create or fetch your api key for [OpenAI](https://platform.openai.com/account/api-keys). Note: you will need an OpenAI account.
4. Create or fetch your api key for [SendGrid](https://app.SendGrid.com/settings/api_keys). You will need a SendGrid account. The free tier will generally suffice.
5. Set the following secrets:
   - `OPENAI_API_KEY`
   - `SENDGRID_API_KEY`
   - `FROM_EMAIL` (only if you don't have it set in `config.yaml`)
   - `TO_EMAIL` (only if you don't have it set in `config.yaml`)
6. Manually trigger the action or wait until the scheduled action takes place.

![artifact](./readme_images/trigger.png)


### Running as a github action with SMTP credentials.

An alternative way to get started using this repository is to:

1. Fork the repository
2. Modify `config.yaml` and merge the changes into your main branch. If you want a different schedule than Sunday through Thursday at 1:25PM UTC, then also modify the file `.github/workflows/daily_pipeline.yaml`
3. Create or fetch your api key for [OpenAI](https://platform.openai.com/account/api-keys). Note: you will need an OpenAI account.
4. Find your email provider's SMTP settings and set the secret `MAIL_CONNECTION` to that. It should be in the form `smtp://user:password@server:port` or `smtp+starttls://user:password@server:port`. Alternatively, if you are using Gmail, you can set `MAIL_USERNAME` and `MAIL_PASSWORD` instead, using an [application password](https://support.google.com/accounts/answer/185833).
5. Set the following secrets:
   - `OPENAI_API_KEY`
   - `MAIL_CONNECTION` (see above)
   - `MAIL_PASSWORD` (only if you don't have `MAIL_CONNECTION` set)
   - `MAIL_USERNAME` (only if you don't have `MAIL_CONNECTION` set)
   - `FROM_EMAIL` (only if you don't have it set in `config.yaml`)
   - `TO_EMAIL` (only if you don't have it set in `config.yaml`)
6. Manually trigger the action or wait until the scheduled action takes place.

#### Running as a github action without emails 

If you do not wish to create a SendGrid account or use your email authentication, the action will also emit an artifact containing the HTML output. Simply do not create the SendGrid or SMTP secrets.

You can access this digest as part of the github action artifact.

![artifact](./readme_images/artifact.png)

### Running from the command line

If you do not wish to fork this repository, and would prefer to clone and run it locally instead:

1. Install the requirements in `src/requirements.txt`
2. Modify the configuration file `config.yaml`
3. Create or fetch your api key for [OpenAI](https://platform.openai.com/account/api-keys). Note: you will need an OpenAI account.
4. Create or fetch your api key for [SendGrid](https://app.SendGrid.com/settings/api_keys) (optional, if you want the script to email you)
5. Set the following secrets:
   - `OPENAI_API_KEY`
   - `SENDGRID_API_KEY` (only if using SendGrid)
   - `FROM_EMAIL` (only if using SendGrid and if you don't have them set in `config.yaml`)
   - `TO_EMAIL` (only if using SendGrid and if you don't have them set in `config.yaml`)
6. Run `python action.py`.
7. If you are not using SendGrid, the html of the digest will be written to `digest.html`. You can then use your favorite webbrowser to view it.

You may want to use something like crontab to schedule the digest.

### Running with a user interface

Install the requirements in `src/requirements.txt` as well as `gradio`. Set the evironment variables `OPENAI_API_KEY`, `FROM_EMAIL` and `SENDGRID_API_KEY`

Run `python src/app.py` and go to the local URL. From there you will be able to preview the papers from today, as well as the generated digests.

## Extending and Contributing

You may (and are encourage to) modify the code in this repository to suit your personal needs. If you think your modifications would be in any way useful to others, please submit a pull request.

These types of modifications include things like changes to the prompt, different language models, or additional ways for the digest is delivered to you.
