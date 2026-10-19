# Documentation site

This folder holds the documentation site of shirabe-profiling. It is built with Docus, a Nuxt layer.

## Running the site

Run these commands from the repository root.

| Command | Result |
| --- | --- |
| `just docs-dev` | Serves the site with live reload. |
| `just docs-build` | Builds the static site into `docs/.output/public`. |
| `just docs-links` | Checks the links and anchors of the built site, with no network. |

The recipes use nub when it is installed, and npm if not. Node.js 22 or newer is needed.

## Layout

- `content/` holds the pages as Markdown. The numbers in the file names set the order of the sidebar.
- `app/components/` holds the Vue components that the pages use.
- `nuxt.config.ts` holds the site settings, such as the logo and the base path.
- `public/images/`, `public/logo/`, and `public/fonts/` hold the static files.
  The recipes copy the pictures and the wordmark from `assets/` at build time, and git ignores those copies.

`app/app.config.ts`, `app/app.css`, `app/assets/css/`, and `public/fonts/` are copies from the design kit.
Change the kit and copy it again, instead of editing these files here.

## Deploying

A release tag builds the site under `/shirabe-profiling/` and deploys it to GitHub Pages.
Read `CONTRIBUTING.md` for the steps and for how to test the base path on your machine.
