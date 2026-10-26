# Deploying the public demo (Render)

The demo is a static site built from the synthetic fixture. It has no backend and accepts no uploads.

1. Push the repository to GitHub.
2. In Render, choose **New > Blueprint** and select the repository. `render.yaml` configures a static site with `rootDir: frontend`, build command `npm ci && npm run build`, publish directory `dist` and `VITE_DEMO_MODE=true`.
3. After the deploy, open the URL and check that:
   - the orange "Public Demo — SYNTHETIC" banner is visible;
   - the Setup, Import and Review tabs are absent;
   - the Backtest tab shows TabPFN as unavailable (unless the fixture was regenerated with TabPFN installed).

To refresh the fixture: `python scripts/generate_demo_fixture.py`.
