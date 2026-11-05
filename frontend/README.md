# HireSense AI frontend

## Run locally

Install dependencies and start the frontend:

```bash
npm install
npm run dev
```

Open `http://localhost:3000`. The API defaults to port `8000` on the same
hostname used to open the frontend, so this also works when accessing the
development frontend from another device on a private network.

To use a different backend, set `NEXT_PUBLIC_API_BASE_URL` in `.env.local`,
for example:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

The backend must be running and its database must be available. For a
non-local frontend origin, configure the backend's comma-separated
`CORS_ORIGINS` environment variable with the exact frontend origin(s), including
scheme and port. With Docker Compose, set it in the project-root `.env` file,
then restart the backend. Localhost and private-network HTTP origins are allowed
for development.

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
