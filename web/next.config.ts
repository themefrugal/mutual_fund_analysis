import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Reduce Turbopack memory pressure for dev
  experimental: {
    turbo: {
      // Use SWC transforms to reduce memory
      rules: {},
    },
  },
};

export default nextConfig;
