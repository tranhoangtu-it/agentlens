import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'AgentLens',
      description: 'Debug AI agents visually — self-hosted, open-source observability',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/tranhoangtu-it/agentlens' },
      ],
      sidebar: [
        { label: 'Getting Started', autogenerate: { directory: 'getting-started' } },
        { label: 'SDKs', autogenerate: { directory: 'sdks' } },
        { label: 'Integrations', autogenerate: { directory: 'integrations' } },
        { label: 'Features', autogenerate: { directory: 'features' } },
        { label: 'API Reference', autogenerate: { directory: 'api' } },
      ],
    }),
  ],
});
