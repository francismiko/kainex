import { defineConfig } from "vitepress";

export default defineConfig({
  title: "Kainex",
  description: "Open-source multi-market quantitative trading platform",

  appearance: "dark",

  themeConfig: {
    nav: [
      { text: "Guide", link: "/guide/getting-started" },
      { text: "API", link: "/api/rest" },
      { text: "Strategies", link: "/strategies/overview" },
    ],

    sidebar: {
      "/guide/": [
        {
          text: "Guide",
          items: [
            { text: "Getting Started", link: "/guide/getting-started" },
            { text: "Architecture", link: "/guide/architecture" },
            { text: "Configuration", link: "/guide/configuration" },
          ],
        },
      ],
      "/strategies/": [
        {
          text: "Strategies",
          items: [
            { text: "Overview", link: "/strategies/overview" },
            { text: "Built-in Strategies", link: "/strategies/built-in" },
            { text: "Custom Strategy Development", link: "/strategies/custom" },
          ],
        },
      ],
      "/api/": [
        {
          text: "API Reference",
          items: [
            { text: "REST API", link: "/api/rest" },
            { text: "WebSocket", link: "/api/websocket" },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: "github", link: "https://github.com/francismiko/kainex" },
    ],

    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright 2024-present Francis",
    },

    search: {
      provider: "local",
    },
  },
});
