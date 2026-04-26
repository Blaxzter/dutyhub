# Frontend

A modern Vue 3 + TypeScript frontend application with a comprehensive UI component library and authentication system.

## Tech Stack

- **Vue 3** - The progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript development
- **Vite** - Fast build tool and development server
- **Tailwind CSS v4** - Utility-first CSS framework for styling
- **shadcn-vue (reka-ui)** - High-quality, accessible UI components
- **Auth0** - Secure authentication and user management
- **Pinia** - Intuitive state management for Vue
- **Vue Router** - Official routing library for Vue.js
- **Vue I18n** - Localization and translation support
- **Vee-Validate + Zod** - Form handling and validation
- **VueUse** - Composables/utilities for Vue
- **Lucide Vue Next** - Beautiful & consistent icon library
- **Axios** - Promise-based HTTP client
- **OpenAPI TS** - Auto-generated API client
- **Playwright** - End-to-end testing
- **pnpm** - Package manager

## Features

- ✅ **Modern UI Components** - Pre-built components using shadcn-vue with consistent design
- ✅ **Authentication** - Secure Auth0 integration with session management
- ✅ **Type Safety** - Full TypeScript support with auto-generated API client
- ✅ **Responsive Design** - Mobile-first approach with Tailwind CSS
- ✅ **State Management** - Centralized state with Pinia stores
- ✅ **API Integration** - Auto-generated TypeScript client from OpenAPI specs
- ✅ **End-to-End Testing** - Comprehensive testing with Playwright
- ✅ **Code Quality** - ESLint and Prettier for consistent code formatting

## Recommended IDE Setup

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur) + [TypeScript Vue Plugin](https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin).

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Environment Setup

Copy the example environment file and configure your settings:

```sh
cp .env.example .env
```

Configure the following environment variables:

- `VITE_AUTH0_DOMAIN` - Your Auth0 domain
- `VITE_AUTH0_CLIENT_ID` - Your Auth0 application client ID
- `VITE_AUTH0_API_AUDIENCE` - Your Auth0 API audience
- `VITE_AUTH0_CALLBACK_URL` - Auth0 callback URL (optional, defaults to current origin)
- `VITE_API_SERVER_URL` - Backend API URL (default: http://localhost:8787)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
pnpm install
```

### Generate API Client

Generate TypeScript client from the backend OpenAPI schema:

```sh
pnpm run generate-client
```

### Compile and Hot-Reload for Development

```sh
pnpm dev
```

### Type-Check, Compile and Minify for Production

```sh
pnpm build
```

### Run End-to-End Tests with [Playwright](https://playwright.dev)

```sh
# Install browsers for the first run
npx playwright install

# When testing on CI, must build the project first
pnpm build

# Runs the end-to-end tests
pnpm test:e2e
# Runs only authenticated tests on Chromium
pnpm test:e2e --project=chromium-auth
# Runs only public tests on Chromium
pnpm test:e2e --project=chromium-public
# Runs tests from a specific file
pnpm test:e2e e2e/tests/public/landing.spec.ts
# Runs the tests in debug mode
pnpm test:e2e --debug
```

Auth0 E2E setup:

- `e2e/setup/auth.setup.ts` performs a real Auth0 login and stores state in `e2e/.auth/user.json`.
- Set the following in `frontend/.env` for Playwright:
  - `E2E_AUTH0_USERNAME`
  - `E2E_AUTH0_PASSWORD`

### Lint with [ESLint](https://eslint.org/)

```sh
pnpm lint
```

### Format Code with [Prettier](https://prettier.io/)

```sh
pnpm format
```

## UI Components

This project uses [shadcn-vue](https://www.shadcn-vue.com/) (built on reka-ui) for UI components. Components are:

- **Accessible** - Built with accessibility in mind
- **Customizable** - Easy to customize with Tailwind CSS
- **Consistent** - Unified design system
- **Type-safe** - Full TypeScript support

### Available Components

The project includes pre-configured components in `src/components/ui/`:

- Avatar, Badge, Breadcrumb
- Button, Card, Collapsible
- Dropdown Menu, Form, Input
- Label, Separator, Sheet
- Sidebar, Skeleton, Sonner (Toast)
- Textarea, Tooltip

### Icons

Icons are imported from [Lucide Vue Next](https://lucide.dev/guide/packages/lucide-vue-next):

```vue
<script setup>
import { SettingsIcon, UserIcon } from 'lucide-vue-next'
</script>

<template>
  <UserIcon class="h-4 w-4" />
  <SettingsIcon class="h-4 w-4" />
</template>
```

## Authentication

The application uses [Auth0](https://auth0.com/) for authentication:

- **Secure** - Industry-standard OAuth 2.0 / OIDC
- **User Management** - Built-in user registration and login
- **Social Logins** - Support for Google, GitHub, etc.
- **Session Management** - Automatic token refresh and logout

### Auth Store

Authentication state is managed through Pinia store (`src/stores/auth.ts`):

```typescript
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

// Check authentication status
authStore.isAuthenticated

// Get user information
authStore.user

// Login/Logout
authStore.login()
authStore.logout()
```

## Project Structure

```
src/
├── components/          # Reusable Vue components
│   ├── ui/             # shadcn-vue UI components
│   ├── account/        # Account-related components
│   └── navigation/     # Navigation components
├── views/              # Page components
├── router/             # Vue Router configuration
├── stores/             # Pinia state management
├── composables/        # Vue composition utilities
├── client/             # Auto-generated API client
├── lib/                # Utility functions
└── assets/             # Static assets
```
