/** @type {import('next').NextConfig} */
const nextConfig = {
  // OneDrive/cloud folders can break webpack chunk writes; polling stabilizes dev HMR.
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      }
    }
    return config
  },
}

module.exports = nextConfig
