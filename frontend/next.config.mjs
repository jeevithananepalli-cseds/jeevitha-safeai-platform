/** @type {import('next').NextConfig} */
const nextConfig = {
  // Fail the production build on type or lint errors instead of silently
  // shipping them — the build is part of our quality gate.
  typescript: { ignoreBuildErrors: false },
  eslint: { ignoreDuringBuilds: false },
  reactStrictMode: true,
};

export default nextConfig;
