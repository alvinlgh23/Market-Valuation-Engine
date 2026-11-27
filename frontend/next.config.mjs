/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1", "192.168.0.105"],
  devIndicators: false,
  // The research note PDF (/api/report/[ticker]) prints with Playwright's Chromium, which must not be bundled.
  serverExternalPackages: ["playwright", "playwright-core"]
};

export default nextConfig;
