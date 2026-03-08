# Full Stack FastAPI Template

<a href="https://github.com/fastapi/full-stack-fastapi-template/actions?query=workflow%3ATest" target="_blank"><img src="https://github.com/fastapi/full-stack-fastapi-template/workflows/Test/badge.svg" alt="Test"></a>
<a href="https://coverage-badge.samuelcolvin.workers.dev/redirect/fastapi/full-stack-fastapi-template" target="_blank"><img src="https://coverage-badge.samuelcolvin.workers.dev/fastapi/full-stack-fastapi-template.svg" alt="Coverage"></a>

## Technology Stack and Features

- ⚡ [**FastAPI**](https://fastapi.tiangolo.com) for the Python backend API.
    - 🧰 [SQLModel](https://sqlmodel.tiangolo.com) for ORM/database interactions.
    - 🔍 [Pydantic](https://docs.pydantic.dev) v2 for data validation and settings.
    - 💾 [PostgreSQL](https://www.postgresql.org) as the SQL database.
    - 🧭 [Alembic](https://alembic.sqlalchemy.org/) for migrations.
    - 🔐 Auth0 integration via `auth0-fastapi-api` and JWTs (`pyjwt`).
- 🚀 [Vue 3](https://vuejs.org) for the frontend.
    - 💃 TypeScript, Composition API, and [Vite](https://vite.dev).
    - 🎨 [Tailwind CSS v4](https://tailwindcss.com) for styling.
    - 🧩 [shadcn-vue](https://www.shadcn-vue.com/) (built on [reka-ui](https://reka-ui.com)) for UI components.
    - 📦 [Pinia](https://pinia.vuejs.org) for client state management.
    - 🧭 [Vue Router](https://router.vuejs.org) for routing.
    - 🔐 [Auth0](https://auth0.com) SPA authentication.
    - ✅ [Zod](https://zod.dev) + [Vee-Validate](https://vee-validate.logaretm.com) for forms/validation.
    - 🌍 [Vue I18n](https://vue-i18n.intlify.dev) for localization.
    - 🤖 Auto-generated TypeScript API client via `@hey-api/openapi-ts`.
    - 🎭 [Playwright](https://playwright.dev) for end-to-end testing.
- 🐋 [Docker Compose](https://www.docker.com) for development and production.
- 🔒 Secure password hashing by default.
- 📫 Email based password recovery with MJML templates.
- ✅ Tests with [Pytest](https://pytest.org) and Playwright.
- 📞 [Traefik](https://traefik.io) as a reverse proxy / load balancer.
- 🧹 Linting & formatting with Ruff, basedpyright, ESLint, and Prettier.
- 🏭 CI/CD based on GitHub Actions.

### Home Screen

<img width="1135" height="782" alt="Home Screen" src="https://github.com/user-attachments/assets/d6e074e2-bb5c-40cf-9a46-f184fed45b35" />

### User Settings

<img width="1135" height="782" alt="User Settings" src="https://github.com/user-attachments/assets/212a7858-2c59-49a0-9c87-83431e5e9ba4" />

### Landing Page

<img width="1135" height="782" alt="Image" src="https://github.com/user-attachments/assets/40ab9187-84e3-44b8-a3fb-40aa66240209" />

### Dynamic Breadcrumbs

<img width="1135" height="782" alt="Image" src="https://github.com/user-attachments/assets/652b47f4-43bc-49ee-8c4c-ccde5f9bba7f" />

### Api Example view

<img width="1135" height="782" alt="Image" src="https://github.com/user-attachments/assets/79f4f91a-a5ff-43f5-947c-1bc7a7655959" />

## How To Use It

You can **just fork or clone** this repository and use it as is.

✨ It just works. ✨

### How to Use a Private Repository

If you want to have a private repository, GitHub won't allow you to simply fork it as it doesn't allow changing the visibility of forks.

But you can do the following:

- Create a new GitHub repo, for example `my-full-stack`.
- Clone this repository manually, set the name with the name of the project you want to use, for example `my-full-stack`:

```bash
git clone git@github.com:Blaxzter/fastapi-vue-fullstack-template.git my-full-stack
```

- Enter into the new directory:

```bash
cd my-full-stack
```

- Set the new origin to your new repository, copy it from the GitHub interface, for example:

```bash
git remote set-url origin git@github.com:octocat/my-full-stack.git
```

- Add this repo as another "remote" to allow you to get updates later:

```bash
git remote add upstream git@github.com:Blaxzter/fastapi-vue-fullstack-template.git
```

- Push the code to your new repository:

```bash
git push -u origin main
```

### Update From the Original Template

After cloning the repository, and after doing changes, you might want to get the latest changes from this original template.

- Make sure you added the original repository as a remote, you can check it with:

```bash
git remote -v

origin    git@github.com:octocat/my-full-stack.git (fetch)
origin    git@github.com:octocat/my-full-stack.git (push)
upstream    git@github.com:Blaxzter/fastapi-vue-fullstack-template.git (fetch)
upstream    git@github.com:Blaxzter/fastapi-vue-fullstack-template.git (push)
```

- Pull the latest changes without merging:

```bash
git pull --no-commit upstream master
```

This will download the latest changes from this template without committing them, that way you can check everything is right before committing.

- If there are conflicts, solve them in your editor.

- Once you are done, commit the changes:

```bash
git merge --continue
```

### Clean Up the Template

After cloning, remove sample content you don't need:

```bash
# Remove example/demo pages only
just remove-examples

# Remove the project/task sample domain (models, CRUD, routes, views, migrations, tests)
just remove-domain

# Or do both at once and regenerate the API client
just clean-template
```

After cleanup you'll have a clean foundation with auth, user management, health endpoints, base CRUD infrastructure, and all UI components ready for your own features. See [AGENTS.md](./AGENTS.md#template-cleanup) for details on what each step removes and what remains.

### Generate Secret Keys

Some environment variables in the `.env` file have a default value of `changethis`.

You have to change them with a secret key, to generate secret keys you can run the following command:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the content and use that as password / secret key. And run that again to generate another secure key.

## How To Use It - Alternative With Copier

This repository also supports generating a new project using [Copier](https://copier.readthedocs.io).

It will copy all the files, ask you configuration questions, and update the `.env` files with your answers.

### Install Copier

You can install Copier with:

```bash
pip install copier
```

Or better, if you have [`pipx`](https://pipx.pypa.io/), you can run it with:

```bash
pipx install copier
```

**Note**: If you have `pipx`, installing copier is optional, you could run it directly.

### Generate a Project With Copier

Decide a name for your new project's directory, you will use it below. For example, `my-awesome-project`.

Go to the directory that will be the parent of your project, and run the command with your project's name:

```bash
copier copy https://github.com/Blaxzter/fastapi-vue-fullstack-template.git my-awesome-project --trust
```

If you have `pipx` and you didn't install `copier`, you can run it directly:

```bash
pipx run copier copy https://github.com/Blaxzter/fastapi-vue-fullstack-template.git my-awesome-project --trust
```

**Note** the `--trust` option is necessary to be able to execute a [post-creation script](https://github.com/Blaxzter/fastapi-vue-fullstack-template.git/blob/master/.copier/update_dotenv.py) that updates your `.env` files.

### Input Variables

Copier will ask you for some data, you might want to have at hand before generating the project.

But don't worry, you can just update any of that in the `.env` files afterwards.

The input variables, with their default values (some auto generated) are:

- `project_name`: (default: `"FastAPI Project"`) The name of the project, shown to API users (in .env).
- `stack_name`: (default: `"fastapi-project"`) The name of the stack used for Docker Compose labels and project name (no spaces, no periods) (in .env).
- `smtp_host`: (default: "") The SMTP server host to send emails, you can set it later in .env.
- `smtp_user`: (default: "") The SMTP server user to send emails, you can set it later in .env.
- `smtp_password`: (default: "") The SMTP server password to send emails, you can set it later in .env.
- `emails_from_email`: (default: `"info@example.com"`) The email account to send emails from, you can set it later in .env.
- `postgres_password`: (default: `"changethis"`) The password for the PostgreSQL database, stored in .env, you can generate one with the method above.
- `sentry_dsn`: (default: "") The DSN for Sentry, if you are using it, you can set it later in .env.

## Backend Development

Backend docs: [backend/README.md](./backend/README.md).

## Frontend Development

Frontend docs: [frontend/README.md](./frontend/README.md).

## Deployment

Deployment docs: [deployment.md](./deployment.md).

## Development

General development docs: [development.md](./development.md).

This includes using Docker Compose, custom local domains, `.env` configurations, etc.

## Release Notes

Check the file [release-notes.md](./release-notes.md).

## License

The Full Stack FastAPI Template is licensed under the terms of the MIT license.
